"""
交易所适配器抽象基类
定义统一的订单执行接口，支持回测和实盘
"""
from abc import ABC, abstractmethod
from typing import Optional


class BrokerBase(ABC):
    """
    交易所适配器基类
    实盘和回测 broker 都继承此类
    """

    @abstractmethod
    def check_balance(self) -> float:
        """获取账户余额"""
        pass

    @abstractmethod
    def order_open(self, code: str, oside: str, otype: str,
                   osize: float, oprice: float = None) -> dict:
        """
        开仓

        Args:
            code: 交易对
            oside: 方向 (LONG/SHORT)
            otype: 类型 (MARKET/LIMIT)
            osize: 数量
            oprice: 价格（市价单可为None）

        Returns:
            dict: {success: bool, order_id: str, deal_price: float, status: str}
        """
        pass

    @abstractmethod
    def order_close(self, code: str, oside: str, otype: str,
                    osize: float, oprice: float = None) -> dict:
        """
        平仓

        Args:
            code: 交易对
            oside: 持仓方向 (LONG/SHORT)
            otype: 类型 (MARKET/LIMIT)
            osize: 数量
            oprice: 价格

        Returns:
            dict: {success: bool, order_id: str, deal_price: float, profit: float}
        """
        pass

    def get_order_status(self, order_id: str) -> str:
        """查询订单状态"""
        return "SUCCESS"

    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        return True