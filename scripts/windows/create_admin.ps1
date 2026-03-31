. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "建立 Django 超級管理員"
Ensure-Command "uv"

Set-Location (Join-Path $RepoRoot "backend")
uv run python manage.py createsuperuser
