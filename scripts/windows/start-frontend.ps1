. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "啟動 React 前端"
Ensure-Command "npm"
Start-ServiceProcess "frontend" (Join-Path $RepoRoot "frontend") "npm run dev -- --host 0.0.0.0 --port 5173"
