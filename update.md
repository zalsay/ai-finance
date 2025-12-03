## 更新内容 - 2025-12-03

### 44. 前端优化：预测卡片信息展示升级
- **修改文件**：
    - `fintrack-front/types.ts`: 在 `StockPrediction` 接口中新增 `modelName`, `contextLen`, `horizonLen` 字段。
    - `fintrack-front/components/dashboard/Dashboard.tsx`: 在数据映射时填充上述新字段。
    - `fintrack-front/components/dashboard/StockPredictionCard.tsx`: 重构预测信息展示区域。
- **效果**：
    - 将原有的单行文本描述替换为三个独立的徽章（Badge）样式展示：
        - **模型 (Model)**: 显示最佳模型名称（如 `mtf-0.4`），使用主题色高亮。
        - **上下文 (Context)**: 显示上下文长度（如 `8K`），配以内存图标。
        - **预测周期 (Horizon)**: 显示预测天数（如 `7天`），配以日历图标。
    - 增加了标签说明（Label）和图标，使信息层级更清晰，视觉效果更突出。
    - 保留了旧版文本作为回退显示方案。

### 45. timesfm_inference：改为使用均方差聚合
- **修改文件**：
    - `ai-fucntions/timesfm_inference/predict_chunked_functions.py`
- **变更内容**：
    - 将 `avg_return_diff` 与 `avg_mle` 的计算由 `np.mean(...)` 改为 `np.var(...)`，即采用均方差（方差）作为聚合指标；空列表仍回退为 `float('inf')`。
- **效果**：
    - 更强调不同分块间波动性与稳定性，综合评分中对涨跌幅差异与 MLE 的权重保持不变，但度量从均值改为方差，更适合筛选稳定性更高的预测项。

### 46. 数据预处理：修复 start_date 为空与日期格式不一致
- **修改文件**：
    - `ai-fucntions/preprocess_data/processor.py`
- **变更内容**：
    - 新增统一日期解析与归一化方法，支持 `YYYY-MM-DD` 与 `YYYYMMDD` 两种输入格式。
    - `end_date` 默认使用昨天并规范为 `YYYYMMDD`；`start_date` 为空时根据 `years` 回溯计算并规范为 `YYYYMMDD`；若不为空也进行格式归一化。
    - 增加 `start_date > end_date` 的纠偏逻辑，确保区间有效。
- **效果**：
    - 解决 `start_date` 为空导致的错误，并避免日期格式不一致导致的数据读取失败或日志显示异常。

### 47. PG区间读取：取消最早日期覆盖判断
- **修改文件**：
    - `ai-fucntions/akshare-tools/postgres.py`
- **变更内容**：
    - 在 `ensure_date_range_df` 中移除“最早日期未覆盖到目标起始交易日”的判断与对应增量同步逻辑，仅保留对最新日期（区间末端）的覆盖校验与增量。
- **效果**：
    - 避免无意义的向前回补触发，减少不必要的增量同步与异常日志（例如出现 `20251202~20251201` 的区间），提升数据拉取的稳定性。

### 48. 前端卡片：统一上下文长度显示规则
- **修改文件**：
    - `fintrack-front/components/dashboard/StockPredictionCard.tsx`
- **变更内容**：
    - 徽章“上下文”显示与 `Dashboard.tsx` 的分析字符串一致：小于 `1024` 直接显示数值；否则显示 `Math.round(value/1024)+'K'`；空值显示为 `?`。
- **效果**：
    - 前后两处展示规则一致，避免 `512` 被显示为 `1K` 的不一致情况，提升信息准确性与一致性。

### 49. 前端优化：支持授权错误自动跳转登录（全面覆盖）
- **修改文件**：
    - `fintrack-front/App.tsx`
    - `fintrack-front/components/dashboard/Dashboard.tsx`
    - `fintrack-front/components/watchlist/Watchlist.tsx`
    - `fintrack-front/components/dashboard/AddStockModal.tsx`
    - `fintrack-front/contexts/LanguageContext.tsx`
- **变更内容**：
    - `App.tsx`: 修复 `handleAuthError` 初始化顺序问题，确保在 `fetchPredictions` 调用前已定义；实现“显示模态框 -> 延迟1.5秒 -> 跳转登录”的平滑流程；在数据请求（`fetchPredictions`）捕获到授权错误（Authorization/401）时，**自动触发**该流程，不再设置错误状态。
    - `Watchlist.tsx` / `AddStockModal.tsx`: 在捕获到 API 授权错误时，**优先触发** `onAuthError` 进行自动跳转，而非显示错误信息。
    - `LanguageContext.tsx`: 新增 `auth.sessionExpired` 和 `auth.redirectingLogin` 多语言字段。
- **效果**：
    - 当用户遇到认证错误（如 Token 过期、Authorization header required）时，系统会**自动**弹出全屏提示框告知“会话已过期”，并自动跳转至登录页，无需用户手动点击错误提示，体验更加智能流畅。

### 50. 前端优化：修复图标加载闪烁问题 (FOUC)
- **修改文件**：
    - `fintrack-front/index.html`
- **变更内容**：
    - 将 Google Fonts 引用链接中的 `display` 参数设为 `block`，并补充完整的 `Material Symbols Outlined` 字体参数。
    - 在 `<style>` 中完善 `.material-symbols-outlined` 类的 CSS 定义，显式指定 `font-family` 及防抖动属性（`white-space: nowrap`, `overflow: hidden` 等）。
- **效果**：
    - 解决了 Landing 页及应用内图标在字体加载前短暂显示文本（如 "trending_up"）的问题。现在图标在字体加载完成前会保持隐藏，加载完成后立即显示，消除了视觉上的突兀感。
