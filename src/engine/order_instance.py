"""
订单实例 - 管理单个订单的完整生命周期
支持开仓、加仓、减仓、平仓操作和盈亏计算
"""
import logging
import pandas as pd
from src.utils.constants import (
    ORDER_ACTION_OPEN, ORDER_ACTION_CLOSE,
    ERR_SUCCESS, ERR_ORDER_SIZE_EXCEED,
)

logger = logging.getLogger(__name__)


class OrderInstance:
    """
    单个订单实例

    管理:
    - 持仓方向 (LONG/SHORT)
    - 持仓数量 (size)
    - 平均开仓价 (aveprice)
    - 浮动盈亏 (floatingPL)
    - 平仓盈亏 (closeprofit)
    """

    def __init__(self, forder: list, dex: str = None, precision: int = 3):
        """
        初始化订单

        Args:
            forder: 订单数据列表 [name, id_inter, uid, action, otype, status,
                                  createtime, market, side, osize, oprice, dealprice, tickprice]
            dex: 交易所名称
            precision: 精度
        """
        self.precision = precision

        self.name = forder[0]
        self.id_inter = forder[1]
        self.uid = forder[2]
        self.action = forder[3]
        self.otype = forder[4]
        self.status = None
        self.market = forder[7]
        self.side = forder[8]
        self.osize = round(float(forder[9]), self.precision)
        self.size = 0  # 累计持仓量
        self.dex = dex

        self.createtime = forder[6]
        self.openprice = round(float(forder[10]), 6)
        self.dealprice = None
        self.aveprice = 0.0
        self.closeprice = None
        self.closeprofit = 0.0
        self.floatingPL = 0.0
        self.totalvalue = 0.0

        self._create_order()

    def _create_order(self):
        """初始化订单状态"""
        if self.dex is None or self.dex == 'backtest':
            self.dex = 'backtest'
            self.status = 'processing'
        logger.info(f"Order created: uid={self.uid}, side={self.side}, "
                     f"market={self.market}")

    def _update_by_forder(self, forder: list):
        """根据新订单数据更新字段"""
        self.name = forder[0]
        self.id_inter = forder[1]
        self.uid = forder[2]
        self.action = forder[3]
        self.otype = forder[4]
        self.createtime = forder[6]
        self.market = forder[7]
        self.side = forder[8]
        self.osize = round(float(forder[9]), self.precision)
        self.openprice = round(float(forder[10]), 6)

    def inc_position(self, forder: list, broker_result: dict = None) -> int:
        """
        增加持仓（开仓/加仓）

        Args:
            forder: 订单数据
            broker_result: 实盘 broker 返回结果 (live mode)

        Returns:
            int: 错误码 (0=成功)
        """
        self._update_by_forder(forder)
        deal_price = float(forder[12])

        # --- Live mode: use broker result ---
        if broker_result and broker_result.get('success'):
            deal_price = broker_result.get('deal_price', None)
            if deal_price is None or deal_price <= 0:
                # Broker 未返回成交价（市价单），用 TickPrice 兜底
                deal_price = float(forder[12])
            self.size = round(self.size + float(forder[9]), self.precision)
            self.totalvalue += round(deal_price * float(forder[9]), 6)
            self.aveprice = self.totalvalue / self.size if self.size > 0 else 0
            self.action = ORDER_ACTION_OPEN
            self.dealprice = deal_price
            self.status = broker_result.get('status', self.status)
            return ERR_SUCCESS

        # --- Backtest mode ---
        if self.dex == 'backtest' and self.status == 'processing':
            self.size = round(self.size + float(forder[9]), self.precision)
            self.totalvalue += round(deal_price * float(forder[9]), 6)
            self.aveprice = self.totalvalue / self.size if self.size > 0 else 0
            self.action = ORDER_ACTION_OPEN
            self.dealprice = deal_price
            return ERR_SUCCESS

        logger.warning(f"incPosition not implemented for dex={self.dex}")
        return 0x1

    def dec_position(self, forder: list, broker_result: dict = None) -> tuple:
        """
        减少持仓（减仓/平仓）

        Args:
            forder: 订单数据
            broker_result: 实盘 broker 返回结果 (live mode)

        Returns:
            tuple: (closeprofit, error_code)
        """
        self._update_by_forder(forder)
        close_size = float(forder[9])
        tick_price = round(float(forder[12]), 6)

        # --- Live mode: use broker result ---
        if broker_result and broker_result.get('success'):
            deal_price = broker_result.get('deal_price', None)
            if deal_price is None or deal_price <= 0:
                deal_price = tick_price
            if round(self.size - close_size, self.precision) < 0:
                logger.error(f"Close size exceeds holding: hold={self.size}, "
                              f"req={close_size}")
                return self.closeprofit, ERR_ORDER_SIZE_EXCEED

            # 部分平仓
            if round(self.size - close_size, self.precision) != 0:
                if self.side == 'LONG':
                    self.closeprofit += (deal_price - self.aveprice) * close_size
                else:
                    self.closeprofit -= (deal_price - self.aveprice) * close_size

                self.size = round(self.size - close_size, self.precision)
                self.totalvalue -= round(deal_price * close_size, 6)
                self.aveprice = self.totalvalue / self.size if self.size > 0 else 0
                self.action = ORDER_ACTION_CLOSE
                self.dealprice = deal_price
                return self.closeprofit, ERR_SUCCESS

            # 完全平仓
            self.closeprice = deal_price
            if self.side == 'LONG':
                self.closeprofit += (deal_price - self.aveprice) * self.size
            else:
                self.closeprofit -= (deal_price - self.aveprice) * self.size

            self.status = 'finished'
            self.action = ORDER_ACTION_CLOSE
            self.size = round(self.size - close_size, self.precision)
            self.totalvalue = 0.0
            self.dealprice = deal_price
            return self.closeprofit, ERR_SUCCESS

        # --- Backtest mode ---
        if self.dex == 'backtest' and self.status == 'processing':
            # 检查平仓量是否超过持仓
            if round(self.size - close_size, self.precision) < 0:
                logger.error(f"Close size exceeds holding: hold={self.size}, "
                              f"req={close_size}")
                return self.closeprofit, ERR_ORDER_SIZE_EXCEED

            # 部分平仓
            if round(self.size - close_size, self.precision) != 0:
                if self.side == 'LONG':
                    self.closeprofit += (tick_price - self.aveprice) * close_size
                else:
                    self.closeprofit -= (tick_price - self.aveprice) * close_size

                self.size = round(self.size - close_size, self.precision)
                self.totalvalue -= round(tick_price * close_size, 6)
                self.aveprice = self.totalvalue / self.size if self.size > 0 else 0
                self.action = ORDER_ACTION_CLOSE
                self.dealprice = forder[12]
                return self.closeprofit, ERR_SUCCESS

            # 完全平仓
            self.closeprice = round(float(forder[10]), 6)
            if self.side == 'LONG':
                self.closeprofit += (tick_price - self.aveprice) * self.size
            else:
                self.closeprofit -= (tick_price - self.aveprice) * self.size

            self.status = 'finished'
            self.action = ORDER_ACTION_CLOSE
            self.size = round(self.size - close_size, self.precision)
            self.totalvalue = 0.0
            self.dealprice = forder[12]
            return self.closeprofit, ERR_SUCCESS

        logger.warning(f"decPosition not implemented for dex={self.dex}")
        return self.closeprofit, 0x1

    def show(self) -> dict:
        """显示订单信息"""
        return {
            "name": self.name,
            "InternalID": self.id_inter,
            "UID": self.uid,
            "LastAction": self.action,
            "Status": self.status,
            "Market": self.market,
            "Side": self.side,
            "Size": self.size,
            "OpenPrice": self.openprice,
            "ClosePrice": self.closeprice,
            "AveragePrice": self.aveprice,
            "FloatingPL": self.floatingPL,
            "CloseProfit": self.closeprofit,
        }