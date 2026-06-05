param(
    [int]$SleepTimeoutMinutes = 60,
    [int]$HibernateTimeoutMinutes = 0,
    [int]$MonitorTimeoutMinutes = 30
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectDir "logs"
$LogPath = Join-Path $LogDir "power-restore.log"

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

Write-Host ""
Write-Host "This will restore plugged-in/AC power settings only:"
Write-Host "- Sleep while plugged in: $SleepTimeoutMinutes minutes"
Write-Host "- Hibernate while plugged in: $HibernateTimeoutMinutes minutes"
Write-Host "- Display timeout while plugged in: $MonitorTimeoutMinutes minutes"
Write-Host ""
$Confirm = Read-Host "Apply these AC-only restore settings? Type YES to continue"
if ($Confirm -ne "YES") {
    Write-Log "User cancelled power restore."
    exit 0
}

Write-Log "Restoring AC standby timeout to $SleepTimeoutMinutes minutes."
powercfg /x standby-timeout-ac $SleepTimeoutMinutes | Tee-Object -FilePath $LogPath -Append
Write-Log "Restoring AC hibernate timeout to $HibernateTimeoutMinutes minutes."
powercfg /x hibernate-timeout-ac $HibernateTimeoutMinutes | Tee-Object -FilePath $LogPath -Append
Write-Log "Restoring AC monitor timeout to $MonitorTimeoutMinutes minutes."
powercfg /x monitor-timeout-ac $MonitorTimeoutMinutes | Tee-Object -FilePath $LogPath -Append
Write-Log "Power restore complete."
