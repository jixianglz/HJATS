# HJATS — AI 上下文入口文件

> 本文件是 AI 工具（Cline/Cursor）的"第一读取文件"。
> 包含项目当前状态的最精简摘要，帮助 AI 在数秒内理解上下文。

---

## 🚀 一句话定位

**HJATS** = 基于 Python 多线程的自动化交易系统，支持 **回测** 和 **实盘** Binance U本位合约。

版本: **v2.1.0** | 目录: `/home/ubuntu/HJATS/`

---

## 🧠 核心架构：三线程模块化管道

```
DriverProcessor (DP) ──queue──→ StrategyManager (SM) ──queue──→ OrderManager (OM)
  数据驱动                     策略执行                     订单管理
  + RiskManager 风控            + signalAlg                  + orderpool 增删改
  + LiveStatus 状态             + orderAlg                   + 盈亏结算
```

- 三个 `threading.Thread` 通过 `queue.Queue` 串连，每个模块独立可升级
- **回测模式**：DP 逐根推K线，queue.join 同步等待
- **实盘模式**：`run_live.py` 基于 DP/SM/OM 组装，RiskManager 监控风控
- 入口: `run.py`（回测+实盘）、`run_backtest.py`（简化回测）、`run_live.py`（实盘）

---

## 📁 关键文件路径

| 文件 | 说明 |
|------|------|
| `run.py` | 主入口（三线程 DP→SM→OM，支持回测/实盘）|
| `run_backtest.py` | 简化回测运行器（单线程，推荐）|
| `run_live.py` | **实盘入口**（基于 DP→SM→OM + RiskManager + LiveStatus）|
| `src/engine/driver.py` | DriverProcessor 数据驱动（回测+实时双模式）|
| `src/engine/strategy.py` | StrategyManager 策略执行线程 |
| `src/engine/order_manager.py` | OrderManager 订单管理线程 |
| `src/engine/order_instance.py` | OrderInstance 持仓管理 |
| `src/engine/risk_manager.py` | **RiskManager 独立风控模块**（日亏损/连续亏损/余额保护）|
| `src/engine/live_status.py` | LiveStatus 状态文件 `/tmp/live_status.json` |
| `src/data/datamanager.py` | DataManager 数据调度中心 |
| `src/data/market.py` | MarketClient Binance API |
| `src/broker/backtest_broker.py` | 回测模拟券商 |
| `src/broker/binance_broker.py` | 实盘券商 |
| `strategies/signalAlg.py` | **信号算法**（MA10/MA30交叉）|
| `strategies/orderAlg.py` | **订单算法**（多空切换，参数从 config.ini 读取）|
| `strategies/indicators.py` | 技术指标库（SMA/ROC/KST）|
| `strategies/config.ini` | 策略+风控配置 |
| `scripts/fetch_data.py` | 数据下载工具 |
| `scripts/report_generator.py` | 报告生成器（Plotly HTML）|
| `scripts/hjats_agent.py` | AI 协同接口（OpenClaw/Cline 共用）|
| `.env.example` | API Key 模板 |
| `.clinerules` | Cline 回测标准流程 |
| `requirements.txt` | 依赖清单 |

---

## 🎯 当前状态速览（2026-06-29）

### ✅ 工作正常的
- 数据下载（分批自动下载 Binance K线）
- 简化回测（`run_backtest.py` — 单线程，完整盈亏统计）
- 报告生成（Plotly HTML，`http://localhost:8081`）
- 双均线策略（MA10/30 Crossover，Frequency=5m）
- **三线程模块化架构**（DP→SM→OM，每个独立可升级）✅
- **独立风控模块** `risk_manager.py`（日亏损%/连续亏损/最低余额/日交易笔数）✅
- **测试框架**：16 tests 全部通过 ✅
- **AI 协同接口**：`scripts/hjats_agent.py` 指向 `run_live.py` ✅
- **BinanceBroker 连接验证**：$20 余额正常 ✅
- **配置外部化**：策略参数从 config.ini 读取，MongoDB 密码迁移到 .env ✅
- **回测产物统一输出到 `reports/`** ✅
- **order_size = 0.02** ✅
- **小写频率支持**（`5m` 兼容 `5MINS`）✅

### ⚠️ 需要注意的
- `modules_github/` 是旧版代码，与新 `src/` 并存
- **新实盘入口** `run_live.py` 待 OpenClaw 驱动端到端测试
- `.env` 需手动配置（已从 `.env.example` 恢复模板）

### ❌ 已清理的旧问题
1. ~~config.ini 含明文 MongoDB 密码~~ → 已修复 ✅
2. ~~策略参数硬编码~~ → 已修复 (config.ini) ✅
3. ~~实盘冷启动数据不足~~ → 已修复 (remote_init 100根) ✅
4. ~~回测文件散落根目录~~ → 已修复 (统一 reports/) ✅
5. ~~LiveEngine 单体类破坏模块化~~ → 已废弃，回归 DP/SM/OM ✅

---

## 📊 当前策略

**双均线交叉（MA Crossover）**
- MA10（快线）上穿 MA30（慢线）→ **金叉** → signal=1 → 开多
- MA10 下穿 MA30 → **死叉** → signal=-1 → 开空
- 仓位: 0.02 ETH（从 config.ini [OrderPara] 读取）
- 交易对: ETH-USD

---

## 📋 常用命令

```bash
# 下载数据
python3 scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1

# 回测
python3 run_backtest.py --data data/xxx.csv --balance 20

# 生成报告
python3 scripts/report_generator.py \
    --data-file data/xxx.csv \
    --report-json reports/xxx.json \
    --trades-csv reports/xxx_trades.csv \
    --equity-csv reports/xxx_equity.csv \
    --output-dir reports

# 启动实盘
python3 run_live.py
# 后台: nohup python3 run_live.py > /tmp/live_engine.log 2>&1 &

# 查看实盘状态
cat /tmp/live_status.json | python3 -m json.tool
python3 scripts/hjats_agent.py status

# 停止实盘
python3 scripts/hjats_agent.py stop-live

# 运行测试
python3 -m pytest tests/ -v
```

---

## 📚 更多上下文

详见 `.context/` 目录下的其他文件：
- `PROJECT_SUMMARY.md` — 项目概览、目录结构
- `ARCHITECTURE.md` — 三线程管道架构详解
- `CURRENT_STATUS.md` — 各模块详细状态
- `CHANGELOG.md` — 版本历史
- `ROADMAP.md` — 未来计划
- `STRATEGIES.md` — 策略开发指南
- `API_REFERENCE.md` — 核心 API 速查
- `COMMANDS.md` — 命令速查
- `TESTING.md` — 测试指南（16 tests）