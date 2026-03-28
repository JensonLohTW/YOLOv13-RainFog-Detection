. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "啟動 FastAPI 推理服務"
Ensure-Command "uv"
Start-ServiceProcess "inference" (Join-Path $RepoRoot "backend") "uv run uvicorn inference_service.main:app --host 0.0.0.0 --port 9000 --reload"
