. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "停止 FastAPI 推理服務"
Stop-ServiceByPidFile "inference"
