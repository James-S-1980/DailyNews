$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$scriptPath = Join-Path $projectRoot "run_newsletter.ps1"
$powershell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$taskAction = '\"' + $powershell + '\" -NoProfile -ExecutionPolicy Bypass -File \"' + $scriptPath + '\" --once-per-day'
$runKeyAction = '"' + $powershell + '" -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "' + $scriptPath + '" --once-per-day --not-before 04:00'

$dailyTaskName = "Daily Newsletters"
$runKeyName = "DailyNewslettersCatchup"
$runKeyPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

schtasks /Create /TN $dailyTaskName /SC DAILY /ST 04:00 /TR $taskAction /F | Out-Host
Set-ItemProperty -Path $runKeyPath -Name $runKeyName -Value $runKeyAction

Write-Host "Registered '$dailyTaskName' for 4:00 AM daily."
Write-Host "Registered '$runKeyName' for user logon catch-up runs."
