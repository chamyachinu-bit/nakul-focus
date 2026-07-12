"""
main.py -- Nakul Focus System -- single CLI entry point

QUICK REFERENCE

python main.py setup                    First-time setup
python main.py status                   Overall system status

FOCUS TIMER
python main.py timer                    Interactive mode (choose duration)
python main.py timer pomodoro           25 min focus
python main.py timer deep               50 min focus
python main.py timer flow               90 min focus

BLOCKER
python main.py block                    Block sites now
python main.py unblock                  Unblock (password + 3 min wait)
python main.py block status             Show blocker status

HABITS
python main.py habits                   Today's checklist
python main.py habits done 1 3 5        Mark habits 1, 3, 5 as done
python main.py habits add               Add a new habit
python main.py habits week              Weekly summary

WORK
python main.py work log                 Log a work session (interactive)
python main.py work today               Today's work summary
python main.py work week                Weekly summary
python main.py work month               Monthly income
python main.py work recent              Last 10 sessions

BALI FUND
python main.py bali                     Show fund status
python main.py bali add 5000            Add Rs.5000
python main.py bali spend 500           Record an expense

REMINDERS
python main.py reminders                List all reminders
python main.py reminders add            Add a custom reminder
python main.py reminders off <id>       Disable a reminder
python main.py reminders on <id>        Enable a reminder
python main.py reminders delete <id>    Delete a reminder
python main.py reminders start          Run reminder service (stays open)

WEIGHT
python main.py weight 74.5              Log today's weight
python main.py weight log               Interactive weight log

MOOD
python main.py mood                     Log current mood (1-5)

DASHBOARD
python main.py dashboard                Open browser dashboard
"""

import sys
import os

# Ensure imports resolve from this directory regardless of where CLI is called from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import compat  # noqa: F401 -- UTF-8 fix for Windows console

from database import initialize_database, seed_defaults

# Init DB on every run -- safe, fast, idempotent
initialize_database()
seed_defaults()


#  HELPERS 

def _require_arg(args: list, position: int, name: str) -> str:
    if len(args) <= position:
        print(f"[ERR]  Missing argument: {name}")
        sys.exit(1)
    return args[position]


def _print_help():
    print(__doc__)


#  SUBCOMMAND HANDLERS 

def cmd_timer(args):
    from focus_timer import FocusTimer, run_interactive

    if not args:
        run_interactive()
        return

    mode_aliases = {
        "pomodoro": "pomodoro", "p": "pomodoro", "25": "pomodoro",
        "deep":     "deep",     "d": "deep",     "50": "deep",
        "flow":     "flow",     "f": "flow",     "90": "flow",
    }
    mode_key = args[0].lower()
    mode = mode_aliases.get(mode_key)

    if not mode:
        print(f"[ERR]  Unknown mode '{args[0]}'. Use: pomodoro, deep, or flow")
        sys.exit(1)

    project = args[1] if len(args) > 1 else None
    FocusTimer(mode=mode, project=project).start()


def cmd_block(args):
    from website_blocker import block_sites, get_status

    if args and args[0] == "status":
        s = get_status()
        blocked   = "[X] BLOCKED"  if s["blocked"]     else "[OK] OPEN"
        schedule  = "[ALARM] ACTIVE"   if s["in_schedule"]  else " INACTIVE"
        print(f"\n  Site status:    {blocked}")
        print(f"  Schedule:       {schedule} ({s['block_start']}:00-{s['block_end']}:00)")
        print(f"  Sites in list:  {s['sites_count']}\n")
        return

    if args and args[0] == "setpassword":
        import hashlib, getpass
        from database import set_setting
        p1 = getpass.getpass("  New override password: ")
        p2 = getpass.getpass("  Confirm password:      ")
        if p1 != p2:
            print("[ERR]  Passwords do not match.")
            sys.exit(1)
        if len(p1) < 8:
            print("[ERR]  Password must be at least 8 characters.")
            sys.exit(1)
        h = hashlib.sha256(p1.encode()).hexdigest()
        set_setting("override_password_hash", h)
        print("[OK]  Override password updated.")
        return

    block_sites()


def cmd_unblock(args):
    from website_blocker import override_unblock, unblock_sites
    override_unblock()


