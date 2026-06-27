# HJATS 测试指南

> 最后更新: 2026-06-27

## 概述

测试框架基于 **pytest**，覆盖交易系统的核心模块：
- 信号算法（signalAlg）
- 订单算法（orderAlg）
- 订单实例（OrderInstance）
- 技术指标（indicators）

当前共 **16 个测试**，全部通过，执行时间 < 0.3s。

---

## 运行测试

```bash
# 运行全部测试
PYTHONPATH=. python3 -m pytest tests/ -v

# 运行特定文件
PYTHONPATH=. python3 -m pytest tests/test_signal.py -v

# 带覆盖率报告
PYTHONPATH=. python3 -m pytest tests/ --cov=src --cov=strategies --cov-report=html

# 只跑失败的
PYTHONPATH=. python3 -m pytest tests/ --lf

# 遇到第一个失败就停
PYTHONPATH=. python3 -m pytest tests/ -x
```

---

## 测试文件详解

### 1. conftest.py — 共享 Fixtures

| Fixture | 用途 |
|---------|------|
| `empty_pool` | 空的订单池 `{}` |
| `account_100` | 账户余额 $100 |
| `account_0` | 账户余额 $0（测试资金不足）|
| `sample_klines_50` | 50根模拟K线（先跌后涨）|
| `short_klines_20` | 20根模拟K线（不够算MA30）|

---

### 2. test_signal.py — 信号算法测试

**被测函数**: `signalAlg.run({'dataset': df})`

| 测试 | 测什么 | 预期 |
|------|--------|------|
| `test_flat_no_signal` | 价格不变时 | signal=0（无交叉）|
| `test_insufficient_data` | K线不足31根时 | signal=0（数据不够）|

---

### 3. test_order.py — 订单算法测试

**被测函数**: `orderAlg.run(parapoll)`

| 测试 | 场景 | 预期订单 |
|------|------|----------|
| `test_signal1_open_long` | 金叉信号，空仓 | 1笔：开多 |
| `test_signal1_already_long` | 金叉信号，已有多单 | 0笔：不动 |
| `test_signal1_close_short_open_long` | 金叉信号，持有空单 | 2笔：平空 + 开多 |
| `test_signal_neg1_open_short` | 死叉信号，空仓 | 1笔：开空 |
| `test_signal_neg1_already_short` | 死叉信号，已有空单 | 0笔：不动 |
| `test_signal_0_hold` | 无信号 | 0笔：不动 |
| `test_insufficient_balance` | 余额为0 | 0笔：资金不足 |

**完整覆盖了信号×持仓的所有组合**:
```
signal=1  × (空仓 | 已多 | 已空)
signal=-1 × (空仓 | 已空 | 已多)
signal=0  × 空仓
余额=0   × signal=1
```

---

### 4. test_order_instance.py — 持仓管理测试

**被测类**: `OrderInstance(forder_list)`

| 测试 | 测什么 | 验证点 |
|------|--------|--------|
| `test_init_long` | 创建多单 | side=LONG, size=0.01, status=processing |
| `test_inc_position` | 加仓两次 | size 从 0→0.01→0.02, aveprice=2050 |
| `test_dec_position_long_profit` | 做多盈利平仓 | 2000买→2100卖, profit=+1.0 |
| `test_dec_position_long_loss` | 做多亏损平仓 | 2000买→1900卖, profit=-1.0 |

**OrderInstance 是交易系统的核心数据结构**，每个测试确保持仓数量、均价、盈亏计算正确。

---

### 5. test_indicators.py — 技术指标测试

**被测函数**: `sma()`, `break_out()`

| 测试 | 测什么 | 验证点 |
|------|--------|--------|
| `test_sma_basic` | 简单移动平均 | sma([1,2,3,4,5], 3)=2.0, sma(..., 5)=3.0 |
| `test_break_out_at_low` | 价格在窗口最低 | bull=0, bear=1 |
| `test_break_out_at_high` | 价格在窗口最高 | bull=1, bear=0 |

---

## 测试架构

```
tests/
├── __init__.py              # Python包
├── conftest.py              # 共享fixtures（样本数据、空订单池、账户）
├── test_signal.py           # 信号算法 : 2 tests
├── test_order.py            # 订单算法 : 7 tests
├── test_order_instance.py   # 持仓管理 : 4 tests
└── test_indicators.py       # 技术指标 : 3 tests
```

## 如何添加新测试

1. 在 `conftest.py` 中添加新的 fixture（如果需要样本数据）
2. 创建 `tests/test_xxx.py`，命名以 `test_` 开头
3. 测试类以 `Test` 开头，方法以 `test_` 开头
4. 使用 `pytest.approx()` 进行浮点数比较

示例:
```python
# tests/test_new.py
class TestNewFeature:
    def test_something(self, sample_klines_50, empty_pool):
        # 你的测试逻辑
        assert result == expected
```

## 已知局限

- Golden/Death Cross 精确交叉信号测试待补充（需要更复杂的K线数据构造）
- 实盘 Broker 测试待实盘验证时添加
- 回测引擎 end-to-end 集成测试待添加
- MongoDB 相关代码未测试
