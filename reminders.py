"""
reminders.py -- Desktop notification scheduler

Runs a background thread checking every 30 seconds whether any
reminders should fire. Fires each reminder once per day at its
configured time.

Standalone usage:  python reminders.py
Via CLI:           python main.py reminders start
"""

import sys
import time
import threading
import compat  # noqa: F401
from datetime import datetime, date
from database import get_connection, initialize_database, seed_defaults


#  NOTIFICATION 

def send_notification(title: str, message: str):
    """Send a cross-platform desktop notification."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Nakul Focus",
            timeout=12,
        )
    except Exception:
        # Fallback to terminal if plyer isn't installed / notification fails
        ts = datetime.now().strftime("%H:%M")
        print(f"[{ts}] [BELL]  {title} -- {message}")


#  DATABASE HELPERS 

def get_active_reminders() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM reminders WHERE active = 1 ORDER BY time").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_reminders() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM reminders ORDER BY time").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_reminder(time_str: str, message: str, days: str = "daily") -> int:
    """
    Add a reminder.

    Args:
        time_str: "HH:MM"  (e.g. "07:30")
        message:  Notification text
        days:     "daily" | "weekdays" | "weekends" | "mon,wed,fri"
    """
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        raise ValueError(f"Time must be HH:MM format, got: {time_str}")

    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO reminders (time, message, days) VALUES (?,?,?)",
        (time_str, message, days)
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    print(f"[OK]  Reminder #{new_id} added: '{message}' at {time_str} ({days})")
    return new_id


def delete_reminder(reminder_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()
    print(f"   Reminder #{reminder_id} deleted.")


def toggle_reminder(reminder_id: int, active: bool):
    conn = get_connection()
    conn.execute("UPDATE reminders SET active = ? WHERE id = ?", (1 if active else 0, reminder_id))
    conn.commit()
    conn.close()
    state = "enabled" if active else "disabled"
    print(f"[OK]  Reminder #{reminder_id} {state}.")


#  SCHEDULE LOGIC 

def _should_fire_today(days_config: str) -> bool:
    """
    Return True if today matches the reminder's day config.
      "daily"    -- every day
      "weekdays" -- Mon-Fri
      "weekends" -- Sat-Sun
      "mon,wed"  -- specific days (3-letter abbreviations)
    """
    wd = datetime.now().weekday()          # 0 = Monday
    name = datetime.now().strftime("%a").lower()  # 'mon', 'tue', 

    if days_config == "daily":
        return True
    if days_config == "weekdays":
        return wd < 5
    if days_config == "weekends":
        return wd >= 5
    # Comma-separated day list
    return name in [d.strip().lower() for d in days_config.split(",")]


#  SCHEDULER 

class ReminderScheduler:
    """
    Lightweight scheduler that polls every 30 s.
    Each reminder fires at most once per day.
    """

    def __init__(self):
        self.running  = False
        self._thread  = None
        self._fired   = set()   # {(reminder_id, date_str)} -- prevents double-firing

    def _tick(self):
        """Called every 30 s. Fires any reminders whose minute has arrived."""
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        today_str    = now.strftime("%Y-%m-%d")

        for r in get_active_reminders():
            key = (r["id"], today_str)
            if key in self._fired:
                continue
            if r["time"] == current_time and _should_fire_today(r["days"]):
                send_notification("[ALARM]  Nakul Focus", r["message"])
                self._fired.add(key)
                print(f"[{current_time}] [BELL]  {r['message'][:60]}")

        # Prune old entries (keep only today)
        self._fired = {k for k in self._fired if k[1] == today_str}

    def _loop(self):
        loaded = len(get_active_reminders())
        print(f"[ALARM]  Reminder service started -- {loaded} active reminders.")
        print("    Press Ctrl+C to stop.\n")

        while self.running:
            try:
                self._tick()
            except Exception as e:
                print(f"[WARN]   Scheduler error: {e}")
            # Sleep in 1 s increments so Ctrl+C is responsive
            for _ in range(30):
                if not self.running:
                    break
                time.sleep(1)

    def start(self, background: bool = True):
        self.running = True
        if background:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()
        else:
            self._loop()   # Blocking -- for standalone use

    def stop(self):
        self.running = False
        print("[ALARM]  Reminder service stopped.")


#  LIST / PRINT 

def list_reminders():
    reminders = get_all_reminders()
    if not reminders:
        print("No reminders configured. Run: python main.py reminders add")
        return

    print("\n" + "=" * 72)
    print(f"  {'#':<4} {'TIME':<8} {'ON':<5} {'DAYS':<12} MESSAGE")
    print("=" * 72)
    for r in reminders:
        status = "yes" if r["active"] else "no "
        print(f"  {r['id']:<4} {r['time']:<8} {status:<5} {r['days']:<12} {r['message'][:40]}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    initialize_database()
    seed_defaults()

    scheduler = ReminderScheduler()
    try:
        scheduler.start(background=False)
    except KeyboardInterrupt:
        scheduler.stop()

