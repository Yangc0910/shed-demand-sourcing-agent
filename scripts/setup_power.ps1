param(
    [int]$MonitorTimeoutMinutes = 30,
    [switch]$EnableWakeTimers
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectDir "logs"
$LogPath = Join-Path $LogDir "power-setup.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Message)
    $Line = "$(Get-Date -Format s) $Message"
    Write-Host $Line
    Add-Content -Path $LogPath -Value $Line
}

$Principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $Principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Log "Administrator privileges are required. Re-run PowerShell as Administrator."
    exit 1
}

Write-Log "Current wake timers:"
powercfg /waketimers | Tee-Object -FilePath $LogPath -Append
Write-Log "Current power requests:"
powercfg /requests | Tee-Object -FilePath $LogPath -Append

Write-Host ""
Write-Host "This will change plugged-in/AC power settings only:"
Write-Host "- Sleep while plugged in: never"
Write-Host "- Hibernate while plugged in: never"
Write-Host "- Display timeout while plugged in: $MonitorTimeoutMinutes minutes"
if ($EnableWakeTimers) {
    Write-Host "- Wake timers: attempt to enable for current AC power scheme"
}
Write-Host ""
$Confirm = Read-Host "Apply these AC-only power settings? Type YES to continue"
if ($Confirm -ne "YES") {
    Write-Log "User cancelled power setup."
    exit 0
}

Write-Log "Setting AC standby timeout to never."
powercfg /x standby-timeout-ac 0 | Tee-Object -FilePath $LogPath -Append
Write-Log "Setting AC hibernate timeout to never."
powercfg /x hibernate-timeout-ac 0 | Tee-Object -FilePath $LogPath -Append
Write-Log "Setting AC monitor timeout to $MonitorTimeoutMinutes minutes."
powercfg /x monitor-timeout-ac $MonitorTimeoutMinutes | Tee-Object -FilePath $LogPath -Append

if ($EnableWakeTimers) {
    Write-Log "Attempting to enable AC wake timers for the active scheme."
    powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_SLEEP RTCWAKE 1 | Tee-Object -FilePath $LogPath -Append
    powercfg /S SCHEME_CURRENT | Tee-Object -FilePath $LogPath -Append
}

Write-Log "Post-change wake timers:"
powercfg /waketimers | Tee-Object -FilePath $LogPath -Append
Write-Log "Post-change power requests:"
powercfg /requests | Tee-Object -FilePath $LogPath -Append
Write-Log "Power setup complete."
