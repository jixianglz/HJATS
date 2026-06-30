# Cline 对话历史演绎

> 记录 Cline（AI 编码助手）在 HJATS 项目中的所有重要改动与决策。
> 按时间倒序排列，最近的在最前面。

---

## 2026-06-30 下午 — 实盘下单失败根因修复 (OpenClaw 定位)

### 问题
13:46 金叉开多失败 → 16:22 死叉开空又失败 → 两次重启后信号穿越事件被跳过，系统不再自动开仓。

### 根因 & 修复

**1. `strategies/config.ini` [OrderPara] code 写错**
- 之前写的是 `ETH-USD`（带横杠），Binance 只认 `ETHUSDT`
- 已修复为 `ETHUSDT`

**2. `src/broker/binance_broker.py` 多余 `positionSide` 参数**
- 合约账户是单向持仓模式，不需要 `positionSide` 参数
- 已移除 `order_open()` 和 `order_close()` 中的 `'positionSide': oside`

**3. `strategies/orderAlg.py` 兜底补开仓**
- 因前两单失败重启，信号穿越事件被跳过，系统不会再自动开仓
- 新增逻辑：空仓 + MA10/MA30 方向明确且差值 > $0.5 → 自动补开仓 (CATCHUP)
- `src/engine/strategy.py` 传递 `cur_indicators` 给 orderAlg 用于兜底判断

### 清理
- `strategies/orderAlg.py` docstring 和 fallback 值 `ETH-USD` → `ETHUSDT`

---

## 2026-06-30 早间 — OM 实盘下单链路修复 & LiveLogger 接入

### 问题定位 (OpenClaw 报告)
实盘运行时 signal=1 正确产生，但 OM 从未向 Binance 提交订单（trades.csv 不存在）。
根因分析：
1. **order_instance.py**: `inc_position()`/`dec_position()` 仅处理 `dex='backtest'`，live 模式返回 `0x1`（未实现）
2. **order_manager.py**: `_process_order()` 有 `self.broker` 但从未调用 `order_open()`/`order_close()`
3. **live_logger.py**: `log_trade()` 方法存在但无人调用

### 修复

**`src/engine/order_instance.py`**:
- `inc_position()` 新增 `broker_result` 参数，优先使用 live broker 返回的成交价
- `dec_position()` 新增 `broker_result` 参数，live 模式用 broker 成交价计算盈亏
- 保持 backtest 模式完全不变（向后兼容）

**`src/engine/order_manager.py`**:
- `__init__()` 新增 `live_log` 参数
- `_process_order()` 实盘分支：先调用 `self.broker.order_open()`/`order_close()` 向 Binance 下单，拿到 `broker_result` 后传给 `OrderInstance.inc_position()`/`dec_position()`
- OPEN/CLOSE 成功后调用 `self.live_log.log_trade()` 记录成交

**`run_live.py`**:
- OM 构造时传入 `live_log=live_log`

### 测试结果
16/16 全部通过，无回归。

---

## 2026-06-30 凌晨 — 持久化 CSV 日志 & 实盘 Bug 修复

### 新增 `src/data/live_logger.py` 持久化日志模块
- 每个实盘 session 在 `reports/live_YYYYMMDD_HHMMSS/` 下创建独立目录
- 三个 csv：`strategy_ticks.csv`、`monitor_ticks.csv`、`trades.csv`
- 采用 lazy-open + flush-on-write 模式，不占用内存
- 测试 16/16 全部通过
- 集成到 `run_live.py` 主循环中

### OpenClaw 发现的 3 个运行时 Bug 修复

#### Bug 1: `order_manager.py:132` — `rawdata_show` None guard
- 实盘模式下没有可视化数据传入，`rawdata_show` 为 None
- 调用 `dm.create_rawdata_show()` 触发 AttributeError
- 修复：添加 `if rawdata_show is not None:` 保护

#### Bug 2: 线程异常 `break` → `continue`
- `order_manager.py:141` 和 `strategy.py:93` 的 except 块使用 `break`
- 单次异常导致整个线程退出（线程自杀）
- 修复：改为 `continue`，跳过单次异常继续运行

#### Bug 3: `dp_queue.join()` 死锁
- `run_live.py:208-212` 主循环调用 `dp_queue.join()`
- 实盘持续运行下 join() 永不返回，导致主线程卡死
- 修复：移除 join()，改用 `threading.Event` 机制同步

