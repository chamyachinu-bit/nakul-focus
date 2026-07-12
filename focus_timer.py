"""
focus_timer.py -- Pomodoro+ focus timer with site blocking

Modes:
  pomodoro -- 25 min focus / 5 min break
  deep     -- 50 min focus / 10 min break
  flow     -- 90 min focus / 20 min break

During focus: distraction sites are blocked automatically.
After focus:  sites unblocked for break time.
Sounds play at start, end of focus, and end of break.
Sessions are logged to SQLite for tracking.
"""

import time
import platform
import compat  # noqa: F401
from datetime import datetime
from database import get_connection
from website_blocker import block_sites, unblock_sites, is_currently_blocked
from config import TIMER_MODES


#  SOUND 

def _play_sound(event: str):
    """
    Play a subtle beep. Uses winsound on Windows (built-in, no install needed).
    Falls back to terminal bell on Mac/Linux.
    event: 'start' | 'end' | 'break_end'
    """
    try:
        if platform.system() == "Windows":
            import winsound
            patterns = {
                "start":     [(880, 150), (1100, 250)],
                "end":       [(1100, 200), (880, 200), (660, 350)],
                "break_end": [(660, 200), (880, 200), (1100, 350)],
            }
            for freq, dur in patterns.get(event, [(880, 300)]):
                winsound.Beep(freq, dur)
                time.sleep(0.08)
        else:
            print("\a", end="", flush=True)
            if event in ("end", "break_end"):
                time.sleep(0.3)
                print("\a", end="", flush=True)
    except Exception:
        pass  # Sound failure must never crash the timer


#  NOTIFICATION 

def _notify(title: str, body: str):
    """Send a desktop notification. Falls back to terminal print on error."""
    try:
        from plyer import notification
        notification.notify(title=title, message=body, app_name="Nakul Focus", timeout=10)
    except Exception:
        print(f"\n[BELL]  {title} -- {body}")


#  DATABASE HELPERS 

def log_focus_session(duration_mins: int, mode: str, completed: bool, project: str = None):
    conn = get_connection()
    conn.execute(
        "INSERT INTO focus_sessions (duration_mins, mode, completed, project, start_time) VALUES (?,?,?,?,?)",
        (duration_mins, mode, 1 if completed else 0, project, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_today_deep_work_hours() -> float:
    conn = get_connection()
    row = conn.execute(
        "SELECT SUM(duration_mins) FROM focus_sessions WHERE date = date('now') AND completed = 1"
    ).fetchone()
    conn.close()
    return round((row[0] or 0) / 60, 2)


#  COUNTDOWN DISPLAY 

def _countdown(total_secs: int, label: str, stop_check=None) -> bool:
    """
    Live countdown bar. Returns True if it ran to completion.
    stop_check: optional callable that returns True to stop early.
    """
    start = time.time()
    elapsed = 0

    while elapsed < total_secs:
        if stop_check and stop_check():
            return False

        remaining = total_secs - elapsed
        m, s = divmod(int(remaining), 60)
        progress = elapsed / total_secs
        filled = int(progress * 42)
        bar = "" * filled + "" * (42 - filled)

        print(f"\r  {label}  {bar}  {m:02d}:{s:02d} left  ", end="", flush=True)
        time.sleep(1)
        elapsed = time.time() - start

    print()  # newline after countdown ends
    return True


#  FOCUS TIMER CLASS 

class FocusTimer:
    """
    Run a focus block with optional site blocking.

    Usage:
        FocusTimer(mode="deep", project="Arkoun Farms").start()
    """

    def __init__(self, mode: str = "pomodoro", project: str = None):
        if mode not in TIMER_MODES:
            raise ValueError(f"mode must be one of {list(TIMER_MODES)}")
        self.mode       = mode
        self.cfg        = TIMER_MODES[mode]
        self.project    = project
        self._pre_blocked = False  # were sites already blocked before we started?

    def start(self):
        focus_mins = self.cfg["focus"]
        break_mins = self.cfg["break"]

        print("\n" + "=" * 62)
        print(f"  [>]  {self.cfg['label'].upper()}")
        if self.project:
            print(f"    Project: {self.project}")
        print(f"  [TIME]   Focus: {focus_mins} min  ->  Break: {break_mins} min")
        print("=" * 62)
        print("  Ctrl+C to stop early.\n")

        # Block sites, remembering whether they were already blocked
        self._pre_blocked = is_currently_blocked()
        if not self._pre_blocked:
            block_sites(silent=True)
            print("  [X]  Distraction sites blocked.\n")

        _play_sound("start")
        _notify("[>] Focus starts now", f"{focus_mins} min {self.cfg['label']}. You've got this.")

        session_start = datetime.now()
        completed = False

        try:
            #  FOCUS PHASE 
            print(f"    FOCUS -- {focus_mins} min\n")
            focus_done = _countdown(focus_mins * 60, "FOCUS")

            if focus_done:
                completed = True
                log_focus_session(focus_mins, self.mode, True, self.project)

                print(f"\n  [OK]  Focus block complete! Amazing work.")
                _play_sound("end")
                _notify("[OK] Focus block done!", f"{focus_mins} min done. Take a {break_mins} min break.")

                #  BREAK PHASE 
                # Unblock sites during break
                if not self._pre_blocked:
                    unblock_sites(silent=True)

                print(f"\n  [COFFEE]  BREAK -- {break_mins} min")
                print(f"  Stand up. Water. Stretch. No screens.\n")
                _countdown(break_mins * 60, "BREAK ")

                _play_sound("break_end")
                _notify("[FLASH] Break over!", "Ready for the next block?")
                print(f"\n  [FLASH]  Break over. Start another block?\n")

                # Re-block for potential next session
                if not self._pre_blocked:
                    block_sites(silent=True)

        except KeyboardInterrupt:
            elapsed_mins = max(1, int((datetime.now() - session_start).seconds / 60))
            print(f"\n\n  [STOP]   Stopped after {elapsed_mins} min.")
            if elapsed_mins >= 5:
                log_focus_session(elapsed_mins, self.mode, False, self.project)
                print(f"  [OK]  Logged {elapsed_mins} min of partial work.")
            completed = False

        finally:
            # Always restore pre-timer block state
            if not self._pre_blocked and is_currently_blocked():
                # If we're now in a break and re-blocked, unblock since session ended
                if not completed:
                    unblock_sites(silent=True)

            total = get_today_deep_work_hours()
            print(f"\n  [CHART]  Today's deep work total: {total:.1f} hours")
            print("=" * 62 + "\n")


#  INTERACTIVE LAUNCHER 

def run_interactive():
    """Ask user to choose mode, then start the timer."""
    print("\n" + "=" * 62)
    print("  [>]  NAKUL FOCUS TIMER")
    print("=" * 62)
    print("\n  Choose mode:")
    print("  [1]  Pomodoro   -- 25 min focus + 5 min break")
    print("  [2]  Deep Work  -- 50 min focus + 10 min break")
    print("  [3]  Flow State -- 90 min focus + 20 min break\n")

    choice = input("  Choice (1/2/3, default 1): ").strip() or "1"
    mode = {"1": "pomodoro", "2": "deep", "3": "flow"}.get(choice, "pomodoro")

    project = input("  Project name (Enter to skip): ").strip() or None

    FocusTimer(mode=mode, project=project).start()


if __name__ == "__main__":
    run_interactive()

