# Nakul Focus System

Local dopamine control and deep work system. Python + SQLite. No cloud. No tracking.

## Quick Start

```
cd nakul-focus
setup.bat               # first time only
python main.py          # daily status overview
python main.py dashboard  # browser dashboard at localhost:5050
```

**Website blocking requires admin.** Right-click terminal → Run as administrator.

---

## Command Reference

### Focus Timer
```
python main.py timer              # interactive — choose mode
python main.py timer pomodoro     # 25 min focus
python main.py timer deep         # 50 min focus  ← recommended
python main.py timer flow         # 90 min focus
```
Sites auto-block during focus, auto-unblock during break.

### Website Blocker
```
python main.py block              # block now
python main.py unblock            # password + 3 min delay
python main.py block status       # check state
```
Schedule: auto-blocks 6 AM–9 PM. Override password in `config.py`.

### Habits
```
python main.py habits             # today's checklist
python main.py habits done 1 3 5  # check off habits by ID
python main.py habits add         # add new habit
python main.py habits week        # weekly completion summary
```

### Work Tracker
```
python main.py work log           # log a session (interactive)
python main.py work today         # today's summary
python main.py work week          # weekly summary
python main.py work month         # monthly income
python main.py work recent        # last 10 sessions
```

### Bali Fund
```
python main.py bali               # current status
python main.py bali add 5000      # add ₹5000
python main.py bali spend 500     # record expense
```

### Reminders
```
python main.py reminders          # list all
python main.py reminders add      # add custom reminder
python main.py reminders off 3    # disable reminder #3
python main.py reminders start    # run service (keep terminal open)
```

### Other
```
python main.py weight 74.5        # log weight
python main.py mood               # log mood (1–5)
python main.py status             # full overview
```

---

## Auto-start Reminders on Windows

1. Press `Win+R`, type `shell:startup`, press Enter
2. Copy `start_reminders.bat` shortcut into that folder
3. Reminders will run silently every time you log in

---

## Customisation

All config lives in `config.py`:
- `BLOCKED_SITES` — add/remove domains
- `OVERRIDE_PASSWORD` — change this before you forget
- `BLOCK_START_HOUR / BLOCK_END_HOUR` — change schedule window
- `DEFAULT_HABITS` — add/remove habits (only affects first run)
- `BALI_FUND_TARGET` — update your savings goal

---

## Architecture (Phase 2 notes)

Designed to expand into a SaaS product:

```
nakul-focus/
  config.py         ← constants, easy to move to env vars
  database.py       ← SQLite now, swap to Postgres for multi-user
  website_blocker.py
  focus_timer.py
  reminders.py
  habit_tracker.py
  work_tracker.py
  main.py           ← CLI; replace with FastAPI for multi-user API
  dashboard/
    app.py          ← Flask; upgrade to FastAPI + React for SaaS
    templates/
      index.html    ← pure HTML/JS; ready to extract to React
```

When going multi-user:
1. Add `user_id` FK to every table
2. Swap SQLite for Postgres
3. Replace Flask with FastAPI + JWT auth
4. Mobile: Capacitor wrapper around the existing HTML dashboard
5. Cloud sync: replicate SQLite writes to Supabase

---

*"You have a right to perform your prescribed duties, but you are not entitled to the fruits." — BG 2.47*