### 信号竞态条件修复
- 主循环 push 数据后立即检查 `dm.signal`，但 SM 线程尚未处理
- 导致 status 文件始终显示 signal=0
- 修复：StrategyManager 新增 `processing_done = threading.Event()`
- 主循环用 `event.wait(timeout=5)` 等待 SM 处理完毕再读取

### 指标空值修复
- `update_signal()` 传入空字典 `{}`
- 修复：提取 `dm.indicators` 中的 MA10/MA30 实际值传入

### Commit: `47ce68f`

---

## 2026-06-29 — 架构重构：废弃单体 LiveEngine，回归模块化管道

### 背景
- 此前为了实盘快速上线，将 DP/SM/OM 逻辑合并为 480 行的单体 `LiveEngine` 类
- 用户评价为"大流水账"，要求回归原始的三线程模块化设计

### 改动
- **删除** `src/engine/live_engine.py` 及 `.bak` 备份
- **删除** `tests/test_live_engine.py`
- **新建** `run_live.py` — 组装 DP/SM/OM 三线程 + RiskManager + LiveStatus
- **新建** `src/engine/risk_manager.py` — 独立风控模块
  - `check()` 返回 `{"action": "pause"|"stop"|"none", "reason": str}`
  - 监控：日亏损%、连续亏损次数、最低余额、日交易上限
- 更新 `src/engine/__init__.py`：移除 LiveEngine，新增 RiskManager
- 更新 `scripts/hjats_agent.py`：指向 `run_live.py`
- 更新 `.clinerules`：实盘命令改用 `run_live.py`
- 更新 `.context/CONTEXT_CURSOR.md` → v2.1.0

### 架构图
```
DriverProcessor (DP) ──queue──→ StrategyManager (SM) ──queue──→ OrderManager (OM)
  数据驱动                      策略执行                      订单管理
  + RiskManager 风控             + signalAlg                   + orderpool 增删改
  + LiveStatus 状态              + orderAlg                    + 盈亏结算
```

---

## 2026-06-29 — 配置外部化

### 安全修复：MongoDB 明文密码
- `strategies/config.ini` 中 `mongohost` 包含明文密码（`mongodb://admin:xxx@host`）
- 修复：迁移密码到 `.env` 的 `MONGODB_PASSWORD`
- 恢复 `.env.example` 模板（之前被错误覆盖为完整 .env）
- `DBconnection.py` 从环境变量拼接连接串

### 策略参数外部化
- `strategies/orderAlg.py` 中 `order_size = 0.01` 硬编码
- 修复：从 `config.ini` 的 `[OrderPara]` section 读取
- **最终确认 order_size = 0.02**

### 回测产物统一
- 之前回测输出散落在项目根目录
- 修复：所有产物（report JSON、trades CSV、equity CSV）输出到 `reports/`

### 小写频率兼容
- `src/utils/constants.py` 新增小写映射（`5m` → `5MINS`、`15m` → `15MINS`）
- `strategies/config.ini` 中 Frequency 从 `15m` 改为 `5m`

---

## 2026-06-29 早些时候 — BinanceBroker 连接验证

- 验证 `BinanceBroker` 能正常连接 Binance Testnet
- 确认账户余额 ~$20，API 密钥工作正常
- 确认 `src/broker/binance_broker.py` 可用

---

## 2026-06-29 之前 — 基础架构建立

- 三线程管道架构（DP→SM→OM）从 `modules_github/` 迁移到 `src/`
- 策略层分离到 `strategies/`（signalAlg、orderAlg、indicators）
- 回测系统 `run_backtest.py` 单线程简化版
- 报告生成器 `scripts/report_generator.py`（Plotly HTML）
- 数据下载 `scripts/fetch_data.py`（分批自动下载 Binance K 线）
- AI 协同接口 `scripts/hjats_agent.py`
- 测试框架 16 tests 建立

---

## 📋 关键决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 06-29 | 废弃 LiveEngine 单体类 | 用户要求回归模块化 DP/SM/OM 设计 |
| 06-29 | RiskManager 独立模块 | 风控逻辑与引擎解耦 |
| 06-29 | 移除 dp_queue.join() | 实盘持续运行下死锁 |
| 06-29 | break → continue | 防止单次异常导致线程退出 |
| 06-30 | LiveLogger 延迟写盘 | 不占内存，session 隔离 |
| 06-30 | threading.Event 同步 | 替代 queue.join 解决竞态条件 |