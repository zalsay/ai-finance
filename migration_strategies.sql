ALTER TABLE timesfm_strategy_params ADD COLUMN IF NOT EXISTS is_public INTEGER DEFAULT 0;

INSERT INTO timesfm_strategy_params (
    unique_key, name, is_public, user_id,
    buy_threshold_pct, sell_threshold_pct, initial_cash,
    enable_rebalance, max_position_pct, min_position_pct,
    slope_position_per_pct, rebalance_tolerance_pct,
    trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac
) VALUES (
    'strategy_conservative', 'Conservative', 1, NULL,
    0.5, -0.5, 10000,
    true, 1.0, 0.0,
    0.1, 0.05,
    0.001, 0.0, 0.0
) ON CONFLICT (unique_key) DO UPDATE SET
    name = EXCLUDED.name,
    is_public = 1,
    user_id = NULL,
    buy_threshold_pct = EXCLUDED.buy_threshold_pct,
    sell_threshold_pct = EXCLUDED.sell_threshold_pct;

INSERT INTO timesfm_strategy_params (
    unique_key, name, is_public, user_id,
    buy_threshold_pct, sell_threshold_pct, initial_cash,
    enable_rebalance, max_position_pct, min_position_pct,
    slope_position_per_pct, rebalance_tolerance_pct,
    trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac
) VALUES (
    'strategy_balanced', 'Balanced', 1, NULL,
    1.5, -1.5, 10000,
    true, 1.0, 0.0,
    0.1, 0.05,
    0.001, 0.0, 0.0
) ON CONFLICT (unique_key) DO UPDATE SET
    name = EXCLUDED.name,
    is_public = 1,
    user_id = NULL,
    buy_threshold_pct = EXCLUDED.buy_threshold_pct,
    sell_threshold_pct = EXCLUDED.sell_threshold_pct;

INSERT INTO timesfm_strategy_params (
    unique_key, name, is_public, user_id,
    buy_threshold_pct, sell_threshold_pct, initial_cash,
    enable_rebalance, max_position_pct, min_position_pct,
    slope_position_per_pct, rebalance_tolerance_pct,
    trade_fee_rate, take_profit_threshold_pct, take_profit_sell_frac
) VALUES (
    'strategy_aggressive', 'Aggressive', 1, NULL,
    3.0, -3.0, 10000,
    true, 1.0, 0.0,
    0.1, 0.05,
    0.001, 0.0, 0.0
) ON CONFLICT (unique_key) DO UPDATE SET
    name = EXCLUDED.name,
    is_public = 1,
    user_id = NULL,
    buy_threshold_pct = EXCLUDED.buy_threshold_pct,
    sell_threshold_pct = EXCLUDED.sell_threshold_pct;
