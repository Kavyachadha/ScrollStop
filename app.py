# ─────────────────────────────────────────────
#  app.py  —  Flask dashboard server
#  Run with: python app.py
#  Then open: http://localhost:5000
# ─────────────────────────────────────────────

from flask import Flask, render_template_string, request, redirect
from database import get_last_7_days_data, get_streak, get_limits, set_limit

app = Flask(__name__)


def seconds_to_hm(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m}m"
    elif m > 0:
        return f"{m}m {s}s"
    return f"{s}s"


TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScrollStop</title>
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg:        #121212;
            --surface:   #2c2c2c;
            --border:    #353a3e;
            --accent:    #acaba9;
            --accent2:   #75706f;
            --text:      #eaeaea;
            --muted:     #eaeaea;
            --over:      #ff4e8b;
            --safe:      #4effa3;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            background: var(--bg);
            color: var(--text);
            font-family: 'Syne', sans-serif;
            min-height: 100vh;
            padding: 48px 40px;
        }

        /* ── noise texture overlay ── */
        body::before {
            content: '';
            position: fixed;
            inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E");
            pointer-events: none;
            z-index: 0;
        }

        .wrapper { position: relative; z-index: 1; max-width: 1100px; margin: 0 auto; }

        /* ── Header ── */
        header {
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            margin-bottom: 56px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 24px;
        }

        header h1 {
            font-size: 36px;
            font-weight: 800;
            letter-spacing: -1px;
            background: linear-gradient(135deg, #fff 30%, var(--accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        header .date {
            font-family: 'DM Mono', monospace;
            font-size: 13px;
            color: var(--muted);
        }

        /* ── Section label ── */
        .section-label {
            font-family: 'DM Mono', monospace;
            font-size: 11px;
            letter-spacing: 2px;
            color: var(--muted);
            text-transform: uppercase;
            margin-bottom: 20px;
        }

        /* ── Cards ── */
        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 56px;
        }

        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px 24px;
            position: relative;
            overflow: hidden;
            transition: border-color 0.2s;
        }

        .card:hover { border-color: var(--accent); }

        /* glow blob behind card */
        .card::after {
            content: '';
            position: absolute;
            width: 80px;
            height: 80px;
            background: var(--accent);
            border-radius: 50%;
            top: -20px;
            right: -20px;
            opacity: 0.07;
            filter: blur(20px);
        }

        .card .site {
            font-size: 12px;
            font-family: 'DM Mono', monospace;
            color: var(--muted);
            letter-spacing: 1px;
            text-transform: uppercase;
            margin-bottom: 12px;
        }

        .card .time {
            font-size: 30px;
            font-weight: 800;
            letter-spacing: -1px;
            color: var(--text);
            margin-bottom: 4px;
        }

        .card .time.over  { color: var(--over); }
        .card .time.safe  { color: var(--safe); }

        .card .limit-line {
            font-family: 'DM Mono', monospace;
            font-size: 11px;
            color: var(--muted);
            margin-bottom: 14px;
        }

        .card .streak {
            display: inline-flex;
            align-items: center;
            gap: 5px;
            background: #acaba9;
            border: 1px solid #353a3e;
            border-radius: 20px;
            padding: 4px 10px;
            font-size: 12px;
            font-family: 'DM Mono', monospace;
            color: #0e1424;
        }

        /* progress bar */
        .progress-track {
            height: 3px;
            background: var(--border);
            border-radius: 2px;
            margin: 14px 0 16px;
            overflow: hidden;
        }
        .progress-fill {
            height: 100%;
            border-radius: 2px;
            background: var(--accent);
            transition: width 0.4s ease;
        }
        .progress-fill.over { background: var(--over); }

        /* ── 7-day table ── */
        .table-wrap {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 56px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'DM Mono', monospace;
            font-size: 13px;
        }

        thead th {
            background: #0a0a14;
            padding: 14px 20px;
            text-align: left;
            color: var(--muted);
            font-weight: 500;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border);
        }

        tbody td {
            padding: 13px 20px;
            border-top: 1px solid var(--border);
            color: var(--muted);
        }

        tbody tr:hover td { background: rgba(94,78,255,0.04); }

        td.date-cell { color: var(--text); font-weight: 500; }
        td.has-data  { color: var(--accent2); }
        td.over-limit { color: var(--over); font-weight: 600; }

        /* ── Edit limits form ── */
        .limit-input {
            background: #0a0a14;
            border: 1px solid var(--border);
            color: var(--text);
            border-radius: 8px;
            padding: 6px 10px;
            font-family: 'DM Mono', monospace;
            font-size: 13px;
            width: 90px;
            transition: border-color 0.2s;
        }
        .limit-input:focus {
            outline: none;
            border-color: var(--accent);
        }

        .save-btn {
            background: var(--accent);
            color: #fff;
            border: none;
            border-radius: 8px;
            padding: 6px 16px;
            cursor: pointer;
            font-family: 'Syne', sans-serif;
            font-size: 13px;
            font-weight: 600;
            transition: opacity 0.2s;
        }
        .save-btn:hover { opacity: 0.85; }

        .form-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }

        /* ── auto-refresh note ── */
        .refresh-note {
            font-family: 'DM Mono', monospace;
            font-size: 11px;
            color: var(--muted);
            text-align: right;
            margin-top: 24px;
        }

        /* ── flash message ── */
        .flash {
            font-family: 'DM Mono', monospace;
            font-size: 12px;
            color: var(--safe);
            background: rgba(78,255,163,0.08);
            border: 1px solid rgba(78,255,163,0.2);
            border-radius: 8px;
            padding: 10px 16px;
            margin-bottom: 28px;
            display: inline-block;
        }
    </style>
