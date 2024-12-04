from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
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

def format_array_value(array_data):
    """格式化数组显示"""
    return f"[{', '.join(str(x) for x in array_data)}]"

def convert_value(value, data_type):
    """转换值到指定的数据类型"""
    try:
        if not value:
            return None
            
        if data_type == 'array':
            # 验证数组值
            try:
                array_data = json.loads(value)
                # 检查数组中的所有值是否在Int16范围内
                for val in array_data:
                    if not isinstance(val, (int, float)) or val < -32768 or val > 32767:
                        raise ValueError('数组中的所有值必须是Int16类型（-32768到32767之间的整数）')
                # 返回OPC UA数组变量
                return ua.Variant(array_data, ua.VariantType.Int16, is_array=True)
            except json.JSONDecodeError:
                raise ValueError('无效的数组格式')
        elif data_type == 'double':
            return float(value)
        elif data_type == 'float':
            return float(value)
        elif data_type == 'int32':
            return int(value)
        elif data_type == 'int64':
            return int(value)
        elif data_type == 'uint16':
            val = int(value)
            if val < 0 or val > 65535:
                raise ValueError('UInt16值必须在0到65535之间')
            return val
        elif data_type == 'uint32':
            return int(value)
        elif data_type == 'uint64':
            return int(value)
        elif data_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif data_type == 'datetime':
            return datetime.fromisoformat(value)
        else:
            return str(value)
    except (ValueError, TypeError, json.JSONDecodeError) as e:
        raise ValueError(f'值"{value}"无法转换为{data_type}类型: {str(e)}')

class NodeListView(ListView):
    """节点列表视图"""
    model = OpcNode
    template_name = 'opcua_manager/node_list.html'
    context_object_name = 'nodes'

@method_decorator(csrf_exempt, name='dispatch')
class NodeCreateView(CreateView):
    """创建节点视图"""
    model = OpcNode
    fields = ['name', 'node_type', 'node_id', 'data_type', 'parent_node', 'value', 'description']

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            
            # 验证必填字段
            required_fields = ['name', 'node_type', 'node_id']
            for field in required_fields:
                if field not in data:
                    return JsonResponse({
                        'success': False,
                        'error': f'缺少必填字段: {field}'
                    })
            
            # 获取数据类型
            data_type = data.get('data_type', 'double')
            
            # 如果是变量类型，验证并转换值
            if data['node_type'] == 'variable':
                if 'value' not in data:
                    return JsonResponse({
                        'success': False,
                        'error': '变量节点必须提供值'
                    })
                try:
                    typed_value = convert_value(data['value'], data_type)
                except ValueError as e:
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    })
            
            # 首先尝试在OPC UA服务器上创建节点
            server = OpcUaServer()
            try:
                node_id = ua.NodeId.from_string(data['node_id'])
                if data['node_type'] == 'variable':
                    var = server.add_variable(
                        node_id,
                        data['name'],
                        typed_value,
                        varianttype=get_ua_data_type(data_type)
                    )
                elif data['node_type'] == 'object':
                    server.add_object(node_id, data['name'])
                else:
                    return JsonResponse({
                        'success': False,
                        'error': f'不支持的节点类型: {data["node_type"]}'
                    })
            except Exception as e:
                logger.error(f'Failed to create OPC UA node: {str(e)}')
                return JsonResponse({
                    'success': False,
                    'error': f'创建OPC UA节点失败: {str(e)}'
                })

            # OPC UA节点创建成功后，保存到数据库
            node = OpcNode.objects.create(
                name=data['name'],
                node_type=data['node_type'],
                node_id=data['node_id'],
                data_type=data_type,
                value=data.get('value', ''),
                description=data.get('description', '')
            )
            
            return JsonResponse({
                'success': True,
                'id': node.id,
                'data': {
                    'name': node.name,
                    'node_type': node.node_type,
                    'node_id': node.node_id,
                    'data_type': node.data_type,
                    'value': node.value,
                    'description': node.description
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': '无效的JSON数据'
            })
        except Exception as e:
            logger.error(f'Error creating node: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'创建节点失败: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class NodeUpdateView(UpdateView):
    """更新节点视图"""
    model = OpcNode
    fields = ['name', 'value', 'description']

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            node = self.get_object()
            
            # 记录更新前的值
            old_value = node.value
            new_value = data.get('value', node.value)
            
            # 如果是变量节点且值发生变化，则先验证并转换值
            if node.node_type == 'variable' and old_value != new_value:
                try:
                    typed_value = convert_value(new_value, node.data_type)
                except ValueError as e:
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    })
                
                # 更新OPC UA服务器
                try:
                    server = OpcUaServer()
                    var = server.get_node(ua.NodeId.from_string(node.node_id))
                    var.set_value(typed_value, varianttype=get_ua_data_type(node.data_type))
                except Exception as e:
                    logger.error(f'Failed to update OPC UA node: {str(e)}')
                    return JsonResponse({
                        'success': False,
                        'error': f'更新OPC UA节点失败: {str(e)}'
                    })
            
            # OPC UA更新成功后，更新数据库
            node.name = data.get('name', node.name)
            node.value = new_value
            node.description = data.get('description', node.description)
            node.save()
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': node.id,
                    'name': node.name,
                    'value': node.value,
                    'description': node.description
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': '无效的JSON数据'
            })
        except OpcNode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '节点不存在'
            })
        except Exception as e:
            logger.error(f'Error updating node: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'更新失败: {str(e)}'
            })