def cmd_habits(args):
    from habit_tracker import (
        print_today_checklist, print_weekly_summary,
        mark_habit, add_habit, get_all_habits
    )

    if not args or args[0] == "list":
        print_today_checklist()
        return

    if args[0] == "done":
        ids = args[1:]
        if not ids:
            print("[ERR]  Provide habit IDs. Example: python main.py habits done 1 3 5")
            sys.exit(1)
        for id_str in ids:
            try:
                mark_habit(int(id_str), completed=True)
                print(f"  [OK]  Habit #{id_str} marked complete")
            except ValueError:
                print(f"  [WARN]   '{id_str}' is not a valid ID -- skipping")
        print()
        return

    if args[0] == "undone":
        ids = args[1:]
        for id_str in ids:
            try:
                mark_habit(int(id_str), completed=False)
                print(f"    Habit #{id_str} marked incomplete")
            except ValueError:
                print(f"  [WARN]   '{id_str}' is not a valid ID -- skipping")
        return

    if args[0] == "add":
        name = input("  Habit name: ").strip()
        if not name:
            print("[ERR]  Name cannot be empty.")
            sys.exit(1)
        print("  Category options: spiritual, health, work, general")
        category = input("  Category (default: general): ").strip() or "general"
        add_habit(name, category)
        return

    if args[0] == "week":
        print_weekly_summary()
        return

    if args[0] in ("remove", "delete", "rm"):
        ids = args[1:]
        if not ids:
            print("[ERR]  Provide habit IDs. Example: nf habits remove 5")
            sys.exit(1)
        for id_str in ids:
            try:
                from habit_tracker import deactivate_habit
                deactivate_habit(int(id_str))
            except ValueError:
                print(f"  [WARN]  '{id_str}' is not a valid ID -- skipping")
        return

    print(f"[ERR]  Unknown habits command '{args[0]}'")
    print("  Usage: habits | habits done <id>... | habits add | habits week | habits remove <id>")


def cmd_work(args):
    from work_tracker import (
        log_work_session, print_work_summary,
        get_recent_sessions
    )
    from config import WORK_TYPES

    if not args or args[0] == "today":
        print_work_summary("today")
        return

    if args[0] == "week":
        print_work_summary("week")
        return

    if args[0] == "month":
        print_work_summary("month")
        return

    if args[0] == "recent":
        sessions = get_recent_sessions(10)
        if not sessions:
            print("No work sessions logged yet.")
            return
        print("\n" + "=" * 70)
        print(f"  {'DATE':<12} {'PROJECT':<22} {'TYPE':<15} {'HRS':<6} INCOME")
        print("=" * 70)
        for s in sessions:
            h   = s["duration_mins"] / 60
            inc = f"Rs.{s['income']:,.0f}" if s["income"] > 0 else "--"
            print(f"  {s['date']:<12} {s['project'][:20]:<22} {s['work_type']:<15} {h:<6.1f} {inc}")
        print("=" * 70 + "\n")
        return

    if args[0] == "log":
        print("\n  [LOG]  LOG WORK SESSION")
        print("  ")
        project = input("  Project name: ").strip()
        if not project:
            print("[ERR]  Project name required.")
            sys.exit(1)

        try:
            hours_str = input("  Duration in hours (e.g. 1.5): ").strip()
            duration_mins = int(float(hours_str) * 60)
        except ValueError:
            print("[ERR]  Invalid duration.")
            sys.exit(1)

        print(f"  Work types: {', '.join(WORK_TYPES)}")
        work_type = input("  Type (default: freelance): ").strip() or "freelance"

        income_str = input("  Income earned Rs. (0 if none): ").strip() or "0"
        try:
            income = float(income_str)
        except ValueError:
            income = 0

        notes = input("  Notes (optional): ").strip() or None
        print()

        log_work_session(project, duration_mins, work_type, income, notes)
        return

    print(f"[ERR]  Unknown work command '{args[0]}'")
    print("  Usage: work | work log | work today | work week | work month | work recent")


def cmd_bali(args):
    from work_tracker import log_bali_fund, print_work_summary

    if not args:
        print_work_summary("bali")
        return

    if args[0] == "add":
        if len(args) < 2:
            amount_str = input("  Amount to add (Rs.): ").strip()
        else:
            amount_str = args[1]
        try:
            amount = float(amount_str)
        except ValueError:
            print("[ERR]  Invalid amount.")
            sys.exit(1)
        notes = args[2] if len(args) > 2 else input("  Note (optional): ").strip() or None
        log_bali_fund(amount, "deposit", notes)
        return

    if args[0] == "spend":
        if len(args) < 2:
            amount_str = input("  Amount spent (Rs.): ").strip()
        else:
            amount_str = args[1]
        try:
            amount = float(amount_str)
        except ValueError:
            print("[ERR]  Invalid amount.")
            sys.exit(1)
        log_bali_fund(amount, "withdrawal", "expense")
        return

    print_work_summary("bali")


