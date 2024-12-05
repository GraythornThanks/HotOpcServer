from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
import json
import logging
from datetime import datetime
from .models import OpcNode
from .opcua_server import OpcUaServer
from opcua import ua

logger = logging.getLogger(__name__)

class NodeListView(ListView):
    """节点列表视图"""
    model = OpcNode
    template_name = 'opcua_manager/node_list.html'
    context_object_name = 'nodes'

def node_list(request):
    """获取节点列表API"""
    try:
        nodes = OpcNode.objects.all()
        server = OpcUaServer()
        node_data = []
        
        # 检查服务器是否运行
        if not server.is_running():
            logger.warning("OPC UA Server is not running")
            # 返回数据库中的值
            for node in nodes:
                node_data.append({
                    'id': node.id,
                    'name': node.name,
                    'node_type': node.node_type,
                    'node_id': node.node_id,
                    'data_type': node.data_type,
                    'value': node.value,
                    'description': node.description,
                    'variation_type': node.variation_type,
                    'variation_interval': node.variation_interval,
                    'variation_min': node.variation_min,
                    'variation_max': node.variation_max,
                    'variation_step': node.variation_step,
                    'variation_values': node.variation_values
                })
        else:
            # 服务器运行中，尝试获取实时值
            for node in nodes:
                # 如果是变量节点，尝试从OPC UA服务器获取最新值
                current_value = node.value
                if node.node_type == 'variable':
                    try:
                        ua_node = server.get_node(ua.NodeId.from_string(node.node_id))
                        if ua_node and ua_node.get_browse_name():  # 确保节点存在且有效
                            current_value = str(ua_node.get_value())
                            # 更新数据库中的值
                            if current_value != node.value:
                                node.value = current_value
                                node.save(update_fields=['value'])
                        else:
                            logger.warning(f"Node {node.node_id} does not exist in OPC UA server")
                    except Exception as e:
                        logger.warning(f'Failed to get value from OPC UA server for node {node.node_id}: {str(e)}')
                
                node_data.append({
                    'id': node.id,
                    'name': node.name,
                    'node_type': node.node_type,
                    'node_id': node.node_id,
                    'data_type': node.data_type,
                    'value': current_value,
                    'description': node.description,
                    'variation_type': node.variation_type,
                    'variation_interval': node.variation_interval,
                    'variation_min': node.variation_min,
                    'variation_max': node.variation_max,
                    'variation_step': node.variation_step,
                    'variation_values': node.variation_values
                })
        
        return JsonResponse({
            'success': True,
            'nodes': node_data,
            'server_running': server.is_running()
        })
    except Exception as e:
        logger.error(f'Error getting node list: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': f'获取节点列表失败: {str(e)}'
        })

@csrf_exempt
def add_node(request):
    """添加节点"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不支持的请求方法'})
    
    try:
        data = json.loads(request.body)
        logger.info(f"Adding node with data: {data}")
        
        with transaction.atomic():
            # 首先在OPC UA服务器中创建节点
            server = OpcUaServer()
            node_id = ua.NodeId.from_string(data['node_id'])
            
            # 准备初始值
            if data['node_type'] == 'variable':
                initial_value = convert_value(data.get('value', 0), data.get('data_type', 'double'))
                if initial_value is None:
                    initial_value = 0  # 默认值
                
                # 在OPC UA服务器中创建变量节点
                try:
                    var = server.add_variable(
                        node_id,
                        data['name'],
                        initial_value,
                        varianttype=get_ua_data_type(data.get('data_type', 'double'))
                    )
                    var.set_writable()  # 设置为可写
                except Exception as e:
                    logger.error(f'Failed to create OPC UA variable node: {str(e)}')
                    raise Exception(f'创建OPC UA变量节点失败: {str(e)}')
            else:
                # 创建对象节点
                try:
                    server.add_object(node_id, data['name'])
                except Exception as e:
                    logger.error(f'Failed to create OPC UA object node: {str(e)}')
                    raise Exception(f'创建OPC UA对象节点失败: {str(e)}')
            
            # 然后创建数据库记录
            node = OpcNode.objects.create(
                name=data['name'],
                node_type=data['node_type'],
                node_id=data['node_id'],
                data_type=data.get('data_type', 'double'),
                value=data.get('value'),
                description=data.get('description'),
                variation_type=data.get('variation_type', 'none'),
                variation_interval=int(data.get('variation_interval', 1000)),
                variation_min=float(data['variation_min']) if data.get('variation_min') else None,
                variation_max=float(data['variation_max']) if data.get('variation_max') else None,
                variation_step=float(data['variation_step']) if data.get('variation_step') else None,
                variation_values=data.get('variation_values')
            )
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': node.id,
                    'name': node.name,
                    'node_type': node.node_type,
                    'node_id': node.node_id,
                    'data_type': node.data_type,
                    'value': node.value,
                    'description': node.description,
                    'variation_type': node.variation_type,
                    'variation_interval': node.variation_interval,
                    'variation_min': node.variation_min,
                    'variation_max': node.variation_max,
                    'variation_step': node.variation_step,
                    'variation_values': node.variation_values
                }
            })
    except Exception as e:
        logger.error(f'Error adding node: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': f'添加节点失败: {str(e)}'
        })

@csrf_exempt
def delete_node(request, node_id):
    """删除节点"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不支持请求方法'})
    
    try:
        node = get_object_or_404(OpcNode, id=node_id)
        node.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        logger.error(f'Error deleting node {node_id}: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': f'删除节点失败: {str(e)}'
        })

def get_ua_data_type(data_type):
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

