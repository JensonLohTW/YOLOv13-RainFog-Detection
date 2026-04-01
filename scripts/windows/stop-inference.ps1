. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "Stop FastAPI inference service"
Stop-ServiceByPidFile "inference"