def cmd_reminders(args):
    from reminders import (
        list_reminders, add_reminder, delete_reminder,
        toggle_reminder, ReminderScheduler
    )

    if not args:
        list_reminders()
        return

    if args[0] == "add":
        print("\n  [ALARM]  ADD REMINDER")
        time_str = input("  Time (HH:MM, 24h): ").strip()
        message  = input("  Message: ").strip()
        if not time_str or not message:
            print("[ERR]  Time and message are required.")
            sys.exit(1)
        print("  Days: daily | weekdays | weekends | mon,wed,fri")
        days = input("  Days (default: daily): ").strip() or "daily"
        add_reminder(time_str, message, days)
        return

    if args[0] == "delete" and len(args) > 1:
        delete_reminder(int(args[1]))
        return

    if args[0] == "off" and len(args) > 1:
        toggle_reminder(int(args[1]), active=False)
        return

    if args[0] == "on" and len(args) > 1:
        toggle_reminder(int(args[1]), active=True)
        return

    if args[0] == "start":
        # Blocking -- keep the terminal open as a reminder service
        from reminders import ReminderScheduler
        scheduler = ReminderScheduler()
        try:
            scheduler.start(background=False)
        except KeyboardInterrupt:
            scheduler.stop()
        return

    list_reminders()


def cmd_weight(args):
    from database import get_connection
    from datetime import datetime

    if not args or args[0] == "log":
        weight_str = input("  Today's weight (kg): ").strip()
    else:
        weight_str = args[0]

    try:
        weight = float(weight_str)
    except ValueError:
        print("[ERR]  Invalid weight value.")
        sys.exit(1)

    notes = input("  Note (optional, Enter to skip): ").strip() if (not args or args[0] == "log") else None

    conn = get_connection()
    conn.execute("INSERT INTO weight_logs (weight_kg, notes) VALUES (?,?)", (weight, notes))
    conn.commit()
    conn.close()

    from config import WEIGHT_GOAL
    goal = WEIGHT_GOAL
    diff = weight - goal
    arrow = "v" if diff > 0 else "[OK]"
    print(f"\n  [OK]  Weight logged: {weight} kg")
    print(f"  Goal: {goal} kg  |  {arrow}  {abs(diff):.1f} kg {'to lose' if diff > 0 else 'below target -- great!'}\n")


def cmd_mood(args):
    from database import get_connection
    from datetime import datetime

    labels = {
        "1": "Struggling ",
        "2": "Low ",
        "3": "Okay ",
        "4": "Good ",
        "5": "On fire ",
    }

    print("\n  How are you feeling right now?")
    print("  1 -- Struggling ")
    print("  2 -- Low ")
    print("  3 -- Okay ")
    print("  4 -- Good ")
    print("  5 -- On fire \n")

    score_str = (args[0] if args else input("  Score (1-5): ")).strip()
    if score_str not in labels:
        print("[ERR]  Enter a number 1-5.")
        sys.exit(1)

    score = int(score_str)
    label = labels[score_str]
    notes = input("  One word about it (optional): ").strip() or None

    conn = get_connection()
    conn.execute(
        "INSERT INTO mood_logs (mood_score, mood_label, time, notes) VALUES (?,?,?,?)",
        (score, label, datetime.now().strftime("%H:%M"), notes)
    )
    conn.commit()
    conn.close()
    print(f"\n  [OK]  Mood logged: {label}\n")


def cmd_status(args):
    """Print a full daily status overview."""
    from datetime import date as _date
    from habit_tracker import get_today_completion_percent, get_all_habits, get_today_logs, get_habit_streak
    from work_tracker import get_today_summary, get_bali_fund_total
    from focus_timer import get_today_deep_work_hours
    from website_blocker import get_status as blocker_status

    print("\n" + "=" * 62)
    print(f"  [BRAIN]  NAKUL FOCUS -- {_date.today().strftime('%A, %d %B %Y')}")
    print("=" * 62)

    # Habits
    pct = get_today_completion_percent()
    habits = get_all_habits()
    logs   = get_today_logs()
    done   = sum(1 for h in habits if logs.get(h["id"], False))
    best_streak = max((get_habit_streak(h["id"]) for h in habits), default=0)
    print(f"\n  [-]  Habits:      {done}/{len(habits)} done  ({pct}%)")
    if best_streak >= 3:
        print(f"    Best streak: {best_streak} days")

    # Focus / deep work
    deep_hrs = get_today_deep_work_hours()
    print(f"  [TIME]   Deep work:   {deep_hrs:.1f} hours today")

    # Work / income
    work = get_today_summary()
    if work["total_income"] > 0:
        print(f"  [Rs]  Income:      Rs.{work['total_income']:,.0f} today")
    total_work_hrs = work["total_mins"] / 60
    print(f"  [W]  Work logged: {total_work_hrs:.1f} hours")

    # Bali fund
    bali = get_bali_fund_total()
    pct_bali = min(100, bali / 55000 * 100)
    print(f"    Bali fund:   Rs.{bali:,.0f} / Rs.55,000  ({pct_bali:.1f}%)")

    # Blocker
    bs = blocker_status()
    b_state = "[X] blocked" if bs["blocked"] else "[OK] open"
    print(f"    Sites:       {b_state}")

    print("\n" + "=" * 62)
    print("  Commands:  timer | habits | work | block | dashboard | help")
    print("=" * 62 + "\n")