def convert_value(value, data_type):
    """转换值到指定的数据类型"""
    try:
        if not value:
            return None
            
        if data_type == 'array':
            try:
                array_data = json.loads(value)
                return array_data
            except json.JSONDecodeError:
                return None
        elif data_type in ['double', 'float']:
            return float(value)
        elif data_type in ['int32', 'int64']:
            return int(value)
        elif data_type in ['uint16', 'uint32', 'uint64']:
            val = int(value)
            if val < 0:
                raise ValueError('无符号整数不能为负数')
            return val
        elif data_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif data_type == 'datetime':
            return datetime.fromisoformat(value)
        else:
            return value
    except (ValueError, TypeError) as e:
        logger.error(f'Error converting value {value} to type {data_type}: {str(e)}')
        return None

def start_server(request):
    """启动OPC UA服务器"""
    try:
        server = OpcUaServer()
        server.start()
        messages.success(request, 'OPC UA服务器已启动')
    except Exception as e:
        messages.error(request, f'启动服务器失败: {str(e)}')
    return redirect('node-list')

def stop_server(request):
    """停止OPC UA服务器"""
    try:
        server = OpcUaServer()
        server.stop()
        messages.success(request, 'OPC UA服务器已停止')
    except Exception as e:
        messages.error(request, f'停止服务器失败: {str(e)}')
    return redirect('node-list')

@csrf_exempt
def edit_node(request, node_id):
    """编辑节点"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不支持的请求方法'})
    
    try:
        data = json.loads(request.body)
        logger.info(f"Editing node {node_id} with data: {data}")
        
        with transaction.atomic():
            node = get_object_or_404(OpcNode, id=node_id)
            server = OpcUaServer()
            
            # 获取OPC UA节点
            try:
                ua_node = server.get_node(ua.NodeId.from_string(node.node_id))
                if not ua_node:
                    # 如果节点不存在，尝试创建
                    if node.node_type == 'variable':
                        ua_node = server.add_variable(
                            ua.NodeId.from_string(node.node_id),
                            node.name,
                            0,  # 默认值
                            varianttype=get_ua_data_type(node.data_type)
                        )
                        ua_node.set_writable()
                    else:
                        ua_node = server.add_object(ua.NodeId.from_string(node.node_id), node.name)
            except Exception as e:
                logger.error(f'Failed to get or create OPC UA node: {str(e)}')
                raise Exception(f'获取或创建OPC UA节点失败: {str(e)}')
            
            # 更新基本信息
            node.name = data.get('name', node.name)
            node.description = data.get('description', node.description)
            
            # 更新变化配置
            variation_type = data.get('variation_type')
            if variation_type is not None:  # 只有当前端明确发送了variation_type时才更新
                logger.info(f"Updating variation type to: {variation_type}")
                node.variation_type = variation_type
                node.variation_interval = int(data.get('variation_interval', 1000))
                
                # 根据变化类型设置相应的配置
                if variation_type in ['random', 'linear', 'cycle']:
                    try:
                        if 'variation_min' in data:
                            node.variation_min = float(data['variation_min'])
                        if 'variation_max' in data:
                            node.variation_max = float(data['variation_max'])
                        if variation_type in ['linear', 'cycle'] and 'variation_step' in data:
                            node.variation_step = float(data['variation_step'])
                    except (TypeError, ValueError) as e:
                        raise ValueError(f'变化配置参数无效: {str(e)}')
                elif variation_type == 'discrete':
                    if 'variation_values' in data:
                        try:
                            # 验证离散值是否为有效的JSON数组
                            values = json.loads(data['variation_values'])
                            if not isinstance(values, list):
                                raise ValueError('离散值必须是数组格式')
                            node.variation_values = data['variation_values']
                        except json.JSONDecodeError:
                            raise ValueError('离散值必须是有效的JSON数组格式')
                elif variation_type == 'none':
                    # 清除变化配置
                    node.variation_min = None
                    node.variation_max = None
                    node.variation_step = None
                    node.variation_values = None
            
            # 处理节点值
            value = data.get('value')
            if node.node_type == 'variable' and value is not None:
                try:
                    # 转换并验证值
                    typed_value = convert_value(value, node.data_type)
                    if typed_value is None:
                        raise ValueError('无效的值格式')
                    
                    # 更新OPC UA服务器
                    try:
                        if node.data_type == 'array':
                            ua_node.set_value(typed_value)
                        else:
                            ua_node.set_value(typed_value, varianttype=get_ua_data_type(node.data_type))
                    except Exception as e:
                        logger.error(f'Failed to update OPC UA node value: {str(e)}')
                        raise Exception(f'更新OPC UA节点值失败: {str(e)}')
                    
                    # OPC UA更新成功后，更新值
                    node.value = value
                    
                except ValueError as e:
                    raise ValueError(f'值格式错误: {str(e)}')
            
            # 保存所有更改
            node.save()
            logger.info(f"Node {node_id} updated successfully with variation_type: {node.variation_type}")
            
            # 验证保存是否成功
            node.refresh_from_db()
            logger.info(f"Verified node {node_id} after save: variation_type={node.variation_type}")
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': node.id,
                    'name': node.name,
                    'node_type': node.node_type,
                    'node_id': node.node_id,
                    'data_type': node.data_type,
                    'value': node.value,
                    'description': node.description,
                    'variation_type': node.variation_type,
                    'variation_interval': node.variation_interval,
                    'variation_min': node.variation_min,
                    'variation_max': node.variation_max,
                    'variation_step': node.variation_step,
                    'variation_values': node.variation_values
                }
            })
    except Exception as e:
        logger.error(f'Error updating node {node_id}: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': f'更新失败: {str(e)}'
        })
