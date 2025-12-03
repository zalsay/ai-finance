
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
32→
33→18. Python：分块预测持久化统一四位小数
34→    - 修改文件：`ai-fucntions/timesfm_inference/predict_chunked_functions.py`
35→    - 内容：新增 `_round4` 与 `_round_obj`，在保存到数据库与JSON文件前对所有计算结果统一保留四位小数。
36→      - 覆盖项：`best_metrics`、`validation_results`、分块 `metrics`、`predictions`、`actual_values`、`concatenated_predictions`、`concatenated_actual`、`processing_time` 等。
37→      - 数据库：`save_best_prediction` 与 `save_best_val_chunk` 的payload进行四位小数处理。
38→      - JSON：最佳分位JSON与`chunked_response.json`的payload进行四位小数处理。
39→    - 语法校验：执行 `python3 -m py_compile ai-fucntions/timesfm_inference/predict_chunked_functions.py` 通过。
40. Python：修复增量同步日期覆盖判断（仅按日期比较）
    - 修改文件：`ai-fucntions/akshare-tools/postgres.py`
    - 内容：在 `ensure_date_range_df` 中去除时间偏移，统一将 `latest_dt` 与交易日 `target_end_date` 转为日期进行比较，避免出现“最新日期 00:00:00 未覆盖到 08:00:00”的误判。
    - 逻辑：`latest_dt_date < target_end_date` 触发增量同步；相等视为已覆盖。
    - 语法校验：执行 `python3 -m py_compile ai-fucntions/akshare-tools/postgres.py` 通过。
41. Python：新增 start_date 覆盖判断并触发增量
    - 修改文件：`ai-fucntions/akshare-tools/postgres.py`
    - 内容：在 `ensure_date_range_df` 增加对区间起始覆盖的判断，比较 `earliest_dt_date` 与交易日 `target_start_date`，若最早日期晚于起始交易日则同样触发 `sync_stock`。
    - 逻辑：`earliest_dt_date > target_start_date` 或 `latest_dt_date < target_end_date` 均触发增量；任一满足即重读区间数据。
    - 语法校验：执行 `python3 -m py_compile ai-fucntions/akshare-tools/postgres.py` 通过。
42. Python：验证分块写入缺少best时自动补写
    - 修改文件：`ai-fucntions/timesfm_inference/predict_chunked_functions.py`
    - 内容：在验证分块持久化前，若 `GET /api/v1/save-predictions/mtf-best/by-unique` 返回404，则自动调用 `POST /api/v1/save-predictions/mtf-best` 以补写 `unique_key` 对应的 timesfm-best 记录，使用验证集指标或最小payload，随后继续写入验证分块，避免外键冲突。
    - 逻辑：先检查存在性；不存在则构造 `go_payload`（包含 train/test/val 起止日期、`best_prediction_item`、`best_metrics`、`context_len`、`horizon_len` 等）进行补写；补写成功则继续写入验证分块；失败则保持原有跳过策略。
    - 语法校验：执行 `python3 -m py_compile ai-fucntions/timesfm_inference/predict_chunked_functions.py` 通过。
