. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "停止 React 前端"
Stop-ServiceByPidFile "frontend"
