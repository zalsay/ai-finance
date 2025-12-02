
14. 前端优化：LandingPage 按钮与演示模式
   - 优化内容：
     - 完善 `LanguageContext.tsx` 中的翻译键值，增加 `login.loginButton` 和 `login.registerButton`。
     - 修改 `App.tsx` 增加 `isDemoMode` 状态，允许非登录用户通过演示模式访问 Dashboard。
     - 修改 `LandingPage.tsx`，将 "View Demo" 按钮连接到 `onDemo` 回调，实现免登录跳转 Dashboard。
   - 效果：用户点击 "View Demo" 可直接查看 Dashboard（使用公开/Mock数据）。

15. 前端界面调整：Dashboard 与 Sidebar
    - 修改内容：
      - `Dashboard.tsx`: 隐藏筛选器（Filter Chips）区域。
      - `Sidebar.tsx`:
        - 移除用户头像显示。
        - 将用户名称统一修改为 "Hello"。
        - 获取并显示当前登录用户的邮箱地址。
    - 效果：界面更加简洁，用户信息显示更符合需求。

16. 后端新增：TimesFM 策略参数持久化（PG表与API）
    - PG表结构：新增 `timesfm_strategy_params`，用于保存回测/策略参数（排除 `actual_total_return_pct`、`fixed_quantile_key`）。
      - 字段包含：`buy_threshold_pct`、`sell_threshold_pct`、`initial_cash`、`enable_rebalance`、`max_position_pct`、`min_position_pct`、`slope_position_per_pct`、`rebalance_tolerance_pct`、`trade_fee_rate`、`take_profit_threshold_pct`、`take_profit_sell_frac`，以及 `unique_key`、`symbol`、`timesfm_version`、`context_len`、`horizon_len`、`user_id`。
    - postgres-handler：
      - 新增接口：`POST /api/v1/strategy/params`（保存/更新），`GET /api/v1/strategy/params/by-unique?unique_key=...`（查询）。
    - fintrack-api：
      - 新增后端路由：`POST /api/v1/strategy/params`、`GET /api/v1/strategy/params/by-unique`，并在 `database/schema.sql` 同步表结构。
25→    - 构建验证：`go build` 通过（`postgres-handler` 与 `fintrack-api`）。
26→
27→17. Python：回测前读取策略参数并覆盖默认值
28→    - 修改文件：`ai-fucntions/timesfm_inference/exchange_server.py`
29→    - 新增函数：`fetch_strategy_params(unique_key)`，从 `fintrack-api` 的 `GET /api/v1/strategy/params/by-unique` 读取参数。
30→    - 在 `run_backtest` 开始处，根据 `unique_key` 覆盖参数：`buy_threshold_pct`、`sell_threshold_pct`、`initial_cash`、`enable_rebalance`、`max_position_pct`、`min_position_pct`、`slope_position_per_pct`、`rebalance_tolerance_pct`、`trade_fee_rate`、`take_profit_threshold_pct`、`take_profit_sell_frac`。
31→    - 语法校验：执行 `python3 -m py_compile ai-fucntions/timesfm_inference/exchange_server.py` 通过。
