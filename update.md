### 61. 后端优化：策略公开性字段支持
- **功能改进**：
    - 数据库 `timesfm_strategy_params` 表新增 `is_public` 字段，用于明确标识官方/公开策略。
    - 插入/更新了3个官方策略（Conservative, Balanced, Aggressive），并设置 `is_public=1`。
    - 后端 `GetUserStrategies` 接口更新，支持返回 `is_public` 字段，并基于 `is_public` 进行筛选和排序。
- **修改文件**：
    - `fintrack-api/models/stock.go`: `StrategyParams` 结构体新增 `IsPublic` 字段。
    - `fintrack-api/services/watchlist_service.go`: 更新 SQL 查询以支持 `is_public`。
    - `migration_strategies.sql`: 数据库迁移脚本。

### 62. 前端适配：使用 is_public 字段
- **功能改进**：
    - 前端 `StrategyParams` 类型定义新增 `is_public` 字段。
    - `Portfolio` 和 `BindStrategyModal` 组件更新逻辑，优先使用 `is_public === 1` 来判定官方策略。
    - `StrategyCard` 组件更新逻辑，使用 `is_public` 字段显示“官方推荐”或“个人策略”标签。
- **修改文件**：
    - `fintrack-front/types.ts`: 更新接口定义。
    - `fintrack-front/components/portfolio/Portfolio.tsx`: 更新分组逻辑。
    - `fintrack-front/components/portfolio/BindStrategyModal.tsx`: 更新 Tab 筛选逻辑。
    - `fintrack-front/components/dashboard/StrategyCard.tsx`: 更新 Badge 显示逻辑。

### 63. UI交互优化：策略展示与绑定
- **功能改进**：
    - `Portfolio` 页面顶部的策略列表区域逻辑重构：不再仅显示当前持仓绑定的策略，而是显示**所有可用策略**（包括官方推荐和个人策略）。
    - 修复了官方推荐策略行不显示的问题（现在基于 `userStrategies` 列表渲染）。
    - `Portfolio` 页面底部的策略绑定列表操作按钮文案优化：
        - 未绑定时显示：“绑定” / “Bind”。
        - 已绑定时显示：“换绑” / “Change”。
        - 移除了按钮上冗余的策略名称显示（策略名称已在“当前策略”列显示）。
- **修改文件**：
    - `fintrack-front/components/portfolio/Portfolio.tsx`: 重构策略列表渲染逻辑，更新绑定按钮文案。

### 64. 策略详情UI及权限优化
- **功能改进**：
    - **官方策略标识修复**：后端 `GetStrategyParamsByUniqueKey` 接口补充返回 `is_public` 字段，确保前端能正确识别并显示“官方推荐”标签。
    - **UI 细节调整**：
        - `StrategyCard` 中的买卖阈值分隔符由 `/` 改为 `|`。
        - `AddStrategyModal` 中的复选框勾选颜色调整为特定的绿色 (`#91caae`)，与登录页保持一致。
    - **权限控制**：
        - 官方策略（`is_public=1`）隐藏编辑/设置按钮，禁止用户修改。
- **修改文件**：
    - `fintrack-api/services/watchlist_service.go`: 修复 `GetStrategyParamsByUniqueKey` 查询字段。
    - `fintrack-front/components/dashboard/StrategyCard.tsx`: 更新分隔符及编辑按钮显示逻辑。
    - `fintrack-front/components/dashboard/AddStrategyModal.tsx`: 更新 Checkbox 样式。

### 65. 前端性能优化：本地打包 Icon 字体
- **功能改进**：
    - **本地化图标字体**：将 `Material Symbols` 图标字体从 Google CDN 改为本地 npm 包 (`material-symbols`) 引入。
    - **解决样式闪烁**：修复了页面加载时图标短暂显示为文字名称 (Flash of Unstyled Content) 的问题。
    - **构建优化**：字体文件现包含在项目构建产物中，减少外部网络依赖。
- **修改文件**：
    - `fintrack-front/package.json`: 新增依赖 `material-symbols`。
    - `fintrack-front/index.tsx`: 引入 `material-symbols/outlined.css`。
    - `fintrack-front/index.html`: 移除 Google Fonts CDN 链接及内联 CSS 样式。

