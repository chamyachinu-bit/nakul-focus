"""
dashboard/app.py -- Local web dashboard (Flask)

Opens at http://127.0.0.1:5050
Run standalone:  python dashboard/app.py
Via CLI:         python main.py dashboard
"""

import sys
import os
import webbrowser
import threading
import time

# Allow imports from parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compat  # noqa: F401

from flask import Flask, render_template, jsonify, request
from datetime import datetime, date, timedelta
from database import get_connection, initialize_database, seed_defaults
from habit_tracker import (
    get_all_habits, get_today_logs, get_today_completion_percent,
    get_habit_streak, mark_habit,
)
from work_tracker import (
    get_today_summary, get_weekly_summary, get_bali_fund_total,
    log_bali_fund, log_work_session,
)
from focus_timer import get_today_deep_work_hours
from timetable import (
    get_today_entries, add_entry as tt_add, remove_entry as tt_remove,
    mark_entry as tt_mark, import_template as tt_import, update_entry as tt_update,
)
from config import BALI_FUND_TARGET, DASHBOARD_HOST, DASHBOARD_PORT

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "nakul-dev-secret-change-in-prod")

# On Vercel (serverless) there is no run_dashboard() call, so initialise here.
# The guard prevents a double-init when running locally via run_dashboard().
if os.environ.get("VERCEL") or os.environ.get("DATABASE_URL"):
    initialize_database()
    seed_defaults()

#  PAGES 

@app.route("/")
def index():
    return render_template("index.html")


#  DATA API 

@app.route("/api/dashboard")
def api_dashboard():
    """Full dashboard payload -- called by JS on load and every 60 s."""

    # Habits
    habits     = get_all_habits()
    today_logs = get_today_logs()
    habits_out = [
        {
            "id":        h["id"],
            "name":      h["name"],
            "category":  h["category"],
            "completed": today_logs.get(h["id"], False),
            "streak":    get_habit_streak(h["id"]),
        }
        for h in habits
    ]
    done_count  = sum(1 for h in habits_out if h["completed"])
    best_streak = max((h["streak"] for h in habits_out), default=0)

    # Work
    today_work = get_today_summary()
    week_work  = get_weekly_summary()

    # Focus sessions -- last 7 days
    conn = get_connection()
    focus_chart = []
    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        row = conn.execute(
            "SELECT SUM(duration_mins) FROM focus_sessions WHERE date=? AND completed=1",
            (d.isoformat(),)
        ).fetchone()
        focus_chart.append({
            "date":  d.isoformat(),
            "day":   d.strftime("%a"),
            "hours": round((row[0] or 0) / 60, 1),
        })

    # Weight -- last 30 entries
    weight_rows = conn.execute(
        "SELECT date, weight_kg FROM weight_logs ORDER BY date DESC LIMIT 30"
    ).fetchall()
    weight_data = [{"date": r["date"], "weight": r["weight_kg"]} for r in reversed(weight_rows)]

    # Latest mood
    mood_row = conn.execute(
        "SELECT mood_score, mood_label FROM mood_logs ORDER BY date DESC, time DESC LIMIT 1"
    ).fetchone()
    mood = dict(mood_row) if mood_row else {"mood_score": 0, "mood_label": "Not logged"}

    # Work sessions -- last 5 for recent activity
    recent_sessions = conn.execute(
        "SELECT project, duration_mins, work_type, income, date FROM work_sessions ORDER BY date DESC, start_time DESC LIMIT 5"
    ).fetchall()

    conn.close()

    # Bali fund
    bali_current = get_bali_fund_total()
    bali_pct     = round(min(100, bali_current / BALI_FUND_TARGET * 100), 1)

    return jsonify({
        "date": date.today().strftime("%A, %d %B %Y"),
        "habits": {
            "list":               habits_out,
            "completion_percent": get_today_completion_percent(),
            "done":               done_count,
            "total":              len(habits),
            "best_streak":        best_streak,
        },
        "work": {
            "today_hours":     round(today_work["total_mins"] / 60, 1),
            "today_income":    today_work["total_income"],
            "week_hours":      round(week_work["total_mins"] / 60, 1),
            "week_income":     week_work["total_income"],
            "deep_work_today": get_today_deep_work_hours(),
            "recent":          [dict(r) for r in recent_sessions],
        },
        "focus_chart": focus_chart,
        "weight": {
            "data":    weight_data,
            "current": weight_data[-1]["weight"] if weight_data else None,
            "target":  65,
        },
        "mood": mood,
        "bali": {
            "current":   bali_current,
            "target":    BALI_FUND_TARGET,
            "percent":   bali_pct,
            "remaining": max(0, BALI_FUND_TARGET - bali_current),
        },
    })


#  ACTION ENDPOINTS 

@app.route("/api/habits/<int:habit_id>/toggle", methods=["POST"])
def toggle_habit(habit_id):
    logs    = get_today_logs()
    current = logs.get(habit_id, False)
    mark_habit(habit_id, not current)
    return jsonify({"success": True, "completed": not current})


