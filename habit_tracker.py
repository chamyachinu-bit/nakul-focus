"""
habit_tracker.py -- Daily habits with streak tracking

Tracks Nakul's 13 default habits. Calculates streaks, weekly rates,
and today's completion percentage. All data lives in SQLite.
"""

import compat  # noqa: F401
from datetime import date, timedelta
from database import get_connection


#  HELPERS 

def _today() -> str:
    return date.today().isoformat()


#  READ 

def get_all_habits(active_only: bool = True) -> list:
    conn = get_connection()
    query = "SELECT * FROM habits"
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY category, name"
    rows = conn.execute(query).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_today_logs() -> dict:
    """Return {habit_id: completed (bool)} for today."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT habit_id, completed FROM habit_logs WHERE date = ?", (_today(),)
    ).fetchall()
    conn.close()
    return {r["habit_id"]: bool(r["completed"]) for r in rows}


def get_habit_streak(habit_id: int) -> int:
    """
    Count consecutive days (ending today or yesterday) on which
    this habit was completed. Returns 0 if never completed.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT date FROM habit_logs WHERE habit_id=? AND completed=1 ORDER BY date DESC LIMIT 365",
        (habit_id,)
    ).fetchall()
    conn.close()

    completed = {r["date"] for r in rows}
    if not completed:
        return 0

    streak = 0
    day = date.today()
    # If today isn't logged yet, start streak check from yesterday
    if day.isoformat() not in completed:
        day -= timedelta(days=1)

    while day.isoformat() in completed:
        streak += 1
        day -= timedelta(days=1)

    return streak


def get_today_completion_percent() -> float:
    habits = get_all_habits()
    if not habits:
        return 0.0
    logs = get_today_logs()
    done = sum(1 for h in habits if logs.get(h["id"], False))
    return round(done / len(habits) * 100, 1)


def get_completion_rates(days: int = 7) -> dict:
    """Return {habit_id: rate (0.0-1.0)} for the last N days."""
    conn = get_connection()
    since = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT habit_id,
               SUM(CASE WHEN completed=1 THEN 1 ELSE 0 END) AS done,
               COUNT(*) AS total
        FROM habit_logs WHERE date >= ?
        GROUP BY habit_id
    """, (since,)).fetchall()
    conn.close()
    return {r["habit_id"]: round(r["done"] / r["total"], 2) if r["total"] else 0 for r in rows}


#  WRITE 

def mark_habit(habit_id: int, completed: bool = True, notes: str = None):
    """Upsert today's log entry for a habit."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO habit_logs (habit_id, date, completed, notes)
        VALUES (?,?,?,?)
        ON CONFLICT(habit_id, date) DO UPDATE SET
            completed = excluded.completed,
            notes     = excluded.notes
    """, (habit_id, _today(), 1 if completed else 0, notes))
    conn.commit()
    conn.close()


def add_habit(name: str, category: str = "general") -> int:
    conn = get_connection()
    cur = conn.execute("INSERT INTO habits (name, category) VALUES (?,?)", (name, category))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"[OK]  Habit added: '{name}' [{category}] -- id #{new_id}")
    return new_id


def deactivate_habit(habit_id: int):
    conn = get_connection()
    conn.execute("UPDATE habits SET active=0 WHERE id=?", (habit_id,))
    conn.commit()
    conn.close()
    print(f"  Habit #{habit_id} deactivated.")


#  DISPLAY 

def _bar(filled: int, total: int) -> str:
    """Return an ASCII progress bar string."""
    f = int(filled / total * 32) if total else 0
    return "#" * f + "." * (32 - f)


def print_today_checklist():
    habits = get_all_habits()
    logs   = get_today_logs()

    print("\n" + "=" * 58)
    print(f"  DAILY HABITS -- {date.today().strftime('%A, %d %B %Y')}")
    print("=" * 58)

    current_cat = None
    for h in habits:
        if h["category"] != current_cat:
            current_cat = h["category"]
            print(f"\n  [{current_cat.upper()}]")

        done    = logs.get(h["id"], False)
        streak  = get_habit_streak(h["id"])
        s_label = f"  streak:{streak}" if streak >= 3 else (f"  {streak}d" if streak > 0 else "")
        box     = "[x]" if done else "[ ]"

        print(f"    {box} [{h['id']:2d}]  {h['name']:<36}{s_label}")

    pct        = get_today_completion_percent()
    done_count = sum(1 for h in habits if logs.get(h["id"], False))

    print("\n" + "-" * 58)
    print(f"  [{_bar(done_count, len(habits))}] {pct}%")
    print(f"  {done_count}/{len(habits)} habits done today")
    print("=" * 58)
    print("  Mark done:  python main.py habits done <id> [id2 ...]")
    print("  Example:    python main.py habits done 1 3 5\n")


def print_weekly_summary():
    habits = get_all_habits()
    rates  = get_completion_rates(days=7)
    today  = date.today()
    week_start = (today - timedelta(days=6)).isoformat()

    print("\n" + "=" * 62)
    print(f"  WEEKLY SUMMARY  ({week_start} -> {today.isoformat()})")
    print("=" * 62)

    by_cat: dict = {}
    for h in habits:
        by_cat.setdefault(h["category"], []).append(h)

    for cat, cat_habits in by_cat.items():
        print(f"\n  [{cat.upper()}]")
        for h in cat_habits:
            rate    = rates.get(h["id"], 0)
            pct     = int(rate * 100)
            f       = int(rate * 18)
            bar     = "#" * f + "." * (18 - f)
            streak  = get_habit_streak(h["id"])
            s_label = f"  streak:{streak}" if streak >= 3 else ""
            print(f"    [{bar}] {pct:3d}%  {h['name'][:32]}{s_label}")

    print("\n" + "=" * 62 + "\n")
