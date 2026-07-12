"""
timetable.py -- Daily schedule with per-day completion tracking
"""

import compat  # noqa: F401
from datetime import date
from database import get_connection


def _today() -> str:
    return date.today().isoformat()


def get_all_entries(active_only: bool = True) -> list:
    conn = get_connection()
    q = "SELECT * FROM timetable_entries"
    if active_only:
        q += " WHERE active = 1"
    q += " ORDER BY time_start"
    rows = conn.execute(q).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_logs() -> dict:
    conn = get_connection()
    rows = conn.execute(
        "SELECT entry_id, completed FROM timetable_logs WHERE date = ?", (_today(),)
    ).fetchall()
    conn.close()
    return {r["entry_id"]: bool(r["completed"]) for r in rows}


def get_today_entries() -> list:
    entries = get_all_entries()
    logs = get_today_logs()
    for e in entries:
        e["completed"] = logs.get(e["id"], False)
    return entries


def add_entry(time_start: str, name: str, category: str = "work",
              time_end: str = None, note: str = None, days: str = "daily") -> int:
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO timetable_entries (time_start, time_end, name, category, note, days)
        VALUES (?,?,?,?,?,?)
    """, (time_start, time_end, name, category, note or "", days))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"[OK]  Added: {time_start}  {name} [{category}]  #{new_id}")
    return new_id


def update_entry(entry_id: int, time_start: str = None, time_end: str = None,
                 name: str = None, category: str = None, note: str = None):
    conn = get_connection()
    fields, vals = [], []
    if time_start is not None: fields.append("time_start=?"); vals.append(time_start)
    if time_end   is not None: fields.append("time_end=?");   vals.append(time_end or None)
    if name       is not None: fields.append("name=?");       vals.append(name)
    if category   is not None: fields.append("category=?");   vals.append(category)
    if note       is not None: fields.append("note=?");       vals.append(note)
    if fields:
        vals.append(entry_id)
        conn.execute(f"UPDATE timetable_entries SET {', '.join(fields)} WHERE id=?", vals)
        conn.commit()
    conn.close()


def remove_entry(entry_id: int):
    conn = get_connection()
    conn.execute("UPDATE timetable_entries SET active = 0 WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()
    print(f"  Entry #{entry_id} removed from schedule.")


def mark_entry(entry_id: int, completed: bool = True):
    conn = get_connection()
    conn.execute("""
        INSERT INTO timetable_logs (entry_id, date, completed)
        VALUES (?,?,?)
        ON CONFLICT(entry_id, date) DO UPDATE SET completed = excluded.completed
    """, (entry_id, _today(), 1 if completed else 0))
    conn.commit()
    conn.close()


def get_completion_percent() -> float:
    entries = get_all_entries()
    if not entries:
        return 0.0
    logs = get_today_logs()
    done = sum(1 for e in entries if logs.get(e["id"], False))
    return round(done / len(entries) * 100, 1)


# ── TEMPLATES ──────────────────────────────────────────────────────────────────
# Each row: (time_start, time_end, name, category, note, days)

TEMPLATES = {
    "exam": [
        ("06:00", "06:10", "Wake up · Water · No phone",          "spiritual", "Phone across room. Drink water first.", "daily"),
        ("06:10", "06:30", "Morning Prayer + Gratitude",           "spiritual", "Connect with Krishna. Set intention.",  "daily"),
        ("06:30", "07:00", "Meditation — Morning (30 min)",        "spiritual", "MaitriBodh practice.",                 "daily"),
        ("06:45", "07:55", "Tennis",                               "health",    "5 mins from home.",                    "daily"),
        ("08:00", "10:30", "Deep Study Block 1",                   "work",      "Exam prep — focused, phone away.",     "daily"),
        ("10:30", "10:45", "Break + Healthy Snack",                "rest",      "15 min only.",                         "daily"),
        ("10:45", "13:00", "Deep Study Block 2",                   "work",      "Continue exam prep.",                  "daily"),
        ("13:00", "14:00", "Lunch (cook)",                         "health",    "Healthy. Cook when possible.",         "daily"),
        ("14:00", "16:00", "Freelance / Portfolio Work",           "work",      "Suhas collab, case studies.",          "daily"),
        ("16:00", "18:00", "Study Block 3 / Revision",             "work",      "Lighter revision or practice papers.", "daily"),
        ("18:00", "19:00", "Walk / Home Workout",                  "health",    "10k steps target.",                    "daily"),
        ("19:00", "20:00", "YGPT / MaitriBodh Seva",              "seva",      "Volunteer work, community.",           "daily"),
        ("20:00", "21:00", "Dinner (cook)",                        "health",    "Practice cooking.",                    "daily"),
        ("21:00", "21:30", "Evening Meditation (30 min)",          "spiritual", "Wind down. Reconnect.",                "daily"),
        ("21:30", "22:00", "Journal + Reflection",                 "personal",  "3 gratitudes + day reflection.",       "daily"),
        ("22:00", "23:00", "Wind down — Light reading only",       "rest",      "No screens. Atomic Habits, Gita.",    "daily"),
        ("23:00", None,    "Sleep",                                "rest",      "Phone across room. Target 7 hrs.",     "daily"),
    ],
    "syrma": [
        ("05:30", "05:45", "Wake up · Water · No phone",           "spiritual", "Earlier start for Syrma days.",       "daily"),
        ("05:45", "06:15", "Morning Prayer + Meditation (20 min)", "spiritual", "Shorter on office days.",             "daily"),
        ("06:15", "06:45", "Get ready + breakfast",                "health",    "Prep the night before helps.",        "daily"),
        ("06:45", "07:55", "Tennis (non-Syrma days)",              "health",    "On office days: skip or shorten.",    "daily"),
        ("08:00", "13:00", "Syrma Internship / Remote Work",       "work",      "Full focus. Learn everything.",       "daily"),
        ("13:00", "14:00", "Lunch break",                          "health",    "Healthy meal. Avoid junk.",           "daily"),
        ("17:30", "17:45", "Freelance outreach (15 min)",          "work",      "3 Loom audits/week. Daily LinkedIn.", "daily"),
        ("18:30", "19:30", "Workout / Walk",                       "health",    "Non-negotiable even if tired.",       "daily"),
        ("19:30", "20:30", "Seva / Personal time",                 "seva",      "YGPT work or personal goals.",        "daily"),
        ("20:30", "21:30", "Dinner + Cook",                        "health",    "Build cooking habit.",                "daily"),
        ("21:30", "22:00", "Evening Meditation (30 min)",          "spiritual", "Process the day.",                    "daily"),
        ("22:00", "22:30", "Journal + Wind down",                  "personal",  "3 gratitudes. Tomorrow plan.",        "daily"),
        ("23:00", None,    "Sleep",                                "rest",      "7 hours minimum.",                    "daily"),
    ],
    "4thyear": [
        ("06:00", "06:15", "Wake up · Water · No phone",           "spiritual", "Start right.",                        "daily"),
        ("06:15", "06:50", "Morning Prayer + Meditation (30 min)", "spiritual", "Full morning practice.",              "daily"),
        ("06:50", "07:55", "Tennis",                               "health",    "6:45–7:55 AM daily.",                 "daily"),
        ("08:00", "13:00", "College / Classes",                    "work",      "Attend everything. Placement matters.","daily"),
        ("13:00", "14:00", "Lunch + Brief rest",                   "health",    "",                                    "daily"),
        ("14:00", "16:00", "Deep Work — Freelance / Client",       "work",      "2 hrs focused. 2 clients max.",       "daily"),
        ("16:00", "16:30", "DSA Practice (30 min)",                "work",      "Placement backup. Consistent.",       "daily"),
        ("16:30", "16:45", "LinkedIn post / Outreach (15 min)",    "work",      "Weekly post. Daily Loom audits.",     "daily"),
        ("17:30", "19:30", "Workout + Walk",                       "health",    "10k steps. Gym when ready.",          "daily"),
        ("19:30", "20:30", "Seva + Social time",                   "seva",      "YGPT work. Don't isolate.",           "daily"),
        ("20:30", "21:30", "Dinner + Cook",                        "health",    "Cook 5 days/week target.",            "daily"),
        ("21:30", "22:00", "Evening Meditation (30 min)",          "spiritual", "",                                    "daily"),
        ("22:00", "22:30", "Journal + Gratitude",                  "personal",  "",                                    "daily"),
        ("23:00", None,    "Sleep",                                "rest",      "",                                    "daily"),
    ],
}


def import_template(name: str) -> int:
    """Deactivate all current entries and load the named template."""
    template = TEMPLATES.get(name)
    if not template:
        raise ValueError(f"Unknown template '{name}'. Available: {list(TEMPLATES)}")
    conn = get_connection()
    conn.execute("UPDATE timetable_entries SET active = 0")
    count = 0
    for row in template:
        conn.execute("""
            INSERT INTO timetable_entries (time_start, time_end, name, category, note, days)
            VALUES (?,?,?,?,?,?)
        """, row)
        count += 1
    conn.commit()
    conn.close()
    print(f"[OK]  Imported {count} entries from '{name}' template.")
    return count


# ── DISPLAY ────────────────────────────────────────────────────────────────────

def print_today():
    entries = get_today_entries()
    if not entries:
        print("\n  No timetable entries.")
        print("  Add one: nf timetable add")
        print("  Or import a template: nf timetable import exam\n")
        return

    from datetime import datetime as dt
    now_mins = dt.now().hour * 60 + dt.now().minute

    print("\n" + "=" * 72)
    print(f"  DAILY TIMETABLE  {date.today().strftime('%A, %d %B %Y')}")
    print("=" * 72)
    print(f"  {'ID':<4} {'TIME':<13} {'DONE':<6} {'CATEGORY':<12} ACTIVITY")
    print("-" * 72)

    for e in entries:
        done_mark = "[x]" if e["completed"] else "[ ]"
        t = e["time_start"]
        if e.get("time_end"):
            t += f"-{e['time_end']}"
        print(f"  {e['id']:<4} {t:<13} {done_mark:<6} {e['category'][:11]:<12} {e['name'][:36]}")

    done = sum(1 for e in entries if e["completed"])
    pct  = round(done / len(entries) * 100) if entries else 0
    print("=" * 72)
    print(f"  {done}/{len(entries)} complete  ({pct}%)")
    print("  Mark done:     nf timetable done <id>")
    print("  Add new block: nf timetable add\n")