def cmd_timetable(args):
    from timetable import (
        print_today, add_entry, remove_entry, mark_entry,
        import_template, get_all_entries
    )

    if not args:
        print_today()
        return

    if args[0] == "done":
        ids = args[1:]
        if not ids:
            print("[ERR]  Provide entry IDs. Example: nf timetable done 3 7")
            sys.exit(1)
        for id_str in ids:
            try:
                mark_entry(int(id_str), completed=True)
                print(f"  [OK]  Entry #{id_str} marked done")
            except ValueError:
                print(f"  [WARN]  '{id_str}' is not a valid ID -- skipping")
        return

    if args[0] == "undone":
        for id_str in args[1:]:
            try:
                mark_entry(int(id_str), completed=False)
            except ValueError:
                pass
        return

    if args[0] in ("remove", "rm", "delete"):
        ids = args[1:]
        if not ids:
            print("[ERR]  Provide entry IDs.")
            sys.exit(1)
        for id_str in ids:
            try:
                remove_entry(int(id_str))
            except ValueError:
                print(f"  [WARN]  '{id_str}' is not valid")
        return

    if args[0] == "add":
        print("\n  ADD SCHEDULE BLOCK")
        time_start = input("  Start time (HH:MM, 24h): ").strip()
        time_end   = input("  End time (HH:MM, optional): ").strip() or None
        name       = input("  Activity name: ").strip()
        if not name or not time_start:
            print("[ERR]  Time and activity are required.")
            sys.exit(1)
        print("  Categories: work, health, spiritual, personal, seva, rest")
        category = input("  Category (default: work): ").strip() or "work"
        note = input("  Note (optional): ").strip() or None
        add_entry(time_start, name, category, time_end, note)
        return

    if args[0] == "import":
        template_name = args[1] if len(args) > 1 else input("  Template (exam/syrma/4thyear): ").strip()
        try:
            import_template(template_name)
        except ValueError as e:
            print(f"[ERR]  {e}")
            sys.exit(1)
        return

    if args[0] == "list":
        entries = get_all_entries()
        if not entries:
            print("  No timetable entries. Run: nf timetable add")
            return
        print_today()
        return

    print(f"[ERR]  Unknown timetable command '{args[0]}'")
    print("  Usage: timetable | timetable add | timetable done <id> | timetable remove <id> | timetable import <template>")


def cmd_backup(args):
    from database import backup_database
    path = backup_database()
    print(f"[OK]  Backup saved: {path}")


def cmd_dashboard(args):
    from dashboard.app import run_dashboard
    run_dashboard(open_browser=True)


def cmd_setup(args):
    """First-time setup wizard."""
    print("\n" + "=" * 62)
    print("  [GO]  NAKUL FOCUS SYSTEM -- FIRST TIME SETUP")
    print("=" * 62)
    print("\n  [OK]  Database initialized with your 13 default habits.")
    print("  [OK]  7 daily reminders loaded.")
    print("\n  NEXT STEPS:")
    print("  1. Change OVERRIDE_PASSWORD in config.py")
    print("  2. Run reminders in background: python main.py reminders start")
    print("  3. Open dashboard:              python main.py dashboard")
    print("  4. Start your first timer:      python main.py timer")
    print("\n  NOTE: Website blocking requires admin rights.")
    print("  Windows: right-click terminal -> Run as administrator")
    print("=" * 62 + "\n")


#  ENTRY POINT 

COMMANDS = {
    "timer":     cmd_timer,
    "t":         cmd_timer,
    "block":     cmd_block,
    "unblock":   cmd_unblock,
    "habits":    cmd_habits,
    "h":         cmd_habits,
    "work":      cmd_work,
    "w":         cmd_work,
    "bali":      cmd_bali,
    "reminders": cmd_reminders,
    "remind":    cmd_reminders,
    "r":         cmd_reminders,
    "weight":    cmd_weight,
    "mood":      cmd_mood,
    "status":    cmd_status,
    "s":         cmd_status,
    "timetable": cmd_timetable,
    "tt":        cmd_timetable,
    "schedule":  cmd_timetable,
    "backup":    cmd_backup,
    "dashboard": cmd_dashboard,
    "dash":      cmd_dashboard,
    "setup":     cmd_setup,
    "help":      lambda _: _print_help(),
}


def main():
    argv = sys.argv[1:]

    if not argv:
        cmd_status([])
        return

    cmd = argv[0].lower()
    rest = argv[1:]

    handler = COMMANDS.get(cmd)
    if handler:
        handler(rest)
    else:
        print(f"[ERR]  Unknown command: '{cmd}'")
        print("    Run 'python main.py help' for usage.")
        sys.exit(1)


if __name__ == "__main__":
    main()

