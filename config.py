# ─────────────────────────────────────────────
#  config.py  —  Initial default limits
#
#  These values are only used ONCE — on the very
#  first run — to seed the database.
#
#  After that, all limits are stored in the DB
#  and can be edited live from the dashboard at
#  http://localhost:5000
#
#  Values are in SECONDS.
# ─────────────────────────────────────────────

TRACKED_SITES = {
    "Instagram": 30 * 60,    # 30 minutes
    "YouTube":   60 * 60,    # 60 minutes
    "Netflix":   10 * 60,    # 10 minutes
    "Reddit":    10 * 60,    # 10 minutes
}