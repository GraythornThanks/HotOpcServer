from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Node(models.Model):
    """节点总表：存储所有可用的节点配置"""
    name = models.CharField("节点名称", max_length=100)
    node_id = models.CharField("节点ID", max_length=100)
    data_type = models.CharField("数据类型", max_length=50)
    description = models.TextField("描述", blank=True)
    
    # 变化参数
    variation_type = models.CharField("变化类型", max_length=20, choices=[
        ('none', '无变化'),
        ('random', '随机变化'),
        ('linear', '线性变化'),
        ('sine', '正弦变化'),
        ('step', '步进变化'),
    ])
    min_value = models.FloatField("最小值", null=True, blank=True)
    max_value = models.FloatField("最大值", null=True, blank=True)
    step = models.FloatField("步长", null=True, blank=True)
    interval = models.IntegerField("变化间隔(ms)", 
        validators=[MinValueValidator(100)], 
        null=True, blank=True
    )
    
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.node_id})"

    class Meta:
        verbose_name = "节点"
        verbose_name_plural = "节点"

class OpcServer(models.Model):
    """OPC UA服务器配置"""
    name = models.CharField("服务器名称", max_length=100)
    endpoint = models.CharField("服务器地址", max_length=200)
    port = models.IntegerField("端口号", 
        validators=[MinValueValidator(1024), MaxValueValidator(65535)]
    )
    uri = models.CharField("服务器URI", max_length=200)
    
    # 安全配置
    allow_anonymous = models.BooleanField("允许匿名访问", default=True)
    username = models.CharField("用户名", max_length=50, blank=True)
    password = models.CharField("密码", max_length=50, blank=True)
    
    # 高级配置
    min_publish_interval = models.IntegerField("最小发布间隔(ms)", 
        validators=[MinValueValidator(100)],
        default=500
    )
    default_namespace = models.CharField("默认命名空间", max_length=200, blank=True)
    
    # 运行状态
    is_running = models.BooleanField("运行状态", default=False)
    last_start_time = models.DateTimeField("最后启动时间", null=True, blank=True)
    
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.endpoint}:{self.port})"

    class Meta:
        verbose_name = "OPC服务器"
        verbose_name_plural = "OPC服务器"

class ServerNode(models.Model):
    """服务器节点关联：定义每个服务器使用哪些节点"""
    server = models.ForeignKey(OpcServer, on_delete=models.CASCADE, 
                             verbose_name="所属服务器",
                             related_name="server_nodes")
    node = models.ForeignKey(Node, on_delete=models.SET_NULL, 
                            verbose_name="关联节点",
                            null=True,
                            related_name="server_nodes")
    
    # 节点在服务器中的自定义配置，允许覆盖总表中的设置
    enabled = models.BooleanField("是否启用", default=True)
    custom_name = models.CharField("自定义名称", max_length=100, blank=True)
    custom_node_id = models.CharField("自定义节点ID", max_length=100, blank=True)
    
    # 变化参数覆盖
    override_variation = models.BooleanField("覆盖变化设置", default=False)
    custom_variation_type = models.CharField("自定义变化类型", max_length=20, 
        choices=[
            ('none', '无变化'),
            ('random', '随机变化'),
            ('linear', '线性变化'),
            ('sine', '正弦变化'),
            ('step', '步进变化'),
        ],
        blank=True
    )
    custom_min_value = models.FloatField("自定义最小值", null=True, blank=True)
    custom_max_value = models.FloatField("自定义最大值", null=True, blank=True)
    custom_step = models.FloatField("自定义步长", null=True, blank=True)
    custom_interval = models.IntegerField("自定义变化间隔(ms)", 
        validators=[MinValueValidator(100)],
        null=True, blank=True
    )
    
    created_at = models.DateTimeField("创建时间", auto_now_add=True)
    updated_at = models.DateTimeField("更新时间", auto_now=True)

    def __str__(self):
        return f"{self.server.name} - {self.node.name if self.node else '已删除的节点'}"

    class Meta:
        verbose_name = "服务器节点"
        verbose_name_plural = "服务器节点"
        unique_together = ['server', 'node']  # 确保每个节点在一个服务器中只能出现一次

    def get_effective_name(self):
        """获取实际使用的节点名称"""
        return self.custom_name or (self.node.name if self.node else None)

    def get_effective_node_id(self):
        """获取实际使用的节点ID"""
        return self.custom_node_id or (self.node.node_id if self.node else None)

    def get_effective_variation_settings(self):
        """获取实际使用的变化设置"""
        if not self.override_variation or not self.node:
            return {
                'type': self.node.variation_type if self.node else 'none',
                'min_value': self.node.min_value if self.node else None,
                'max_value': self.node.max_value if self.node else None,
                'step': self.node.step if self.node else None,
                'interval': self.node.interval if self.node else None,
            }
        return {
            'type': self.custom_variation_type,
            'min_value': self.custom_min_value,
            'max_value': self.custom_max_value,
            'step': self.custom_step,
            'interval': self.custom_interval,
        }
