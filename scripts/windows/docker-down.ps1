. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "停止 Docker 基礎設施"
Ensure-Command "docker"
Set-Location $RepoRoot
docker compose -f docker-compose.dev.yml down
