"""
驱动处理器 - 数据推送引擎线程 (DP)

负责:
- 回测模式: 逐行读取CSV数据，按指定速度推送给策略
- 实时模式: 定时从交易所拉取最新K线，推送给策略
"""
import logging
import threading
import queue
import time
import configparser
import os
import pandas as pd
from src.utils.helpers import trans_frq2sec, print_colored
from src.utils.constants import DEFAULT_STORJ_MAXLEN

logger = logging.getLogger(__name__)


class DriverProcessor(threading.Thread):
    """
    数据驱动处理器

    通过 queue.Queue 与 StrategyManager 通信
    回测时严格同步（queue.join），实时时由 Timer 驱动
    """

    def __init__(self, thread_id: int, name: str, q_id: int, q_name: str,
                 dp_type: str, data_manager, msg_queue,
                 speed: float = None, q_length: int = None,
                 visualization: bool = True):
        """
        Args:
            thread_id: 线程ID
            name: 名称
            q_id: 队列ID
            q_name: 队列名称
            dp_type: "backtest" 或 "realtime"
            data_manager: DataManager 实例
            msg_queue: 消息队列（用于接收 start/pause/stop 命令）
            speed: 回测速度（秒/每K线）
            q_length: 队列长度
            visualization: 是否启用可视化
        """
        threading.Thread.__init__(self)
        self.threadID = thread_id
        self.daemon = True
        self.name = name
        self.q_id = q_id
        self.q_name = q_name
        self.qlength = q_length or 1
        self.queue = queue.Queue(self.qlength)
        self.thread_stop = False
        self.dp_type = dp_type
        self.dataset = data_manager.rawdata
        self.speed = speed
        self.dataM = data_manager
        self.visualization = visualization

        # GUI
        self.GUI = None

        # 消息控制
        self.msg_queue = msg_queue
        self.msg_hold = None
        self.timer = None
        self.initflag = True

        # 配置文件
        self.config_path = os.getcwd() + "/strategies/config.ini"
        self.conf = configparser.ConfigParser()
        self._read_config()

        # 实时模式组件
        self.marketclient = None
        self.treadclient = None
        self.realtime_run_mode = 'FreqMode'

    def _read_config(self):
        """读取配置文件"""
        if os.path.exists(self.config_path):
            self.conf.read(self.config_path)

    # ================================================================
    # 回测模式
    # ================================================================

    def _run_backtest(self):
        """回测模式主循环"""
        logger.info("[DP] Backtest mode started")
        start_time = time.time()
        count = 0

        try:
            for index, row in self.dataset.iterrows():
                # 速度控制
                if self.speed:
                    time.sleep(self.speed)

                # 维护 storj 长度
                if len(self.dataM.storj) >= self.dataM.storj_maxlen:
                    self.dataM.storj = self.dataM.storj.drop(
                        str(self.dataM.storj.iloc[-1].name)
                    )

                # 新数据插入头部
                self.dataM.storj = pd.concat([
                    self.dataset.loc[[str(index)]],
                    self.dataM.storj
                ])

                # 可视化的原始数据（正序）
                self.dataM.rawdata_show = pd.concat([
                    self.dataM.rawdata_show,
                    self.dataset.loc[[str(index)]]
                ])

                # 推送数据给策略
                self.queue.put(self.dataM.storj)

                last_close = self.dataM.storj['close'].iloc[0]
                print_colored(
                    f'[DP] BT Round: index={index}, close={last_close:.2f}, count={count}',
                    bg_color='red'
                )
                count += 1

                # 等待策略处理完成
                self.queue.join()

            # 回测完成
            self.thread_stop = True
            if self.visualization and self.GUI:
                self.GUI.draw_results()

            elapsed = time.time() - start_time
            logger.info(f"[DP] Backtest finished. {count} bars in "
                         f"{elapsed:.2f}s ({elapsed / 60:.2f} min)")

        except Exception as e:
            logger.exception(f"[DP] Backtest error: {e}")

    # ================================================================
    # 实时模式
    # ================================================================

    def _realtime_init(self):
        """实时模式初始化"""
        self.conf.read(self.config_path)
        initpara = {
            "TimeStop": "Now",
            "Frequency": self.conf.get('AlgPara', 'Frequency', fallback='15MINS'),
            "Code": self.conf.get('AlgPara', 'Code', fallback='BTC-USD'),
            "nHistoryCounts": int(self.conf.get('AlgPara', 'nHistoryCounts', fallback='100')),
        }

        # 数据库配置
        db_remote = self.conf.get('DataBase', 'remote', fallback='false')
        dbconfig = None
        if db_remote == 'true':
            dbconfig = {
                'user': self.conf.get('DataBase', 'user', fallback=''),
                'passwd': self.conf.get('DataBase', 'passwd', fallback=''),
                'host': self.conf.get('DataBase', 'host', fallback='localhost'),
                'port': self.conf.get('DataBase', 'port', fallback='27017'),
                'authSource': self.conf.get('DataBase', 'authSource', fallback='admin'),
            }

        try:
            # 初始化交易所和账户
            from src.broker.binance_broker import BinanceBroker
            self.treadclient = BinanceBroker()
            dex_info = self.treadclient.dex_name

            from src.data.market import MarketClient
            self.marketclient = MarketClient(dex_name=dex_info)

            init_balance = float(self.treadclient.check_balance())
            self.dataM.account['asset'] = init_balance
            self.dataM.account['assetinit'] = init_balance
            logger.info(f"Initial balance: {init_balance}")

            # 初始化远程数据
            self.dataM.remote_init(initpara)

            # 连接数据库
            if dbconfig:
                self.dataM.connect_db(dbconfig)

            # 初始数据存储
            if self.dataM.database:
                self.dataM.database.df_to_collection(
                    self.dataM.rawdata,
                    self.dataM.database.namelist_of_collections[1]
                )

            # 初始化 storj
            self.dataM.storj = self.dataM.rawdata.sort_index(ascending=False)

            logger.info("[DP] Realtime init success")

        except Exception as e:
            logger.exception(f"[DP] Realtime init failed: {e}")

    def _new_timer(self, timerpara=None):
        """创建新定时器"""
        self.timer = threading.Timer(10, self._time_engine, (timerpara,))
        self.timer.daemon = True
        self.timer.start()

    def _time_engine(self, para=None):
        """定时引擎：拉取最新K线并推送"""
        self.conf.read(self.config_path)

        if self.msg_hold == "pause":
            if self.timer and self.timer.is_alive():
                self.timer.cancel()
                logger.info("[DP] Timer paused")
            return

        # 首次运行初始化
        if self.initflag:
            self._realtime_init()
            self.initflag = False

        try:
            # 获取最新K线
            self.dataM.storj_new_candle = self.marketclient.get_price_v1(
                code=self.conf.get('AlgPara', 'Code', fallback='BTC-USD'),
                count=2,
                frequency=self.conf.get('AlgPara', 'Frequency', fallback='15MINS')
            )
        except Exception as e:
            logger.error(f"Failed to get new candle: {e}")
            self._new_timer(timerpara=para)
            return

        # FreqMode: 按K线时间戳更新
        if self.realtime_run_mode == 'FreqMode':
            timestamp_now = self.dataM.storj_new_candle.index[1].value
            timestamp_last = self.dataM.storj.index[0].value
            time_diff = int((timestamp_now - timestamp_last) / 1e9)

            freq_seconds = trans_frq2sec(
                self.conf.get('AlgPara', 'Frequency', fallback='15MINS')
            )

            if time_diff == freq_seconds:
                # 维护 storj 长度
                if len(self.dataM.storj) >= self.dataM.storj_maxlen:
                    self.dataM.storj = self.dataM.storj.drop(
                        self.dataM.storj.tail(1).index
                    )

                # 新数据插入头部
                index_temp = str(self.dataM.storj_new_candle.index[1])
                self.dataM.storj = pd.concat([
                    self.dataM.storj_new_candle.loc[[index_temp]],
                    self.dataM.storj
                ])
                self.dataM.storj = self.dataM.storj.astype(float)

                # 更新数据库
                if self.dataM.database:
                    self.dataM.database.df_to_collection(
                        self.dataM.storj_new_candle.iloc[[1]].astype(float),
                        self.dataM.database.namelist_of_collections[1]
                    )

                # 推送给策略
                try:
                    self.queue.put(self.dataM.storj)
                except queue.Full:
                    logger.warning("[DP] Queue is full, dropping data")

        # 启动下一次定时器
        self._new_timer(timerpara=para)

    def _run_realtime(self):
        """实时模式主循环"""
        logger.info("[DP] Realtime mode started")
        while not self.thread_stop:
            try:
                self.msg_hold = self.msg_queue.get(block=True)
                time.sleep(0.05)
                logger.info(f"[DP] Received command: {self.msg_hold}")

                if self.msg_hold == 'start':
                    self._new_timer(timerpara=self.msg_hold)
                elif self.msg_hold in ('stop', 'break'):
                    self.stop()

                self.msg_hold = ''

            except queue.Empty:
                pass

    # ================================================================
    # 公共方法
    # ================================================================

    def run(self):
        """线程入口"""
        logger.info(f"[DP] {self.name} started (type={self.dp_type})")

        if self.dp_type == "realtime":
            self._run_realtime()
        elif self.dp_type == "backtest":
            self._run_backtest()

    def stop(self):
        """停止线程"""
        self.thread_stop = True
        logger.info("[DP] Stop signal received")
        if self.timer and self.timer.is_alive():
            self.timer.cancel()
            logger.info("[DP] Timer stopped")