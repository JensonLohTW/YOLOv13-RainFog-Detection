. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "安裝後端依賴"
Ensure-Command "uv"

$BackendEnv = Join-Path $RepoRoot "backend/.env"
$BackendEnvExample = Join-Path $RepoRoot "backend/.env.example"
if (-not (Test-Path $BackendEnv) -and (Test-Path $BackendEnvExample)) {
  Copy-Item $BackendEnvExample $BackendEnv
  Write-Host "[INFO] 已生成 backend/.env"
}

Set-Location (Join-Path $RepoRoot "backend")
uv sync --extra yolo
