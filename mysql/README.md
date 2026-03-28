# MySQL Local Config

本目錄存放本地開發所需的 MySQL 配置與 SQL 腳本。

## 目錄說明

- `conf.d/my.cnf`
  Docker 版 MySQL 的本地配置。

- `sql/00_create_database.sql.tpl`
  建立業務資料庫的 SQL 模板。

- `sql/01_create_user.sql.tpl`
  建立應用帳號的 SQL 模板。

- `sql/02_grant_privileges.sql.tpl`
  為應用帳號授權的 SQL 模板。

- `sql/03_verify_setup.sql`
  驗證資料庫與帳號是否已成功建立。

## 使用方式

若你稍後手動安裝了 MySQL，可以直接使用以下腳本：

- macOS：
  `scripts/macos/init_mysql.sh`

- Windows：
  `scripts/windows/init-mysql.ps1`

執行前建議先設置以下環境變量：

- `MYSQL_ROOT_PASSWORD`
- `MYSQL_DATABASE`
- `MYSQL_APP_USER`
- `MYSQL_APP_PASSWORD`
