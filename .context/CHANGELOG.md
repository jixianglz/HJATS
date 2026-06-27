# HJATS 变更日志

> 格式: [版本号] - [日期]
> 基于 Git 提交记录 + 手动记录

---

## v2.0.0 - 2026-06-26

### ✨ 新架构（从 modules_github 重构）

- **三线程管道引擎重写**：`DriverProcessor` → `StrategyManager` → `OrderManager`
  - 基于 `queue.Queue` 的线程通信
  - 回测模式严格同步（queue.join）
  - 实盘模式 Timer 驱动
- **新目录结构**：`src/` 下按功能模块拆分
  - `src/engine/` — 三线程引擎
  - `src/data/` — 数据管理层
  - `src/broker/` — 交易所适配层
  - `src/server/` — 状态管理
  - `src/utils/` — 工具函数
  - `src/visualization/` — 可视化
- **独立回测运行器**：`run_backtest.py` — 更简单的回测入口
- **策略热插拔接口**：`signalAlg.run()` + `orderAlg.run()` 标准化

### 📊 报告生成

- **Plotly 交互式 HTML 报告**：K线图 + 买卖点 + 收益曲线 + 技术指标
- **报告目录自动组织**：`reports/bt_时间戳_数据源/`
- **手机端查看**：HTTP 服务器模式

### 🛠 工具脚本

- **`scripts/fetch_data.py`**：自动分批下载 Binance K线
- **`scripts/report_generator.py`**：回测报告可视化生成
- **`scripts/live_status.py`**：实盘状态查看

### 🤖 AI 集成

- **MCP Skills**：`hjats-data`（数据下载）和 `hjats-backtest`（回测）工具

### 🔐 安全

- `.env` 文件管理 API 密钥
- `python-dotenv` 加载环境变量

---

## v1.x（modules_github 旧版）

> 旧版代码保留在 `modules_github/` 目录中，包含：
> - 旧版 `ATSCore.py`（三线程原始实现）
> - 旧版 `ATS_BTEngine.py`（回测引擎）
> - 旧版 `FrontEnd.py` / `FrontEnd2.py` / `FrontEnd3.py`（GUI）
> - 旧版 `ATSGUI.py`
> - `UserCase/` 下的历史策略版本
> - `Controller/ATSServerCore.py`（旧版服务器）

---

## v0.1.0 - 初始版本（未记录）

初始项目创建，旧版架构。
