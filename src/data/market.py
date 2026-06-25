"""
市场数据客户端 - 从交易所获取K线数据
"""
import logging
import pandas as pd
from binance.um_futures import UMFutures

import src.utils.constants as const

logger = logging.getLogger(__name__)


class MarketClient:
    """
    市场数据获取客户端

    当前支持: binance (币安合约)
    历史支持: dydx (已移除)
    """

    def __init__(self, dex_name: str = 'binance'):
        self.dex_name = dex_name
        self.client = None
        self._init_client()

    def _init_client(self):
        """初始化交易所客户端"""
        if self.dex_name == 'binance':
            self.client = UMFutures()
            logger.info("MarketClient: Binance initialized")
        else:
            raise ValueError(f"Unsupported exchange: {self.dex_name}")

    def get_price_v1(self, code=None, count=None, frequency=None,
                     start=None, stop=None):
        """
        获取K线数据

        Args:
            code: 交易对，如 "BTCUSDT", "ETHUSDT"
            count: 返回K线数量
            frequency: K线周期，如 "1m", "5m", "15m", "1h", "4h", "1d"
            start: 开始时间 (ISO格式字符串)
            stop: 结束时间 (ISO格式字符串)

        Returns:
            DataFrame, index=时间, columns=[open, high, low, close, volume]
        """
        if self.dex_name == 'binance':
            return self._get_binance_klines(code, count, frequency, start, stop)
        else:
            raise ValueError(f"Unsupported exchange: {self.dex_name}")

    def _get_binance_klines(self, code, count, frequency, start, stop):
        """获取 Binance K线数据"""
        # 时间戳转换
        start_ts = None
        stop_ts = None
        if start:
            start_ts = int(pd.Timestamp(start).timestamp() * 1000)
        if stop:
            stop_ts = int(pd.Timestamp(stop).timestamp() * 1000)

        res = self.client.klines(
            symbol=code,
            interval=frequency,
            startTime=start_ts,
            endTime=stop_ts,
            limit=count,
        )

        df = pd.DataFrame(res)
        df.rename(columns={
            0: "time", 1: "open", 2: "high", 3: "low", 4: "close",
            5: "volume", 8: "number_of_trades", 9: "taker_volume",
        }, inplace=True)

        df['time'] = df['time'].astype('datetime64[ms]')
        df.set_index(pd.to_datetime(df['time']), inplace=True)
        df.drop(labels=['time', 6, 7, 10, 11], axis=1, inplace=True, errors='ignore')

        return df.astype(float)

    def get_market_info(self, code: str) -> dict:
        """获取市场信息"""
        if self.dex_name == 'binance':
            info = self.client.exchange_info(symbol=code)
            return info
        return {}