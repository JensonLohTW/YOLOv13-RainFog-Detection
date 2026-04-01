. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "Start Django backend"
Ensure-Command "uv"
Start-ServiceProcess "backend" (Join-Path $RepoRoot "backend") "uv run python manage.py runserver 0.0.0.0:8000"
