"""
work_tracker.py -- Log work sessions and income

Track freelance, study, seva, and internship work.
Monitor monthly income progress toward financial goals.
Manage the Bali fund separately.
"""

import compat  # noqa: F401
from datetime import datetime, date, timedelta
from database import get_connection
from config import WORK_TYPES, BALI_FUND_TARGET


def _bar(pct: float, width: int = 40) -> str:
    """Return an ASCII progress bar."""
    filled = int(pct / 100 * width)
    return "#" * filled + "." * (width - filled)


# ─── WORK SESSIONS ───────────────────────────────────────────────────────────

def log_work_session(
    project:       str,
    duration_mins: int,
    work_type:     str   = "freelance",
    income:        float = 0,
    notes:         str   = None,
) -> int:
    """
    Record a completed work session.

    Args:
        project:       Name of project or task
        duration_mins: Duration in minutes
        work_type:     One of WORK_TYPES
        income:        Rs. earned (0 for study / seva)
        notes:         What you did

    Returns: new row id
    """
    if work_type not in WORK_TYPES:
        raise ValueError(f"work_type must be one of {WORK_TYPES}")

    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO work_sessions (project, duration_mins, work_type, income, notes, start_time)
        VALUES (?,?,?,?,?,?)
    """, (project, duration_mins, work_type, income, notes, datetime.now().isoformat()))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()

    hrs = duration_mins / 60
    print(f"[OK]  Work logged: {project} -- {hrs:.1f}h [{work_type}]")
    if income > 0:
        print(f"      Income: Rs.{income:,.0f}")
    return new_id


def get_recent_sessions(limit: int = 10) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM work_sessions ORDER BY date DESC, start_time DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── SUMMARIES ───────────────────────────────────────────────────────────────

def get_today_summary() -> dict:
    conn = get_connection()
    rows = conn.execute("""
        SELECT work_type,
               SUM(duration_mins) AS mins,
               SUM(income)        AS income,
               COUNT(*)           AS sessions
        FROM work_sessions WHERE date = date('now')
        GROUP BY work_type
    """).fetchall()
    conn.close()

    by_type      = {r["work_type"]: {"mins": r["mins"], "income": r["income"], "sessions": r["sessions"]}
                    for r in rows}
    total_mins   = sum(v["mins"]   for v in by_type.values())
    total_income = sum(v["income"] for v in by_type.values())

    return {
        "date":         date.today().isoformat(),
        "by_type":      by_type,
        "total_mins":   total_mins,
        "total_income": total_income,
    }


def get_weekly_summary() -> dict:
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    conn = get_connection()

    by_day = conn.execute("""
        SELECT date, work_type, SUM(duration_mins) AS mins, SUM(income) AS income
        FROM work_sessions WHERE date >= ?
        GROUP BY date, work_type ORDER BY date
    """, (week_start,)).fetchall()

    totals = conn.execute("""
        SELECT SUM(duration_mins) AS mins, SUM(income) AS income
        FROM work_sessions WHERE date >= ?
    """, (week_start,)).fetchone()
    conn.close()

    return {
        "week_start":   week_start,
        "total_mins":   totals["mins"]   or 0,
        "total_income": totals["income"] or 0,
        "by_day":       [dict(r) for r in by_day],
    }


def get_monthly_income(year: int = None, month: int = None) -> dict:
    year  = year  or date.today().year
    month = month or date.today().month

    conn = get_connection()
    projects = conn.execute("""
        SELECT project, work_type,
               SUM(duration_mins) AS mins,
               SUM(income)        AS income,
               COUNT(*)           AS sessions
        FROM work_sessions
        WHERE strftime('%Y',date)=? AND strftime('%m',date)=?
        GROUP BY project, work_type
        ORDER BY income DESC
    """, (str(year), f"{month:02d}")).fetchall()

    total = conn.execute("""
        SELECT SUM(income) FROM work_sessions
        WHERE strftime('%Y',date)=? AND strftime('%m',date)=?
    """, (str(year), f"{month:02d}")).fetchone()[0] or 0
    conn.close()

    return {
        "year":         year,
        "month":        month,
        "total_income": total,
        "projects":     [dict(r) for r in projects],
    }


# ─── BALI FUND ───────────────────────────────────────────────────────────────

def log_bali_fund(amount: float, entry_type: str = "deposit", notes: str = None):
    """Add or subtract from the Bali fund."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO bali_fund (amount, entry_type, notes) VALUES (?,?,?)",
        (amount, entry_type, notes)
    )
    conn.commit()
    conn.close()

    current   = get_bali_fund_total()
    pct       = min(100, current / BALI_FUND_TARGET * 100)
    remaining = max(0, BALI_FUND_TARGET - current)

    print(f"\n  Bali Fund:  Rs.{current:,.0f}  /  Rs.{BALI_FUND_TARGET:,.0f}")
    print(f"  [{_bar(pct, 30)}]  {pct:.1f}%")
    print(f"  Rs.{remaining:,.0f} to go -- December 2026.\n")


