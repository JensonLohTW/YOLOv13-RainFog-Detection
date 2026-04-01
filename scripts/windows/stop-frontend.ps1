. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "Stop React frontend"
Stop-ServiceByPidFile "frontend"
