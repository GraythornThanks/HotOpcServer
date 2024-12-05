from opcua import Server, ua
import threading
import time
import random
import math
from datetime import datetime
import logging
from django.conf import settings
from django.db.models import Min
from .models import OpcNode

logger = logging.getLogger(__name__)

class OpcUaServer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.server = None
                cls._instance.running = False
                cls._instance.stop_variation = False
                cls._instance.variation_thread = None
                cls._instance.nodes = {}  # 存储活动节点
            return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.server = Server()
            self.server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
            self.server.set_server_name("Hot OPC UA Server")
            
            # 创建地址空间
            idx = self.server.register_namespace("http://examples.freeopcua.github.io")
            self.objects = self.server.nodes.objects
            
            self.initialized = True
            self.running = False
            self.stop_variation = False
            self.variation_thread = None
            self.nodes = {}  # 存储活动节点

    def start(self):
        """启动服务器"""
        if not self.running:
            self.server.start()
            self.running = True
            self.stop_variation = False
            self.nodes.clear()  # 清除旧的节点缓存
            
            # 从数据库重建所有节点
            from .models import OpcNode
            nodes = OpcNode.objects.all()
            for node in nodes:
                try:
                    node_id = ua.NodeId.from_string(node.node_id)
                    if node.node_type == 'variable':
                        # 创建变量节点
                        initial_value = convert_value(node.value, node.data_type) if node.value else 0
                        var = self.objects.add_variable(
                            node_id,
                            node.name,
                            initial_value,
                            varianttype=get_ua_data_type(node.data_type)
                        )
                        var.set_writable()
                        self.nodes[str(node_id)] = var
                    else:
                        # 创建对象节点
                        obj = self.objects.add_object(node_id, node.name)
                        self.nodes[str(node_id)] = obj
                    logger.info(f"Rebuilt node from database: {node.node_id}")
                except Exception as e:
                    logger.error(f"Failed to rebuild node {node.node_id}: {str(e)}")
            
            # 启动变化值线程
            self.variation_thread = threading.Thread(target=self._variation_loop)
            self.variation_thread.daemon = True
            self.variation_thread.start()
            
            logger.info("OPC UA Server started")

    def stop(self):
        """停止服务器"""
        if self.running:
            self.stop_variation = True
            if self.variation_thread:
                self.variation_thread.join(timeout=5.0)
            self.server.stop()
            self.running = False
            self.nodes.clear()  # 清除节点缓存
            logger.info("OPC UA Server stopped")

    def add_variable(self, node_id, name, value, varianttype=None):
        """添加变量节点"""
        try:
            var = self.objects.add_variable(node_id, name, value, varianttype=varianttype)
            var.set_writable()
            self.nodes[str(node_id)] = var  # 缓存节点
            return var
        except Exception as e:
            logger.error(f"Failed to add variable node {node_id}: {str(e)}")
            raise

    def add_object(self, node_id, name):
        """添加对象节点"""
        try:
            obj = self.objects.add_object(node_id, name)
            self.nodes[str(node_id)] = obj  # 缓存节点
            return obj
        except Exception as e:
            logger.error(f"Failed to add object node {node_id}: {str(e)}")
            raise

    def get_node(self, node_id):
        """获取节点"""
        try:
            node_id_str = str(node_id)
            # 首先从缓存中获取
            if node_id_str in self.nodes:
                return self.nodes[node_id_str]
            
            # 如果缓存中没有，尝试从服务器获取
            node = self.server.get_node(node_id)
            if node and node.get_browse_name():
                self.nodes[node_id_str] = node  # 缓存有效节点
                return node
            return None
        except Exception as e:
            logger.error(f"Failed to get node {node_id}: {str(e)}")
            return None

    def remove_node(self, node_id):
        """删除节点"""
        try:
            node_id_str = str(node_id)
            if node_id_str in self.nodes:
                node = self.nodes[node_id_str]
                node.delete()
                del self.nodes[node_id_str]  # 从缓存中移除
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove node {node_id}: {str(e)}")
            return False

    def _rebuild_nodes(self):
        """重建所有节点"""
        try:
            from .models import OpcNode
            nodes = OpcNode.objects.all()
            
            for node in nodes:
                try:
                    # 尝试获取节点，如果不存在则创建
                    node_id = ua.NodeId.from_string(node.node_id)
                    ua_node = self.get_node(node_id)
                    
                    if not ua_node:  # 节点不存在，创建新节点
                        if node.node_type == 'variable':
                            # 获取初始值
                            initial_value = node.get_typed_value()
                            if initial_value is None:
                                if node.data_type in ['double', 'float']:
                                    initial_value = 0.0
                                elif node.data_type in ['int32', 'int64', 'uint16', 'uint32', 'uint64']:
                                    initial_value = 0
                                elif node.data_type == 'boolean':
                                    initial_value = False
                                elif node.data_type == 'string':
                                    initial_value = ''
                                elif node.data_type == 'datetime':
                                    initial_value = datetime.now()
                                elif node.data_type == 'array':
                                    initial_value = []
                            
                            # 创建变量节点
                            ua_node = self.add_variable(
                                node_id,
                                node.name,
                                initial_value,
                                varianttype=self._get_ua_data_type(node.data_type)
                            )
                            logger.info(f"Rebuilt variable node: {node.node_id}")
                        else:
                            # 创建对象节点
                            ua_node = self.add_object(node_id, node.name)
                            logger.info(f"Rebuilt object node: {node.node_id}")
                except Exception as e:
                    logger.error(f"Failed to rebuild node {node.node_id}: {str(e)}")
        except Exception as e:
            logger.error(f"Error rebuilding nodes: {str(e)}")

    def _variation_loop(self):
        """节点值变化循环"""
        logger.info("Starting variation loop")
        
        while not self.stop_variation and self.running:
            try:
                # 获取所有需要自动变化的变量节点
                nodes = OpcNode.objects.filter(
                    node_type='variable',
                    variation_type__in=['random', 'linear', 'cycle', 'discrete']
                )
                
                if not nodes.exists():
                    time.sleep(1.0)  # 如果没有需要变化的节点，等待1秒
                    continue
                
                # 获取最小间隔时间
                min_interval = min(node.variation_interval for node in nodes)
                interval = max(min_interval or 1000, 100) / 1000.0  # 确保最小100ms，转换为秒
                
                for node in nodes:
                    try:
                        # 获取当前值
                        current_value = node.get_typed_value()
                        if current_value is None:
                            continue
                        
                        # 根据变化类型计算新值
                        if node.variation_type == 'random':
                            if node.variation_min is not None and node.variation_max is not None:
                                new_value = random.uniform(node.variation_min, node.variation_max)
                            else:
                                continue
                        
                        elif node.variation_type == 'linear':
                            if all(x is not None for x in [node.variation_min, node.variation_max, node.variation_step]):
                                current_value = float(current_value)
                                new_value = current_value + node.variation_step
                                if new_value > node.variation_max:
                                    new_value = node.variation_min
                                elif new_value < node.variation_min:
                                    new_value = node.variation_max
                            else:
                                continue
                        
                        elif node.variation_type == 'cycle':
                            if all(x is not None for x in [node.variation_min, node.variation_max, node.variation_step]):
                                current_value = float(current_value)
                                new_value = current_value + node.variation_step
                                if new_value > node.variation_max:
                                    new_value = node.variation_max
                                    node.variation_step = -abs(node.variation_step)
                                elif new_value < node.variation_min:
                                    new_value = node.variation_min
                                    node.variation_step = abs(node.variation_step)
                                node.save(update_fields=['variation_step'])
                            else:
                                continue
                        
                        elif node.variation_type == 'discrete':
                            try:
                                values = node.get_variation_values_list()
                                if not values:
                                    continue
                                current_index = values.index(float(current_value))
                                next_index = (current_index + 1) % len(values)
                                new_value = values[next_index]
                            except (ValueError, IndexError):
                                continue
                        
                        # 更新OPC UA节点值
                        try:
                            ua_node = self.get_node(ua.NodeId.from_string(node.node_id))
                            if ua_node:
                                if node.data_type == 'array':
                                    ua_node.set_value(new_value)
                                else:
                                    ua_node.set_value(new_value, varianttype=self._get_ua_data_type(node.data_type))
                                # 更新数据库中的值
                                node.value = str(new_value)
                                node.save(update_fields=['value'])
                                logger.debug(f"Updated node {node.node_id} value to {new_value}")
                        except Exception as e:
                            logger.error(f"Failed to update node {node.node_id}: {str(e)}")
                    
                    except Exception as e:
                        logger.error(f"Error processing node {node.node_id}: {str(e)}")
                
                # 等待到下一个间隔
                time.sleep(interval)
            
            except Exception as e:
                logger.error(f"Error in variation loop: {str(e)}")
                time.sleep(1.0)  # 发生错误时等待1秒

    def _get_ua_data_type(self, data_type):
        """获取OPC UA数据类型"""
        type_mapping = {
            'double': ua.VariantType.Double,
            'float': ua.VariantType.Float,
            'int32': ua.VariantType.Int32,
            'int64': ua.VariantType.Int64,
            'uint16': ua.VariantType.UInt16,
            'uint32': ua.VariantType.UInt32,
            'uint64': ua.VariantType.UInt64,
            'boolean': ua.VariantType.Boolean,
            'string': ua.VariantType.String,
            'datetime': ua.VariantType.DateTime,
            'bytestring': ua.VariantType.ByteString,
        }
        return type_mapping.get(data_type, ua.VariantType.String)

    def is_running(self):
        """检查服务器是否运行"""
        return self.running
