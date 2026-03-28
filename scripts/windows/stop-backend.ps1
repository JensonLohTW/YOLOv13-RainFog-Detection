. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "停止 Django 後端"
Stop-ServiceByPidFile "backend"
