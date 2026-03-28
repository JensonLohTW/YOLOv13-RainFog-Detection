$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptDir "stop-frontend.ps1")
& (Join-Path $ScriptDir "stop-inference.ps1")
& (Join-Path $ScriptDir "stop-backend.ps1")
