. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "Stop Django backend"
Stop-ServiceByPidFile "backend"
