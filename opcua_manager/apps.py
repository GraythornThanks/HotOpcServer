from django.apps import AppConfig
from django.db.models.signals import post_migrate
import signal
import sys
import logging

logger = logging.getLogger(__name__)

def handle_shutdown(signum, frame):
    """处理关闭信号"""
    from .models import OpcServer
    from .opcua_server import OpcUaServer
    
    logger.info("Received shutdown signal, stopping all OPC UA servers...")
    
    # 获取所有运行中的服务器
    running_servers = OpcServer.objects.filter(is_running=True)
    for server in running_servers:
        try:
            # 停止服务器实例
            opcua_server = OpcUaServer.get_instance(server.id)
            if opcua_server:
                opcua_server.stop()
            
            # 更新数据库状态
            server.is_running = False
            server.save()
            
            logger.info(f"Server {server.name} stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping server {server.name}: {e}")
    
    # 退出程序
    sys.exit(0)

def reset_server_states(sender, **kwargs):
    """重置所有服务器状态为停止"""
    from .models import OpcServer
    
    try:
        # 将所有服务器状态设置为停止
        OpcServer.objects.all().update(is_running=False)
        logger.info("All server states reset to stopped")
    except Exception as e:
        logger.error(f"Error resetting server states: {e}")

class OpcuaManagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'opcua_manager'
    
    def ready(self):
        """应用程序启动时的初始化"""
        # 只在主进程中注册信号处理
        if sys.argv and sys.argv[0].endswith('manage.py'):
            # 注册信号处理器
            signal.signal(signal.SIGINT, handle_shutdown)  # Ctrl+C
            signal.signal(signal.SIGTERM, handle_shutdown)  # kill
            
            # 注册数据库迁移后的回调
            post_migrate.connect(reset_server_states, sender=self)
            
            logger.info("OPC UA Manager initialized with shutdown handlers")
