"""
HJATS - 自动化交易系统 启动入口

运行模式:
    Runtype=1: 回测模式 (BackTest)
    Runtype=2: 实盘模式 (Realtime)

用法:
    python run.py
"""
import queue
import threading
import time
import logging
import os
import sys

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.logger import setup_logger
from src.utils.helpers import print_colored
from src.data.datamanager import DataManager
from src.server.ats_server import ATSServer
from src.engine.driver import DriverProcessor
from src.engine.strategy import StrategyManager
from src.engine.order_manager import OrderManager

# 初始化日志
logger = setup_logger("HJATS", log_level=logging.INFO)

ATS_Run_Config = 'BackTest'


class ThreadPool:
    """简单的线程池管理"""
    def __init__(self):
        self.pool = []

    def join_all(self):
        for thd in self.pool:
            if thd.is_alive():
                thd.join()

    def pool_add(self, thd):
        self.pool.append(thd)


class ThreadManager:
    """线程管理器（按名称注册/访问）"""
    def __init__(self):
        self.threads = {}

    def register(self, name, thread):
        self.threads[name] = thread

    def show_all(self):
        print(f"\nRegistered threads ({len(self.threads)}):")
        for name, thread in self.threads.items():
            print(f"  {name}: alive={thread.is_alive()}, daemon={thread.daemon}")

    def get(self, name):
        return self.threads.get(name)

    def stop_all(self):
        for name, thread in self.threads.items():
            if hasattr(thread, 'stop'):
                thread.stop()
                print(f"Stopped: {name}")


def run_backtest():
    """启动回测"""
    timeinterval = 0
    visualization_switch = True

    manager = ThreadManager()

    para = {
        "Init_Balance": 200,
        "TimeStart": "2022-10-10T00:00:00.000Z",
        "TimeStop": "2022-10-12T12:00:00.000Z",
        "Frequency": "15MINS",
        "Code": "ETH-USD",
    }

    dm1 = DataManager()

    # 使用本地CSV文件初始化（请修改为实际路径）
    csv_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "2022-10-10_2022-10-20_ETH-USD_5MINS.csv"
    )
    if not os.path.exists(csv_path):
        logger.warning(f"CSV file not found: {csv_path}")
        # 尝试 modules_github 下的历史数据
        alt_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "modules_github",
            "historydata",
            "2022-10-10_2022-10-20_ETH-USD_5MINS.csv"
        )
        if os.path.exists(alt_path):
            csv_path = alt_path
            logger.info(f"Using fallback CSV: {csv_path}")
        else:
            logger.error("No CSV data file found!")
            return

    dm1.local_init(csv_path, para)

    thd_pool = ThreadPool()
    ats_server = ATSServer(if_autorun=0, data_manager=dm1)
    manager.register("server", ats_server)

    dp1 = DriverProcessor(
        thread_id=1, name='DP1', q_id=1, q_name='Q1', q_length=1,
        dp_type="backtest",
        msg_queue=ats_server.msg_queue,
        speed=timeinterval,
        data_manager=dm1,
        visualization=visualization_switch,
    )
    manager.register("driverprocessor", dp1)

    st1 = StrategyManager(strategy_id=2, strategy_name='ST1', dp_core=dp1)
    manager.register("strategyprocessor", st1)

    om1 = OrderManager(
        order_manager_id=3, order_manager_name='OM1',
        st_manager=st1, dp_core=dp1,
    )
    manager.register("orderprocessor", om1)

    thd_pool.pool_add(dp1)
    thd_pool.pool_add(st1)
    thd_pool.pool_add(om1)

    dp1.start()
    st1.start()
    om1.start()

    return thd_pool, manager


def run_realtime():
    """启动实盘"""
    dm1 = DataManager()
    ats_server = ATSServer(if_autorun=0, data_manager=dm1)

    thd_pool = ThreadPool()

    dp1 = DriverProcessor(
        thread_id=1, name='DP1', q_id=1, q_name='Q1', q_length=1,
        dp_type="realtime",
        msg_queue=ats_server.msg_queue,
        speed=0.1,
        data_manager=dm1,
        visualization=False,
    )

    st1 = StrategyManager(strategy_id=2, strategy_name='ST1', dp_core=dp1)
    om1 = OrderManager(
        order_manager_id=3, order_manager_name='OM1',
        st_manager=st1, dp_core=dp1,
    )

    thd_pool.pool_add(ats_server)
    thd_pool.pool_add(dp1)
    thd_pool.pool_add(st1)
    thd_pool.pool_add(om1)

    dp1.start()
    st1.start()
    om1.start()

    return thd_pool


if __name__ == '__main__':
    # 选择运行模式
    # 1 = 回测, 2 = 实盘
    Runtype = '1'

    if Runtype == "1":
        print_colored("[Main] Starting Backtest...", bg_color='red')
        thd_pool, manager = run_backtest()
        dp1 = thd_pool.pool[0]
        st1 = thd_pool.pool[1]
        om1 = thd_pool.pool[2]

        # 等待回测完成
        dp1.join()
        logger.info("[Main] Backtest completed")

    elif Runtype == "2":
        print_colored("[Main] Starting Realtime...", bg_color='red')
        thd_pool = run_realtime()
        ats_server = thd_pool.pool[0]
        dp1 = thd_pool.pool[1]

        try:
            ats_server.run()
            while dp1.timer and dp1.timer.is_alive():
                dp1.stop()
            dp1.join()
            logger.info("[Main] Realtime exited")
        except KeyboardInterrupt:
            logger.info("[Main] Keyboard interrupt received")
            ats_server.msg_queue.put("stop")
            while dp1.timer and dp1.timer.is_alive():
                dp1.stop()
            dp1.join()
            logger.info("[Main] Exited cleanly")