@echo off
title Nakul OS

:: Start reminder service silently in background (no window)
start "" /min "D:\Nakul.exe\nakul-focus\start_reminders.bat"

:: Small wait so reminders initialize first
timeout /t 2 /nobreak >nul

:: Launch dashboard (opens browser automatically)
python "D:\Nakul.exe\nakul-focus\main.py" dashboard
