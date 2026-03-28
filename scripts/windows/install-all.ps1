$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
& (Join-Path $ScriptDir "install-backend.ps1")
& (Join-Path $ScriptDir "install-frontend.ps1")
