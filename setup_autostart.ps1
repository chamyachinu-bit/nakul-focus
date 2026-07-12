# setup_autostart.ps1
# Registers two Windows Task Scheduler tasks:
#   1. nakul-focus-reminders  -- starts reminder service on login (background, no window)
#   2. nakul-focus-backup     -- daily backup at 11:55 PM
#
# Run once as Administrator:  powershell -ExecutionPolicy Bypass -File setup_autostart.ps1

$ProjectDir = "D:\Nakul.exe\nakul-focus"
$Python = (Get-Command python).Source

Write-Host "=== Nakul Focus -- Auto-Start Setup ===" -ForegroundColor Cyan
Write-Host ""

# ── Task 1: Reminder Service ────────────────────────────────────────────────
$taskName1 = "nakul-focus-reminders"
$action1   = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$ProjectDir\reminders.py`"" `
    -WorkingDirectory $ProjectDir
$trigger1  = New-ScheduledTaskTrigger -AtLogon
$settings1 = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 23) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -MultipleInstances IgnoreNew

try {
    Unregister-ScheduledTask -TaskName $taskName1 -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName $taskName1 `
        -Action $action1 `
        -Trigger $trigger1 `
        -Settings $settings1 `
        -RunLevel Highest `
        -Description "Nakul Focus reminder service -- starts on login" | Out-Null
    Write-Host "[OK]  Task '$taskName1' registered (starts on login)" -ForegroundColor Green
} catch {
    Write-Host "[ERR] Could not register '$taskName1': $_" -ForegroundColor Red
}

# ── Task 2: Daily Backup ────────────────────────────────────────────────────
$taskName2 = "nakul-focus-backup"
$action2   = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "`"$ProjectDir\main.py`" backup" `
    -WorkingDirectory $ProjectDir
$trigger2  = New-ScheduledTaskTrigger -Daily -At "23:55"
$settings2 = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5)

try {
    Unregister-ScheduledTask -TaskName $taskName2 -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask `
        -TaskName $taskName2 `
        -Action $action2 `
        -Trigger $trigger2 `
        -Settings $settings2 `
        -Description "Nakul Focus daily database backup at 11:55 PM" | Out-Null
    Write-Host "[OK]  Task '$taskName2' registered (daily at 23:55)" -ForegroundColor Green
} catch {
    Write-Host "[ERR] Could not register '$taskName2': $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done. Reminders will start automatically on next login." -ForegroundColor Cyan
Write-Host "To add 'nf' as a global command, add this to your PATH:"
Write-Host "  $ProjectDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "Run this in PowerShell (as Admin) to add to PATH permanently:"
Write-Host '  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";' + $ProjectDir + '", "Machine")' -ForegroundColor Yellow
