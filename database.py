# ─────────────────────────────────────────────
#  database.py  —  All database read/write logic
# ─────────────────────────────────────────────

import sqlite3
from datetime import date, timedelta


DB_PATH = "usage.db"


# ── Connection ────────────────────────────────

def get_connection():
    return sqlite3.connect(DB_PATH)


# ── Setup ─────────────────────────────────────

def setup_db():
    """Create tables if they don't exist yet."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            site           TEXT    NOT NULL,
            date           TEXT    NOT NULL,
            total_seconds  INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()

    setup_limits_table()  # seed limits from config on first run


# ── Daily usage ───────────────────────────────

def load_today_usage():
    """
    Load today's saved seconds so the tracker picks up where it left off
    after a restart. Returns { site: seconds }.
    """
    conn   = get_connection()
    cursor = conn.cursor()
    today  = str(date.today())

    cursor.execute(
        "SELECT site, total_seconds FROM usage_logs WHERE date = ?",
        (today,)
    )
    rows = cursor.fetchall()
    conn.close()

    return {row[0]: row[1] for row in rows}


def save_usage(site, total_seconds):
    """
    Upsert today's usage for a site.
    Updates if a row exists for today, inserts if not.
    """
    conn   = get_connection()
    cursor = conn.cursor()
    today  = str(date.today())

    cursor.execute(
        "SELECT id FROM usage_logs WHERE site = ? AND date = ?",
        (site, today)
    )
    existing = cursor.fetchone()

    if existing:
        cursor.execute(
            "UPDATE usage_logs SET total_seconds = ? WHERE site = ? AND date = ?",
            (total_seconds, site, today)
        )
    else:
        cursor.execute(
            "INSERT INTO usage_logs (site, date, total_seconds) VALUES (?, ?, ?)",
            (site, today, total_seconds)
        )

    conn.commit()
    conn.close()


# ── Streaks ───────────────────────────────────

def get_streak(site):
    """
    Count consecutive days (ending yesterday) where the user
    stayed under their limit for a given site.
    """
    limits = get_limits()
    limit  = limits.get(site)
    if not limit:
        return 0

    conn       = get_connection()
    cursor     = conn.cursor()
    streak     = 0
    check_date = date.today() - timedelta(days=1)   # start from yesterday

    while True:
        cursor.execute(
            "SELECT total_seconds FROM usage_logs WHERE site = ? AND date = ?",
            (site, check_date.isoformat())
        )
        row = cursor.fetchone()

        if row and row[0] < limit:
            streak    += 1
            check_date -= timedelta(days=1)
        else:
            break   # no data or went over limit — streak ends

    conn.close()
    return streak


# ── Weekly summaries ──────────────────────────

def get_weekly_summary():
    """Total seconds per site for the last 7 days."""
    conn   = get_connection()
    cursor = conn.cursor()
    since  = (date.today() - timedelta(days=6)).isoformat()

    cursor.execute(
        "SELECT site, SUM(total_seconds) FROM usage_logs WHERE date >= ? GROUP BY site",
        (since,)
    )
    rows = cursor.fetchall()
    conn.close()

    return {row[0]: row[1] for row in rows}


def get_previous_week_summary():
    """Total seconds per site for the 7 days before last week."""
    conn   = get_connection()
    cursor = conn.cursor()
    end    = (date.today() - timedelta(days=7)).isoformat()
    start  = (date.today() - timedelta(days=13)).isoformat()

    cursor.execute(
        "SELECT site, SUM(total_seconds) FROM usage_logs "
        "WHERE date >= ? AND date <= ? GROUP BY site",
        (start, end)
    )
    rows = cursor.fetchall()
    conn.close()

    return {row[0]: row[1] for row in rows}


# ── Dashboard data ────────────────────────────

def get_last_7_days_data():
    """
    Returns (days_list, data_dict) where data_dict is
    { date_str: { site: seconds } } for the last 7 days.
    """
    conn   = get_connection()
    cursor = conn.cursor()
    days   = [(date.today() - timedelta(days=i)).isoformat() for i in range(6, -1, -1)]

    placeholders = ",".join("?" * len(days))
    cursor.execute(
        f"SELECT site, date, total_seconds FROM usage_logs WHERE date IN ({placeholders})",
        days
    )
    rows = cursor.fetchall()
    conn.close()

    data = {day: {} for day in days}
    for site, date_val, seconds in rows:
        data[date_val][site] = seconds

    return days, data


# ── Site Limits ───────────────────────────────

def setup_limits_table():
    """Create limits table and seed from config if empty."""
    from config import TRACKED_SITES

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS site_limits (
            site          TEXT PRIMARY KEY,
            limit_seconds INTEGER NOT NULL
        )
    """)

    # Seed from config.py only if the table is empty
    cursor.execute("SELECT COUNT(*) FROM site_limits")
    if cursor.fetchone()[0] == 0:
        for site, seconds in TRACKED_SITES.items():
            cursor.execute(
                "INSERT INTO site_limits (site, limit_seconds) VALUES (?, ?)",
                (site, seconds)
            )

    conn.commit()
    conn.close()


def get_limits():
    """Returns { site: limit_seconds } from DB."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT site, limit_seconds FROM site_limits")
    rows = cursor.fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def set_limit(site, seconds):
    """Update or insert a limit for a site."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO site_limits (site, limit_seconds) VALUES (?, ?)
        ON CONFLICT(site) DO UPDATE SET limit_seconds = excluded.limit_seconds
    """, (site, seconds))
    conn.commit()
    conn.close()