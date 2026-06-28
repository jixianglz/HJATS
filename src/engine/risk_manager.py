"""
风控管理器 — 独立可升级的风控模块

职责:
- 日亏损百分比限额
- 连续亏损笔数限制
- 最低余额保护
- 日交易笔数上限
- 跨天自动重置

被 DriverProcessor 或外部入口调用，与策略/订单模块解耦。
"""
import logging
from datetime import datetime
from src.utils.helpers import print_colored

logger = logging.getLogger(__name__)


class RiskManager:
    """
    独立风控模块

    与 DP/SM/OM 解耦，可单独替换升级。
    """

    def __init__(self, config: dict = None):
        self._cfg = config or {}

        # 风控阈值
        self.max_daily_loss_pct = float(self._cfg.get("risk_max_daily_loss_pct", 5.0))
        self.max_consecutive_losses = int(self._cfg.get("risk_max_consecutive_losses", 3))
        self.min_balance = float(self._cfg.get("risk_min_balance", 10.0))
        self.max_daily_trades = int(self._cfg.get("risk_max_daily_trades", 50))

        # 状态追踪
        self.consecutive_losses = 0
        self.daily_trade_count = 0
        self.daily_loss_total = 0.0
        self.last_daily_reset = datetime.now().strftime("%Y-%m-%d")
        self.paused = False
        self.stopped = False

    def on_close_profit(self, profit: float):
        """每笔平仓后更新统计"""
        self.daily_trade_count += 1
        if profit > 0:
            self.consecutive_losses = 0
        elif profit < 0:
            self.consecutive_losses += 1
            self.daily_loss_total += abs(profit)

    def check(self, balance: float, daily_start_balance: float) -> dict:
        """
        执行风控检查

        Returns:
            {"action": "pause"|"stop"|"none", "reason": str}
        """
        # 每日重置
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self.last_daily_reset:
            self.daily_trade_count = 0
            self.daily_loss_total = 0.0
            self.consecutive_losses = 0
            self.last_daily_reset = today
            logger.info("[Risk] Daily stats reset")

        # 最低余额保护（紧急停止）
        if balance < self.min_balance:
            self.stopped = True
            return {
                "action": "stop",
                "reason": f"余额 ${balance:.2f} 低于最低保护 ${self.min_balance:.2f}",
            }

        # 日亏损百分比
        if daily_start_balance > 0:
            daily_pnl = balance - daily_start_balance
            loss_pct = abs(daily_pnl) / daily_start_balance * 100
            if daily_pnl < 0 and loss_pct > self.max_daily_loss_pct:
                self.paused = True
                return {
                    "action": "pause",
                    "reason": f"当日亏损 {loss_pct:.1f}% 超过限额 {self.max_daily_loss_pct}%",
                }

        # 连续亏损笔数
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.paused = True
            return {
                "action": "pause",
                "reason": f"连续亏损 {self.consecutive_losses} 笔 超过限额 {self.max_consecutive_losses}",
            }

        # 日交易笔数上限
        if self.daily_trade_count >= self.max_daily_trades:
            self.paused = True
            return {
                "action": "pause",
                "reason": f"日交易 {self.daily_trade_count} 笔已达上限",
            }

        return {"action": "none", "reason": ""}