"""
ATS 状态管理服务器

功能:
1. 启动时读取并恢复上次状态
2. 运行中实时保存状态到 JSON 文件
3. 异常时记录遗言数据
4. 提供命令控制和状态恢复接口
"""
import threading
import queue
import os
import json
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ATSServer(threading.Thread):
    """
    ATS 状态管理服务器线程

    通过 msg_queue 接收 start/pause/stop/exit 命令
    自动保存状态到 runninghistory/ 目录
    """

    def __init__(self, if_autorun: int = 0, data_manager=None):
        threading.Thread.__init__(self)

        self.daemon = False
        self.msg_queue = queue.Queue(1)
        self._stop_event = threading.Event()
        self.data_manager = data_manager

        # 状态文件目录
        self.status_dir = "./runninghistory"
        self.status_file = os.path.join(self.status_dir, "status.json")
        self.last_words_file = os.path.join(self.status_dir, "last_words.json")

        # 状态数据
        self.status_data = {
            "last_command": None,
            "last_run_time": None,
            "running_state": "stopped",
            "error_info": None,
            "restart_count": 0,
            "last_heartbeat": None,
            "account": {
                "asset": 0, "assetinit": 0, "profit": 0,
                "h_profit": 0, "h_profit_long": 0, "h_profit_short": 0,
            },
            "orderpool": {},
            "order_count": 0,
            "strategy": {
                "iteration_count": 0,
                "last_signal": None,
                "indicators": {},
                "order_statistic": {},
            },
            "data": {
                "last_timestamp": None,
                "data_length": 0,
                "frequency": None,
                "code": None,
            },
            "user_data": {},
        }

        self.need_recovery = False
        self.auto_save_interval = 10
        self.save_timer = None

        self._ensure_directory_exists()
        self._load_status()

        if if_autorun == 1:
            try:
                self.msg_queue.put('start', block=False)
            except queue.Full:
                pass

    def _ensure_directory_exists(self):
        """确保状态文件目录存在"""
        os.makedirs(self.status_dir, exist_ok=True)

    def _load_status(self):
        """加载状态文件"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self.status_data.update(loaded)

                logger.info(f"Status loaded: running_state={self.status_data['running_state']}, "
                            f"asset={self.status_data['account']['asset']}")

                if self.status_data['running_state'] == 'running':
                    logger.warning("Previous run exited abnormally")
                    self.need_recovery = True

                self.status_data['restart_count'] += 1
            else:
                logger.info("No status file found, first run")
        except Exception as e:
            logger.error(f"Failed to load status: {e}")

    def _save_status(self, reason="periodic"):
        """保存状态"""
        try:
            if self.data_manager:
                self._sync_from_datamanager()

            self.status_data['last_run_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status_data['last_heartbeat'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Status saved: {reason}")
        except Exception as e:
            logger.error(f"Failed to save status: {e}")

    def _sync_from_datamanager(self):
        """从 DataManager 同步状态"""
        if not self.data_manager:
            return
        try:
            dm = self.data_manager
            self.status_data['account'] = dm.account.copy()

            # 同步订单池
            orderpool_dict = {}
            for uid, order in dm.orderpool.items():
                if hasattr(order, 'uid'):
                    orderpool_dict[uid] = {
                        "uid": order.uid, "side": order.side,
                        "size": order.size, "aveprice": order.aveprice,
                        "market": order.market, "status": order.status,
                        "totalvalue": order.totalvalue,
                        "closeprofit": order.closeprofit,
                        "floatingPL": order.floatingPL,
                    }
                else:
                    orderpool_dict[uid] = order
            self.status_data['orderpool'] = orderpool_dict

            # 同步策略状态
            if hasattr(dm, 'order_statistic'):
                self.status_data['strategy']['order_statistic'] = dm.order_statistic

            # 同步数据状态
            if dm.storj is not None and len(dm.storj) > 0:
                self.status_data['data']['last_timestamp'] = str(dm.storj.index[0])
                self.status_data['data']['data_length'] = len(dm.storj)
        except Exception as e:
            logger.error(f"Sync failed: {e}")

    def _start_auto_save(self):
        """启动自动保存"""
        if self.save_timer and self.save_timer.is_alive():
            self.save_timer.cancel()
        self.save_timer = threading.Timer(self.auto_save_interval, self._auto_save_callback)
        self.save_timer.daemon = True
        self.save_timer.start()

    def _auto_save_callback(self):
        """自动保存回调"""
        self._save_status(reason="auto")
        self._start_auto_save()

    def _stop_auto_save(self):
        """停止自动保存"""
        if self.save_timer:
            self.save_timer.cancel()

    def record_last_words(self, error_type: str, error_info):
        """记录遗言"""
        last_words = {
            "error_type": error_type,
            "error_info": str(error_info),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "running_state": self.status_data['running_state'],
            "account": self.status_data['account'].copy(),
        }
        self.status_data['error_info'] = str(error_info)
        self._save_status(reason=f"last_words-{error_type}")

        try:
            with open(self.last_words_file, 'w', encoding='utf-8') as f:
                json.dump(last_words, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save last words: {e}")

    def _execute_command(self, cmd: str):
        """执行命令"""
        self.status_data['last_command'] = cmd

        if cmd == 'start':
            self.status_data['running_state'] = 'running'
            self._start_auto_save()
        elif cmd == 'pause':
            self.status_data['running_state'] = 'paused'
        elif cmd == 'stop':
            self.status_data['running_state'] = 'stopped'
            self._stop_auto_save()
        elif cmd == 'exit':
            self.status_data['running_state'] = 'stopped'
            self._stop_auto_save()
            self._save_status(reason="exit")
            return True

        self._save_status(reason=f"cmd-{cmd}")

        try:
            self.msg_queue.put(cmd, block=False)
        except queue.Full:
            self.msg_queue.queue.clear()
            self.msg_queue.put(cmd, block=False)

        return False

    def cmd(self, command: str) -> bool:
        """外部命令接口"""
        try:
            should_exit = self._execute_command(command)
            logger.info(f"Command executed: {command}")
            return not should_exit
        except Exception as e:
            logger.error(f"Command failed: {command}, error={e}")
            return False

    def run(self):
        """主循环"""
        logger.info("[Server] ATSServer running")
        while not self._stop_event.is_set():
            try:
                msg = self.msg_queue.get(timeout=0.5)
                if msg == "exit":
                    break
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[Server] Error: {e}")
                self.record_last_words("runtime_error", e)

        self._cleanup()

    def _cleanup(self):
        """清理"""
        self._stop_auto_save()
        self.status_data['running_state'] = 'stopped'
        self._save_status(reason="cleanup")
        logger.info("[Server] Cleaned up")

    def stop(self):
        """停止服务器"""
        logger.info("[Server] Stopping...")
        self.record_last_words("user_stop", "User stopped")
        self._stop_event.set()

    def get_status(self) -> dict:
        """获取当前状态"""
        return self.status_data.copy()

    def set_user_data(self, key: str, value):
        """设置用户自定义数据"""
        self.status_data['user_data'][key] = value
        self._save_status(reason=f"user_data-{key}")

    def get_user_data(self, key: str, default=None):
        """获取用户自定义数据"""
        return self.status_data['user_data'].get(key, default)