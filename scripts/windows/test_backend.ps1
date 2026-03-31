. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "執行 Django / 推理服務測試"
Ensure-Command "uv"

$LogFile = Join-Path $LogDir "backend-test.log"
$env:DJANGO_SETTINGS_MODULE = "config.settings.test"
Set-Location (Join-Path $RepoRoot "backend")
uv run --group dev python -m pytest $args 2>&1 | Tee-Object -FilePath $LogFile
