#!/usr/bin/env python3
"""
HJATS 实盘入口 — 基于原始三线程管道架构

架构:
  DriverProcessor (DP) ──queue──→ StrategyManager (SM) ──queue──→ OrderManager (OM)
    数据获取/推送                   策略执行                       订单管理
    + RiskManager 风控              + signalAlg                    + orderpool
    + LiveStatus 状态监控           + orderAlg                     + 盈亏结算

启动方式:
  python3 run_live.py
  或者 tmux 后台: tmux new -s hjats-live "python3 run_live.py"
"""
import os
import sys
import time
import logging
import configparser
import threading

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import setup_logger
from src.utils.helpers import print_colored
from src.data.datamanager import DataManager
from src.engine.driver import DriverProcessor
from src.engine.strategy import StrategyManager
from src.engine.order_manager import OrderManager
from src.engine.risk_manager import RiskManager
from src.engine.live_status import LiveStatus, STATUS_FILE
from src.data.live_logger import LiveLogger

logger = setup_logger("HJATS_Live", log_level=logging.INFO)

# ============================================================
# 实盘控制台 UI
# ============================================================

def print_status(engine_status: dict):
    """打印当前运行状态"""
    s = engine_status
    print("\033[2J\033[H")  # 清屏
    print_colored("=" * 60, bg_color="blue")
    print_colored(f"  HJATS 实盘引擎  ({s.get('timestamp', 'N/A')})", bg_color="blue", bold=True)
    print_colored("=" * 60, bg_color="blue")
    print(f"  运行状态:  {'▶ 运行中' if s.get('running') else '⏸ 暂停'}")
    print(f"  风控状态:  {'⛔ 已触发' if s.get('risk_stopped') else '✅ 正常'}")
    print(f"  账户余额:  ${s.get('balance', 0):.2f}")
    print(f"  持仓:      {s.get('position', '无')}")
    print(f"  信号:      {s.get('signal', '无')}")
    print_colored("  状态文件:  " + STATUS_FILE, bg_color="blue")
    print()
    print("  Ctrl+C 停止")


# ============================================================
# 主逻辑
# ============================================================

