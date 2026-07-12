"""
website_blocker.py -- Block distraction sites via the hosts file

HOW IT WORKS:
  Adds '127.0.0.1 youtube.com' entries to the system hosts file.
  The OS redirects those domains to localhost -- they just fail to load.

WINDOWS:  Run Python / terminal as Administrator.
MAC/LINUX: Run with sudo.

The script marks its entries with comment markers so it can cleanly
remove them without touching anything else in hosts.
"""

import os
import sys
import time
import hashlib
import platform
import getpass
import compat  # noqa: F401
from datetime import datetime
from config import (
    HOSTS_FILE, BLOCKED_SITES,
    HOSTS_MARKER_START, HOSTS_MARKER_END,
    OVERRIDE_DELAY_SECONDS,
    BLOCK_START_HOUR, BLOCK_END_HOUR,
)


#  PRIVILEGE CHECK 

def is_admin() -> bool:
    """True if running with admin (Windows) or root (Unix) privileges."""
    if platform.system() == "Windows":
        try:
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def require_admin():
    """Print instructions and exit if not running as admin."""
    if is_admin():
        return
    if platform.system() == "Windows":
        print("\n[WARN]  ADMIN REQUIRED")
        print("   Right-click your terminal -> 'Run as administrator', then try again.")
        print("   Or right-click main.py -> 'Run as administrator'.")
    else:
        print("\n[WARN]  ROOT REQUIRED -- re-run with: sudo python main.py block")
    sys.exit(1)


#  HOSTS FILE HELPERS 

def _read_hosts() -> str:
    try:
        with open(HOSTS_FILE, "r") as f:
            return f.read()
    except PermissionError:
        require_admin()
    except FileNotFoundError:
        return ""


def _write_hosts(content: str):
    try:
        with open(HOSTS_FILE, "w") as f:
            f.write(content)
    except PermissionError:
        require_admin()


#  PUBLIC API 

def is_currently_blocked() -> bool:
    """Check whether our block section is present in the hosts file."""
    return HOSTS_MARKER_START in _read_hosts()


def block_sites(sites: list = None, silent: bool = False) -> bool:
    """
    Add blocked sites to the hosts file.
    Returns True if sites were newly blocked, False if already blocked.
    """
    require_admin()
    sites = sites or BLOCKED_SITES
    content = _read_hosts()

    if HOSTS_MARKER_START in content:
        if not silent:
            print("[X] Sites are already blocked.")
        return False

    lines = [
        f"\n{HOSTS_MARKER_START}",
        "# Nakul Focus System -- do not edit this section manually",
        f"# Blocked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    ]
    for site in sites:
        lines.append(f"127.0.0.1 {site}")
    lines.append(HOSTS_MARKER_END)

    _write_hosts(content + "\n".join(lines) + "\n")

    if not silent:
        print(f"[X] Blocked {len(sites)} distraction sites.")
        print("   YouTube · Instagram · Netflix · Hotstar · Reddit · 9GAG")
        print("   Now go build something. [YES]")
    return True


def unblock_sites(silent: bool = False) -> bool:
    """
    Remove our block section from the hosts file.
    Returns True if sites were unblocked, False if they weren't blocked.
    """
    require_admin()
    content = _read_hosts()

    if HOSTS_MARKER_START not in content:
        if not silent:
            print("[OK] Sites are not currently blocked.")
        return False

    # Strip everything between our markers (inclusive)
    new_lines = []
    inside = False
    for line in content.split("\n"):
        if HOSTS_MARKER_START in line:
            inside = True
            continue
        if HOSTS_MARKER_END in line:
            inside = False
            continue
        if not inside:
            new_lines.append(line)

    _write_hosts("\n".join(new_lines))

    if not silent:
        print("[OK] Sites unblocked.")
    return True


def override_unblock() -> bool:
    """
    Password-gated unblock with a mandatory 3-minute wait.
    Intentionally annoying -- that's the point.
    """
    print("\n[WARN]  OVERRIDE MODE")
    print("   You're about to break your own rules.")
    print("   Ask yourself: Is this worth it?\n")

    from database import get_setting
    stored_hash = get_setting("override_password_hash", "")
    entered = getpass.getpass("   Password: ")
    entered_hash = hashlib.sha256(entered.encode()).hexdigest()
    if entered_hash != stored_hash:
        print("\n[ERR] Wrong password. Back to work.")
        return False

    print(f"\n[OK] Password correct.")
    print(f"   BUT -- you have to wait {OVERRIDE_DELAY_SECONDS // 60} minutes first.")
    print(f"   Use this time to reconsider. Press Ctrl+C to cancel.\n")

    try:
        for remaining in range(OVERRIDE_DELAY_SECONDS, 0, -1):
            m, s = divmod(remaining, 60)
            print(f"\r   Unlocking in {m:02d}:{s:02d} -- Ctrl+C to stay focused", end="", flush=True)
            time.sleep(1)
        print("\n")
    except KeyboardInterrupt:
        print("\n\n[YES] Smart choice. Stay locked in.")
        return False

    return unblock_sites()


def enforce_schedule(silent: bool = True):
    """
    Auto-block during 6 AM-9 PM, auto-unblock after.
    Call this from the background scheduler every minute.
    """
    hour = datetime.now().hour
    should_block = BLOCK_START_HOUR <= hour < BLOCK_END_HOUR
    blocked = is_currently_blocked()

    if should_block and not blocked:
        block_sites(silent=silent)
        if not silent:
            print("[CAL] Schedule: Sites blocked (6 AM-9 PM window)")
    elif not should_block and blocked:
        unblock_sites(silent=silent)
        if not silent:
            print("[CAL] Schedule: Sites unblocked (after 9 PM)")


def get_status() -> dict:
    """Return current blocker status as a dict (for dashboard API)."""
    hour = datetime.now().hour
    return {
        "blocked":     is_currently_blocked(),
        "in_schedule": BLOCK_START_HOUR <= hour < BLOCK_END_HOUR,
        "block_start": BLOCK_START_HOUR,
        "block_end":   BLOCK_END_HOUR,
        "sites_count": len(BLOCKED_SITES),
    }


if __name__ == "__main__":
    status = get_status()
    print(f"Blocked:           {status['blocked']}")
    print(f"Schedule active:   {status['in_schedule']} ({status['block_start']}:00-{status['block_end']}:00)")
    print(f"Sites in list:     {status['sites_count']}")
