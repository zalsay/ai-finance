-- 数据库迁移脚本 - 重新创建表结构
-- 删除冲突的表
DROP TABLE IF EXISTS user_watchlist CASCADE;
DROP TABLE IF EXISTS stock_prices CASCADE;
DROP TABLE IF EXISTS stocks CASCADE;

-- 重新创建stocks表
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

-- 重新创建user_watchlist表
CREATE TABLE IF NOT EXISTS user_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    notes TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, stock_id)
);

-- 重新创建stock_prices表
CREATE TABLE IF NOT EXISTS stock_prices (
    id SERIAL PRIMARY KEY,
    stock_id INTEGER REFERENCES stocks(id) ON DELETE CASCADE,
    price DECIMAL(10,4),
    change_percent DECIMAL(8,4),
    volume BIGINT,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(stock_id, recorded_at)
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_user_watchlist_user_id ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_user_watchlist_stock_id ON user_watchlist(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_prices_stock_id ON stock_prices(stock_id);
CREATE INDEX IF NOT EXISTS idx_stock_prices_recorded_at ON stock_prices(recorded_at);

-- 插入初始股票数据
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

-- 插入初始股票价格数据
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

-- 为stocks表创建更新时间戳的触发器
DROP TRIGGER IF EXISTS update_stocks_updated_at ON stocks;
CREATE TRIGGER update_stocks_updated_at BEFORE UPDATE ON stocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();