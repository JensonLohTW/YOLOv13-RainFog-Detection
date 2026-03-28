$ErrorActionPreference = "Stop"

# 統一計算專案根目錄，方便所有 PowerShell 腳本共用。
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
    throw "缺少命令：$Name"
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
      Write-Host "[INFO] $Name 已在運行，PID=$ExistingPid"
      return
    }
    Remove-Item $PidFile -Force
  }

  # 使用 PowerShell 後台進程啟動服務，並將 PID 記錄到 .run。
  $Process = Start-Process powershell -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Set-Location '$Workdir'; $Command *> '$LogFile'" -PassThru
  Set-Content -Path $PidFile -Value $Process.Id
  Write-Host "[INFO] 已啟動 $Name，PID=$($Process.Id)，日誌=$LogFile"
}

function Stop-ServiceByPidFile {
  param([string]$Name)

  $PidFile = Join-Path $RunDir "$Name.pid"
  if (-not (Test-Path $PidFile)) {
    Write-Host "[INFO] $Name 沒有 PID 文件，跳過停止。"
    return
  }

  $Pid = Get-Content $PidFile
  if (Get-Process -Id $Pid -ErrorAction SilentlyContinue) {
    Stop-Process -Id $Pid -Force
    Write-Host "[INFO] 已停止 $Name，PID=$Pid"
  } else {
    Write-Host "[WARN] $Name 的 PID=$Pid 不存在，將清理 PID 文件。"
  }

  Remove-Item $PidFile -Force
}
