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

CREATE TABLE IF NOT EXISTS timesfm_strategy_params (
    id SERIAL PRIMARY KEY,
    unique_key VARCHAR(255) NOT NULL UNIQUE,
    user_id INTEGER,
    buy_threshold_pct DOUBLE PRECISION,
    sell_threshold_pct DOUBLE PRECISION,
    initial_cash DOUBLE PRECISION,
    enable_rebalance BOOLEAN,
    max_position_pct DOUBLE PRECISION,
    min_position_pct DOUBLE PRECISION,
    slope_position_per_pct DOUBLE PRECISION,
    rebalance_tolerance_pct DOUBLE PRECISION,
    trade_fee_rate DOUBLE PRECISION,
    take_profit_threshold_pct DOUBLE PRECISION,
    take_profit_sell_frac DOUBLE PRECISION,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_strategy_params_user ON timesfm_strategy_params(user_id);
CREATE INDEX IF NOT EXISTS idx_strategy_params_unique_key ON timesfm_strategy_params(unique_key);
CREATE INDEX IF NOT EXISTS idx_strategy_params_user_unique_key ON timesfm_strategy_params(user_id, unique_key);
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
