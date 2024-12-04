from opcua import Server
import threading
import time
from datetime import datetime

class OpcUaServer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(OpcUaServer, cls).__new__(cls)
                cls._instance.initialized = False
            return cls._instance

    def __init__(self):
        if self.initialized:
            return
        
        self.server = Server()
        self.server.set_endpoint("opc.tcp://0.0.0.0:4840/freeopcua/server/")
        self.server.set_server_name("HotOpcServer")
        
        # 创建地址空间
        self.root = self.server.get_objects_node()
        self.running = False
        self.initialized = True

    def start(self):
        """启动服务器"""
        if not self.running:
            self.server.start()
            self.running = True
            
    def stop(self):
        """停止服务器"""
        if self.running:
            self.server.stop()
            self.running = False

    def add_variable(self, node_id, name, value, varianttype=None):
        """添加变量节点
        
        Args:
            node_id: 节点ID（ua.NodeId对象）
            name: 节点名称
            value: 节点值
            varianttype: 值类型（ua.VariantType对象）
        
        Returns:
            新创建的变量节点
        """
        new_node = self.root.add_variable(node_id, name, value, varianttype=varianttype)
        new_node.set_writable()  # 设置变量可写
        return new_node

    def add_object(self, node_id, name):
        """添加对象节点
        
        Args:
            node_id: 节点ID（ua.NodeId对象）
            name: 节点名称
        
        Returns:
            新创建的对象节点
        """
        new_node = self.root.add_object(node_id, name)
        return new_node

    def remove_node(self, node_id):
        """删除节点
        
        Args:
            node_id: 节点ID（ua.NodeId对象）
        """
        node = self.server.get_node(node_id)
        node.delete()

    def get_node(self, node_id):
        """获取节点
        
        Args:
            node_id: 节点ID（ua.NodeId对象）
            
        Returns:
            获取到的节点对象
        """
        return self.server.get_node(node_id)

    def get_node_value(self, node_id):
        """获取节点值
        
        Args:
            node_id: 节点ID（ua.NodeId对象）
            
        Returns:
            节点的当前值
        """
        node = self.server.get_node(node_id)
        return node.get_value()

    def is_running(self):
        """检查服务器是否正在运行
        
        Returns:
            bool: 服务器运行状态
        """
        return self.running
