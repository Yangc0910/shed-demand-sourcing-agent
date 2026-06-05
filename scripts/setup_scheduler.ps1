$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$TaskName = "Shed Demand Listener Routine"
$RunScript = Join-Path $ScriptDir "run_routine.ps1"

if (-not (Test-Path $RunScript)) {
    throw "Routine wrapper not found: $RunScript"
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RunScript`"" `
    -WorkingDirectory $ProjectDir

$TriggerTimes = @(
    "08:00",
    "10:00",
    "12:00",
    "14:00",
    "16:00",
    "18:00",
    "20:00"
)

$Triggers = foreach ($time in $TriggerTimes) {
    New-ScheduledTaskTrigger -Daily -At $time
}

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries:$false `
    -DontStopIfGoingOnBatteries:$false `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 45) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

$Description = "Runs the Shed Demand Listener local routine every two hours during the day and once at 8 PM. Reports are written to reports\\ and logs to logs\\."

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Triggers `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description `
    -Force | Out-Null

Write-Host "Updated scheduled task: $TaskName"
Write-Host "Run times: $($TriggerTimes -join ', ')"
