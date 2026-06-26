#!/usr/bin/env python3
"""
实盘状态管理器 — 实时保存和查询运行状态

状态文件: /tmp/live_status.json (每 monitor_interval 秒更新一次)
          /tmp/live_engine.log (日志)
"""
import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

STATUS_FILE = "/tmp/live_status.json"


def default_status(balance: float = 0) -> dict:
    """返回默认状态结构"""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "engine_running": False,
        "engine_paused": False,
        "account": {
            "balance": balance,
            "floating_pl": 0.0,
            "equity": balance,
            "daily_pnl": 0.0,
            "daily_max_dd": 0.0,
            "peak_equity": balance,
        },
        "position": {
            "side": None,  # LONG / SHORT / None
            "size": 0.0,
            "entry_price": 0.0,
            "current_price": 0.0,
            "unrealized_pl": 0.0,
        },
        "signal": {
            "value": 0,
            "indicators": {},
        },
        "engine": {
            "strategy_interval": 300,
            "monitor_interval": 30,
            "strategy_last_run": None,
            "monitor_last_run": None,
            "strategy_ok": True,
            "monitor_ok": True,
            "errors": [],
        },
        "daily": {
            "trade_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "start_balance": balance,
            "start_date": datetime.now().strftime("%Y-%m-%d"),
        },
        "last_orders": [],  # 最近5笔订单
    }


class LiveStatus:
    """实盘状态管理器"""

    def __init__(self, initial_balance: float = 0):
        self.data = default_status(initial_balance)
        self._load()

    def _load(self):
        """从文件恢复状态"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    saved = json.load(f)
                    # 保留关键运行状态，不覆盖配置
                    for k in ['account', 'position', 'signal', 'daily']:
                        if k in saved:
                            self.data[k].update(saved[k])
                    logger.info("Live status restored from %s", STATUS_FILE)
            except Exception as e:
                logger.warning("Failed to load live status: %s", e)

    def save(self):
        """保存状态到文件"""
        self.data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(STATUS_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save live status: %s", e)

    # ========== 更新方法 ==========

    def update_account(self, balance: float, floating_pl: float):
        """更新账户状态"""
        d = self.data["account"]
        d["balance"] = round(balance, 2)
        d["floating_pl"] = round(floating_pl, 2)
        equity = balance + floating_pl
        d["equity"] = round(equity, 2)

        # 每日盈亏
        start_balance = d.get("daily_start", balance)
        d["daily_pnl"] = round(equity - start_balance, 2)

        # 最大回撤
        peak = max(d.get("peak_equity", equity), equity)
        d["peak_equity"] = peak
        dd = peak - equity
        if dd > 0:
            d["daily_max_dd"] = round(max(d.get("daily_max_dd", 0), dd), 2)

    def update_position(self, side, size, entry_price, current_price):
        """更新持仓状态"""
        p = self.data["position"]
        p["side"] = side
        p["size"] = size
        p["entry_price"] = round(entry_price, 2) if entry_price else 0
        p["current_price"] = round(current_price, 2) if current_price else 0
        if side and size > 0:
            if side == "LONG":
                p["unrealized_pl"] = round((current_price - entry_price) * size, 2)
            else:
                p["unrealized_pl"] = round((entry_price - current_price) * size, 2)
        else:
            p["unrealized_pl"] = 0.0

    def update_signal(self, signal: int, indicators: dict):
        """更新信号状态"""
        self.data["signal"]["value"] = signal
        self.data["signal"]["indicators"] = {
            k: round(v, 2) if isinstance(v, float) else v
            for k, v in indicators.items()
        }

    def add_order(self, order: dict):
        """记录一笔订单"""
        orders = self.data["last_orders"]
        orders.insert(0, order)
        if len(orders) > 10:
            orders.pop()
        self.data["daily"]["trade_count"] += 1
        if order.get("profit", 0) > 0:
            self.data["daily"]["win_count"] += 1
        elif order.get("profit", 0) < 0:
            self.data["daily"]["loss_count"] += 1

    def set_engine_status(self, field: str, value):
        """设置引擎状态字段"""
        self.data["engine"][field] = value

    def add_error(self, error_msg: str):
        """记录错误"""
        errors = self.data["engine"]["errors"]
        errors.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "msg": str(error_msg),
        })
        if len(errors) > 20:
            errors.pop(0)

    def get(self) -> dict:
        """获取当前状态快照"""
        return self.data

    def get_summary(self) -> str:
        """获取格式化的状态摘要"""
        d = self.data
        lines = [
            "=" * 60,
            f"  实盘状态  ({d['timestamp']})",
            "=" * 60,
            f"  运行状态:   {'▶ 运行中' if d['engine_running'] else '⏹ 已停止'}"
            f"{' (暂停)' if d['engine_paused'] else ''}",
            "─" * 60,
            f"  账户余额:   ${d['account']['balance']:.2f}",
            f"  浮动盈亏:   ${d['account']['floating_pl']:+.2f}",
            f"  当前权益:   ${d['account']['equity']:.2f}",
            "─" * 60,
        ]

        pos = d["position"]
        if pos["side"] and pos["size"] > 0:
            lines += [
                f"  持仓:        {pos['side']} {pos['size']} ETH @ ${pos['entry_price']:.2f}",
                f"  当前价:      ${pos['current_price']:.2f}",
                f"  未实现盈亏:  ${pos['unrealized_pl']:+.2f}",
            ]
        else:
            lines.append(f"  持仓:        无")

        sig = d["signal"]
        sig_text = {1: "看多 🟢", -1: "看空 🔴", 0: "无信号"}.get(sig["value"], str(sig["value"]))
        lines += [
            "─" * 60,
            f"  信号:        {sig_text}",
        ]
        if sig["indicators"]:
            for k, v in sig["indicators"].items():
                lines.append(f"    {k}:        {v}")

        eng = d["engine"]
        lines += [
            "─" * 60,
            f"  策略循环:    {'✅' if eng['strategy_ok'] else '❌'}  (上次: {eng['strategy_last_run'] or 'N/A'})",
            f"  监控循环:    {'✅' if eng['monitor_ok'] else '❌'}  (上次: {eng['monitor_last_run'] or 'N/A'})",
        ]

        daily = d["daily"]
        lines += [
            "─" * 60,
            f"  今日交易:    {daily['trade_count']} (胜: {daily['win_count']} 负: {daily['loss_count']})",
            f"  今日盈亏:    ${d['account']['daily_pnl']:+.2f}",
            f"  今日最大回撤: ${d['account']['daily_max_dd']:.2f}",
            "=" * 60,
        ]
        return "\n".join(lines)
