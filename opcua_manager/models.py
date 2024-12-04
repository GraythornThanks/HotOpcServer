from django.db import models

class OpcNode(models.Model):
    NODE_TYPES = (
        ('variable', '变量'),
        ('object', '对象'),
        ('method', '方法'),
    )
    
    DATA_TYPES = (
        ('double', '双精度浮点数(Double)'),
        ('float', '单精度浮点数(Float)'),
        ('int32', '32位整数(Int32)'),
        ('int64', '64位整数(Int64)'),
        ('uint16', '无符号16位整数(UInt16)'),
        ('uint32', '无符号32位整数(UInt32)'),
        ('uint64', '无符号64位整数(UInt64)'),
        ('boolean', '布尔值(Boolean)'),
        ('string', '字符串(String)'),
        ('datetime', '日期时间(DateTime)'),
        ('bytestring', '字节串(ByteString)'),
        ('array', '数组(Array)'),
    )
    
    name = models.CharField(max_length=100, verbose_name='节点名称')
    node_type = models.CharField(max_length=20, choices=NODE_TYPES, verbose_name='节点类型')
    node_id = models.CharField(max_length=100, verbose_name='节点ID')
    data_type = models.CharField(max_length=20, choices=DATA_TYPES, default='double', verbose_name='数据类型')
    parent_node = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, verbose_name='父节点')
    value = models.CharField(max_length=255, blank=True, null=True, verbose_name='节点值')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'OPC UA节点'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name} ({self.node_id})"

    def get_typed_value(self):
        """根据数据类型转换值"""
        if not self.value:
            return None
            
        try:
            if self.data_type == 'double':
                return float(self.value)
            elif self.data_type == 'float':
                return float(self.value)
            elif self.data_type == 'int32':
                return int(self.value)
            elif self.data_type == 'int64':
                return int(self.value)
            elif self.data_type == 'uint16':
                return int(self.value)
            elif self.data_type == 'uint32':
                return int(self.value)
            elif self.data_type == 'uint64':
                return int(self.value)
            elif self.data_type == 'boolean':
                return self.value.lower() in ('true', '1', 'yes', 'on')
            elif self.data_type == 'datetime':
                from datetime import datetime
                return datetime.fromisoformat(self.value)
            elif self.data_type == 'array':
                # 将字符串形式的数组转换为Python列表
                import json
                return json.loads(self.value)
            else:
                return self.value
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