@method_decorator(csrf_exempt, name='dispatch')
class NodeDeleteView(DeleteView):
    """删除节点视图"""
    model = OpcNode
    
    def post(self, request, *args, **kwargs):
        try:
            node = self.get_object()
            
            # 尝试从OPC UA服务器删除节点
            try:
                server = OpcUaServer()
                server.remove_node(ua.NodeId.from_string(node.node_id))
            except Exception as e:
                logger.warning(f'Failed to delete OPC UA node {node.node_id}: {str(e)}')
                # 即使OPC UA删除失败，也继续删除数据库记录
                logger.info(f'Proceeding to delete database record for node {node.node_id}')
            
            # 无论OPC UA服务器操作是否成功，都删除数据库记录
            node.delete()
            return JsonResponse({
                'success': True,
                'message': '节点已删除'
            })
            
        except OpcNode.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': '节点不存在'
            })
        except Exception as e:
            logger.error(f'Error deleting node: {str(e)}')
            return JsonResponse({
                'success': False,
                'error': f'删除失败: {str(e)}'
            })

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
def add_node(request):
    """添加节点"""
    try:
        data = json.loads(request.body)
        node = OpcNode()
        node.name = data.get('name')
        node.node_type = data.get('nodeType')
        node.node_id = data.get('nodeId')
        node.data_type = data.get('dataType')
        node.description = data.get('description')
        
        value = data.get('value')
        if node.data_type == 'array' and value:
            # 验证数组值
            try:
                array_data = json.loads(value)
                # 检查数组中的所有值是否在Int16范围内
                for val in array_data:
                    if not isinstance(val, (int, float)) or val < -32768 or val > 32767:
                        raise ValueError('数组中的所有值必须是Int16类型（-32768到32767之间的整数）')
                node.value = value
            except json.JSONDecodeError:
                raise ValueError('无效的数组格式')
        else:
            node.value = value

        if data.get('parentId'):
            node.parent_node = OpcNode.objects.get(id=data.get('parentId'))
            
        node.save()
        
        # 如果是变量节点，创建OPC UA变量
        if node.node_type == 'variable':
            try:
                server = OpcUaServer()
                server.add_variable(node)
            except Exception as e:
                node.delete()
                raise Exception(f'创建OPC UA节点失败: {str(e)}')
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'创建失败: {str(e)}'
        })

@csrf_exempt
def edit_node(request, node_id):
    """编辑节点"""
    try:
        data = json.loads(request.body)
        node = get_object_or_404(OpcNode, id=node_id)
        
        node.name = data.get('name', node.name)
        node.description = data.get('description', node.description)
        
        value = data.get('value')
        if node.node_type == 'variable' and value is not None:
            try:
                # 转换并验证值
                typed_value = convert_value(value, node.data_type)
                if typed_value is None:
                    raise ValueError('无效的值格式')
                
                # 更新OPC UA服务器
                try:
                    server = OpcUaServer()
                    var = server.get_node(ua.NodeId.from_string(node.node_id))
                    if node.data_type == 'array':
                        # 对于数组类型，直接使用convert_value返回的Variant
                        var.set_value(typed_value)
                    else:
                        # 对于其他类型，使用常规的set_value方法
                        var.set_value(typed_value, varianttype=get_ua_data_type(node.data_type))
                except Exception as e:
                    logger.error(f'Failed to update OPC UA node: {str(e)}')
                    raise Exception(f'更新OPC UA节点失败: {str(e)}')
                
                # OPC UA更新成功后，更新数据库
                node.value = value
                node.save()
                
            except ValueError as e:
                raise ValueError(f'值格式错误: {str(e)}')
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'更新失败: {str(e)}'
        })