def main():
    # 加载配置
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "strategies", "config.ini")
    conf = configparser.ConfigParser()
    conf.read(config_path)

    code = conf.get("AlgPara", "Code", fallback="ETHUSDT")
    frequency = conf.get("AlgPara", "Frequency", fallback="5m")
    strategy_interval = conf.getfloat("LiveEngine", "strategy_interval", fallback=300)
    monitor_interval = conf.getfloat("LiveEngine", "monitor_interval", fallback=30)

    print_colored(f"[Live] 启动实盘: {code} @ {frequency}", bg_color="blue")
    print_colored(f"[Live] 策略间隔: {strategy_interval}s, 监控间隔: {monitor_interval}s",
                  bg_color="blue")

    # 1. 数据管理器
    dm = DataManager()
    initpara = {
        "TimeStop": "Now",
        "Frequency": frequency,
        "Code": code,
        "nHistoryCounts": int(conf.get("AlgPara", "nHistoryCounts", fallback="100")),
    }
    dm.remote_init(initpara)
    dm.storj = dm.rawdata.sort_index(ascending=False)
    print_colored(f"[Live] 预热完成: {len(dm.storj)} 根历史K线", bg_color="blue")

    # 2. 风控模块
    risk_config = {
        "risk_max_daily_loss_pct": conf.getfloat("LiveEngine", "risk_max_daily_loss_pct", fallback=5.0),
        "risk_max_consecutive_losses": conf.getint("LiveEngine", "risk_max_consecutive_losses", fallback=3),
        "risk_min_balance": conf.getfloat("LiveEngine", "risk_min_balance", fallback=10.0),
        "risk_max_daily_trades": conf.getint("LiveEngine", "risk_max_daily_trades", fallback=50),
    }
    risk_mgr = RiskManager(risk_config)
    print_colored("[Live] 风控模块已加载", bg_color="blue")

    # 3. 状态监控
    live_status = LiveStatus(dm.account.get('asset', 0))
    live_status.data["engine_running"] = True
    live_status.data["engine_paused"] = False
    live_status.save()

    # 3.5 实盘持久化日志
    live_log = LiveLogger()
    print_colored(f"[Live] 日志目录: {live_log.session_dir}", bg_color="blue")

    # 4. 组装三线程管道
    import queue
    msg_q = queue.Queue()
    dp_queue = queue.Queue(1)

    # DP: 数据驱动（手动控制，不启动线程）
    dp = DriverProcessor(
        thread_id=1, name='DP_Live', q_id=1, q_name='Q_Live', q_length=1,
        dp_type="realtime",
        msg_queue=msg_q,
        speed=0.1,
        data_manager=dm,
        visualization=False,
    )
    dp.queue = dp_queue  # 共用队列
    dp._realtime_init()
    print_colored(f"[Live] DP 初始化完成, balance=${dm.account['asset']:.2f}",
                  bg_color="blue")

    # SM: 策略执行
    sm = StrategyManager(strategy_id=2, strategy_name='ST_Live', dp_core=dp)
    sm.queue = dp_queue
    sm.DPtype = "realtime"

    # OM: 订单管理（使用真实 broker）
    from src.broker.binance_broker import BinanceBroker
    broker = BinanceBroker()
    om = OrderManager(
        order_manager_id=3, order_manager_name='OM_Live',
        st_manager=sm, dp_core=dp,
        broker=broker,
        live_log=live_log,
    )
    om.DPtype = "realtime"

    # 启动 SM 和 OM 线程
    sm.start()
    om.start()
    print_colored("[Live] SM/OM 线程已启动", bg_color="green")

    # 5. 实盘主循环
    running = True
    start_balance = dm.account['asset']
    monitor_last = time.time()
    strategy_last = time.time()

    print_colored("[Live] ▶ 进入实盘运行", bg_color="green", bold=True)

    try:
        while running:
            now = time.time()

            # === 监控循环 ===
            if now - monitor_last >= monitor_interval:
                monitor_last = now
                try:
                    current_balance = float(broker.check_balance())
                    dm.account['asset'] = current_balance
                except Exception:
                    pass

                # 风控检查
                risk_result = risk_mgr.check(current_balance, start_balance)
                if risk_result["action"] == "stop":
                    print_colored(f"[Live] ⛔ 风控停止: {risk_result['reason']}",
                                  bg_color="red", bold=True)
                    running = False
                    break
                elif risk_result["action"] == "pause":
                    print_colored(f"[Live] ⚠️ 风控暂停: {risk_result['reason']}",
                                  bg_color="red", bold=True)

                # 更新状态文件
                live_status.update_account(current_balance, 0)
                live_status.set_engine_status("monitor_last_run",
                    time.strftime("%H:%M:%S"))
                live_status.set_engine_status("monitor_ok", True)
                live_status.save()

                # 持久化监控 tick
                mon_ts = time.strftime("%Y-%m-%d %H:%M:%S")
                mon_price = live_status.data["position"].get("current_price", 0)
                live_log.log_monitor_tick(
                    mon_ts, current_balance, mon_price,
                    risk_action=risk_result.get("action", ""),
                    risk_reason=risk_result.get("reason", ""))

            # === 策略循环 ===
            if not risk_mgr.paused and now - strategy_last >= strategy_interval:
                strategy_last = now
                try:
                    from src.data.market import MarketClient
                    mkt = MarketClient(dex_name="binance")
                    candles = mkt.get_price_v1(code=code, count=2, frequency=frequency)

                    if candles is not None and len(candles) > 0:
                        new_candle = candles.iloc[[-1]]
                        if len(dm.storj) == 0:
                            dm.storj = new_candle[::-1]
                        else:
                            new_time = str(new_candle.index[0])
                            if new_time != str(dm.storj.index[0]):
                                dm.storj = pd.concat([new_candle[::-1], dm.storj])
                                if len(dm.storj) > 100:
                                    dm.storj = dm.storj.drop(dm.storj.tail(1).index)

                        # 推送到策略队列
                        try:
                            dp_queue.put(dm.storj, block=False)
                        except queue.Full:
                            pass

                        # 等 SM 处理完（Event 机制，避免死锁）
                        if sm.is_alive() and om.is_alive():
                            sm.processing_done.clear()
                            sm.processing_done.wait(timeout=5.0)
                        else:
                            logger.error("[Live] SM or OM thread died — breaking")
                            running = False
                            break

                        # 更新信号 + 指标
                        tick_ts = time.strftime("%Y-%m-%d %H:%M:%S")
                        if dm.signal:
                            latest_indicators = {}
                            for k, v in dm.indicators.items():
                                if v:
                                    latest_indicators[k] = v[-1]
                            live_status.update_signal(dm.signal[-1], latest_indicators)

                            # 持久化策略 tick
                            close_price = float(dm.storj.iloc[0]["close"])
                            ma10_val = latest_indicators.get("ind1")
                            ma30_val = latest_indicators.get("ind2")
                            live_log.log_strategy_tick(
                                tick_ts, dm.signal[-1],
                                ma10=ma10_val, ma30=ma30_val,
                                close=close_price, balance=current_balance)

                except Exception as e:
                    logger.error(f"Strategy tick error: {e}")

                live_status.set_engine_status("strategy_last_run",
                    time.strftime("%H:%M:%S"))
                live_status.set_engine_status("strategy_ok", True)
                live_status.save()

            time.sleep(0.5)

    except KeyboardInterrupt:
        print()
        print_colored("[Live] 收到停止信号", bg_color="yellow")

    finally:
        sm.thread_stop = True
        om.thread_stop = True
        live_status.data["engine_running"] = False
        live_status.save()
        print_colored("[Live] 实盘已停止", bg_color="red")


if __name__ == "__main__":
    import pandas as pd
    main()