import os
import json
import shutil
from pathlib import Path
from django.conf import settings

class DatabaseManager:
    """配置集管理器类"""
    
    def __init__(self):
        # 配置集存储目录
        self.base_dir = Path(settings.BASE_DIR) / 'databases'
        self.base_dir.mkdir(exist_ok=True)
        
        # 确保default配置集存在
        self.ensure_default_database()
        
        # 当前激活的配置集
        self._active_database = self.get_active_database()
    
    def ensure_default_database(self):
        """确保default配置集存在"""
        default_db = self.base_dir / 'default'
        if not default_db.exists():
            default_db.mkdir()
            self.save_nodes([], 'default')
    
    def get_active_database(self):
        """获取当前激活的配置集"""
        active_file = self.base_dir / 'active.txt'
        if active_file.exists():
            return active_file.read_text().strip()
        return 'default'
    
    def set_active_database(self, db_name):
        """设置当前激活的配置集"""
        if not self.database_exists(db_name):
            raise ValueError(f"配置集 {db_name} 不存在")
        
        active_file = self.base_dir / 'active.txt'
        active_file.write_text(db_name)
        self._active_database = db_name
    
    def get_database_list(self):
        """获取所有配置集列表"""
        databases = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                databases.append(item.name)
        return sorted(databases)
    
    def database_exists(self, db_name):
        """检查配置集是否存在"""
        return (self.base_dir / db_name).is_dir()
    
    def create_database(self, db_name):
        """创建新的配置集"""
        if not self._is_valid_database_name(db_name):
            raise ValueError("配置集名称只能包含字母、数字和下划线，长度在3-20个字符之间")
        
        if self.database_exists(db_name):
            raise ValueError(f"配置集 {db_name} 已存在")
        
        db_dir = self.base_dir / db_name
        db_dir.mkdir()
        self.save_nodes([], db_name)
        return True
    
    def copy_database(self, source_name, target_name):
        """复制配置集"""
        if not self._is_valid_database_name(target_name):
            raise ValueError("配置集名称只能包含字母、数字和下划线，长度在3-20个字符之间")
        
        if not self.database_exists(source_name):
            raise ValueError(f"源配置集 {source_name} 不存在")
        
        if self.database_exists(target_name):
            raise ValueError(f"目标配置集 {target_name} 已存在")
        
        source_dir = self.base_dir / source_name
        target_dir = self.base_dir / target_name
        shutil.copytree(source_dir, target_dir)
        return True
    
    def delete_database(self, db_name):
        """删除配置集"""
        if db_name == 'default':
            raise ValueError("不能删除default配置集")
        
        if not self.database_exists(db_name):
            raise ValueError(f"配置集 {db_name} 不存在")
        
        if self._active_database == db_name:
            self.set_active_database('default')
        
        db_dir = self.base_dir / db_name
        shutil.rmtree(db_dir)
        return True
    
    def get_nodes(self, db_name=None):
        """获取指定配置集的节点列表"""
        if db_name is None:
            db_name = self._active_database
        
        if not self.database_exists(db_name):
            raise ValueError(f"配置集 {db_name} 不存在")
        
        nodes_file = self.base_dir / db_name / 'nodes.json'
        if not nodes_file.exists():
            return []
        
        try:
            with open(nodes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    
    def save_nodes(self, nodes, db_name=None):
        """保存节点列表到指定配置集"""
        if db_name is None:
            db_name = self._active_database
        
        if not self.database_exists(db_name):
            raise ValueError(f"配置集 {db_name} 不存在")
        
        nodes_file = self.base_dir / db_name / 'nodes.json'
        with open(nodes_file, 'w', encoding='utf-8') as f:
            json.dump(nodes, f, ensure_ascii=False, indent=2)
    
    def _is_valid_database_name(self, name):
        """验证配置集名称是否有效"""
        import re
        pattern = r'^[a-zA-Z0-9_]{3,20}$'
        return bool(re.match(pattern, name))
    
    @property
    def active_database(self):
        """获取当前激活的配置集名称"""
        return self._active_database

# 创建全局数据库管理器实例
db_manager = DatabaseManager() 