# HJATS — AI 上下文入口文件

> 本文件是 AI 工具（Cline/Cursor）的"第一读取文件"。
> 包含项目当前状态的最精简摘要，帮助 AI 在数秒内理解上下文。

---

## 🚀 一句话定位

**HJATS** = 基于 Python 多线程的自动化交易系统，支持 **回测** 和 **实盘** Binance U本位合约。

版本: **v2.0.0** | 目录: `/home/ubuntu/HJATS/`

---

## 🧠 核心架构：三线程管道

```
DriverProcessor (DP) →[queue]→ StrategyManager (SM) →[queue]→ OrderManager (OM)
  数据驱动                     策略执行                     订单管理
```

- 三个 `threading.Thread` 通过 `queue.Queue` 串连
- **回测模式**：DP 逐根推K线，queue.join 同步等待
- **实盘模式**：Timer 定时轮询，speed=0.1 秒间隔
- 入口: `run.py`（Runtype='1'=回测, '2'=实盘）

---

## 📁 关键文件路径

| 文件 | 说明 |
|------|------|
| `run.py` | 主入口（三线程完整版） |
| `run_backtest.py` | 简化回测运行器（单线程，推荐） |
| `src/engine/driver.py` | DriverProcessor 类 |
| `src/engine/strategy.py` | StrategyManager 类 |
| `src/engine/order_manager.py` | OrderManager 类 |
| `src/engine/order_instance.py` | OrderInstance 持仓管理 |
| `src/engine/live_engine.py` | LiveEngine 实盘引擎 |
| `src/data/datamanager.py` | DataManager 数据调度 |
| `src/data/market.py` | MarketClient Binance API |
| `src/server/ats_server.py` | ATSServer 状态管理 |
| `src/broker/backtest_broker.py` | 回测模拟券商 |
| `src/broker/binance_broker.py` | 实盘券商 |
| `strategies/signalAlg.py` | **信号算法**（MA10/MA30交叉） |
| `strategies/orderAlg.py` | **订单算法**（多空切换） |
| `strategies/indicators.py` | 技术指标库（SMA/ROC/KST） |
| `strategies/config.ini` | 策略配置 |
| `scripts/fetch_data.py` | 数据下载工具 |
| `scripts/report_generator.py` | 报告生成器 |
| `.env.example` | API Key 模板 |
| `requirements.txt` | 依赖清单 |

---

## 🎯 当前状态速览

### ✅ 工作正常的
- 数据下载（分批自动下载 Binance K线）
- 简化回测（`run_backtest.py` — 单线程，完整盈亏统计）
- 报告生成（Plotly HTML，含K线图+买卖点+收益曲线）
- 双均线策略（MA10/30 Crossover）
- 三线程引擎基本流程（DP→SM→OM）

### ⚠️ 需要注意的
- Git + 测试框架已完备 ✅
- `modules_github/` 是旧版代码，与新 `src/` 并存
- pytest 测试框架已搭建（16 tests, 4 files）✅
- 实盘模式未充分验证
- `config.ini` 含明文 MongoDB 密码

### ❌ 已知问题
1. config.ini 含明文 MongoDB 密码
2. 策略参数硬编码（0.01 ETH）
3. 0 测试金，安全风险可控
# 新增测试命令

---

## 📊 当前策略

**双均线交叉（MA Crossover）**
- MA10（快线）上穿 MA30（慢线）→ **金叉** → signal=1 → 开多
- MA10 下穿 MA30 → **死叉** → signal=-1 → 开空
- 仓位: 固定 0.01 ETH
- 交易对: ETH-USD

---

## 📋 常用命令

```bash
# 下载数据
python scripts/fetch_data.py --symbol ETHUSDT --interval 5m --days 1

# 回测
python run_backtest.py --data data/xxx.csv --balance 100

# 生成报告
python scripts/report_generator.py \
    --data-file data/xxx.csv \
    --report-json reports/xxx.json \
    --trades-csv reports/xxx_trades.csv \
    --equity-csv reports/xxx_equity.csv
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
