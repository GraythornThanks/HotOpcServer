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
    
    VARIATION_TYPES = (
        ('none', '不变化'),
        ('random', '随机变化'),
        ('linear', '线性变化'),
        ('discrete', '离散变化'),
        ('cycle', '循环变化'),
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

    # 自动变化相关字段
    variation_type = models.CharField(max_length=20, choices=VARIATION_TYPES, default='none', verbose_name='变化类型')
    variation_min = models.FloatField(null=True, blank=True, verbose_name='变化最小值')
    variation_max = models.FloatField(null=True, blank=True, verbose_name='变化最大值')
    variation_step = models.FloatField(null=True, blank=True, verbose_name='变化步长')
    variation_interval = models.IntegerField(default=1000, verbose_name='变化间隔(毫秒)')
    variation_values = models.TextField(null=True, blank=True, verbose_name='离散值集合')
    variation_direction = models.IntegerField(default=1, verbose_name='变化方向')  # 1表示增加，-1表示减少
    variation_cycle = models.BooleanField(default=False, verbose_name='是否循环')

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
                import json
                return json.loads(self.value)
            else:
                return self.value
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

    def get_variation_values_list(self):
        """获取离散值集合列表"""
        if not self.variation_values:
            return []
        try:
            import json
            return json.loads(self.variation_values)
        except json.JSONDecodeError:
            return []

    def get_next_value(self):
        """获取下一个值"""
        current_value = self.get_typed_value()
        if current_value is None:
            return None

        if self.variation_type == 'none':
            return current_value
        
        elif self.variation_type == 'random':
            import random
            if self.variation_min is not None and self.variation_max is not None:
                if self.data_type in ['int32', 'int64', 'uint16', 'uint32', 'uint64']:
                    return random.randint(int(self.variation_min), int(self.variation_max))
                else:
                    return random.uniform(self.variation_min, self.variation_max)
            return current_value
        
        elif self.variation_type in ['linear', 'cycle']:
            if self.variation_min is None or self.variation_max is None or self.variation_step is None:
                return current_value
            
            next_value = float(current_value) + (self.variation_step * self.variation_direction)
            
            if self.variation_type == 'cycle':
                # 循环变化：到达边界时回到起点
                if self.variation_direction == 1 and next_value > self.variation_max:
                    next_value = self.variation_min
                elif self.variation_direction == -1 and next_value < self.variation_min:
                    next_value = self.variation_max
            else:
                # 线性变化：到达边界时改变方向
                if next_value >= self.variation_max:
                    self.variation_direction = -1
                    next_value = self.variation_max
                elif next_value <= self.variation_min:
                    self.variation_direction = 1
                    next_value = self.variation_min
            
            self.save()  # 保存方向变化
            return next_value
        
        elif self.variation_type == 'discrete':
            values = self.get_variation_values_list()
            if not values:
                return current_value
            
            try:
                current_index = values.index(float(current_value))
                next_index = (current_index + 1) % len(values)
                return values[next_index]
            except (ValueError, IndexError):
                return values[0]
        
        return current_value
