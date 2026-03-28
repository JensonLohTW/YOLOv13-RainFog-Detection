-- =============================================================
--  YOLOv13 RainFog Detection Admin — 完整資料庫初始化腳本
--  執行方式：mysql -u root -p < mysql/init.sql
--  執行後無需再執行 python manage.py migrate
--  預設管理員帳號：admin  密碼：admin123
-- =============================================================

-- ─────────────────────────────────────────
-- 1. 資料庫與使用者
-- ─────────────────────────────────────────
CREATE DATABASE IF NOT EXISTS `rainfog`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS 'rainfog'@'%'      IDENTIFIED BY 'rainfog123';
CREATE USER IF NOT EXISTS 'rainfog'@'localhost' IDENTIFIED BY 'rainfog123';

GRANT ALL PRIVILEGES ON `rainfog`.* TO 'rainfog'@'%';
GRANT ALL PRIVILEGES ON `rainfog`.* TO 'rainfog'@'localhost';
FLUSH PRIVILEGES;

USE `rainfog`;

-- ─────────────────────────────────────────
-- 2. Django 框架內部表
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `django_content_type` (
    `id`        int NOT NULL AUTO_INCREMENT,
    `app_label` varchar(100) NOT NULL,
    `model`     varchar(100) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `django_content_type_app_label_model_uniq` (`app_label`, `model`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `auth_permission` (
    `id`              int NOT NULL AUTO_INCREMENT,
    `name`            varchar(255) NOT NULL,
    `content_type_id` int NOT NULL,
    `codename`        varchar(100) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_permission_content_type_id_codename_uniq` (`content_type_id`, `codename`),
    CONSTRAINT `auth_permission_content_type_id_fk`
        FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `auth_group` (
    `id`   int NOT NULL AUTO_INCREMENT,
    `name` varchar(150) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_group_name_uniq` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `auth_group_permissions` (
    `id`            bigint NOT NULL AUTO_INCREMENT,
    `group_id`      int NOT NULL,
    `permission_id` int NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_group_permissions_group_id_permission_id_uniq` (`group_id`, `permission_id`),
    CONSTRAINT `auth_group_permissions_group_id_fk`
        FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
    CONSTRAINT `auth_group_permissions_permission_id_fk`
        FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `auth_user` (
    `id`           int NOT NULL AUTO_INCREMENT,
    `password`     varchar(128) NOT NULL,
    `last_login`   datetime(6) NULL,
    `is_superuser` tinyint(1) NOT NULL DEFAULT 0,
    `username`     varchar(150) NOT NULL,
    `first_name`   varchar(150) NOT NULL DEFAULT '',
    `last_name`    varchar(150) NOT NULL DEFAULT '',
    `email`        varchar(254) NOT NULL DEFAULT '',
    `is_staff`     tinyint(1) NOT NULL DEFAULT 0,
    `is_active`    tinyint(1) NOT NULL DEFAULT 1,
    `date_joined`  datetime(6) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_user_username_uniq` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `auth_user_groups` (
    `id`       bigint NOT NULL AUTO_INCREMENT,
    `user_id`  int NOT NULL,
    `group_id` int NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_user_groups_user_id_group_id_uniq` (`user_id`, `group_id`),
    CONSTRAINT `auth_user_groups_user_id_fk`
        FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
    CONSTRAINT `auth_user_groups_group_id_fk`
        FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `auth_user_user_permissions` (
    `id`            bigint NOT NULL AUTO_INCREMENT,
    `user_id`       int NOT NULL,
    `permission_id` int NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_uniq` (`user_id`, `permission_id`),
    CONSTRAINT `auth_user_user_permissions_user_id_fk`
        FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
    CONSTRAINT `auth_user_user_permissions_permission_id_fk`
        FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `django_admin_log` (
    `id`             int NOT NULL AUTO_INCREMENT,
    `action_time`    datetime(6) NOT NULL,
    `object_id`      longtext NULL,
    `object_repr`    varchar(200) NOT NULL,
    `action_flag`    smallint UNSIGNED NOT NULL,
    `change_message` longtext NOT NULL,
    `content_type_id` int NULL,
    `user_id`        int NOT NULL,
    PRIMARY KEY (`id`),
    CONSTRAINT `django_admin_log_content_type_id_fk`
        FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
    CONSTRAINT `django_admin_log_user_id_fk`
        FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `django_migrations` (
    `id`      bigint NOT NULL AUTO_INCREMENT,
    `app`     varchar(255) NOT NULL,
    `name`    varchar(255) NOT NULL,
    `applied` datetime(6) NOT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `django_session` (
    `session_key`  varchar(40) NOT NULL,
    `session_data` longtext NOT NULL,
    `expire_date`  datetime(6) NOT NULL,
    PRIMARY KEY (`session_key`),
    KEY `django_session_expire_date_idx` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─────────────────────────────────────────
-- 3. 業務應用表
-- ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS `image_assets` (
    `id`           bigint NOT NULL AUTO_INCREMENT,
    `file`         varchar(255) NOT NULL,
    `original_name` varchar(255) NOT NULL,
    `file_name`    varchar(255) NOT NULL,
    `file_ext`     varchar(32) NOT NULL DEFAULT '',
    `mime_type`    varchar(128) NOT NULL DEFAULT '',
    `file_size`    bigint UNSIGNED NOT NULL DEFAULT 0,
    `width`        int UNSIGNED NULL,
    `height`       int UNSIGNED NULL,
    `sha256`       varchar(64) NOT NULL,
    `storage_type` varchar(32) NOT NULL DEFAULT 'local',
    `uploaded_by_id` int NULL,
    `created_at`   datetime(6) NOT NULL,
    `updated_at`   datetime(6) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `image_assets_sha256_uniq` (`sha256`),
    CONSTRAINT `image_assets_uploaded_by_id_fk`
        FOREIGN KEY (`uploaded_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `detection_tasks` (
    `id`                   bigint NOT NULL AUTO_INCREMENT,
    `task_no`              varchar(32) NOT NULL,
    `image_id`             bigint NOT NULL,
    `status`               varchar(16) NOT NULL DEFAULT 'PENDING',
    `trigger_mode`         varchar(16) NOT NULL DEFAULT 'manual',
    `source_type`          varchar(32) NOT NULL DEFAULT 'image_upload',
    `weather_scene`        varchar(16) NOT NULL DEFAULT 'unknown',
    `confidence_threshold` double NOT NULL DEFAULT 0.25,
    `iou_threshold`        double NOT NULL DEFAULT 0.45,
    `requested_by_id`      int NULL,
    `started_at`           datetime(6) NULL,
    `finished_at`          datetime(6) NULL,
    `error_message`        longtext NOT NULL,
    `created_at`           datetime(6) NOT NULL,
    `updated_at`           datetime(6) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `detection_tasks_task_no_uniq` (`task_no`),
    KEY `detection_tasks_task_no_idx` (`task_no`),
    KEY `detection_tasks_status_idx` (`status`),
    KEY `detection_tasks_created_at_idx` (`created_at`),
    CONSTRAINT `detection_tasks_image_id_fk`
        FOREIGN KEY (`image_id`) REFERENCES `image_assets` (`id`) ON DELETE RESTRICT,
    CONSTRAINT `detection_tasks_requested_by_id_fk`
        FOREIGN KEY (`requested_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `inference_records` (
    `id`                bigint NOT NULL AUTO_INCREMENT,
    `task_id`           bigint NOT NULL,
    `engine_type`       varchar(64) NOT NULL,
    `engine_version`    varchar(64) NOT NULL DEFAULT '',
    `model_name`        varchar(128) NOT NULL DEFAULT '',
    `model_version`     varchar(64) NOT NULL DEFAULT '',
    `request_payload`   json NOT NULL,
    `response_payload`  json NOT NULL,
    `result_image_path` varchar(255) NOT NULL DEFAULT '',
    `result_image_url`  varchar(255) NOT NULL DEFAULT '',
    `object_count`      int UNSIGNED NOT NULL DEFAULT 0,
    `avg_confidence`    double NULL,
    `duration_ms`       int UNSIGNED NOT NULL DEFAULT 0,
    `is_mock`           tinyint(1) NOT NULL DEFAULT 1,
    `created_at`        datetime(6) NOT NULL,
    PRIMARY KEY (`id`),
    CONSTRAINT `inference_records_task_id_fk`
        FOREIGN KEY (`task_id`) REFERENCES `detection_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `detection_objects` (
    `id`          bigint NOT NULL AUTO_INCREMENT,
    `record_id`   bigint NOT NULL,
    `class_name`  varchar(128) NOT NULL,
    `class_id`    int NOT NULL,
    `confidence`  double NOT NULL,
    `bbox_x1`     int NOT NULL,
    `bbox_y1`     int NOT NULL,
    `bbox_x2`     int NOT NULL,
    `bbox_y2`     int NOT NULL,
    `bbox_width`  int NOT NULL,
    `bbox_height` int NOT NULL,
    `area_ratio`  double NULL,
    `created_at`  datetime(6) NOT NULL,
    PRIMARY KEY (`id`),
    KEY `detection_objects_class_name_idx` (`class_name`),
    CONSTRAINT `detection_objects_record_id_fk`
        FOREIGN KEY (`record_id`) REFERENCES `inference_records` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `system_config_items` (
    `id`            bigint NOT NULL AUTO_INCREMENT,
    `config_key`    varchar(128) NOT NULL,
    `config_value`  longtext NOT NULL,
    `value_type`    varchar(16) NOT NULL DEFAULT 'string',
    `description`   varchar(255) NOT NULL DEFAULT '',
    `updated_by_id` int NULL,
    `created_at`    datetime(6) NOT NULL,
    `updated_at`    datetime(6) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `system_config_items_config_key_uniq` (`config_key`),
    CONSTRAINT `system_config_items_updated_by_id_fk`
        FOREIGN KEY (`updated_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `operation_logs` (
    `id`            bigint NOT NULL AUTO_INCREMENT,
    `user_id`       int NULL,
    `module`        varchar(64) NOT NULL DEFAULT '',
    `action`        varchar(64) NOT NULL DEFAULT '',
    `method`        varchar(16) NOT NULL,
    `path`          varchar(255) NOT NULL,
    `ip`            varchar(64) NOT NULL DEFAULT '',
    `request_body`  longtext NOT NULL,
    `response_code` int UNSIGNED NOT NULL DEFAULT 200,
    `status`        varchar(16) NOT NULL DEFAULT 'success',
    `duration_ms`   int UNSIGNED NOT NULL DEFAULT 0,
    `created_at`    datetime(6) NOT NULL,
    PRIMARY KEY (`id`),
    CONSTRAINT `operation_logs_user_id_fk`
        FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ─────────────────────────────────────────
-- 4. Content types（Django 權限系統所需）
-- ─────────────────────────────────────────

INSERT IGNORE INTO `django_content_type` (`id`, `app_label`, `model`) VALUES
(1,  'contenttypes', 'contenttype'),
(2,  'auth',         'permission'),
(3,  'auth',         'group'),
(4,  'auth',         'user'),
(5,  'admin',        'logentry'),
(6,  'sessions',     'session'),
(7,  'media',        'imageasset'),
(8,  'detection',    'detectiontask'),
(9,  'detection',    'inferencerecord'),
(10, 'detection',    'detectionobject'),
(11, 'system',       'systemconfigitem'),
(12, 'audit',        'operationlog');

-- ─────────────────────────────────────────
-- 5. Auth Permissions（每個 model 四個：add/change/delete/view）
-- ─────────────────────────────────────────

INSERT IGNORE INTO `auth_permission` (`id`, `name`, `content_type_id`, `codename`) VALUES
-- contenttypes
(1,  'Can add content type',     1, 'add_contenttype'),
(2,  'Can change content type',  1, 'change_contenttype'),
(3,  'Can delete content type',  1, 'delete_contenttype'),
(4,  'Can view content type',    1, 'view_contenttype'),
-- auth | permission
(5,  'Can add permission',       2, 'add_permission'),
(6,  'Can change permission',    2, 'change_permission'),
(7,  'Can delete permission',    2, 'delete_permission'),
(8,  'Can view permission',      2, 'view_permission'),
-- auth | group
(9,  'Can add group',            3, 'add_group'),
(10, 'Can change group',         3, 'change_group'),
(11, 'Can delete group',         3, 'delete_group'),
(12, 'Can view group',           3, 'view_group'),
-- auth | user
(13, 'Can add user',             4, 'add_user'),
(14, 'Can change user',          4, 'change_user'),
(15, 'Can delete user',          4, 'delete_user'),
(16, 'Can view user',            4, 'view_user'),
-- admin | logentry
(17, 'Can add log entry',        5, 'add_logentry'),
(18, 'Can change log entry',     5, 'change_logentry'),
(19, 'Can delete log entry',     5, 'delete_logentry'),
(20, 'Can view log entry',       5, 'view_logentry'),
-- sessions | session
(21, 'Can add session',          6, 'add_session'),
(22, 'Can change session',       6, 'change_session'),
(23, 'Can delete session',       6, 'delete_session'),
(24, 'Can view session',         6, 'view_session'),
-- media | imageasset
(25, 'Can add image asset',      7, 'add_imageasset'),
(26, 'Can change image asset',   7, 'change_imageasset'),
(27, 'Can delete image asset',   7, 'delete_imageasset'),
(28, 'Can view image asset',     7, 'view_imageasset'),
-- detection | detectiontask
(29, 'Can add detection task',   8, 'add_detectiontask'),
(30, 'Can change detection task',8, 'change_detectiontask'),
(31, 'Can delete detection task',8, 'delete_detectiontask'),
(32, 'Can view detection task',  8, 'view_detectiontask'),
-- detection | inferencerecord
(33, 'Can add inference record',   9, 'add_inferencerecord'),
(34, 'Can change inference record',9, 'change_inferencerecord'),
(35, 'Can delete inference record',9, 'delete_inferencerecord'),
(36, 'Can view inference record',  9, 'view_inferencerecord'),
-- detection | detectionobject
(37, 'Can add detection object',   10, 'add_detectionobject'),
(38, 'Can change detection object',10, 'change_detectionobject'),
(39, 'Can delete detection object',10, 'delete_detectionobject'),
(40, 'Can view detection object',  10, 'view_detectionobject'),
-- system | systemconfigitem
(41, 'Can add system config item',   11, 'add_systemconfigitem'),
(42, 'Can change system config item',11, 'change_systemconfigitem'),
(43, 'Can delete system config item',11, 'delete_systemconfigitem'),
(44, 'Can view system config item',  11, 'view_systemconfigitem'),
-- audit | operationlog
(45, 'Can add operation log',    12, 'add_operationlog'),
(46, 'Can change operation log', 12, 'change_operationlog'),
(47, 'Can delete operation log', 12, 'delete_operationlog'),
(48, 'Can view operation log',   12, 'view_operationlog');

-- ─────────────────────────────────────────
-- 6. 標記 Django Migrations 為已執行
-- ─────────────────────────────────────────

INSERT IGNORE INTO `django_migrations` (`app`, `name`, `applied`) VALUES
('contenttypes', '0001_initial',                        NOW()),
('contenttypes', '0002_remove_content_type_name',       NOW()),
('auth',         '0001_initial',                        NOW()),
('auth',         '0002_alter_permission_name_max_length', NOW()),
('auth',         '0003_alter_user_email_max_length',    NOW()),
('auth',         '0004_alter_user_username_opts',       NOW()),
('auth',         '0005_alter_user_last_login_null',     NOW()),
('auth',         '0006_require_contenttypes_0002',      NOW()),
('auth',         '0007_alter_validators_add_error_messages', NOW()),
('auth',         '0008_alter_user_username_max_length', NOW()),
('auth',         '0009_alter_user_last_name_max_length',NOW()),
('auth',         '0010_alter_group_name_max_length',    NOW()),
('auth',         '0011_update_proxy_permissions',       NOW()),
('auth',         '0012_alter_user_first_name_max_length', NOW()),
('admin',        '0001_initial',                        NOW()),
('admin',        '0002_logentry_remove_auto_add',       NOW()),
('admin',        '0003_logentry_add_action_flag_choices', NOW()),
('sessions',     '0001_initial',                        NOW()),
('media',        '0001_initial',                        NOW()),
('detection',    '0001_initial',                        NOW()),
('system',       '0001_initial',                        NOW()),
('audit',        '0001_initial',                        NOW());

-- ─────────────────────────────────────────
-- 7. 預設管理員帳號
--    帳號：admin  密碼：admin123
-- ─────────────────────────────────────────

INSERT IGNORE INTO `auth_user`
    (`id`, `password`, `last_login`, `is_superuser`, `username`,
     `first_name`, `last_name`, `email`, `is_staff`, `is_active`, `date_joined`)
VALUES (
    1,
    'pbkdf2_sha256$600000$P7KPgjWLlgpnQ7qtqaQ7G3$vZGuJVaSlGwRDMf/uukLZ6KLFfISezvpIRlGiIgsWYA=',
    NULL, 1, 'admin', 'System', 'Administrator', 'admin@rainfog.local', 1, 1, NOW()
);

-- ─────────────────────────────────────────
-- 8. 系統預設配置項
-- ─────────────────────────────────────────

INSERT IGNORE INTO `system_config_items`
    (`config_key`, `config_value`, `value_type`, `description`, `updated_by_id`, `created_at`, `updated_at`)
VALUES
('inference_base_url',   'http://127.0.0.1:9000', 'url',     'FastAPI 推理服務地址',             NULL, NOW(), NOW()),
('inference_use_mock',   'true',                  'boolean', '是否使用 Mock 推理模式',            NULL, NOW(), NOW()),
('inference_model_mode', 'mock',                  'string',  '當前推理 Adapter 模式（mock/yolov13）', NULL, NOW(), NOW()),
('inference_model_name', 'yolov13-rainfog',        'string',  '當前推理模型名稱',                  NULL, NOW(), NOW()),
('redis_host',           '127.0.0.1',             'string',  'Redis 主機地址',                    NULL, NOW(), NOW()),
('redis_port',           '6379',                  'integer', 'Redis 埠號',                        NULL, NOW(), NOW()),
('redis_db',             '0',                     'integer', 'Redis 資料庫索引',                  NULL, NOW(), NOW());

-- ─────────────────────────────────────────
-- 完成
-- ─────────────────────────────────────────
SELECT '✓ rainfog 資料庫初始化完成' AS result;
SELECT CONCAT('  管理員帳號: admin / admin123') AS info;
SELECT CONCAT('  資料庫: rainfog  使用者: rainfog  密碼: rainfog123') AS info;