@app.route("/api/mood", methods=["POST"])
def log_mood_api():
    data   = request.get_json()
    score  = int(data.get("score", 3))
    labels = {1: "Struggling ", 2: "Low ", 3: "Okay ", 4: "Good ", 5: "On fire "}
    label  = labels.get(score, "Okay ")
    conn   = get_connection()
    conn.execute(
        "INSERT INTO mood_logs (mood_score, mood_label, time) VALUES (?,?,?)",
        (score, label, datetime.now().strftime("%H:%M"))
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True, "label": label})


@app.route("/api/weight", methods=["POST"])
def log_weight_api():
    data   = request.get_json()
    weight = data.get("weight")
    if not weight:
        return jsonify({"error": "weight required"}), 400
    conn = get_connection()
    conn.execute("INSERT INTO weight_logs (weight_kg) VALUES (?)", (float(weight),))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/bali", methods=["POST"])
def bali_api():
    data   = request.get_json()
    amount = data.get("amount")
    if not amount:
        return jsonify({"error": "amount required"}), 400
    log_bali_fund(float(amount), data.get("type", "deposit"), data.get("notes", ""))
    return jsonify({"success": True, "current": get_bali_fund_total()})


@app.route("/api/work", methods=["POST"])
def work_api():
    data = request.get_json()
    log_work_session(
        project       = data.get("project", "General"),
        duration_mins = int(data.get("duration_mins", 60)),
        work_type     = data.get("work_type", "freelance"),
        income        = float(data.get("income", 0)),
        notes         = data.get("notes", ""),
    )
    return jsonify({"success": True})


@app.route("/api/habits/<int:habit_id>/remove", methods=["POST"])
def remove_habit_api(habit_id):
    from habit_tracker import deactivate_habit
    deactivate_habit(habit_id)
    return jsonify({"success": True})


#  TIMETABLE API

@app.route("/api/timetable")
def timetable_api():
    return jsonify(get_today_entries())


@app.route("/api/timetable", methods=["POST"])
def timetable_add_api():
    data = request.get_json()
    name = data.get("name", "").strip()
    time_start = data.get("time_start", "").strip()
    if not name or not time_start:
        return jsonify({"error": "name and time_start required"}), 400
    new_id = tt_add(
        time_start = time_start,
        name       = name,
        category   = data.get("category", "work"),
        time_end   = data.get("time_end") or None,
        note       = data.get("note", ""),
    )
    return jsonify({"success": True, "id": new_id})


@app.route("/api/timetable/<int:entry_id>/toggle", methods=["POST"])
def timetable_toggle_api(entry_id):
    entries = get_today_entries()
    current = next((e["completed"] for e in entries if e["id"] == entry_id), False)
    tt_mark(entry_id, not current)
    return jsonify({"success": True, "completed": not current})


@app.route("/api/timetable/<int:entry_id>", methods=["DELETE"])
def timetable_delete_api(entry_id):
    tt_remove(entry_id)
    return jsonify({"success": True})


@app.route("/api/timetable/<int:entry_id>", methods=["PUT"])
def timetable_update_api(entry_id):
    data = request.get_json()
    tt_update(
        entry_id,
        time_start=data.get("time_start"),
        time_end=data.get("time_end"),
        name=data.get("name"),
        category=data.get("category"),
        note=data.get("note"),
    )
    return jsonify({"success": True})


@app.route("/api/timetable/import/<name>", methods=["POST"])
def timetable_import_api(name):
    try:
        count = tt_import(name)
        return jsonify({"success": True, "count": count})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── MILESTONES API ─────────────────────────────────────────────────────────────

@app.route("/api/milestones")
def milestones_get():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM milestones ORDER BY sort_order, id").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/milestones", methods=["POST"])
def milestones_add():
    data = request.get_json()
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO milestones (title, target_date, progress, color, sort_order) VALUES (?,?,?,?,?)",
        (data.get("title","New Milestone"), data.get("target_date",""),
         int(data.get("progress", 0)), data.get("color","var(--blue)"),
         int(data.get("sort_order", 99)))
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({"success": True, "id": new_id})


