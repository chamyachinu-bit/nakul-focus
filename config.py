"""
config.py -- Central configuration for Nakul Focus System
Modify these values to personalize your experience.
"""

import os
import platform

#  PATHS 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "nakul_focus.db")

# Hosts file path differs by OS
if platform.system() == "Windows":
    HOSTS_FILE = r"C:\Windows\System32\drivers\etc\hosts"
else:
    HOSTS_FILE = "/etc/hosts"

#  WEBSITE BLOCKER 
BLOCKED_SITES = [
    "youtube.com",      "www.youtube.com",    "m.youtube.com",
    "instagram.com",    "www.instagram.com",  "m.instagram.com",
    "netflix.com",      "www.netflix.com",
    "hotstar.com",      "www.hotstar.com",
    "reddit.com",       "www.reddit.com",     "old.reddit.com",
    "9gag.com",         "www.9gag.com",
]

ALLOWED_SITES = [
    "github.com", "claude.ai", "google.com",
    "linkedin.com", "docs.google.com", "stackoverflow.com",
]

# Blocking schedule window (24-hour)
BLOCK_START_HOUR = 6   # 6 AM
BLOCK_END_HOUR   = 21  # 9 PM

# Override: password is stored as a SHA-256 hash in the DB settings table.
# To change it, run:  nf block setpassword
# The default on first setup is "balidec2026ygpt" -- change it immediately.
DEFAULT_OVERRIDE_PASSWORD = "balidec2026ygpt"
OVERRIDE_DELAY_SECONDS    = 180  # 3-minute penalty before unblocking

# Markers so we can cleanly remove our entries from hosts file
HOSTS_MARKER_START = "# NAKUL-FOCUS-BLOCK-START"
HOSTS_MARKER_END   = "# NAKUL-FOCUS-BLOCK-END"

#  FOCUS TIMER 
TIMER_MODES = {
    "pomodoro": {"focus": 25, "break": 5,  "label": "Pomodoro (25 min)"},
    "deep":     {"focus": 50, "break": 10, "label": "Deep Work (50 min)"},
    "flow":     {"focus": 90, "break": 20, "label": "Flow State (90 min)"},
}

#  REMINDERS 
DEFAULT_REMINDERS = [
    {"time": "06:00", "message": "Phone across room? Water first.",              "days": "daily"},
    {"time": "06:30", "message": "Time to meditate. 30 minutes.",                "days": "daily"},
    {"time": "09:00", "message": "Deep work block starts now. Block distractions.", "days": "daily"},
    {"time": "13:00", "message": "Lunch break. Cook something real.",            "days": "daily"},
    {"time": "17:30", "message": "Workout time. No excuses.",                    "days": "daily"},
    {"time": "21:00", "message": "Evening meditation. Wind down.",               "days": "daily"},
    {"time": "22:30", "message": "Journal. Gratitude. Sleep by 11.",             "days": "daily"},
]

#  HABITS 
DEFAULT_HABITS = [
    {"name": "Morning prayer + gratitude",  "category": "spiritual"},
    {"name": "Meditation -- 30 min",         "category": "spiritual"},
    {"name": "Read 1 Gita verse",           "category": "spiritual"},
    {"name": "Evening meditation",          "category": "spiritual"},
    {"name": "Journal + 3 gratitudes",      "category": "spiritual"},
    {"name": "Tennis / Workout",            "category": "health"},
    {"name": "10,000 steps",               "category": "health"},
    {"name": "Cook own food",              "category": "health"},
    {"name": "No junk food",               "category": "health"},
    {"name": "Phone off by 10:30 PM",      "category": "health"},
    {"name": "In bed by 11 PM",            "category": "health"},
    {"name": "Deep work (2+ hours)",       "category": "work"},
    {"name": "Freelance outreach",         "category": "work"},
]

#  WEIGHT
WEIGHT_GOAL = 65.0  # kg

#  BALI FUND
BALI_FUND_TARGET = 55000  # Rs.55,000 -- December 2026

#  DASHBOARD 
DASHBOARD_HOST = "127.0.0.1"
DASHBOARD_PORT = 5050

#  WORK 
WORK_TYPES = ["freelance", "study", "seva", "internship", "personal_project"]
