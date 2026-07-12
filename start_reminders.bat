@echo off
:: Run this at Windows startup to keep reminders running.
:: To auto-start on boot: add a shortcut to this file in
::   Shell:startup  (Win+R -> shell:startup)
title Nakul Focus — Reminders
echo ============================================================
echo   NAKUL FOCUS — Reminder Service
echo   Minimise this window. Do NOT close it.
echo ============================================================
echo.
python reminders.py
pause
