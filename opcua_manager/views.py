from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import OpcServer, Node
from .opcua_server import OpcUaServer
import asyncio
import socket
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NodeListView(TemplateView):
    template_name = 'opcua_manager/node_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['servers'] = OpcServer.objects.all()
        return context

# 服务器管理API
@require_http_methods(["GET"])
def server_list(request):
    """获取所有服务器列表"""
    servers = OpcServer.objects.all()
    server_list = []
    for server in servers:
        server_list.append({
            'id': server.id,
            'name': server.name,
            'endpoint': server.endpoint,
            'port': server.port,
            'uri': server.uri,
            'allow_anonymous': server.allow_anonymous,
            'username': server.username,
            'min_sampling_interval': server.min_sampling_interval,
            'is_running': server.is_running,
            'node_count': server.nodes.count(),
            'created_at': server.created_at.isoformat(),
            'updated_at': server.updated_at.isoformat()
        })
    return JsonResponse({'success': True, 'servers': server_list})

@require_http_methods(["POST"])
def add_server(request):
    """添加新服务器"""
    try:
        data = json.loads(request.body)
        
        # 检查服务器名称是否重复
        if OpcServer.objects.filter(name=data['name']).exists():
            return JsonResponse({
                'success': False,
                'error': '服务器名称已存在'
            })
        
        # 检查终端点和端口组合是否已存在
        if OpcServer.objects.filter(endpoint=data['endpoint'], port=data['port']).exists():
            return JsonResponse({
                'success': False,
                'error': f'终端点 {data["endpoint"]}:{data["port"]} 已被其他服务器使用'
            })
        
        server = OpcServer.objects.create(
            name=data['name'],
            endpoint=data['endpoint'],
            port=data['port'],
            uri=data['uri'],
            allow_anonymous=data.get('allow_anonymous', True),
            username=data.get('username', ''),
            password=data.get('password', ''),
            min_sampling_interval=data.get('min_sampling_interval', 100)
        )
        return JsonResponse({
            'success': True,
            'server': {
                'id': server.id,
                'name': server.name,
                'is_running': server.is_running
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def edit_server(request, server_id):
    """编辑服务器配置"""
    try:
        server = get_object_or_404(OpcServer, id=server_id)
        data = json.loads(request.body)
        
        # 检查服务器名称是否重复（排除当前服务器）
        if OpcServer.objects.filter(name=data['name']).exclude(id=server_id).exists():
            return JsonResponse({
                'success': False,
                'error': '服务器名称已存在'
            })
        
        # 检查终端点和端口组合是否已存在（排除当前服务器）
        if OpcServer.objects.filter(
            endpoint=data['endpoint'], 
            port=data['port']
        ).exclude(id=server_id).exists():
            return JsonResponse({
                'success': False,
                'error': f'终端点 {data["endpoint"]}:{data["port"]} 已被其他服务器使用'
            })
        
        # 更新基本信息
        server.name = data['name']
        server.endpoint = data['endpoint']
        server.port = data['port']
        server.uri = data['uri']
        server.allow_anonymous = data.get('allow_anonymous', True)
        server.min_sampling_interval = data.get('min_sampling_interval', 100)
        
        # 如果不允许匿名访问，更新认证信息
        if not data.get('allow_anonymous', True):
            server.username = data.get('username', '')
            if 'password' in data and data['password']:
                server.password = data['password']
        
        server.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def delete_server(request, server_id):
    """删除服务器"""
    try:
        server = get_object_or_404(OpcServer, id=server_id)
        if server.is_running:
            return JsonResponse({
                'success': False,
                'error': '无法删除��行中的服务器，请先停止服务器'
            })
        server.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def start_server(request, server_id):
    """启动服务器"""
    try:
        server = get_object_or_404(OpcServer, id=server_id)
        if server.is_running:
            return JsonResponse({
                'success': False,
                'error': '服务器已经在运行'
            })
        
        # 创建OPC UA服务器实例并启动
        opcua_server = OpcUaServer.create_instance(server)
        if opcua_server.start():
            server.is_running = True
            server.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({
                'success': False,
                'error': '服务器启动失败'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def stop_server(request, server_id):
    """停止服务器"""
    try:
        server = get_object_or_404(OpcServer, id=server_id)
        if not server.is_running:
            return JsonResponse({
                'success': False,
                'error': '服务器已经停止'
            })
        
        # 停止OPC UA服务器
        opcua_server = OpcUaServer.get_instance(server.id)
        if opcua_server and opcua_server.stop():
            server.is_running = False
            server.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({
                'success': False,
                'error': '服务器停止失败'
            })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def server_status(request, server_id):
    """获取服务器状态"""
    try:
        server = get_object_or_404(OpcServer, id=server_id)
        return JsonResponse({
            'success': True,
            'is_running': server.is_running,
            'node_count': server.nodes.count()
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# 新增的服务器管理API
@require_http_methods(["POST"])
def test_server_connection(request):
    """测试服务器连接"""
    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'add')  # 获取操作模式
        original_id = data.get('original_id')  # 获取原始服务器ID

        # 验证URI格式
        if not data['uri'].startswith('urn:'):
            return JsonResponse({
                'success': False,
                'message': 'URI必须以"urn:"开头'
            })
        
        # 检查服务器名称是否重复
        existing_server = OpcServer.objects.filter(name=data['name'])
        if mode == 'edit':
            # 编辑模式：排除当前服务器
            existing_server = existing_server.exclude(id=original_id)
        
        if existing_server.exists():
            return JsonResponse({
                'success': False,
                'message': '服务器名称已存在'
            })

        # 检查终端点和端口组合是否已存在
        existing_endpoint = OpcServer.objects.filter(
            endpoint=data['endpoint'],
            port=data['port']
        )
        if mode == 'edit':
            # 编辑模式：排除当前服务器
            existing_endpoint = existing_endpoint.exclude(id=original_id)
        
        if existing_endpoint.exists():
            return JsonResponse({
                'success': False,
                'message': f'终端点 {data["endpoint"]}:{data["port"]} 已被其他服务器使用'
            })

        # 测试端口是否可用（仅在端口和终端点组合不存在时测试）
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((data['endpoint'], int(data['port'])))
        sock.close()
        
        if result == 0:
            return JsonResponse({
                'success': False,
                'message': f'端口 {data["port"]} 已被占用，请使用其他端口'
            })
        
        success_message = '连接测试成功，可以创建服务器' if mode == 'add' else '接测试成功，可以更新服务器配置'
        return JsonResponse({
            'success': True,
            'message': success_message
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'连接测试失败: {str(e)}'
        })

@require_http_methods(["POST"])
def import_servers(request):
    """导入服务器配置"""
    try:
        data = json.loads(request.body)
        servers = data['servers']
        options = data['options']
        
        with transaction.atomic():
            for server_data in servers:
                if options.get('overwrite') and OpcServer.objects.filter(name=server_data['name']).exists():
                    # 如果选择覆盖，则更新现有服务器
                    server = OpcServer.objects.get(name=server_data['name'])
                    for key, value in server_data.items():
                        if key not in ['id', 'created_at', 'updated_at', 'is_running']:
                            setattr(server, key, value)
                    server.save()
                else:
                    # 创建新服务器
                    server_data.pop('id', None)
                    server_data.pop('created_at', None)
                    server_data.pop('updated_at', None)
                    server_data.pop('is_running', None)
                    OpcServer.objects.create(**server_data)
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def export_servers(request):
    """导出服务器配置"""
    try:
        servers = OpcServer.objects.all()
        config = []
        for server in servers:
            server_data = {
                'id': server.id,
                'name': server.name,
                'endpoint': server.endpoint,
                'port': server.port,
                'uri': server.uri,
                'allow_anonymous': server.allow_anonymous,
                'username': server.username,
                'password': server.password,
                'min_sampling_interval': server.min_sampling_interval,
                'created_at': server.created_at.isoformat(),
                'updated_at': server.updated_at.isoformat()
            }
            config.append(server_data)
        
        return JsonResponse({
            'success': True,
            'config': config
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def batch_start_servers(request):
    """批量启动服务器"""
    try:
        data = json.loads(request.body)
        server_ids = data.get('server_ids', [])
        
        success_count = 0
        errors = []
        
        for server_id in server_ids:
            try:
                server = OpcServer.objects.get(id=server_id)
                if not server.is_running:
                    opcua_server = OpcUaServer(server)
                    asyncio.run(opcua_server.start())
                    server.is_running = True
                    server.save()
                    success_count += 1
            except Exception as e:
                errors.append(f'服务器 {server_id} 启动失败: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'成功启动 {success_count} 个服务器',
            'errors': errors
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def batch_stop_servers(request):
    """批量停止服务器"""
    try:
        data = json.loads(request.body)
        server_ids = data.get('server_ids', [])
        
        success_count = 0
        errors = []
        
        for server_id in server_ids:
            try:
                server = OpcServer.objects.get(id=server_id)
                if server.is_running:
                    opcua_server = OpcUaServer(server)
                    asyncio.run(opcua_server.stop())
                    server.is_running = False
                    server.save()
                    success_count += 1
            except Exception as e:
                errors.append(f'服务器 {server_id} 停止失败: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'成功停止 {success_count} 个服务器',
            'errors': errors
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def batch_delete_servers(request):
    """批量删除服务器"""
    try:
        data = json.loads(request.body)
        server_ids = data.get('server_ids', [])
        
        success_count = 0
        errors = []
        
        with transaction.atomic():
            for server_id in server_ids:
                try:
                    server = OpcServer.objects.get(id=server_id)
                    if not server.is_running:
                        server.delete()
                        success_count += 1
                    else:
                        errors.append(f'服务器 {server.name} 正��运行，无法删除')
                except Exception as e:
                    errors.append(f'服务器 {server_id} 删除失败: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {success_count} 个服务器',
            'errors': errors
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
def node_list(request):
    """获取节点列表"""
    if request.method == 'GET':
        server_id = request.GET.get('server_id')
        try:
            if server_id:
                server = OpcServer.objects.get(id=server_id)
                nodes = server.nodes.all()
            else:
                nodes = Node.objects.all()
            
            return JsonResponse({
                'success': True,
                'nodes': [{
                    'id': node.id,
                    'name': node.name,
                    'node_id': node.node_id,
                    'node_type': node.node_type,
                    'data_type': node.data_type,
                    'value': node.value,
                    'description': node.description,
                    'variation_type': node.variation_type,
                    'server_id': node.server_id,
                    'server_name': node.server.name
                } for node in nodes]
            })
        except Exception as e:
            logger.error(f"Error getting node list: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})

@csrf_exempt
def add_node(request):
    """添加新节点"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            server = OpcServer.objects.get(id=data['server_id'])
            
            node = Node.objects.create(
                server=server,
                name=data['name'],
                node_id=data['node_id'],
                node_type=data['node_type'],
                data_type=data['data_type'],
                value=data.get('value'),
                description=data.get('description'),
                variation_type=data.get('variation_type', 'none'),
                variation_interval=data.get('variation_interval', 1000),
                variation_min=data.get('variation_min'),
                variation_max=data.get('variation_max'),
                variation_step=data.get('variation_step'),
                variation_values=data.get('variation_values'),
                decimal_places=data.get('decimal_places', 2)
            )
            
            # 如果服务器正在运行，添加点到服务器实例
            if server.is_running:
                server_instance = OpcUaServer.get_instance(server.id)
                if server_instance:
                    server_instance.add_node(node)
            
            return JsonResponse({
                'success': True,
                'node': {
                    'id': node.id,
                    'name': node.name,
                    'node_id': node.node_id
                }
            })
        except OpcServer.DoesNotExist:
            return JsonResponse({'success': False, 'error': '服务器不存在'})
        except Exception as e:
            logger.error(f"Error adding node: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})

@csrf_exempt
def edit_node(request, node_id):
    """编辑节点"""
    if request.method == 'POST':
        try:
            node = Node.objects.get(id=node_id)
            data = json.loads(request.body)
            
            # 更新节点配置
            for field in ['name', 'node_id', 'node_type', 'data_type', 'value', 
                         'description', 'variation_type', 'variation_interval',
                         'variation_min', 'variation_max', 'variation_step',
                         'variation_values', 'decimal_places']:
                if field in data:
                    setattr(node, field, data[field])
            
            node.save()
            
            # 如果服务器正在运行，更新节点
            if node.server.is_running:
                server_instance = OpcUaServer.get_instance(node.server.id)
                if server_instance:
                    server_instance.remove_node(node.id)
                    server_instance.add_node(node)
            
            return JsonResponse({'success': True})
        except Node.DoesNotExist:
            return JsonResponse({'success': False, 'error': '节点不存在'})
        except Exception as e:
            logger.error(f"Error editing node: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})

@csrf_exempt
def delete_node(request, node_id):
    """删除节点"""
    if request.method == 'POST':
        try:
            node = Node.objects.get(id=node_id)
            
            # 如果服务器正在运行，先从服务器实例中移除节点
            if node.server.is_running:
                server_instance = OpcUaServer.get_instance(node.server.id)
                if server_instance:
                    server_instance.remove_node(node.id)
            
            node.delete()
            return JsonResponse({'success': True})
        except Node.DoesNotExist:
            return JsonResponse({'success': False, 'error': '节点不存在'})
        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': '不支持的请求方法'})
