"""
数据管理器 - 系统的数据中心
管理市场数据、信号、指标、账户、订单池等所有运行时状态
"""
import os
import logging
import configparser
import pandas as pd

import src.utils.constants as const
from src.utils.helpers import trans_frq2sec
from src.data.market import MarketClient

logger = logging.getLogger(__name__)


class DataManager:
    """
    全局数据管理器

    负责:
    - 市场数据的加载（本地CSV / 远程API）
    - 存储引擎间共享的状态（storj, signal, indicators）
    - 账户和订单池管理
    - 数据库连接
    """

    def __init__(self, config_path: str = None):
        self.initpara = None
        self.rawdata = None          # 原始全量数据
        self.rawdata_show = None     # 回测可视化用
        self.database = None
        self.db_strategy_name = None

        # 配置文件路径
        if config_path is None:
            config_path = os.getcwd() + "/strategies/config.ini"
        self.config_path = config_path
        self.conf = configparser.ConfigParser()
        self._read_config()

        # 信号和指标（环形缓冲区）
        self.max_signal_ind_len = const.DEFAULT_MAX_SIGNAL_IND_LEN
        self.signal = []
        self.indicators = {f'ind{i}': [] for i in range(1, 11)}
        self.indicators_w2 = {f'ind{i}': [] for i in range(1, 11)}

        # 核心数据（storj = 倒序，index[0] = 最新）
        self.storj = pd.DataFrame()
        self.storj_maxlen = const.DEFAULT_STORJ_MAXLEN
        self.storj_show = None
        self.storj_new_candle = None

        # 账户
        self.account = {
            'asset': const.DEFAULT_INIT_BALANCE,
            'assetinit': const.DEFAULT_INIT_BALANCE,
            'profit': 0,
            'h_profit': 0,
            'h_profit_long': 0,
            'h_profit_short': 0,
        }

        # 订单相关
        self.max_orderframe_len = const.DEFAULT_MAX_ORDERFRAME_LEN
        self.orderframe = pd.DataFrame()
        self.orderpool = {}
        self.order_statistic = {
            "totalnumber": 0,
            "win_num": 0,
            "win_win_count": 0,
            "loss_num": 0,
            "loss_loss_count": 0,
            "finish_num": 0,
            "holding_num": 0,
        }

        # 资产曲线
        self.max_aplen = const.DEFAULT_MAX_AP_LEN
        self.floating_pl_line = []
        self.floating_asset_line = []
        self.asset_line = []

        # 数据库利润记录
        self.df_profit_db = pd.DataFrame([], columns=[
            'Asset', 'FloatingPL', 'FloatingAsset'
        ])

    def _read_config(self):
        """读取配置文件"""
        if os.path.exists(self.config_path):
            self.conf.read(self.config_path)
        else:
            logger.warning(f"Config file not found: {self.config_path}")

    # ============================================================
    # 数据加载
    # ============================================================

    def local_init(self, path: str, initpara: dict):
        """
        从本地CSV文件初始化数据（回测用）

        Args:
            path: CSV文件路径
            initpara: 初始化参数，包含 Init_Balance, TimeStart, TimeStop 等
        """
        self.initpara = initpara
        self.account['asset'] = initpara.get("Init_Balance", const.DEFAULT_INIT_BALANCE)
        self.account['assetinit'] = self.account['asset']

        self.rawdata = pd.read_csv(path)
        self.rawdata.set_index('time', inplace=True)
        logger.info(f"Local data loaded: {path}, {len(self.rawdata)} rows")

    def remote_init(self, initpara: dict = None):
        """
        从远程交易所初始化数据（实盘用）

        Args:
            initpara: 初始化参数
        """
        self.initpara = initpara
        para = initpara or {
            "Init_Balance": const.DEFAULT_INIT_BALANCE,
            "TimeStart": "2022-10-20T16:00:00.000Z",
            "TimeStop": "Now",
            "Frequency": "15MINS",
            "Code": "BTC-USD",
            "nHistoryCounts": 100,
        }

        if 'Init_Balance' in para:
            self.account['asset'] = para["Init_Balance"]

        # 解析时间
        if para.get("TimeStop") == "Now":
            timestop = pd.Timestamp.now()
        else:
            timestop = pd.to_datetime(para["TimeStop"])

        if 'TimeStart' in para:
            timestart = pd.to_datetime(para["TimeStart"])
            ntick = int(((timestop.value - timestart.value) / 1e9) / trans_frq2sec(para["Frequency"]))
            self.ntick = ntick
        elif 'nHistoryCounts' in para:
            self.ntick = int(para['nHistoryCounts'])
            ntick = self.ntick

        # 分批拉取历史数据
        client = MarketClient(dex_name='binance')
        rawdata = pd.DataFrame()
        ntick = self.ntick
        data_cyc = int(ntick / 100)
        data_rem = ntick % 100
        data_cyc_rev = 0

        while data_cyc >= 0:
            count_temp = 100
            if data_cyc == 0:
                count_temp = data_rem
            if data_cyc == 0 and data_rem == 0:
                break

            market_res = client.get_price_v1(
                code=para["Code"],
                frequency=para["Frequency"],
                stop=pd.Timestamp(
                    timestop.value - data_cyc_rev * 100 * trans_frq2sec(para["Frequency"]) * 1e9
                ),
                count=count_temp,
            )
            rawdata = pd.concat([rawdata, market_res])
            data_cyc_rev += 1
            data_cyc -= 1

        logger.info("Market data init success")
        self.rawdata = rawdata.sort_index().astype(float)
        # 去掉尾部最新变化数据
        if len(self.rawdata) > 1:
            self.rawdata = self.rawdata.drop(self.rawdata.tail(1).index)

    # ============================================================
    # 数据库
    # ============================================================

    def connect_db(self, dbconfig: dict = None):
        """连接 MongoDB 数据库"""
        from src.data.db_connection import ATSDBClient
        self.database = ATSDBClient(dbconfig)
        logger.info("Database connected!")

        self._read_config()
        strategy_name = self.conf.get('AlgPara', 'StrategyName',
                                      fallback='HJATS_Strategy')
        self.db_strategy_name = f"{strategy_name} {pd.Timestamp.now()}"
        self.database.create_record_collections(self.db_strategy_name)

    # ============================================================
    # 工具方法
    # ============================================================

    def save_to_local(self) -> str:
        """将当前原始数据保存到本地CSV"""
        if not self.initpara:
            return ""

        ts_start = self.initpara['TimeStart'].split('T')[0]
        ts_stop = self.initpara['TimeStop'].split('T')[0]
        code = self.initpara['Code']
        freq = self.initpara['Frequency']
        filename = f"{ts_start}_{ts_stop}_{code}_{freq}.csv"

        data_dir = os.getcwd() + "/data"
        os.makedirs(data_dir, exist_ok=True)
        full_path = os.path.join(data_dir, filename)
        self.rawdata.to_csv(full_path)
        logger.info(f"Data saved to: {full_path}")
        return full_path