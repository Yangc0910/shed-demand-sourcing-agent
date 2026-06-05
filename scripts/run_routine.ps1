$ErrorActionPreference = "Continue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$LogDir = Join-Path $ProjectDir "logs"
$ConsoleLogPath = Join-Path $LogDir "routine-console-latest.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Set-Location $ProjectDir

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . ".\.venv\Scripts\Activate.ps1"
}

& py -m shed_agent.cli routine *> $ConsoleLogPath
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    Write-Error "Shed Demand Listener routine failed with exit code $ExitCode. See $ConsoleLogPath and logs\routine-latest.log"
}

exit $ExitCode