</head>
<body>
<div class="wrapper">

    <header>
        <h1>ScrollStop</h1>
        <span class="date">{{ today }}</span>
    </header>

    {% if saved %}
    <div class="flash">✓ Limit updated — tracker will pick it up within 1 second.</div>
    {% endif %}

    <!-- ── Today's cards ── -->
    <p class="section-label">Today's Usage</p>
    <div class="cards">
        {% for site in all_sites %}
        {% set spent   = today_data.get(site, 0) %}
        {% set limit   = limits[site] %}
        {% set pct     = [[(spent / limit * 100)|int, 0]|max, 100]|min %}
        {% set streak  = streaks[site] %}
        <div class="card">
            <div class="site">{{ site }}</div>
            <div class="time {% if spent >= limit %}over{% elif spent > 0 %}safe{% endif %}">
                {{ spent | hm }}
            </div>
            <div class="limit-line">limit {{ limit | hm }}</div>
            <div class="progress-track">
                <div class="progress-fill {% if spent >= limit %}over{% endif %}"
                     style="width: {{ pct }}%"></div>
            </div>
            {% if streak > 0 %}
            <div class="streak">🔥 {{ streak }}-day streak</div>
            {% else %}
            <div class="streak" style="opacity:0.4">— no streak yet</div>
            {% endif %}
        </div>
        {% endfor %}
    </div>

    <!-- ── Edit Limits ── -->
    <p class="section-label">Edit Time Limits</p>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Site</th>
                    <th>Current Limit</th>
                    <th>New Limit (minutes)</th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                {% for site in all_sites %}
                <tr>
                    <td class="date-cell">{{ site }}</td>
                    <td>{{ limits[site] | hm }}</td>
                    <td colspan="2">
                        <form method="POST" action="/set-limit">
                            <input type="hidden" name="site" value="{{ site }}">
                            <div class="form-row">
                                <input
                                    type="number"
                                    name="minutes"
                                    min="1"
                                    value="{{ (limits[site] // 60) }}"
                                    class="limit-input"
                                >
                                <button type="submit" class="save-btn">Save</button>
                            </div>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    </p>

    <!-- ── 7-day table ── -->
    <p class="section-label">Last 7 Days</p>
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    {% for site in all_sites %}<th>{{ site }}</th>{% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for day in days %}
                <tr>
                    <td class="date-cell">{{ day }}</td>
                    {% for site in all_sites %}
                    {% set secs  = data[day].get(site, 0) %}
                    {% set limit = limits[site] %}
                    <td class="{% if secs >= limit %}over-limit{% elif secs > 0 %}has-data{% endif %}">
                        {{ secs | hm if secs > 0 else "—" }}
                    </td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

</div>

<script>
    setTimeout(() => location.reload(), 60000);
</script>
</body>
</html>
"""


@app.template_filter("hm")
def hm_filter(seconds):
    return seconds_to_hm(seconds)


@app.route("/")
def dashboard():
    saved = request.args.get("saved", False)

    days, data = get_last_7_days_data()
    limits     = get_limits()

    all_sites  = sorted(limits.keys())
    today      = days[-1]
    today_data = data.get(today, {})
    streaks    = {site: get_streak(site) for site in all_sites}

    from datetime import date as dt
    today_label = dt.today().strftime("%A, %B %d %Y")

    return render_template_string(
        TEMPLATE,
        days       = days,
        data       = data,
        all_sites  = all_sites,
        today_data = today_data,
        limits     = limits,
        streaks    = streaks,
        today      = today_label,
        saved      = saved,
    )


@app.route("/set-limit", methods=["POST"])
def update_limit():
    site    = request.form.get("site")
    minutes = request.form.get("minutes", type=int)
    if site and minutes and minutes > 0:
        set_limit(site, minutes * 60)
    return redirect("/?saved=1")


if __name__ == "__main__":
    app.run(debug=True, port=5000)