# Generated by Django 5.1.3 on 2024-12-06 03:10

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('opcua_manager', '0004_opcnode_decimal_places'),
    ]

    operations = [
        migrations.CreateModel(
            name='OpcServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='服务器名称')),
                ('endpoint', models.CharField(max_length=200, verbose_name='终端点')),
                ('port', models.IntegerField(verbose_name='端口号')),
                ('uri', models.CharField(max_length=200, verbose_name='服务器URI')),
                ('allow_anonymous', models.BooleanField(default=True, verbose_name='允许匿名访问')),
                ('username', models.CharField(blank=True, max_length=100, null=True, verbose_name='用户名')),
                ('password', models.CharField(blank=True, max_length=100, null=True, verbose_name='密码')),
                ('min_sampling_interval', models.IntegerField(default=100, verbose_name='最小采样间隔(ms)')),
                ('is_running', models.BooleanField(default=False, verbose_name='运行状态')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': 'OPC UA服务器',
                'verbose_name_plural': 'OPC UA服务器',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='节点名称')),
                ('node_id', models.CharField(max_length=200, verbose_name='节点ID')),
                ('node_type', models.CharField(max_length=20, verbose_name='节点类型')),
                ('data_type', models.CharField(max_length=20, verbose_name='数据类型')),
                ('value', models.CharField(blank=True, max_length=200, null=True, verbose_name='当前值')),
                ('description', models.TextField(blank=True, null=True, verbose_name='描述')),
                ('variation_type', models.CharField(default='none', max_length=20, verbose_name='变化类型')),
                ('variation_interval', models.IntegerField(default=1000, verbose_name='变化间隔(ms)')),
                ('variation_min', models.FloatField(blank=True, null=True, verbose_name='最小值')),
                ('variation_max', models.FloatField(blank=True, null=True, verbose_name='最大值')),
                ('variation_step', models.FloatField(blank=True, null=True, verbose_name='步长')),
                ('variation_values', models.TextField(blank=True, null=True, verbose_name='离散值集合')),
                ('decimal_places', models.IntegerField(default=2, verbose_name='小数位数')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nodes', to='opcua_manager.opcserver', verbose_name='所属服务器')),
            ],
            options={
                'verbose_name': '节点',
                'verbose_name_plural': '节点',
                'ordering': ['name'],
                'unique_together': {('server', 'node_id')},
            },
        ),
        migrations.DeleteModel(
            name='OpcNode',
        ),
    ]
