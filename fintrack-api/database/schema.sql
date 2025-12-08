-- Drop existing tables to ensure schema compatibility
DROP TABLE IF EXISTS user_watchlist CASCADE;
DROP TABLE IF EXISTS stock_prices CASCADE;
DROP TABLE IF EXISTS stocks CASCADE;
DROP TABLE IF EXISTS user_sessions CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Users table
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

-- User sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User watchlist table - now uses symbol directly
CREATE TABLE IF NOT EXISTS user_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    strategy_unique_key VARCHAR(255),
    UNIQUE(user_id, symbol)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON user_watchlist(symbol);

-- TimesFM backtests table: stores strategy backtesting results, idempotent by unique_key
CREATE TABLE IF NOT EXISTS timesfm_backtests (
    id SERIAL PRIMARY KEY,
    unique_key VARCHAR(255) NOT NULL UNIQUE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    strategy_params_id INTEGER REFERENCES timesfm_strategy_params(id) ON DELETE SET NULL,
    symbol VARCHAR(20) NOT NULL,
    timesfm_version VARCHAR(20) NOT NULL,
    context_len INTEGER NOT NULL,
    horizon_len INTEGER NOT NULL,

    used_quantile VARCHAR(50),
    buy_threshold_pct DOUBLE PRECISION,
    sell_threshold_pct DOUBLE PRECISION,
    trade_fee_rate DOUBLE PRECISION,
    total_fees_paid DOUBLE PRECISION,
    actual_total_return_pct DOUBLE PRECISION,

    benchmark_return_pct DOUBLE PRECISION,
    benchmark_annualized_return_pct DOUBLE PRECISION,
    period_days INTEGER,

    validation_start_date DATE,
    validation_end_date DATE,
    validation_benchmark_return_pct DOUBLE PRECISION,
    validation_benchmark_annualized_return_pct DOUBLE PRECISION,
    validation_period_days INTEGER,

    position_control JSONB,
    predicted_change_stats JSONB,
    per_chunk_signals JSONB,

    equity_curve_values JSONB,
    equity_curve_pct JSONB,
    equity_curve_pct_gross JSONB,
    curve_dates JSONB,
    actual_end_prices JSONB,
    trades JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_timesfm_backtests_symbol ON timesfm_backtests(symbol);
CREATE INDEX IF NOT EXISTS idx_timesfm_backtests_strategy_params_id ON timesfm_backtests(strategy_params_id);
CREATE INDEX IF NOT EXISTS idx_timesfm_backtests_strategy_params_unique ON timesfm_backtests(strategy_params_id, unique_key);

CREATE TABLE IF NOT EXISTS timesfm_strategy_params (
    id SERIAL PRIMARY KEY,
    unique_key VARCHAR(255) NOT NULL UNIQUE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name VARCHAR(255),
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

-- Add strategy_unique_key to existing user_watchlist table if it doesn't exist
ALTER TABLE user_watchlist ADD COLUMN IF NOT EXISTS strategy_unique_key VARCHAR(255);

-- Add membership_level to users if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS membership_level INT DEFAULT 0;
