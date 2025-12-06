-- 手动数据库初始化脚本
-- 注意：这个脚本不包含 DROP TABLE 语句，不会清空现有数据

-- 仅在表不存在时创建 users 表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    is_premium BOOLEAN DEFAULT FALSE,
    membership_level INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 仅在表不存在时创建 user_sessions 表
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 仅在表不存在时创建 stocks 表
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL UNIQUE,
    company_name VARCHAR(255),
    exchange VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 仅在表不存在时创建 user_watchlist 表
CREATE TABLE IF NOT EXISTS user_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE(user_id, stock_id)
);

-- 仅在表不存在时创建 stock_prices 表
CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stocks(id) ON DELETE CASCADE,
    price DECIMAL(10, 2) NOT NULL,
    change_percent DECIMAL(5, 2),
    volume BIGINT,
    market_cap BIGINT,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引（如果不存在）
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_stocks_symbol ON stocks(symbol);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_stock ON user_watchlist(stock_id);
CREATE INDEX IF NOT EXISTS idx_prices_stock ON stock_prices(stock_id);
CREATE INDEX IF NOT EXISTS idx_prices_recorded ON stock_prices(recorded_at);

-- 仅在表不存在时创建 timesfm_best_predictions 表，用于保存TimesFM最佳分位预测结果
CREATE TABLE IF NOT EXISTS timesfm_best_predictions (
    id SERIAL PRIMARY KEY,
    unique_key TEXT NOT NULL UNIQUE,
    symbol VARCHAR(20) NOT NULL,
    timesfm_version VARCHAR(20) NOT NULL,
    best_prediction_item VARCHAR(50) NOT NULL,
    best_metrics JSONB NOT NULL,
    is_public SMALLINT NOT NULL DEFAULT 0,
    train_start_date DATE NOT NULL,
    train_end_date DATE NOT NULL,
    test_start_date DATE NOT NULL,
    test_end_date DATE NOT NULL,
    val_start_date DATE NOT NULL,
    val_end_date DATE NOT NULL,
    context_len INTEGER NOT NULL,
    horizon_len INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 兼容已存在的表结构：添加 is_public 列（若不存在）
ALTER TABLE timesfm_best_predictions
    ADD COLUMN IF NOT EXISTS is_public SMALLINT NOT NULL DEFAULT 0;

-- 索引
CREATE INDEX IF NOT EXISTS idx_timesfm_best_predictions_symbol ON timesfm_best_predictions(symbol);

-- 保存验证集分块的pred与actual，并与timesfm-best关联
CREATE TABLE IF NOT EXISTS timesfm_best_validation_chunks (
    id SERIAL PRIMARY KEY,
    unique_key TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    user_id INT4,
    symbol VARCHAR(20),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    predictions JSONB NOT NULL,
    actual_values JSONB NOT NULL,
    dates JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_timesfm_best
        FOREIGN KEY (unique_key)
        REFERENCES timesfm_best_predictions (unique_key)
        ON DELETE CASCADE,
    CONSTRAINT uq_timesfm_best_chunk UNIQUE (unique_key, chunk_index)
);

-- 索引：验证分块按用户维度查询
CREATE INDEX IF NOT EXISTS idx_timesfm_best_validation_chunks_user_id ON timesfm_best_validation_chunks(user_id);
-- 索引：验证分块按股票代码查询
CREATE INDEX IF NOT EXISTS idx_timesfm_best_validation_chunks_symbol ON timesfm_best_validation_chunks(symbol);

-- 如果缺列则添加 membership_level
ALTER TABLE users ADD COLUMN IF NOT EXISTS membership_level INT DEFAULT 0;
