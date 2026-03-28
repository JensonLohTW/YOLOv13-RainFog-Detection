$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptDir "start-backend.ps1")
& (Join-Path $ScriptDir "start-inference.ps1")
& (Join-Path $ScriptDir "start-frontend.ps1")