def get_bali_fund_total() -> float:
    conn = get_connection()
    row = conn.execute("""
        SELECT SUM(CASE WHEN entry_type='deposit' THEN amount ELSE -amount END)
        FROM bali_fund
    """).fetchone()
    conn.close()
    return row[0] or 0.0


# ─── DISPLAY ─────────────────────────────────────────────────────────────────

def print_work_summary(period: str = "today"):
    if period == "today":
        s   = get_today_summary()
        hrs = s["total_mins"] / 60

        print("\n" + "=" * 58)
        print(f"  TODAY'S WORK -- {s['date']}")
        print("=" * 58)

        if not s["by_type"]:
            print("  Nothing logged yet. Run: python main.py work log")
        else:
            for wtype, data in s["by_type"].items():
                h   = data["mins"] / 60
                inc = f"  Rs.{data['income']:,.0f}" if data["income"] > 0 else ""
                print(f"  {wtype:<18} {h:.1f}h  ({data['sessions']} sessions){inc}")

        print("-" * 58)
        print(f"  Total: {hrs:.1f} hours   Income: Rs.{s['total_income']:,.0f}")
        print("=" * 58 + "\n")

    elif period == "week":
        s   = get_weekly_summary()
        hrs = s["total_mins"] / 60

        print("\n" + "=" * 58)
        print(f"  WEEKLY WORK (from {s['week_start']})")
        print("=" * 58)
        print(f"  Total: {hrs:.1f} hours   Income: Rs.{s['total_income']:,.0f}")
        print("=" * 58 + "\n")

    elif period == "month":
        s = get_monthly_income()

        print("\n" + "=" * 62)
        print(f"  MONTHLY INCOME -- {s['year']}-{s['month']:02d}")
        print("=" * 62)

        if not s["projects"]:
            print("  No work logged this month.")
        else:
            for p in s["projects"]:
                h = p["mins"] / 60
                if p["income"] > 0:
                    print(f"  {p['project'][:28]:<28}  {h:.1f}h   Rs.{p['income']:,.0f}")

        print("-" * 62)
        print(f"  TOTAL: Rs.{s['total_income']:,.0f}")
        print("=" * 62 + "\n")

    elif period == "bali":
        current   = get_bali_fund_total()
        pct       = min(100, current / BALI_FUND_TARGET * 100)
        remaining = max(0, BALI_FUND_TARGET - current)

        print("\n" + "=" * 62)
        print("  BALI FUND -- December 2026")
        print("=" * 62)
        print(f"  Saved:     Rs.{current:,.0f}")
        print(f"  Target:    Rs.{BALI_FUND_TARGET:,.0f}")
        print(f"  Remaining: Rs.{remaining:,.0f}")
        print(f"\n  [{_bar(pct, 40)}]  {pct:.1f}%\n")
        print("  Add money: python main.py bali add <amount>")
        print("=" * 62 + "\n")
