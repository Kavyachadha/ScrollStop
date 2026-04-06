# ─────────────────────────────────────────────
#  tracker.py  —  Main tracking loop
#  Run this to start tracking: python tracker.py
# ─────────────────────────────────────────────

import time
import threading
import tkinter as tk
from tkinter import messagebox
from datetime import date

import win32gui
from win10toast import ToastNotifier

from database import (
    setup_db,
    load_today_usage,
    save_usage,
    get_weekly_summary,
    get_previous_week_summary,
    get_limits,
)

# ── Init ──────────────────────────────────────

setup_db()

toaster      = ToastNotifier()

# Load limits from DB (seeded from config.py on first run)
TRACKED_SITES = get_limits()

today_usage  = load_today_usage()

# Cumulative seconds per site for today (picks up from DB on restart)
session_time = {site: today_usage.get(site, 0) for site in TRACKED_SITES}

# snooze_until[site] = timestamp after which the alert can fire again
# float("inf") means "don't alert again today"
snooze_until  = {}
previous_site = None
last_summary_day = None   # track which day we last sent the weekly summary


# ── Helpers ───────────────────────────────────

def get_active_window():
    window = win32gui.GetForegroundWindow()
    return win32gui.GetWindowText(window)


def detect_site(window_title):
    for site in TRACKED_SITES:
        if site.lower() in window_title.lower():
            return site
    return None


def seconds_to_hm(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


# ── Snooze alert popup ────────────────────────

def show_alert_with_snooze(site, spent):
    """Open a Tkinter popup in a background thread so the loop doesn't freeze."""
    def open_popup():
        root = tk.Tk()
        root.withdraw()   # hide the blank root window

        result = messagebox.askquestion(
            "Overuse Alert 🚨",
            f"You've spent {spent // 60} mins on {site} today!\n\n"
            f"Snooze alert for 10 minutes?",
            icon="warning"
        )

        if result == "yes":
            snooze_until[site] = time.time() + 600   # snooze 10 minutes
            print(f"[snooze] {site} alert snoozed for 10 minutes")
        else:
            snooze_until[site] = float("inf")   # dismissed — don't alert again today

        root.destroy()

    thread = threading.Thread(target=open_popup, daemon=True)
    thread.start()


# ── Weekly summary (fires every Sunday) ───────

def check_weekly_summary():
    global last_summary_day
    today = date.today()

    # Only on Sunday and only once per day
    if today.weekday() != 6 or last_summary_day == today:
        return

    last_summary_day = today
    this_week  = get_weekly_summary()
    last_week  = get_previous_week_summary()

    for site, seconds in this_week.items():
        prev = last_week.get(site, 0)
        mins = seconds // 60

        if prev > 0:
            change    = ((seconds - prev) / prev) * 100
            direction = "up" if change > 0 else "down"
            msg = f"{site}: {mins} mins this week, {abs(change):.0f}% {direction} vs last week"
        else:
            msg = f"{site}: {mins} mins this week"

        toaster.show_toast("Weekly Summary 📊", msg, duration=8)
        print(f"[weekly] {msg}")


# ── Main loop ─────────────────────────────────

print("Tracker started. Press Ctrl+C to stop.\n")

while True:
    # Refresh limits every tick so dashboard changes take effect immediately
    TRACKED_SITES = get_limits()

    # Also ensure session_time has an entry for any newly added site
    for site in TRACKED_SITES:
        if site not in session_time:
            session_time[site] = today_usage.get(site, 0)

    active_window = get_active_window()
    current_site  = detect_site(active_window)

    # Print a message whenever the user switches TO a tracked site
    if current_site and current_site != previous_site:
        print(f"\n▶  Switched to {current_site} | "
              f"Total today so far: {seconds_to_hm(session_time[current_site])}")

    if current_site:
        session_time[current_site] += 1
        limit = TRACKED_SITES[current_site]
        spent = session_time[current_site]

        print(f"   {current_site} | {seconds_to_hm(spent)} / {seconds_to_hm(limit)}")

        # Save to DB every 10 seconds
        if spent % 10 == 0:
            save_usage(current_site, spent)

        # Fire alert if over limit and not snoozed
        if spent >= limit:
            snooze_exp = snooze_until.get(current_site, 0)
            if time.time() > snooze_exp:
                show_alert_with_snooze(current_site, spent)
                snooze_until[current_site] = float("inf")   # prevent re-triggering until snoozed/dismissed

    else:
        print(f"   {active_window[:60]}  (not tracked)")

    previous_site = current_site

    # Weekly summary check (only does anything on Sundays)
    check_weekly_summary()

    time.sleep(1)