import logging
from datetime import datetime
import threading
import time
import random
import math
from opcua import Server, ua
from django.utils import timezone
from .models import Node, OpcServer, ServerNode

logger = logging.getLogger(__name__)

class OpcUaServerInstance:
    """单个OPC UA服务器实例的管理类"""
    
    def __init__(self, server_config):
        """
        初始化OPC UA服务器实例
        :param server_config: OpcServer模型实例
        """
        self.config = server_config
        self.server = None
        self.running = False
        self.nodes = {}  # 存储节点对象的字典
        self.variation_threads = {}  # 存储变化线程的字典
        self._stop_event = threading.Event()
    
    def build_endpoint(self):
        """构建服务器端点URL"""
        return f"opc.tcp://{self.config.endpoint}:{self.config.port}{self.config.uri}"
    
    def setup_server(self):
        """配置并初始化OPC UA服务器"""
        self.server = Server()
        
        # 设置服务器URL
        self.server.set_endpoint(self.build_endpoint())
        
        # 设置服务器名称
        self.server.set_server_name(self.config.name)
        
        # 配置安全设置
        if self.config.allow_anonymous:
            self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
        else:
            # TODO: 实现用户认证
            pass
        
        # 获取根节点
        root = self.server.get_root_node()
        
        # 获取Objects节点
        objects = self.server.get_objects_node()
        
        # 创建服务器专用的对象文件夹
        server_folder = objects.add_folder(f"ns=1;s={self.config.name}", self.config.name)
        
        # 加载服务器配置的节点
        self.load_nodes(server_folder)
    
    def load_nodes(self, parent_folder):
        """
        加载服务器配置的所有节点
        :param parent_folder: 父节点文件夹
        """
        # 获取该服务器启用的所有节点
        server_nodes = ServerNode.objects.filter(
            server=self.config,
            enabled=True,
            node__isnull=False  # 确保关联的节点存在
        ).select_related('node')
        
        for server_node in server_nodes:
            try:
                # 获取实际使用的节点配置
                node_name = server_node.get_effective_name()
                node_id = server_node.get_effective_node_id()
                variation_settings = server_node.get_effective_variation_settings()
                
                # 创建变量节点
                var = parent_folder.add_variable(
                    f"ns=1;s={node_id}", 
                    node_name,
                    0.0  # 初始值
                )
                
                # 设置变量可写
                var.set_writable()
                
                # 存储节点信息
                self.nodes[node_id] = {
                    'node': var,
                    'server_node': server_node,
                    'settings': variation_settings
                }
                
                logger.info(f"Added node: {node_name} ({node_id})")
                
            except Exception as e:
                logger.error(f"Error adding node {server_node.node.name}: {str(e)}")
    
    def start_variation_thread(self, node_id):
        """
        启动节点值变化线程
        :param node_id: 节点ID
        """
        if node_id not in self.nodes:
            return
            
        node_info = self.nodes[node_id]
        settings = node_info['settings']
        
        if settings['type'] == 'none':
            return
            
        def variation_task():
            while not self._stop_event.is_set():
                try:
                    new_value = self.calculate_next_value(node_id)
                    node_info['node'].set_value(new_value)
                    time.sleep(settings['interval'] / 1000)  # 转换为秒
                except Exception as e:
                    logger.error(f"Error updating node {node_id}: {str(e)}")
                    time.sleep(1)  # 发生错误时等待1秒
        
        # 创建并启动变化线程
        thread = threading.Thread(target=variation_task)
        thread.daemon = True
        thread.start()
        self.variation_threads[node_id] = thread
    
    def calculate_next_value(self, node_id):
        """
        计算节点的下一个值
        :param node_id: 节点ID
        :return: 计算得到的新值
        """
        node_info = self.nodes[node_id]
        settings = node_info['settings']
        current_value = node_info['node'].get_value()
        
        if settings['type'] == 'random':
            return random.uniform(settings['min_value'], settings['max_value'])
            
        elif settings['type'] == 'linear':
            new_value = current_value + settings['step']
            if new_value > settings['max_value']:
                new_value = settings['min_value']
            return new_value
            
        elif settings['type'] == 'sine':
            # 使用当前时间计算正弦波
            t = time.time() * 1000 / settings['interval']  # 转换为周期单位
            amplitude = (settings['max_value'] - settings['min_value']) / 2
            offset = settings['min_value'] + amplitude
            return offset + amplitude * math.sin(2 * math.pi * t)
            
        elif settings['type'] == 'step':
            if current_value >= settings['max_value']:
                return settings['min_value']
            return current_value + settings['step']
            
        return current_value
    
    def start(self):
        """启动服务器"""
        if self.running:
            return
            
        try:
            # 初始化服务器
            self.setup_server()
            
            # 启动服务器
            self.server.start()
            self.running = True
            self._stop_event.clear()
            
            # 启动所有节点的变化线程
            for node_id in self.nodes:
                self.start_variation_thread(node_id)
            
            # 更新服务器状态
            self.config.is_running = True
            self.config.last_start_time = timezone.now()
            self.config.save()
            
            logger.info(f"Server {self.config.name} started successfully")
            
        except Exception as e:
            logger.error(f"Error starting server {self.config.name}: {str(e)}")
            self.running = False
            raise
    
    def stop(self):
        """停止服务器"""
        if not self.running:
            return
            
        try:
            # 停止所有变化线程
            self._stop_event.set()
            self.variation_threads.clear()
            
            # 停止服务器
            self.server.stop()
            self.running = False
            
            # 更新服务器状态
            self.config.is_running = False
            self.config.save()
            
            logger.info(f"Server {self.config.name} stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping server {self.config.name}: {str(e)}")
            raise
    
    def restart(self):
        """重启服务器"""
        try:
            self.stop()
            time.sleep(1)  # 等待1秒确保完全停止
            self.start()
            logger.info(f"Server {self.config.name} restarted successfully")
        except Exception as e:
            logger.error(f"Error restarting server {self.config.name}: {str(e)}")
            raise

class OpcUaServerManager:
    """OPC UA服务器管理器，负责管理所有服务器实例"""
    
    _instance = None
    _servers = {}  # 存储所有服务器实例
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OpcUaServerManager, cls).__new__(cls)
        return cls._instance
    
    def get_server(self, server_id):
        """
        获取服务器实例
        :param server_id: 服务器ID
        :return: OpcUaServerInstance实例
        """
        if server_id not in self._servers:
            try:
                server_config = OpcServer.objects.get(id=server_id)
                self._servers[server_id] = OpcUaServerInstance(server_config)
            except OpcServer.DoesNotExist:
                raise ValueError(f"Server with id {server_id} does not exist")
        return self._servers[server_id]
    
    def remove_server(self, server_id):
        """
        移除服务器实例
        :param server_id: 服务器ID
        """
        if server_id in self._servers:
            server = self._servers[server_id]
            if server.running:
                server.stop()
            del self._servers[server_id]
    
    def start_server(self, server_id):
        """启动指定的服务器"""
        server = self.get_server(server_id)
        server.start()
    
    def stop_server(self, server_id):
        """停止指定的服务器"""
        if server_id in self._servers:
            server = self._servers[server_id]
            server.stop()
    
    def restart_server(self, server_id):
        """重启指定的服务器"""
        server = self.get_server(server_id)
        server.restart()
    
    def cleanup(self):
        """清理所有服务器实例"""
        for server_id in list(self._servers.keys()):
            self.stop_server(server_id)
        self._servers.clear()

# 创建全局服务器管理器实例
server_manager = OpcUaServerManager()
