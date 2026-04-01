$ErrorActionPreference = "Stop"

# Resolve repo root for all scripts.
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "../..")
$RunDir = Join-Path $RepoRoot ".run"
$LogDir = Join-Path $RepoRoot "logs"

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Step {
  param([string]$Message)
  Write-Host ""
  Write-Host "[STEP] $Message"
}

function Ensure-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Missing required command: $Name"
  }
}

function Start-ServiceProcess {
  param(
    [string]$Name,
    [string]$Workdir,
    [string]$Command
  )

  $PidFile = Join-Path $RunDir "$Name.pid"
  $LogFile = Join-Path $LogDir "$Name.log"

  if (Test-Path $PidFile) {
    $ExistingPid = Get-Content $PidFile
    if (Get-Process -Id $ExistingPid -ErrorAction SilentlyContinue) {
      Write-Host "[INFO] $Name already running, PID=$ExistingPid"
      return
    }
    Remove-Item $PidFile -Force
  }

  # Launch service in a background PowerShell process and record its PID.
  $Process = Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Set-Location '$Workdir'; $Command *> '$LogFile'" -PassThru
  Set-Content -Path $PidFile -Value $Process.Id
  Write-Host "[INFO] Started $Name, PID=$($Process.Id), log=$LogFile"
}

function Stop-ServiceByPidFile {
  param([string]$Name)

  $PidFile = Join-Path $RunDir "$Name.pid"
  if (-not (Test-Path $PidFile)) {
    Write-Host "[INFO] $Name has no PID file, skipping."
    return
  }

  $Pid = Get-Content $PidFile
  if (Get-Process -Id $Pid -ErrorAction SilentlyContinue) {
    Stop-Process -Id $Pid -Force
    Write-Host "[INFO] Stopped $Name, PID=$Pid"
  } else {
    Write-Host "[WARN] $Name PID=$Pid not found, cleaning up PID file."
  }

  Remove-Item $PidFile -Force
}
