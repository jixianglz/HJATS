"""
策略管理器 - 策略执行线程 (SM)

负责:
- 从 DriverProcessor 接收市场数据
- 调用 signalAlg 计算信号
- 调用 orderAlg 生成订单
- 计算浮动盈亏
- 更新数据库
"""
import logging
import threading
import queue
import pandas as pd

logger = logging.getLogger(__name__)


class StrategyManager(threading.Thread):
    """
    策略管理线程

    通过队列与 DriverProcessor 和 OrderManager 通信:
    DP --queue(storj)--> SM --oderqueue(orderlist)--> OM
    """

    def __init__(self, strategy_id: int, strategy_name: str, dp_core):
        """
        Args:
            strategy_id: 策略ID
            strategy_name: 策略名称
            dp_core: DriverProcessor 引用（用于获取队列和数据管理器）
        """
        threading.Thread.__init__(self)
        self.threadID = strategy_id
        self.daemon = True
        self.name = strategy_name
        self.queue = dp_core.queue          # 从 DP 接收数据
        self.oderqueue = queue.Queue(1)     # 向 OM 发送订单
        self.thread_stop = False
        self.core = dp_core
        self.DPtype = self.core.dp_type
        self.task = None
        self.count = 0
        self.processing_done = threading.Event()  # 主循环通知 SM 已完成一轮

    def run(self):
        """主循环：等待数据，执行策略"""
        logger.info(f"[SM] {self.name} started (type={self.DPtype})")

        while not self.thread_stop:
            try:
                # 从 DP 获取数据
                self.task = self.queue.get()
                logger.info(f"[SM] Data received (count={self.count})")

                # 计算浮动盈亏
                self._profit_cal()

                # 调用策略算法
                signal, indicators, indicators_w2 = self._run_algorithms()

                # 更新信号记录
                if len(self.core.dataM.signal) >= self.core.dataM.max_signal_ind_len:
                    del self.core.dataM.signal[0]
                self.core.dataM.signal.append(signal)

                # 更新主窗口指标
                for ind_key in indicators:
                    if len(self.core.dataM.indicators[ind_key]) >= self.core.dataM.max_signal_ind_len:
                        del self.core.dataM.indicators[ind_key][0]
                    self.core.dataM.indicators[ind_key].append(indicators[ind_key])

                # 更新次窗口指标
                for ind_key in indicators_w2:
                    if len(self.core.dataM.indicators_w2[ind_key]) >= self.core.dataM.max_signal_ind_len:
                        del self.core.dataM.indicators_w2[ind_key][0]
                    self.core.dataM.indicators_w2[ind_key].append(indicators_w2[ind_key])

                # 等待订单处理完成
                if not self.oderqueue.empty():
                    self.oderqueue.join()

                logger.info(f"[SM] Task {self.count} done")
                self.count += 1
                self.processing_done.set()  # 通知主循环本轮完成

                # 检查 DP 是否已停止
                if self.core.thread_stop:
                    self.thread_stop = True
                    self.oderqueue.put("stop")
                    logger.info("[SM] DP stopped, exiting")

            except Exception as e:
                logger.exception(f"[SM] Error (recovering): {e}")
                self.processing_done.set()  # 异常也要通知，防止主循环死等
                continue
            finally:
                self.queue.task_done()

    def _run_algorithms(self):
        """
        执行信号算法和订单算法

        Returns:
            tuple: (signal, indicators_dict, indicators_w2_dict)
        """
        try:
            from strategies import signalAlg
            from strategies import orderAlg
        except ImportError:
            logger.warning("No strategies module found, using defaults")
            return 0, {f'ind{i}': [] for i in range(1, 11)}, {f'ind{i}': [] for i in range(1, 11)}

        # 准备参数
        parapoll = {
            'dataset': self.task,
            'indicatorsdic': self.core.dataM.indicators,
            'indicatorsdic_w2': self.core.dataM.indicators_w2,
        }

        # 执行信号算法
        logger.info(f"[SM] SignalAlg starting (count={self.count})")
        try:
            signal, cur_ind_dic, w2_ind_dic = signalAlg.run(parapoll)
            logger.info(f"[SM] SignalAlg done, signal={signal}")
        except Exception as e:
            logger.exception(f"[SM] SignalAlg error: {e}")
            signal, cur_ind_dic, w2_ind_dic = 0, {}, {}

        # 执行订单算法
        parapoll['c_signal'] = signal
        parapoll['orderpool'] = self.core.dataM.orderpool
        parapoll['orderaccount'] = self.core.dataM.account
        parapoll['order_statistic'] = self.core.dataM.order_statistic

        logger.info(f"[SM] OrderAlg starting (count={self.count})")
        try:
            orderlist = orderAlg.run(parapoll)
            logger.info(f"[SM] OrderAlg done, orders={len(orderlist)}")
        except Exception as e:
            logger.exception(f"[SM] OrderAlg error: {e}")
            orderlist = []

        # 发送订单
        if orderlist:
            self.oderqueue.put(orderlist)
            logger.info(f"[SM] Orders sent: {orderlist}")

        return signal, cur_ind_dic, w2_ind_dic

    def _profit_cal(self):
        """
        计算浮动盈亏

        遍历所有持仓订单，按最新价格计算浮动盈亏
        """
        if self.task is None:
            return

        latest_price = self.task['close'].values[0]
        balance = self.core.dataM.account['asset']
        all_floating_pl_long = 0.0
        all_floating_pl_short = 0.0
        all_floating_pl_long_size = 0.0
        all_floating_pl_short_size = 0.0
        all_floating_pl_long_cost = 0.0
        all_floating_pl_short_cost = 0.0

        holding = self.core.dataM.orderpool
        if not holding:
            return

        for order_uid in holding:
            order = holding[order_uid]
            try:
                if order.side == 'LONG' and order.size > 0:
                    all_floating_pl_long_size += order.size
                    all_floating_pl_long_cost += order.size * float(order.aveprice)
                    order.floatingPL = (latest_price - order.aveprice) * order.size

                if order.side == 'SHORT' and order.size > 0:
                    all_floating_pl_short_size += order.size
                    all_floating_pl_short_cost += order.size * float(order.aveprice)
                    order.floatingPL = (order.aveprice - latest_price) * order.size
            except Exception as e:
                logger.warning(f"Profit calc error for order {order_uid}: {e}")

        all_floating_pl_long = (all_floating_pl_long_size * latest_price
                                - all_floating_pl_long_cost)
        all_floating_pl_short = (all_floating_pl_short_cost
                                 - all_floating_pl_short_size * latest_price)
        all_floating_pl = all_floating_pl_long + all_floating_pl_short

        # 更新资产曲线
        dm = self.core.dataM
        for line, value in [
            (dm.asset_line, balance),
            (dm.floating_asset_line, all_floating_pl + balance),
            (dm.floating_pl_line, all_floating_pl),
        ]:
            if len(line) >= dm.max_aplen:
                del line[0]
            line.append(value)

        dm.account['h_profit'] = all_floating_pl
        dm.account['h_profit_long'] = all_floating_pl_long
        dm.account['h_profit_short'] = all_floating_pl_short