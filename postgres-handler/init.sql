-- PostgreSQL 股票数据处理服务 - 数据库初始化脚本
-- 此脚本会在PostgreSQL容器首次启动时自动执行

-- 设置数据库编码和时区
SET client_encoding = 'UTF8';
SET timezone = 'Asia/Shanghai';

-- 创建扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
ALTER TABLE stock_data
ADD COLUMN change_percent DECIMAL(8,4);
ADD COLUMN outstanding_share BIGINT;

-- 创建用户和权限（如果需要额外用户）
-- CREATE USER fintrack_user WITH PASSWORD 'fintrack_password';
-- GRANT ALL PRIVILEGES ON DATABASE fintrack TO fintrack_user;

-- 输出初始化完成信息
DO $$
BEGIN
    RAISE NOTICE '=== PostgreSQL 股票数据处理服务数据库初始化完成 ===';
    RAISE NOTICE '数据库名称: fintrack';
    RAISE NOTICE '编码: UTF-8';
    RAISE NOTICE '时区: Asia/Shanghai';
    RAISE NOTICE '股票数据表将由应用程序自动创建和分区';
END $$;