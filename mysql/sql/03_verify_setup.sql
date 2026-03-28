-- 驗證資料庫與帳號是否已建立成功。
SHOW DATABASES;
SELECT user, host FROM mysql.user ORDER BY user, host;
