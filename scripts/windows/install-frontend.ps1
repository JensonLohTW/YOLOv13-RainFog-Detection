. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "安裝前端依賴"
Ensure-Command "npm"

$FrontendEnv = Join-Path $RepoRoot "frontend/.env"
$FrontendEnvExample = Join-Path $RepoRoot "frontend/.env.example"
if (-not (Test-Path $FrontendEnv) -and (Test-Path $FrontendEnvExample)) {
  Copy-Item $FrontendEnvExample $FrontendEnv
  Write-Host "[INFO] 已生成 frontend/.env"
}

Set-Location (Join-Path $RepoRoot "frontend")
npm install