### 66. UI 细节修复：官方策略标识与操作限制
- **功能改进**：
    - **修复官方策略标识**：调整 `StrategyCard` 中官方策略（`is_public === 1`）的判断逻辑，确保正确显示“官方推荐”标签（此前误显示为“个人策略”）。
    - **操作按钮优化**：严格隐藏官方策略卡片右上角的设置按钮，防止误操作。
    - **绑定列表显示优化**：在 `Portfolio` 页面的策略绑定列表中，为策略名称添加“官方”/“个人”标签，便于用户快速区分。
    - **一致性调整**：统一 `Portfolio` 和 `BindStrategyModal` 中的买卖阈值分隔符为 `|`。
- **修改文件**：
    - `fintrack-front/components/dashboard/StrategyCard.tsx`: 优化 `is_public` 判断条件及按钮显示逻辑。
    - `fintrack-front/components/portfolio/Portfolio.tsx`: 添加策略类型标签，统一分隔符。
    - `fintrack-front/components/portfolio/BindStrategyModal.tsx`: 统一分隔符。

### 67. Watchlist 功能增强：图表预览
- **功能改进**：
    - **预测图表组件化**：将 `StockPredictionCard` 中的图表逻辑提取为独立的 `PredictionChart` 组件，实现复用。
    - **关注列表图表按钮**：在 Watchlist 表格操作列新增“查看图表”按钮。
    - **图表模态框**：点击按钮后弹窗显示该股票的预测图表（复用首页预测数据），保持与首页一致的视觉体验和交互（Tooltip、平滑曲线等）。
- **修改文件**：
    - `fintrack-front/components/common/PredictionChart.tsx`: 新建通用图表组件。
    - `fintrack-front/components/dashboard/StockPredictionCard.tsx`: 使用通用组件替换内部实现。
    - `fintrack-front/components/watchlist/Watchlist.tsx`: 新增图表按钮及模态框逻辑。

### 68. Watchlist 图表详情增强
- **功能改进**：
    - **详情弹窗升级**：Watchlist 图表弹窗扩大至 `max-w-5xl`，图表高度增加至 `350px`，提供更清晰的查看体验。
    - **完整预测数据**：弹窗内补充显示所有预测徽章卡片（模型、上下文、预测周期、最大偏差、置信度、实际涨跌、预测涨跌），内容与 Dashboard 卡片完全一致。
    - **数据一致性**：同步 Dashboard 的计算逻辑，确保弹窗内的“实际涨跌” (Act Chg) 和“预测涨跌” (Pred Chg) 基于预测周期数据计算，而非当日实时数据，避免误导。
- **修改文件**：
    - `fintrack-front/components/watchlist/Watchlist.tsx`: 更新弹窗布局、补充徽章渲染逻辑、同步数据计算逻辑。

### 69. 中英文显示修复：预测指标标签
- **功能改进**：
    - 修复了 `StockPredictionCard` 和 `Watchlist` 图表弹窗中“实际涨跌” (Act Chg) 和“预测涨跌” (Pred Chg) 标签无法正确切换中英文的问题。
    - 在 `LanguageContext` 中新增了 `prediction.actChg` 和 `prediction.predChg` 翻译键值对。
- **修改文件**：
    - `fintrack-front/contexts/LanguageContext.tsx`: 新增翻译键值。
    - `fintrack-front/components/dashboard/StockPredictionCard.tsx`: 更新标签使用正确的翻译键。
    - `fintrack-front/components/watchlist/Watchlist.tsx`: 更新标签使用正确的翻译键。

### 70. 版本控制维护：Git 远程与分支状态检查
- **维护说明**：
    - 当前配置存在两个远程：`origin`（公司内部 Git 服务器）和 `main`（GitHub）。
    - 本地分支：`main`，跟踪 `origin/main`，工作区干净（无未提交更改）。
    - 远程跟踪分支：`remotes/origin/main` 与 `remotes/main/main` 同名但指向不同远程；`main` 远程分支落后于 `origin`。
