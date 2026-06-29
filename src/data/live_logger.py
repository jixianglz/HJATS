"""
实盘持久化日志模块 — 独立可升级

每个实盘 session 创建独立目录，CSV 追加写入:
  reports/live_YYYYMMDD_HHMMSS/
  ├── strategy_ticks.csv   # 策略 tick (timestamp, signal, ma10, ma30, close, balance)
  ├── monitor_ticks.csv    # 监控 tick (timestamp, balance, price)
  └── trades.csv           # 成交记录 (timestamp, action, side, size, price, profit)
"""
import os
import csv
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "reports")


class LiveLogger:
    """实盘 CSV 日志记录器"""

    def __init__(self, session_name: str = None):
        if session_name is None:
            session_name = f"live_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_dir = os.path.join(REPORTS_DIR, session_name)
        os.makedirs(self.session_dir, exist_ok=True)
        logger.info(f"[LiveLog] Session: {self.session_dir}")

        # 文件句柄（惰性打开）
        self._strategy_fp = None
        self._monitor_fp = None
        self._trades_fp = None
        self._strategy_writer = None
        self._monitor_writer = None
        self._trades_writer = None

    # ================================================================
    # 策略 Tick
    # ================================================================
    def log_strategy_tick(self, timestamp: str, signal: int,
                          ma10: float = None, ma30: float = None,
                          close: float = None, balance: float = None):
        if self._strategy_fp is None:
            path = os.path.join(self.session_dir, "strategy_ticks.csv")
            self._strategy_fp = open(path, 'w', newline='')
            self._strategy_writer = csv.writer(self._strategy_fp)
            self._strategy_writer.writerow(
                ["timestamp", "signal", "ma10", "ma30", "close", "balance"])
        self._strategy_writer.writerow([
            timestamp,
            signal,
            round(ma10, 2) if ma10 is not None else "",
            round(ma30, 2) if ma30 is not None else "",
            round(close, 2) if close is not None else "",
            round(balance, 2) if balance is not None else "",
        ])
        self._strategy_fp.flush()

    # ================================================================
    # 监控 Tick
    # ================================================================
    def log_monitor_tick(self, timestamp: str, balance: float, price: float,
                         risk_action: str = "", risk_reason: str = ""):
        if self._monitor_fp is None:
            path = os.path.join(self.session_dir, "monitor_ticks.csv")
            self._monitor_fp = open(path, 'w', newline='')
            self._monitor_writer = csv.writer(self._monitor_fp)
            self._monitor_writer.writerow(
                ["timestamp", "balance", "price", "risk_action", "risk_reason"])
        self._monitor_writer.writerow([
            timestamp,
            round(balance, 2),
            round(price, 2) if price else "",
            risk_action,
            risk_reason,
        ])
        self._monitor_fp.flush()

    # ================================================================
    # 成交记录
    # ================================================================
    def log_trade(self, timestamp: str, action: str, side: str,
                  size: float, price: float, profit: float = 0.0):
        if self._trades_fp is None:
            path = os.path.join(self.session_dir, "trades.csv")
            self._trades_fp = open(path, 'w', newline='')
            self._trades_writer = csv.writer(self._trades_fp)
            self._trades_writer.writerow(
                ["timestamp", "action", "side", "size", "price", "profit"])
        self._trades_writer.writerow([
            timestamp, action, side,
            round(size, 4), round(price, 2), round(profit, 4),
        ])
        self._trades_fp.flush()

    def close(self):
        for fp in (self._strategy_fp, self._monitor_fp, self._trades_fp):
            if fp:
                fp.close()
        logger.info(f"[LiveLog] Session closed: {self.session_dir}")