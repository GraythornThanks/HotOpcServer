from opcua import Server, ua
import threading
import time
import random
import math
from datetime import datetime
import logging
from django.conf import settings
from django.db.models import Min
from .models import Node, OpcServer
import json

logger = logging.getLogger(__name__)

class OpcUaServer:
    _instances = {}  # 存储所有服务器实例
    _lock = threading.Lock()  # 线程锁

    @classmethod
    def get_instance(cls, server_id):
        """获取服务器实例"""
        return cls._instances.get(server_id)

    @classmethod
    def create_instance(cls, server_config):
        """创建新的服务器实例"""
        with cls._lock:
            if server_config.id in cls._instances:
                return cls._instances[server_config.id]
            
            instance = cls(server_config)
            cls._instances[server_config.id] = instance
            return instance

    @classmethod
    def remove_instance(cls, server_id):
        """移除服务器实例"""
        with cls._lock:
            if server_id in cls._instances:
                instance = cls._instances[server_id]
                instance.stop()
                del cls._instances[server_id]

    def __init__(self, server_config):
        """初始化OPC UA服务器"""
        self.config = server_config
        self.server = Server()
        self.running = False
        self.nodes = {}  # 存储节点对象
        self.update_thread = None
        self.stop_event = threading.Event()

        # 配置服务器
        endpoint = f"opc.tcp://{server_config.endpoint}:{server_config.port}"
        self.server.set_endpoint(endpoint)
        self.server.set_server_name(server_config.name)
        self.server.set_security_policy([])  # 暂时不设置安全策略

        # 设置服务器URI
        uri = server_config.uri
        idx = self.server.register_namespace(uri)

        # 创建根节点
        self.root = self.server.nodes.objects.add_folder(idx, server_config.name)

    def add_node(self, node_config):
        """添加节点"""
        try:
            idx = self.server.get_namespace_index(self.config.uri)
            
            if node_config.node_type == 'variable':
                node = self.root.add_variable(idx, node_config.name, self._get_initial_value(node_config))
                node.set_writable()
            elif node_config.node_type == 'object':
                node = self.root.add_object(idx, node_config.name)
            else:
                logger.error(f"Unsupported node type: {node_config.node_type}")
                return None

            self.nodes[node_config.id] = {
                'node': node,
                'config': node_config
            }
            return node

        except Exception as e:
            logger.error(f"Error adding node: {e}")
            return None

    def remove_node(self, node_id):
        """移除节点"""
        if node_id in self.nodes:
            try:
                node_info = self.nodes[node_id]
                node_info['node'].delete()
                del self.nodes[node_id]
                return True
            except Exception as e:
                logger.error(f"Error removing node: {e}")
        return False

    def start(self):
        """启动服务器"""
        if not self.running:
            try:
                self.server.start()
                self.running = True
                self.stop_event.clear()
                self.update_thread = threading.Thread(target=self._update_values)
                self.update_thread.daemon = True
                self.update_thread.start()
                logger.info(f"Server {self.config.name} started")
                return True
            except Exception as e:
                logger.error(f"Error starting server: {e}")
                return False
        return True

    def stop(self):
        """停止服务器"""
        if self.running:
            try:
                self.stop_event.set()
                if self.update_thread:
                    self.update_thread.join(timeout=5)
                self.server.stop()
                self.running = False
                logger.info(f"Server {self.config.name} stopped")
                return True
            except Exception as e:
                logger.error(f"Error stopping server: {e}")
                return False
        return True

    def _update_values(self):
        """更新节点值的后台线程"""
        while not self.stop_event.is_set():
            try:
                for node_id, node_info in self.nodes.items():
                    node = node_info['node']
                    config = node_info['config']
                    
                    if config.node_type == 'variable' and config.variation_type != 'none':
                        new_value = self._calculate_next_value(config)
                        if new_value is not None:
                            node.set_value(new_value)
                            config.value = str(new_value)
                            config.save()

                time.sleep(0.1)  # 短暂休眠以减少CPU使用
            except Exception as e:
                logger.error(f"Error updating values: {e}")
                time.sleep(1)  # 发生错误时等待较长时间

    def _calculate_next_value(self, node_config):
        """计算节点的下一个值"""
        try:
            current_value = float(node_config.value) if node_config.value else 0
            
            if node_config.variation_type == 'random':
                if node_config.variation_min is not None and node_config.variation_max is not None:
                    return random.uniform(node_config.variation_min, node_config.variation_max)
            
            elif node_config.variation_type == 'increment':
                next_value = current_value + (node_config.variation_step or 1)
                if node_config.variation_max is not None and next_value > node_config.variation_max:
                    next_value = node_config.variation_min if node_config.variation_min is not None else 0
                return next_value
            
            elif node_config.variation_type == 'decrement':
                next_value = current_value - (node_config.variation_step or 1)
                if node_config.variation_min is not None and next_value < node_config.variation_min:
                    next_value = node_config.variation_max if node_config.variation_max is not None else 0
                return next_value
            
            elif node_config.variation_type == 'sine':
                time_factor = time.time() * 2 * math.pi / (node_config.variation_interval / 1000)
                amplitude = (node_config.variation_max - node_config.variation_min) / 2
                offset = (node_config.variation_max + node_config.variation_min) / 2
                return offset + amplitude * math.sin(time_factor)
            
            elif node_config.variation_type == 'square':
                time_factor = time.time() * 2 * math.pi / (node_config.variation_interval / 1000)
                return node_config.variation_max if math.sin(time_factor) >= 0 else node_config.variation_min
            
            elif node_config.variation_type == 'triangle':
                time_factor = time.time() * 2 * math.pi / (node_config.variation_interval / 1000)
                amplitude = node_config.variation_max - node_config.variation_min
                period = node_config.variation_interval / 1000
                t = (time.time() % period) / period
                if t < 0.5:
                    return node_config.variation_min + 2 * amplitude * t
                else:
                    return node_config.variation_max - 2 * amplitude * (t - 0.5)
            
            elif node_config.variation_type == 'sawtooth':
                time_factor = time.time() / (node_config.variation_interval / 1000)
                amplitude = node_config.variation_max - node_config.variation_min
                return node_config.variation_min + amplitude * (time_factor % 1)
            
            elif node_config.variation_type == 'discrete':
                if node_config.variation_values:
                    values = json.loads(node_config.variation_values)
                    if values:
                        try:
                            current_index = values.index(current_value)
                            next_index = (current_index + 1) % len(values)
                            return values[next_index]
                        except ValueError:
                            return values[0]
            
            return current_value
            
        except Exception as e:
            logger.error(f"Error calculating next value: {e}")
            return None

    def _get_initial_value(self, node_config):
        """获取节点的初始值"""
        if node_config.value:
            try:
                if node_config.data_type == 'boolean':
                    return node_config.value.lower() in ('true', '1', 'yes', 'on')
                elif node_config.data_type in ['int32', 'int64', 'uint32', 'uint64']:
                    return int(node_config.value)
                elif node_config.data_type in ['float', 'double']:
                    return float(node_config.value)
                elif node_config.data_type == 'datetime':
                    return datetime.fromisoformat(node_config.value)
                else:
                    return node_config.value
            except (ValueError, TypeError):
                pass
        
        # 返回默认值
        if node_config.data_type == 'boolean':
            return False
        elif node_config.data_type in ['int32', 'int64', 'uint32', 'uint64']:
            return 0
        elif node_config.data_type in ['float', 'double']:
            return 0.0
        elif node_config.data_type == 'datetime':
            return datetime.now()
        else:
            return ""