- **建议**：
    - 如无需同时使用两个远程，可保留 `origin` 并移除 `main`（`git remote remove main`），或将 `main` 重命名为更清晰的别名（例如 `github`）。
    - 明确推送目标：对内用 `git push origin main`，对外用 `git push main main`。

### 71. 版本控制维护：重命名远程为 github 并同步内部
- **操作**：
    - 已将远程 `main` 重命名为 `github`，并完成 `git fetch --all`。
    - 尝试将 `origin/main`（公司内部）同步至 `github/main`（GitHub）。
- **结果**：
    - 推送被 GitHub Push Protection 拦截，检测到仓库包含密钥（Tencent Cloud Secret ID）。
    - 关联文件路径：`ai-fucntions/akshare-tools/get_finanial_data.py`（Blob: `05be387b58a8f2a7005b322c352fc5db168d67ed`）。
- **后续建议**：
    - 从代码中移除硬编码密钥，改为读取环境变量，并对相关密钥进行轮换（禁用旧密钥，生成新密钥）。
    - 使用 `git filter-repo` 或 BFG 对历史提交进行清洗，彻底移除敏感信息后再执行推送。
    - 对超过 50MB 的大文件（例如 `ai-fucntions/akshare-server/pyarrow/libarrow.so.1500`）采用 Git LFS 管理。

### 72. 版本控制：仅同步内部最新成果到 GitHub（无历史）
- **操作**：
    - 新建无历史分支 `internal-sync`（orphan），提交当前工作区快照，避免旧历史中的敏感信息被扫描。
    - 推送至 `github` 远程：`github/internal-sync`。
- **代码安全**：
    - `ai-fucntions/akshare-tools/get_finanial_data.py` 中 SCF 调用改为从环境变量读取密钥：`TENCENT_SECRET_ID`、`TENCENT_SECRET_KEY`、`TENCENT_REGION`、`TENCENT_TOKEN`。
- **链接**：
    - 可在此创建 PR 同步到 GitHub 主线：https://github.com/zalsay/ai-finance/pull/new/internal-sync
### 73. GitHub PR：internal-sync 分支创建与合并操作指南
- **目标**：将 `internal-sync`（无历史快照）合并到 `main`，同步内部最新成果。
- **在线创建与合并**：
    - 打开链接：https://github.com/zalsay/ai-finance/pull/new/internal-sync
    - Base 选择 `main`，Compare 选择 `internal-sync`。
    - 审阅 Files changed，重点检查：
        - 无硬编码密钥（已改为环境变量读取）。
        - 超大二进制文件是否需要 LFS 管理。
    - 合并策略：建议使用 “Squash and merge”。
- **命令行（如安装 gh CLI）**：
    - `gh pr create --base main --head internal-sync --title "Sync internal snapshot to main" --body "无历史快照，同步内部最新成果；后续清洗历史与LFS迁移。"`
    - `gh pr merge --squash --delete-branch`

### 74. GitHub PR：解决“无可比较（不同历史）”的方案
- **问题**：GitHub 显示 “There isn’t anything to compare. main and internal-sync are entirely different commit histories.”
- **处理**：在本地为 `internal-sync` 创建一个“合成的合并基”（synthetic merge base），使其与 `main` 共享一个共同祖先，从而可创建 PR。
    - 执行：
        - `git fetch github main`
        - `git checkout internal-sync`
        - `git merge -s ours github/main -m "synthetic merge base: enable PR between unrelated histories"`
        - `git push github internal-sync`
- **效果**：不改变 `internal-sync` 的文件内容，仅创建一个可比较的合并祖先；随后即可在 GitHub 上正常创建 PR 并选择 “Squash and merge”。
### 76. 版本控制维护：清理历史同步分支
- **背景**：为解决 GitHub 无法比较不同历史分支的问题，已采用 `sync-compare` 作为基于 `main` 的比较分支。
- **清理**：
    - 删除 GitHub 远程分支：`internal-sync`、`sync-to-main`。
    - 删除本地分支：`internal-sync`（`sync-to-main` 本地不存在无需删除）。
- **当前建议分支**：使用 `sync-compare` 在 GitHub 发起 PR 合并到 `main`。
