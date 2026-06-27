#!/usr/bin/env python3
"""
实盘引擎 — 双循环设计

StrategyTick (策略执行循环):
  - 频率: config.ini 中 strategy_interval (默认300秒=5分钟)
  - 触发: 到时运行
  - 操作: 拉取最新K线 → signalAlg → orderAlg → 执行订单

MonitorTick (监控查询循环):
  - 频率: config.ini 中 monitor_interval (默认30秒)
  - 触发: 到时运行
  - 操作: 查最新价格 → 计算浮盈 → 更新状态 → 检查风控

启动方式:
  nohup python3 -m src.engine.live_engine > /tmp/live_engine.log 2>&1 &
"""
import os
import sys
import json
import time
import logging
import threading
import configparser
from datetime import datetime

import pandas as pd

# HJATS 项目路径
HJATS_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if HJATS_PATH not in sys.path:
    sys.path.insert(0, HJATS_PATH)

from src.engine.live_status import LiveStatus, STATUS_FILE
from src.broker.binance_broker import BinanceBroker
from src.data.market import MarketClient
from src.utils.helpers import print_colored
from strategies import signalAlg, orderAlg

logger = logging.getLogger(__name__)


class LiveEngine:
    """
    实盘引擎主控

    启动两个定时器线程:
    - _strategy_tick: 策略执行
    - _monitor_tick:  监控查询
    """

    def __init__(self, config_path: str = None):
        self.running = False
        self.paused = False

        # 配置
        if config_path is None:
            config_path = os.path.join(HJATS_PATH, "strategies", "config.ini")
        self.config_path = config_path
        self.conf = configparser.ConfigParser()
        self._load_config()

        # 策略参数
        self.code = self.conf.get("AlgPara", "Code", fallback="ETHUSDT")
        self.frequency = self.conf.get("AlgPara", "Frequency", fallback="5m")
        self.strategy_interval = self.conf.getint("LiveEngine", "strategy_interval", fallback=300)
        self.monitor_interval = self.conf.getint("LiveEngine", "monitor_interval", fallback=30)
        self.risk_max_daily_loss_pct = self.conf.getfloat("LiveEngine", "risk_max_daily_loss_pct", fallback=5.0)
        self.risk_max_position = self.conf.getfloat("LiveEngine", "risk_max_position", fallback=0.05)

        # 组件
        self.broker = BinanceBroker()
        self.market = MarketClient(dex_name="binance")
        self.status = LiveStatus()

        # 策略状态
        self.storj = None
        self.indicators = {f"ind{i}": [] for i in range(1, 11)}
        self.indicators_w2 = {f"ind{i}": [] for i in range(1, 11)}
        self.order_stat = {"totalnumber": 0, "win_num": 0, "loss_num": 0,
                           "finish_num": 0, "holding_num": 0}
        self.order_pool = {}  # uid -> dict
        self.balance = 0.0

        # 线程控制
        self._strategy_timer = None
        self._monitor_timer = None
        self._stop_event = threading.Event()

        print_colored(f"[LiveEngine] 初始化完成: code={self.code}, freq={self.frequency}, "
                      f"strategy={self.strategy_interval}s, monitor={self.monitor_interval}s",
                      bg_color="blue")

    def _load_config(self):
        """加载配置"""
        if os.path.exists(self.config_path):
            self.conf.read(self.config_path)
        else:
            logger.warning("Config not found: %s", self.config_path)

    def start(self):
        """启动实盘引擎"""
        if self.running:
            print_colored("[LiveEngine] 引擎已在运行", bg_color="yellow")
            return

        self.running = True
        self._stop_event.clear()

        # 检查账户
        try:
            self.balance = float(self.broker.check_balance())
            print_colored(f"[LiveEngine] 账户余额: ${self.balance:.2f}", bg_color="green")
            self.status.data["account"]["daily_start"] = self.balance
        except Exception as e:
            logger.error("Failed to check balance: %s", e)
            print_colored(f"[LiveEngine] 余额检查失败: {e}", bg_color="red")
            self.running = False
            return

        # 启动双循环
        self.status.data["engine_running"] = True
        self.status.data["engine_paused"] = False
        self.status.save()

        self._schedule_strategy()
        self._schedule_monitor()

        print_colored("[LiveEngine] ▶ 引擎已启动", bg_color="green", bold=True)
        print_colored(f"  Strategy: 每 {self.strategy_interval}s 执行一次", bg_color="green")
        print_colored(f"  Monitor:  每 {self.monitor_interval}s 查询一次", bg_color="green")

    def stop(self):
        """停止引擎"""
        print_colored("[LiveEngine] ⏹ 正在停止引擎...", bg_color="yellow")
        self.running = False
        self._stop_event.set()
        self._cancel_timers()
        self.status.data["engine_running"] = False
        self.status.save()
        print_colored("[LiveEngine] 引擎已停止", bg_color="red")

    def pause(self):
        """暂停策略执行（保留监控）"""
        if not self.running:
            return
        self.paused = True
        self.status.data["engine_paused"] = True
        self.status.save()
        print_colored("[LiveEngine] ⏸ 策略已暂停（监控继续）", bg_color="yellow")

    def resume(self):
        """恢复策略执行"""
        self.paused = False
        self.status.data["engine_paused"] = False
        self.status.save()
        print_colored("[LiveEngine] ▶ 策略已恢复", bg_color="green")
        if not self._strategy_timer or not self._strategy_timer.is_alive():
            self._schedule_strategy()

    def _cancel_timers(self):
        """取消所有定时器"""
        if self._strategy_timer:
            self._strategy_timer.cancel()
        if self._monitor_timer:
            self._monitor_timer.cancel()

    # ================================================================
    # 策略循环 (StrategyTick)
    # ================================================================

    def _schedule_strategy(self):
        """调度下一次策略执行"""
        if self._stop_event.is_set():
            return
        self._strategy_timer = threading.Timer(self.strategy_interval, self._strategy_tick)
        self._strategy_timer.daemon = True
        self._strategy_timer.start()

    def _strategy_tick(self):
        """策略执行: 拉取K线 → 计算信号 → 执行订单"""
        if not self.running or self._stop_event.is_set():
            return

        try:
            # 1. 拉取最新K线
            candles = self.market.get_price_v1(
                code=self.code, count=2, frequency=self.frequency
            )
            if candles is None or len(candles) == 0:
                logger.warning("No new candles")
                self.status.set_engine_status("strategy_ok", False)
                self.status.add_error("获取K线失败")
                self._schedule_strategy()
                return

            # 2. 更新 storj
            new_candle = candles.iloc[[-1]]
            if self.storj is None:
                self.storj = new_candle[::-1]  # 倒序
            else:
                # 检查是否有新K线
                new_time = str(new_candle.index[0])
                if new_time == str(self.storj.index[0]):
                    # 同一根K线，只更新价格
                    self.storj.iloc[0] = new_candle.iloc[0]
                    self._schedule_strategy()
                    return

                # 新K线
                self.storj = pd.concat([new_candle[::-1], self.storj])
                if len(self.storj) > 100:
                    self.storj = self.storj.drop(self.storj.tail(1).index)

            # 3. 运行信号算法
            signal, cur_ind, w2_ind = signalAlg.run({
                "dataset": self.storj,
                "indicatorsdic": self.indicators,
                "indicatorsdic_w2": self.indicators_w2,
            })

            # 4. 更新指标缓存
            for k in list(self.indicators.keys()):
                if len(self.indicators[k]) >= 100:
                    del self.indicators[k][0]
            for k, v in cur_ind.items():
                if k in self.indicators:
                    self.indicators[k].append(v)

            # 5. 更新信号状态
            self.status.update_signal(signal, cur_ind)

            # 6. 如果暂停，不执行订单
            if self.paused:
                self.status.set_engine_status("strategy_last_run",
                    datetime.now().strftime("%H:%M:%S"))
                self.status.set_engine_status("strategy_ok", True)
                self.status.save()
                self._schedule_strategy()
                return

            # 7. 运行订单算法
            current_price = float(self.storj.iloc[0]["close"])
            orders = orderAlg.run({
                "c_signal": signal,
                "dataset": self.storj,
                "orderpool": self.order_pool,
                "orderaccount": {"asset": self.balance, "profit": 0},
                "order_statistic": self.order_stat,
            })

            # 8. 执行订单
            for order in orders:
                oside = order["oside"]
                osize = float(order["osize"])
                oaction = order["oaction"]

                if oaction == "OPEN":
                    # 检查风控
                    if osize > self.risk_max_position:
                        logger.warning("Order size %s exceeds max %s", osize, self.risk_max_position)
                        continue

                    result = self.broker.order_open(
                        code=self.code,
                        oside=oside,
                        otype="MARKET",
                        osize=osize,
                    )
                    if result["success"]:
                        self.status.add_order({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "action": "OPEN", "side": oside,
                            "size": osize, "price": current_price,
                        })
                        print_colored(f"[LiveEngine] 🟢 开仓 {oside} {osize} @ ${current_price:.2f}",
                                      bg_color="green", bold=True)

                elif oaction == "CLOSE":
                    result = self.broker.order_close(
                        code=self.code,
                        oside=oside,
                        otype="MARKET",
                        osize=osize,
                    )
                    if result["success"]:
                        # 计算实际盈亏（简化）
                        entry = self.order_pool.get(order["uid"], {}).get("entry_price", current_price)
                        profit = (current_price - entry) * osize if oside == "LONG" else (entry - current_price) * osize
                        self.balance += profit
                        self.status.add_order({
                            "time": datetime.now().strftime("%H:%M:%S"),
                            "action": "CLOSE", "side": oside,
                            "size": osize, "price": current_price,
                            "profit": round(profit, 4),
                        })
                        print_colored(f"[LiveEngine] 🔴 平仓 {oside} {osize} @ ${current_price:.2f} "
                                      f"盈亏: ${profit:+.4f}", bg_color="red", bold=True)

            # 9. 更新状态
            self.status.update_account(self.balance, 0)
            self.status.update_position(
                side=None, size=0, entry_price=0, current_price=current_price
            )
            self.status.set_engine_status("strategy_last_run",
                datetime.now().strftime("%H:%M:%S"))
            self.status.set_engine_status("strategy_ok", True)
            self.status.save()

            logger.info("Strategy tick done: signal=%s, orders=%s", signal, len(orders))

        except Exception as e:
            logger.exception("Strategy tick error: %s", e)
            self.status.set_engine_status("strategy_ok", False)
            self.status.add_error(f"策略执行错误: {e}")
            self.status.save()

        self._schedule_strategy()

    # ================================================================
    # 监控循环 (MonitorTick)
    # ================================================================

    def _schedule_monitor(self):
        """调度下一次监控查询"""
        if self._stop_event.is_set():
            return
        self._monitor_timer = threading.Timer(self.monitor_interval, self._monitor_tick)
        self._monitor_timer.daemon = True
        self._monitor_timer.start()

    def _monitor_tick(self):
        """监控查询: 最新价格 → 计算浮盈 → 检查风控"""
        if not self.running or self._stop_event.is_set():
            return

        try:
            # 1. 获取最新价格
            candles = self.market.get_price_v1(
                code=self.code, count=1, frequency="1m"
            )
            if candles is not None and len(candles) > 0:
                current_price = float(candles.iloc[-1]["close"])
            else:
                current_price = 0.0

            # 2. 检查账户余额
            try:
                self.balance = float(self.broker.check_balance())
            except Exception:
                pass

            # 3. 更新状态
            self.status.update_account(self.balance, 0)
            self.status.set_engine_status("monitor_last_run",
                datetime.now().strftime("%H:%M:%S"))
            self.status.set_engine_status("monitor_ok", True)

            # 4. 风控检查
            daily_pnl = self.status.data["account"]["daily_pnl"]
            start_balance = self.status.data["account"].get("daily_start", self.balance)
            if start_balance > 0:
                loss_pct = abs(daily_pnl) / start_balance * 100
                if daily_pnl < 0 and loss_pct > self.risk_max_daily_loss_pct:
                    print_colored(f"[LiveEngine] ⚠️ 当日亏损 {loss_pct:.1f}% 超过限额 {self.risk_max_daily_loss_pct}%，暂停策略",
                                  bg_color="red", bold=True)
                    self.pause()
                    self.status.add_error(f"风控触发: 当日亏损 {loss_pct:.1f}%")

            self.status.save()

        except Exception as e:
            logger.warning("Monitor tick error: %s", e)
            self.status.set_engine_status("monitor_ok", False)
            self.status.add_error(f"监控错误: {e}")
            self.status.save()

        self._schedule_monitor()

    def run_forever(self):
        """主线程阻塞，等待停止信号"""
        print_colored("[LiveEngine] 引擎已进入运行状态", bg_color="blue")
        print_colored(f"  状态文件: {STATUS_FILE}", bg_color="blue")
        print_colored("  使用 live_status.py 查看当前状态", bg_color="blue")
        print_colored("  使用 Ctrl+C 停止", bg_color="blue")
        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(1)
        except KeyboardInterrupt:
            print()
            self.stop()


# ================================================================
# 命令行入口
# ================================================================
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    engine = LiveEngine()
    engine.start()
    engine.run_forever()
