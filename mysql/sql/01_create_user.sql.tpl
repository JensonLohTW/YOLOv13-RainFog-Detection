-- 建立應用程式專用帳號，避免日常開發直接使用 root。
CREATE USER IF NOT EXISTS '{{MYSQL_APP_USER}}'@'%' IDENTIFIED BY '{{MYSQL_APP_PASSWORD}}';