@app.route("/api/milestones/<int:mid>", methods=["PUT"])
def milestones_update(mid):
    data = request.get_json()
    fields, vals = [], []
    for col in ("title", "target_date", "color"):
        if col in data: fields.append(f"{col}=?"); vals.append(data[col])
    if "progress" in data: fields.append("progress=?"); vals.append(int(data["progress"]))
    if "sort_order" in data: fields.append("sort_order=?"); vals.append(int(data["sort_order"]))
    if fields:
        vals.append(mid)
        conn = get_connection()
        conn.execute(f"UPDATE milestones SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
        conn.close()
    return jsonify({"success": True})


@app.route("/api/milestones/<int:mid>", methods=["DELETE"])
def milestones_delete(mid):
    conn = get_connection()
    conn.execute("DELETE FROM milestones WHERE id=?", (mid,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


@app.route("/api/backup", methods=["POST"])
def backup_api():
    from database import backup_database
    path = backup_database()
    return jsonify({"success": True, "path": path})


@app.route("/api/timer/log", methods=["POST"])
def timer_log_api():
    data = request.get_json()
    from focus_timer import log_focus_session
    log_focus_session(
        duration_mins = int(data.get("duration_mins", 0)),
        mode          = data.get("mode", "pomodoro"),
        completed     = bool(data.get("completed", True)),
        project       = data.get("project") or None,
    )
    return jsonify({"success": True})


@app.route("/api/history")
def history_api():
    from_date = request.args.get("from", "")
    to_date   = request.args.get("to", "")
    if not from_date or not to_date:
        return jsonify([])

    conn = get_connection()

    # All distinct dates in range (union of all activity tables)
    dates = conn.execute("""
        SELECT DISTINCT date FROM (
            SELECT date FROM habit_logs
            UNION SELECT date FROM focus_sessions
            UNION SELECT date FROM work_sessions
            UNION SELECT date FROM weight_logs
            UNION SELECT date FROM mood_logs
            UNION SELECT date FROM timetable_logs
        ) WHERE date BETWEEN ? AND ? ORDER BY date DESC
    """, (from_date, to_date)).fetchall()

    from datetime import datetime as _dt
    result = []
    for (d,) in dates:
        label = _dt.strptime(d, "%Y-%m-%d").strftime("%A, %d %B %Y")

        # Habits
        all_habits = conn.execute("SELECT id, name, category FROM habits WHERE active=1 ORDER BY category, name").fetchall()
        habit_logs = {r["habit_id"]: bool(r["completed"]) for r in
                      conn.execute("SELECT habit_id, completed FROM habit_logs WHERE date=?", (d,)).fetchall()}
        habits_out = [{"name": h["name"], "category": h["category"],
                       "completed": habit_logs.get(h["id"], False)} for h in all_habits]

        # Focus
        focus_rows = conn.execute(
            "SELECT duration_mins, mode, completed, project FROM focus_sessions WHERE date=? ORDER BY start_time",
            (d,)).fetchall()
        focus_total = conn.execute(
            "SELECT SUM(duration_mins) FROM focus_sessions WHERE date=? AND completed=1", (d,)).fetchone()[0] or 0

        # Work
        work_rows = conn.execute(
            "SELECT project, duration_mins, work_type, income FROM work_sessions WHERE date=? ORDER BY start_time",
            (d,)).fetchall()
        work_income = conn.execute(
            "SELECT SUM(income) FROM work_sessions WHERE date=?", (d,)).fetchone()[0] or 0

        # Weight
        weight_row = conn.execute(
            "SELECT weight_kg FROM weight_logs WHERE date=? ORDER BY id DESC LIMIT 1", (d,)).fetchone()

        # Mood
        mood_row = conn.execute(
            "SELECT mood_score, mood_label FROM mood_logs WHERE date=? ORDER BY id DESC LIMIT 1", (d,)).fetchone()

        # Timetable
        tt_entries = conn.execute(
            "SELECT te.id, te.time_start, te.time_end, te.name, te.category, COALESCE(tl.completed,0) AS completed "
            "FROM timetable_entries te LEFT JOIN timetable_logs tl ON te.id=tl.entry_id AND tl.date=? "
            "WHERE te.active=1 ORDER BY te.time_start", (d,)).fetchall()
        tt_done = sum(1 for r in tt_entries if r["completed"])

        result.append({
            "date":  d,
            "label": label,
            "habits": {
                "list":  [dict(h) for h in habits_out],
                "done":  sum(1 for h in habits_out if h["completed"]),
                "total": len(habits_out),
            },
            "focus": {
                "sessions":   [dict(r) for r in focus_rows],
                "total_mins": focus_total,
            },
            "work": {
                "sessions":     [dict(r) for r in work_rows],
                "total_income": work_income,
            },
            "weight": {"value": weight_row["weight_kg"] if weight_row else None},
            "mood":   {"score": mood_row["mood_score"], "label": mood_row["mood_label"]} if mood_row else {"score": 0, "label": ""},
            "timetable": {
                "entries": [dict(r) for r in tt_entries],
                "done":    tt_done,
                "total":   len(tt_entries),
            },
        })

    conn.close()
    return jsonify(result)


@app.route("/api/timer/today")
def timer_today_api():
    conn = get_connection()
    rows = conn.execute(
        "SELECT duration_mins, mode, completed, project, start_time FROM focus_sessions WHERE date = date('now') ORDER BY start_time DESC"
    ).fetchall()
    total = conn.execute(
        "SELECT SUM(duration_mins) FROM focus_sessions WHERE date = date('now') AND completed = 1"
    ).fetchone()[0] or 0
    conn.close()
    return jsonify({
        "sessions": [dict(r) for r in rows],
        "total_mins": total,
    })


#  LAUNCHER 

def _open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")


def run_dashboard(open_browser: bool = True):
    initialize_database()
    seed_defaults()
    print(f"\n  [GO]  Dashboard: http://{DASHBOARD_HOST}:{DASHBOARD_PORT}")
    print(f"      Ctrl+C to stop.\n")
    if open_browser:
        threading.Thread(target=_open_browser, daemon=True).start()
    app.run(host=DASHBOARD_HOST, port=DASHBOARD_PORT, debug=False, use_reloader=False)


if __name__ == "__main__":
    run_dashboard()
