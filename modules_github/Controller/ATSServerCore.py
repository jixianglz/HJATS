# -*- coding: utf-8 -*-
"""
Created on Sun Dec  7 21:13:42 2025

@author: Dana Huang
"""

import threading
import queue
import os
import json
import time
from datetime import datetime
import logging

class ATSServerCore(threading.Thread):
    """
    ATS 状态管理服务器
    功能:
    1. 启动时读取并恢复上次状态
    2. 运行中实时保存状态
    3. 异常时记录遗言数据
    4. 提供命令控制和状态恢复接口
    """
    
    def __init__(self, ifautorun=1, DataManager=None):
        threading.Thread.__init__(self)
        
        # ========== 基础配置 ==========
        self.daemon = False  # 非守护线程，确保优雅退出
        self.msg_queue = queue.Queue(1)
        self._stop_event = threading.Event()
        
        # ========== 数据管理器引用 ==========
        self.dataManager = DataManager
        
        # ========== 状态文件配置 ========== 
        self.status_dir = "./runninghistory"
        self.status_file = os.path.join(self.status_dir, "status.json")           # 改为 .json
        self.recovery_file = os.path.join(self.status_dir, "recovery_data.json")  # 保持 .json
        self.crash_history_file = os.path.join(self.status_dir, "crash_history.json")  # 也改为 .json
        self.last_words_file = os.path.join(self.status_dir, "last_words.json")   # 也改为 .json
        
        # ========== 状态数据结构 ==========
        self.status_data = {
            # 基础运行状态
            "last_command": None,
            "last_run_time": None,
            "running_state": "stopped",  # stopped/running/paused
            "error_info": None,
            "crash_info": None,
            "restart_count": 0,
            "last_heartbeat": None,
            
            # 账户状态
            "account": {
                "asset": 0,
                "assetinit": 0,
                "profit": 0,
                "h_profit": 0,
                "h_profit_long": 0,
                "h_profit_short": 0
            },
            
            # 持仓订单
            "orderpool": {},  # {uid: order_dict}
            "order_count": 0,
            "last_order_id": 0,
            
            # 策略状态
            "strategy": {
                "iteration_count": 0,
                "last_signal": None,
                "indicators": {},
                "order_statistic": {}
            },
            
            # 数据状态
            "data": {
                "last_timestamp": None,
                "data_length": 0,
                "frequency": None,
                "code": None
            },
            
            # 用户自定义数据
            "user_data": {}
        }
        
        # ========== 恢复标志 ==========
        self.need_recovery = False
        self.recovery_mode = "normal"  # normal/recovery/crash_recovery
        
        # ========== 初始化 ==========
        self._ensure_directory_exists()
        self._load_status()
        
        # ========== 自动保存定时器 ==========
        self.auto_save_interval = 10  # 秒
        self.save_timer = None
        
        # ========== 自动启动 ==========
        if ifautorun == 1:
            self.msg_queue.put('start', block=False)
            print("✓ Auto-sent: start")
    
    # ========================================
    # 1. 状态文件管理
    # ========================================
    
    def _ensure_directory_exists(self):
        """确保状态文件目录存在"""
        if not os.path.exists(self.status_dir):
            os.makedirs(self.status_dir)
            logging.info(f"[Init] 创建状态目录: {self.status_dir}")
    
    def _load_status(self):
        """启动时加载状态文件（JSON格式）"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                    self.status_data.update(loaded_data)
                
                print("\n" + "="*60)
                print("[状态恢复] 成功加载状态文件 (JSON)")
                print("="*60)
                print(f"  上次运行时间: {self.status_data['last_run_time']}")
                print(f"  上次状态: {self.status_data['running_state']}")
                print(f"  上次命令: {self.status_data['last_command']}")
                print(f"  重启次数: {self.status_data['restart_count']}")
                print(f"  账户资产: {self.status_data['account']['asset']}")
                print(f"  持仓订单数: {len(self.status_data['orderpool'])}")
                print(f"  策略迭代数: {self.status_data['strategy']['iteration_count']}")
                print("="*60 + "\n")
                
                # 检查是否异常退出
                if self.status_data['running_state'] == 'running':
                    print("[警告] 检测到上次异常退出!")
                    self.need_recovery = True
                    self.recovery_mode = "crash_recovery"
                    self._handle_abnormal_exit()
                else:
                    self.recovery_mode = "normal"
                
                # 增加重启计数
                self.status_data['restart_count'] += 1
                
            else:
                print("[Init] 状态文件不存在，首次运行")
                self._save_status(reason="首次初始化")
                
        except json.JSONDecodeError as e:
            print(f"[错误] JSON 格式错误: {e}")
            logging.error(f"[错误] JSON 格式错误: {e}")
            self._backup_corrupted_file()
            print(f"[Init] 已备份损坏文件，使用默认配置")
            
        except Exception as e:
            print(f"[错误] 加载状态文件失败: {e}")
            logging.error(f"[错误] 加载状态文件失败: {e}")
    
    def _save_status(self, reason="定期保存"):
        """保存当前状态到文件（JSON格式）"""
        try:
            # 从 DataManager 更新最新状态
            if self.dataManager:
                self._sync_from_datamanager()
            
            # 更新时间戳
            self.status_data['last_run_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.status_data['last_heartbeat'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 写入 JSON 文件（格式化输出，便于阅读）
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(self.status_data, f, indent=4, ensure_ascii=False)
            
            logging.info(f"[状态保存] {reason} - {self.status_data['last_heartbeat']}")
            
        except Exception as e:
            logging.error(f"[错误] 保存状态文件失败: {e}")
    
    def _sync_from_datamanager(self):
        """从 DataManager 同步最新状态"""
        if not self.dataManager:
            return
        
        try:
            # 同步账户状态
            self.status_data['account'] = self.dataManager.account.copy()
            
            # 同步持仓订单 (只保存关键信息)
            orderpool_dict = {}
            for uid, order in self.dataManager.orderpool.items():
                # 检查是否是字典还是 OrderInstance 对象
                if isinstance(order, dict):
                    orderpool_dict[uid] = order
                else:
                    orderpool_dict[uid] = {
                        "uid": order.uid,
                        "side": order.side,
                        "size": order.size,
                        "aveprice": order.aveprice,
                        "market": order.market,
                        "status": order.status,
                        "totalvalue": order.totalvalue,
                        "closeprofit": order.closeprofit,
                        "floatingPL": order.floatingPL
                    }
            self.status_data['orderpool'] = orderpool_dict
            
            # 同步策略状态
            if hasattr(self.dataManager, 'order_statistic'):
                self.status_data['strategy']['order_statistic'] = self.dataManager.order_statistic
            
            # 同步数据状态
            if self.dataManager.storj is not None and len(self.dataManager.storj) > 0:
                self.status_data['data']['last_timestamp'] = str(self.dataManager.storj.index[0])
                self.status_data['data']['data_length'] = len(self.dataManager.storj)
            
        except Exception as e:
            logging.error(f"[错误] 同步 DataManager 状态失败: {e}")
    
    def _backup_corrupted_file(self):
        """备份损坏的状态文件"""
        if os.path.exists(self.status_file):
            backup_file = f"{self.status_file}.backup.{int(time.time())}"
            os.rename(self.status_file, backup_file)
            logging.info(f"[备份] 损坏文件已备份为: {backup_file}")
    
    def _handle_abnormal_exit(self):
        """处理上次异常退出"""
        print("\n[恢复模式] 正在处理上次异常退出...")
        
        # 记录崩溃信息
        crash_info = {
            "crash_time": self.status_data['last_run_time'],
            "last_command": self.status_data['last_command'],
            "error_info": self.status_data.get('error_info'),
            "detected_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "account_asset": self.status_data['account']['asset'],
            "orderpool_count": len(self.status_data['orderpool']),
            "strategy_count": self.status_data['strategy']['iteration_count']
        }
        
        # 保存到崩溃历史
        self._save_crash_history(crash_info)
        
        # 显示恢复信息
        print(f"\n[恢复信息]")
        print(f"  崩溃时间: {crash_info['crash_time']}")
        print(f"  账户资产: {crash_info['account_asset']}")
        print(f"  持仓订单: {crash_info['orderpool_count']}")
        print(f"  策略迭代: {crash_info['strategy_count']}")
    
    def _save_crash_history(self, crash_info):
        """保存崩溃历史（JSON格式，追加数组）"""
        try:
            # 读取现有崩溃历史
            crash_history = []
            if os.path.exists(self.crash_history_file):
                try:
                    with open(self.crash_history_file, 'r', encoding='utf-8') as f:
                        crash_history = json.load(f)
                except json.JSONDecodeError:
                    crash_history = []
            
            # 追加新的崩溃记录
            crash_history.append(crash_info)
            
            # 保存（只保留最近20条记录）
            if len(crash_history) > 20:
                crash_history = crash_history[-20:]
            
            with open(self.crash_history_file, 'w', encoding='utf-8') as f:
                json.dump(crash_history, f, indent=4, ensure_ascii=False)
            
            logging.info(f"[记录] 崩溃信息已保存到: {self.crash_history_file}")
            
        except Exception as e:
            logging.error(f"[错误] 保存崩溃历史失败: {e}")
    
    # ========================================
    # 2. 状态恢复接口
    # ========================================
    
    def restore_to_datamanager(self, dataManager):
        """将状态恢复到 DataManager"""
        if not self.need_recovery:
            print("[恢复] 无需恢复，正常启动")
            return
        
        print("\n[恢复] 开始恢复状态到 DataManager...")
        
        try:
            # 1. 恢复账户状态
            dataManager.account.update(self.status_data['account'])
            print(f"  ✓ 账户状态已恢复: 资产={dataManager.account['asset']}")
            
            # 2. 恢复持仓订单 (需要重建 OrderInstance 对象)
            # 注意: 这里只恢复订单数据，实际 OrderInstance 需要在 OrderManager 中重建
            restored_orders = {}
            for uid, order_data in self.status_data['orderpool'].items():
                restored_orders[uid] = order_data  # 暂存为字典
            dataManager.orderpool = restored_orders
            print(f"  ✓ 持仓订单已恢复: {len(restored_orders)} 个订单")
            
            # 3. 恢复策略统计
            if 'order_statistic' in self.status_data['strategy']:
                dataManager.order_statistic = self.status_data['strategy']['order_statistic']
                print(f"  ✓ 策略统计已恢复")
            
            # 4. 记录最后数据时间戳（用于数据续接）
            if self.status_data['data']['last_timestamp']:
                print(f"  ✓ 最后数据时间戳: {self.status_data['data']['last_timestamp']}")
            
            print("[恢复] 状态恢复完成\n")
            
        except Exception as e:
            logging.error(f"[错误] 恢复状态失败: {e}")
            print(f"[错误] 恢复失败: {e}")
    
    def get_last_data_timestamp(self):
        """获取上次最后的数据时间戳（用于续接数据）"""
        return self.status_data['data'].get('last_timestamp')
    
    # ========================================
    # 3. 定时保存
    # ========================================
    
    def _start_auto_save(self):
        """启动自动保存定时器"""
        if self.save_timer and self.save_timer.is_alive():
            self.save_timer.cancel()
        
        self.save_timer = threading.Timer(
            self.auto_save_interval, 
            self._auto_save_callback
        )
        self.save_timer.daemon = True
        self.save_timer.start()
    
    def _auto_save_callback(self):
        """自动保存回调"""
        self._save_status(reason="自动保存")
        self._start_auto_save()
    
    def _stop_auto_save(self):
        """停止自动保存"""
        if self.save_timer:
            self.save_timer.cancel()
    
    # ========================================
    # 4. 遗言记录
    # ========================================
    
    def record_last_words(self, error_type, error_info):
        """记录遗言数据（异常/断网时）- JSON格式"""
        last_words = {
            "error_type": error_type,
            "error_info": str(error_info),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_command": self.status_data['last_command'],
            "running_state": self.status_data['running_state'],
            "account": self.status_data['account'].copy(),
            "orderpool_count": len(self.status_data['orderpool']),
            "strategy_count": self.status_data['strategy']['iteration_count']
        }
        
        # 更新状态数据
        self.status_data['error_info'] = str(error_info)
        self.status_data['crash_info'] = last_words
        
        # 立即保存
        self._save_status(reason=f"遗言记录-{error_type}")
        
        # 保存到遗言专用文件（JSON格式）
        try:
            with open(self.last_words_file, 'w', encoding='utf-8') as f:
                json.dump(last_words, f, indent=4, ensure_ascii=False)
            logging.info(f"[遗言] 已记录到: {self.last_words_file}")
        except Exception as e:
            logging.error(f"[错误] 保存遗言失败: {e}")
    
    # ========================================
    # 5. 命令处理
    # ========================================
    
    def _execute_command(self, cmd):
        """执行命令并更新状态"""
        logging.info(f"[执行] 命令: {cmd}")
        
        self.status_data['last_command'] = cmd
        
        try:
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
                self._save_status(reason="正常退出")
                return True
            
            # 保存状态
            self._save_status(reason=f"命令-{cmd}")
            
            # 发送到消息队列
            try:
                self.msg_queue.put(cmd, block=False)
            except queue.Full:
                self.msg_queue.queue.clear()
                self.msg_queue.put(cmd, block=False)
            
        except Exception as e:
            logging.error(f"[错误] 执行命令失败: {e}")
            self.record_last_words("command_error", e)
        
        return False
    
    def cmd(self, command):
        """外部命令接口"""
        try:
            should_exit = self._execute_command(command)
            print(f"✓ Command sent: {command}")
            return not should_exit
        except Exception as e:
            print(f"✗ Command failed: {e}")
            return False
    
    # ========================================
    # 6. 主运行循环
    # ========================================
    
    def run(self):
        """主线程运行"""
        try:
            print("[启动] ATSServer 运行中")
            print("使用 server.cmd('命令') 发送控制命令")
            
            while not self._stop_event.is_set():
                try:
                    # 非阻塞等待消息
                    msg = self.msg_queue.get(timeout=0.5)
                    logging.info(f"[Server] 收到消息: {msg}")
                    
                    if msg == "exit":
                        logging.info("[Server] 退出")
                        break
                        
                except queue.Empty:
                    continue
                    
                except KeyboardInterrupt:
                    print("\n[中断] 收到键盘中断")
                    self.record_last_words("keyboard_interrupt", "用户中断")
                    break
                    
                except Exception as e:
                    logging.error(f"[错误] 运行时错误: {e}")
                    self.record_last_words("runtime_error", e)
                    
        except Exception as e:
            logging.error(f"[严重错误] 主循环异常: {e}")
            self.record_last_words("crash", e)
            
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """清理资源"""
        print("[清理] 正在清理资源...")
        self._stop_auto_save()
        self.status_data['running_state'] = 'stopped'
        self._save_status(reason="清理退出")
        logging.info("[清理] 完成")
    
    def stop(self):
        """停止服务器"""
        print("[停止] 正在停止 ATSServer...")
        self.record_last_words("user_stop", "用户主动停止")
        self._stop_event.set()
    
    # ========================================
    # 7. 状态查询
    # ========================================
    
    def get_status(self):
        """获取当前状态"""
        return self.status_data.copy()
    
    def print_status(self):
        """打印当前状态"""
        print("\n" + "="*60)
        print("当前状态:")
        print("="*60)
        print(f"  运行状态: {self.status_data['running_state']}")
        print(f"  账户资产: {self.status_data['account']['asset']}")
        print(f"  持仓订单: {len(self.status_data['orderpool'])}")
        print(f"  策略迭代: {self.status_data['strategy']['iteration_count']}")
        print(f"  重启次数: {self.status_data['restart_count']}")
        print(f"  最后心跳: {self.status_data['last_heartbeat']}")
        print("="*60 + "\n")
    
    def set_user_data(self, key, value):
        """设置用户自定义数据"""
        self.status_data['user_data'][key] = value
        self._save_status(reason=f"更新用户数据-{key}")
    
    def get_user_data(self, key, default=None):
        """获取用户自定义数据"""
        return self.status_data['user_data'].get(key, default)