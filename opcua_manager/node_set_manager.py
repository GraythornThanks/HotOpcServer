import os
import json
import shutil
from pathlib import Path
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class NodeSetManager:
    """节点集合管理器"""
    
    def __init__(self):
        # 节点集合存储目录
        self.base_dir = Path(settings.BASE_DIR) / 'node_sets'
        self.base_dir.mkdir(exist_ok=True)
        
        # 确保default节点集合存在
        self.ensure_default_set()
        
        # 当前激活的节点集合
        self._active_set = self.get_active_set()
    
    def ensure_default_set(self):
        """确保default节点集合存在"""
        default_set = self.base_dir / 'default'
        if not default_set.exists():
            default_set.mkdir()
            self.save_nodes([], 'default')
    
    def get_active_set(self):
        """获取当前激活的节点集合"""
        active_file = self.base_dir / 'active.txt'
        if active_file.exists():
            return active_file.read_text().strip()
        return 'default'
    
    def set_active_set(self, set_name):
        """设置当前激活的节点集合"""
        if not self.set_exists(set_name):
            raise ValueError(f"节点集合 {set_name} 不存在")
        
        active_file = self.base_dir / 'active.txt'
        active_file.write_text(set_name)
        self._active_set = set_name
    
    def get_set_list(self):
        """获取所有节点集合列表"""
        sets = []
        for item in self.base_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                sets.append({
                    'name': item.name,
                    'node_count': len(self.get_nodes(item.name)),
                    'is_active': item.name == self._active_set
                })
        return sorted(sets, key=lambda x: x['name'])
    
    def set_exists(self, set_name):
        """检查节点集合是否存在"""
        return (self.base_dir / set_name).is_dir()
    
    def create_set(self, set_name, nodes=None):
        """创建新的节点集合"""
        if not self._is_valid_set_name(set_name):
            raise ValueError("节点集合名称只能包含字母、数字和下划线，长度在3-20个字符之间")
        
        if self.set_exists(set_name):
            raise ValueError(f"节点集合 {set_name} 已存在")
        
        set_dir = self.base_dir / set_name
        set_dir.mkdir()
        self.save_nodes(nodes or [], set_name)
        return True
    
    def copy_set(self, source_name, target_name):
        """复制节点集合"""
        if not self._is_valid_set_name(target_name):
            raise ValueError("节点集合名称只能包含字母、数字和下划线，长度在3-20个字符之间")
        
        if not self.set_exists(source_name):
            raise ValueError(f"源节点集合 {source_name} 不存在")
        
        if self.set_exists(target_name):
            raise ValueError(f"目标节点集合 {target_name} 已存在")
        
        source_dir = self.base_dir / source_name
        target_dir = self.base_dir / target_name
        shutil.copytree(source_dir, target_dir)
        return True
    
    def delete_set(self, set_name):
        """删除节点集合"""
        if set_name == 'default':
            raise ValueError("不能删除default节点集合")
        
        if not self.set_exists(set_name):
            raise ValueError(f"节点集合 {set_name} 不存在")
        
        if self._active_set == set_name:
            self.set_active_set('default')
        
        set_dir = self.base_dir / set_name
        shutil.rmtree(set_dir)
        return True
    
    def get_nodes(self, set_name=None):
        """获取指定节点集合的节点列表"""
        if set_name is None:
            set_name = self._active_set
        
        if not self.set_exists(set_name):
            raise ValueError(f"节点集合 {set_name} 不存在")
        
        nodes_file = self.base_dir / set_name / 'nodes.json'
        if not nodes_file.exists():
            return []
        
        try:
            with open(nodes_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    
    def save_nodes(self, nodes, set_name=None):
        """保存节点列表到指定节点集合"""
        if set_name is None:
            set_name = self._active_set
        
        if not self.set_exists(set_name):
            raise ValueError(f"节点集合 {set_name} 不存在")
        
        nodes_file = self.base_dir / set_name / 'nodes.json'
        with open(nodes_file, 'w', encoding='utf-8') as f:
            json.dump(nodes, f, ensure_ascii=False, indent=2)
    
    def add_nodes_to_set(self, set_name, nodes):
        """添加节点到指定集合"""
        if not self.set_exists(set_name):
            raise ValueError(f"节点集合 {set_name} 不存在")
        
        existing_nodes = self.get_nodes(set_name)
        existing_node_ids = {node['node_id'] for node in existing_nodes}
        
        # 过滤掉已存在的节点
        new_nodes = [node for node in nodes if node['node_id'] not in existing_node_ids]
        if not new_nodes:
            return 0
        
        # 为新节点分配ID
        max_id = max((node['id'] for node in existing_nodes), default=0)
        for i, node in enumerate(new_nodes, 1):
            node['id'] = max_id + i
        
        # 合并并保存节点
        existing_nodes.extend(new_nodes)
        self.save_nodes(existing_nodes, set_name)
        return len(new_nodes)
    
    def remove_nodes_from_set(self, set_name, node_ids):
        """从指定集合中移除节点"""
        if not self.set_exists(set_name):
            raise ValueError(f"节点集合 {set_name} 不存在")
        
        nodes = self.get_nodes(set_name)
        original_count = len(nodes)
        nodes = [node for node in nodes if node['id'] not in node_ids]
        
        if len(nodes) < original_count:
            self.save_nodes(nodes, set_name)
            return original_count - len(nodes)
        return 0
    
    def create_set_from_nodes(self, set_name, node_ids, source_set=None):
        """从选定的节点创建新的节点集合"""
        if source_set is None:
            source_set = self._active_set
        
        if not self.set_exists(source_set):
            raise ValueError(f"源节点集合 {source_set} 不存在")
        
        source_nodes = self.get_nodes(source_set)
        selected_nodes = [node.copy() for node in source_nodes if node['id'] in node_ids]
        
        if not selected_nodes:
            raise ValueError("未选择任何节点")
        
        # 重置节点ID
        for i, node in enumerate(selected_nodes, 1):
            node['id'] = i
        
        # 创建新的节点集合
        self.create_set(set_name, selected_nodes)
        return len(selected_nodes)
    
    def _is_valid_set_name(self, name):
        """验证节点集合名称是否有效"""
        import re
        pattern = r'^[a-zA-Z0-9_]{3,20}$'
        return bool(re.match(pattern, name))
    
    @property
    def active_set(self):
        """获取当前激活的节点集合名称"""
        return self._active_set

# 创建全局节点集合管理器实例
node_set_manager = NodeSetManager() 