-- 建立專案資料庫，使用 utf8mb4 以支援完整中文與表情字元。
CREATE DATABASE IF NOT EXISTS `{{MYSQL_DATABASE}}`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
