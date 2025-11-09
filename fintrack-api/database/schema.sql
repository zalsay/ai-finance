-- FinTrack API 数据库 Schema
-- 兼容 postgres-handler 的 stock_data 表

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_premium BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户会话表
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 股票基础信息表（补充 postgres-handler 的 stock_data 表）
CREATE TABLE IF NOT EXISTS stocks (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    exchange VARCHAR(50),
    sector VARCHAR(100),
    industry VARCHAR(100),
    market_cap BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户关注列表表
CREATE TABLE IF NOT EXISTS user_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    notes TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, stock_id)
);

-- 股票价格表（实时价格信息）
CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    price DECIMAL(10,4),
    change_percent DECIMAL(8,4),
    volume BIGINT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, recorded_at)
);

-- 股票预测表
CREATE TABLE IF NOT EXISTS stock_predictions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    prediction_date DATE NOT NULL,
    predicted_price DECIMAL(10,4),
    confidence_score DECIMAL(5,4),
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, prediction_date)
);

-- 用户投资组合表
CREATE TABLE IF NOT EXISTS user_portfolio (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    shares DECIMAL(15,6) NOT NULL,
    average_cost DECIMAL(10,4) NOT NULL,
    purchase_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_watchlist_user_id ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_user_watchlist_stock_id ON user_watchlist(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_id ON stock_prices(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_prices_recorded_at ON stock_prices(recorded_at);
CREATE INDEX IF NOT EXISTS idx_stock_predictions_symbol ON stock_predictions(symbol);
CREATE INDEX IF NOT EXISTS idx_stock_predictions_date ON stock_predictions(prediction_date);
CREATE INDEX IF NOT EXISTS idx_user_portfolio_user_id ON user_portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_user_portfolio_symbol ON user_portfolio(symbol);

-- 插入一些初始股票数据
INSERT INTO stocks (symbol, company_name, exchange, sector) VALUES
('AAPL', 'Apple Inc.', 'NASDAQ', 'Technology'),
('GOOGL', 'Alphabet Inc.', 'NASDAQ', 'Technology'),
('MSFT', 'Microsoft Corporation', 'NASDAQ', 'Technology'),
('AMZN', 'Amazon.com Inc.', 'NASDAQ', 'Consumer Discretionary'),
('TSLA', 'Tesla Inc.', 'NASDAQ', 'Consumer Discretionary'),
('META', 'Meta Platforms Inc.', 'NASDAQ', 'Technology'),
('NVDA', 'NVIDIA Corporation', 'NASDAQ', 'Technology'),
('NFLX', 'Netflix Inc.', 'NASDAQ', 'Communication Services')
ON CONFLICT (symbol) DO NOTHING;

-- 插入一些初始股票价格数据
INSERT INTO stock_prices (stock_id, price, change_percent, volume) 
SELECT s.id, price_data.price, price_data.change_percent, price_data.volume
FROM (VALUES 
    ('AAPL', 175.50, 1.33, 45000000),
    ('GOOGL', 2750.80, -0.55, 1200000),
    ('MSFT', 415.25, 2.15, 25000000),
    ('AMZN', 3380.00, 1.37, 3500000),
    ('TSLA', 248.90, -4.64, 85000000),
    ('META', 485.60, 3.94, 15000000),
    ('NVDA', 875.30, 3.04, 42000000),
    ('NFLX', 445.75, -1.82, 8500000)
) AS price_data(symbol, price, change_percent, volume)
JOIN stocks s ON s.symbol = price_data.symbol
ON CONFLICT (stock_id, recorded_at) DO UPDATE SET
    price = EXCLUDED.price,
    change_percent = EXCLUDED.change_percent,
    volume = EXCLUDED.volume;

-- 创建更新时间戳的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表创建更新时间戳的触发器
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_stocks_updated_at ON stocks;
CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_user_portfolio_updated_at ON user_portfolio;
CREATE TRIGGER update_user_portfolio_updated_at BEFORE UPDATE ON user_portfolio
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();