. (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "common.ps1")

Write-Step "初始化 MySQL 資料庫與帳號"
Ensure-Command "mysql"

$MysqlHost = if ($env:MYSQL_HOST) { $env:MYSQL_HOST } else { "127.0.0.1" }
$MysqlPort = if ($env:MYSQL_PORT) { $env:MYSQL_PORT } else { "3306" }
$MysqlRootUser = if ($env:MYSQL_ROOT_USER) { $env:MYSQL_ROOT_USER } else { "root" }
$MysqlRootPassword = $env:MYSQL_ROOT_PASSWORD
$MysqlDatabase = if ($env:MYSQL_DATABASE) { $env:MYSQL_DATABASE } else { "rainfog" }
$MysqlAppUser = if ($env:MYSQL_APP_USER) { $env:MYSQL_APP_USER } else { "rainfog" }
$MysqlAppPassword = if ($env:MYSQL_APP_PASSWORD) { $env:MYSQL_APP_PASSWORD } else { "rainfog123" }

if (-not $MysqlRootPassword) {
  throw "請先設置 MYSQL_ROOT_PASSWORD 環境變量。"
}

function Invoke-TemplateSql {
  param([string]$TemplatePath)

  $Content = Get-Content $TemplatePath -Raw
  $Content = $Content.Replace("{{MYSQL_DATABASE}}", $MysqlDatabase)
  $Content = $Content.Replace("{{MYSQL_APP_USER}}", $MysqlAppUser)
  $Content = $Content.Replace("{{MYSQL_APP_PASSWORD}}", $MysqlAppPassword)

  $TempFile = [System.IO.Path]::GetTempFileName()
  Set-Content -Path $TempFile -Value $Content

  Get-Content $TempFile | mysql --host=$MysqlHost --port=$MysqlPort --user=$MysqlRootUser --password=$MysqlRootPassword
  Remove-Item $TempFile -Force
}

Invoke-TemplateSql (Join-Path $RepoRoot "mysql/sql/00_create_database.sql.tpl")
Invoke-TemplateSql (Join-Path $RepoRoot "mysql/sql/01_create_user.sql.tpl")
Invoke-TemplateSql (Join-Path $RepoRoot "mysql/sql/02_grant_privileges.sql.tpl")
Get-Content (Join-Path $RepoRoot "mysql/sql/03_verify_setup.sql") | mysql --host=$MysqlHost --port=$MysqlPort --user=$MysqlRootUser --password=$MysqlRootPassword
