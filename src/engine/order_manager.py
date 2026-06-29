"""
订单管理器 - 订单执行线程
负责处理策略生成的订单指令，管理订单池，更新账户状态
"""
import logging
import threading
import queue
import pandas as pd
from src.engine.order_instance import OrderInstance
from src.utils.constants import (
    ORDER_ACTION_OPEN, ORDER_ACTION_CLOSE,
    ERR_SUCCESS, ERR_ORDER_NO_ACTION, ERR_ORDER_SIDE_MISMATCH,
    ERR_ORDER_NOT_IN_POOL,
)

logger = logging.getLogger(__name__)


class OrderManager(threading.Thread):
    """
    订单管理线程 (OM)

    职责:
    - 从策略管理器接收订单指令
    - 创建/更新 OrderInstance
    - 维护 orderpool 和 orderframe
    - 更新账户资产和统计信息
    """

    def __init__(self, order_manager_id: int, order_manager_name: str,
                 st_manager, dp_core,
                 broker=None):
        """
        Args:
            order_manager_id: 线程ID
            order_manager_name: 名称
            st_manager: 策略管理器引用 (获取订单队列)
            dp_core: 驱动处理器引用 (获取数据管理器)
            broker: 交易所适配器 (None=回测模拟)
        """
        threading.Thread.__init__(self)
        self.threadID = order_manager_id
        self.daemon = True
        self.name = order_manager_name
        self.oderqueue = st_manager.oderqueue
        self.thread_stop = False
        self.core = st_manager
        self.broker = broker
        self.dp_type = getattr(st_manager, 'DPtype', 'backtest')
        self.order_id_inter = 0

        # 订单记录 DataFrame
        self.orderframe = pd.DataFrame([], columns=[
            'STname', 'ID_inter', 'UID', 'OrderAction', 'OrderType',
            'Status', 'CreatedTime', 'Market', 'Side', 'Size',
            'ExpectedPrice', 'DealPrice', 'TickPrice'
        ])
        self.orderpool = {}
        self.debug_order = None

        # 胜率统计
        self.order_statistic = {
            "totalnumber": 0,
            "win_num": 0,
            "win_win_count": 0,
            "loss_num": 0,
            "loss_loss_count": 0,
            "finish_num": 0,
            "holding_num": 0,
        }

    def run(self):
        """主循环：等待订单指令并处理"""
        logger.info(f"[OM] {self.name} started")

        count = 1
        while not self.thread_stop:
            try:
                ordertask_list = self.oderqueue.get()
                logger.info(f"[OM] Order task received (count={count})")

                # 检查停止信号
                if ordertask_list == "stop":
                    self.thread_stop = True
                    self.oderqueue.task_done()
                    logger.info("[OM] Stop signal received, exiting")
                    continue

                if not isinstance(ordertask_list, list):
                    logger.warning(f"[OM] Invalid order type: {type(ordertask_list)}")
                    continue

                if len(ordertask_list) == 0:
                    logger.debug("[OM] Empty order list")
                    continue

                # 处理每个订单
                for ordertask in ordertask_list:
                    forder = self._format_order(ordertask)
                    self.debug_order = forder

                    # 执行订单
                    ret = self._process_order(forder)

                    if ret == ERR_SUCCESS:
                        forder[5] = self.orderpool[forder[2]].status
                        forder[11] = self.orderpool[forder[2]].dealprice

                    # 记录订单
                    timeindex = self.core.task.index[0]
                    order_ser = pd.Series(
                        index=self.orderframe.columns,
                        data=forder,
                        name=timeindex
                    )

                    if len(self.orderframe) >= self.core.core.dataM.max_orderframe_len:
                        self.orderframe = self.orderframe.drop(
                            self.orderframe.head(1).index
                        )
                    self.orderframe = pd.concat(
                        [self.orderframe, order_ser.to_frame().T]
                    )

                    # 同步到 DataManager
                    self.core.core.dataM.orderframe = self.orderframe
                    self.core.core.dataM.orderpool = self.orderpool
                    self.core.core.dataM.order_statistic = self.order_statistic

                    # 更新可视化标记
                    if ret == ERR_SUCCESS:
                        raw_show = self.core.core.dataM.rawdata_show
                        if raw_show is not None and not raw_show.empty:
                            raw_show.loc[timeindex, 'Signal'] = ordertask.get('oside', '')

                    self.order_id_inter += 1

                logger.info(f"[OM] Task {count} done")
                count += 1

            except Exception as e:
                logger.exception(f"[OM] Error (recovering): {e}")
                continue
            finally:
                self.oderqueue.task_done()

        logger.info("[OM] Thread stopped")

    def _format_order(self, order: dict) -> list:
        """
        将策略传入的订单字典格式化为标准列表

        Args:
            order: 订单字典

        Returns:
            list: [name, id_inter, uid, action, otype, status, createtime, ...]
        """
        orderstatus = ''
        createtime = pd.Timestamp.utcnow()

        if self.dp_type == "backtest":
            orderstatus = 'SUCCESS'
            orderdealprice = order.get('oprice', 0)
        else:
            orderstatus = 'NA'
            orderdealprice = 'NA'

        tick_price = self.core.task.head(1).close.iloc[0]

        return [
            self.core.name,           # 0: STname
            self.order_id_inter,      # 1: ID_inter
            order.get('uid', ''),     # 2: UID
            order.get('oaction', ''), # 3: OrderAction
            order.get('otype', ''),   # 4: OrderType
            orderstatus,             # 5: Status
            createtime,              # 6: CreatedTime
            order.get('code', ''),   # 7: Market
            order.get('oside', ''),  # 8: Side
            order.get('osize', 0),   # 9: Size
            order.get('oprice', 0),  # 10: ExpectedPrice
            orderdealprice,          # 11: DealPrice
            tick_price,              # 12: TickPrice
        ]

    def _process_order(self, forder: list) -> int:
        """
        处理单个订单（开仓/平仓）

        Args:
            forder: 格式化后的订单列表

        Returns:
            int: 错误码
        """
        oaction = forder[3]
        ouid = forder[2]
        oside = forder[8]

        if oaction == ORDER_ACTION_OPEN:
            # 创建新订单
            if ouid not in self.orderpool:
                logger.info(f"[OM] Creating new order: {ouid}")
                new_order = OrderInstance(forder)
                self.orderpool[ouid] = new_order
                self.order_statistic['totalnumber'] += 1
                self.order_statistic['holding_num'] += 1

            # 方向检查
            if self.orderpool[ouid].side != oside:
                logger.error(f"[OM] Side mismatch: {self.orderpool[ouid].side} != {oside}")
                return ERR_ORDER_SIDE_MISMATCH

            ret = self.orderpool[ouid].inc_position(forder)
            return ret

        elif oaction == ORDER_ACTION_CLOSE:
            if ouid not in self.orderpool:
                logger.error(f"[OM] Order not in pool: {ouid}")
                return ERR_ORDER_NOT_IN_POOL

            if self.orderpool[ouid].side != oside:
                logger.error(f"[OM] Side mismatch for close: {oside}")
                return ERR_ORDER_SIDE_MISMATCH

            closeprofit, ret = self.orderpool[ouid].dec_position(forder)

            # 更新账户
            self.core.core.dataM.account['asset'] += closeprofit
            self.core.core.dataM.account['profit'] += closeprofit

            # 更新胜率统计
            if self.orderpool[ouid].size == 0:
                self.order_statistic['holding_num'] -= 1
                self.order_statistic['finish_num'] += 1
                if closeprofit >= 0:
                    self.order_statistic['win_num'] += 1
                    self.order_statistic['win_win_count'] += 1
                    self.order_statistic['loss_loss_count'] = 0
                else:
                    self.order_statistic['loss_num'] += 1
                    self.order_statistic['win_win_count'] = 0
                    self.order_statistic['loss_loss_count'] += 1

            return ret

        logger.warning(f"[OM] Unknown action: {oaction}")
        return ERR_ORDER_NO_ACTION