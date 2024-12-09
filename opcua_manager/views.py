from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.generic import ListView
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.core.paginator import Paginator
from .models import Node, OpcServer, ServerNode
from .opcua_server import server_manager
import logging
from django.db import models
import json
from django.core.serializers import serialize

logger = logging.getLogger(__name__)

# 节点总表视图
class NodeListView(ListView):
    model = Node
    template_name = 'opcua_manager/node_list.html'
    context_object_name = 'nodes'
    paginate_by = 10
    ordering = ['name']  # 按名称排序
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # 获取所有节点的数据
            nodes_data = []
            for node in self.get_queryset():
                nodes_data.append({
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
                    'variation_values': node.variation_values,
                    'decimal_places': node.decimal_places
                })
            context['nodes_data'] = json.dumps(nodes_data)
            
        except Exception as e:
            logger.error(f"Error in NodeListView.get_context_data: {str(e)}")
            context['error'] = str(e)
        
        return context

def add_node(request):
    """添加新节点到总表"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 检查节点ID是否已存在
            if Node.objects.filter(node_id=data['node_id']).exists():
                return JsonResponse({
                    'success': False, 
                    'error': '节点ID已存在'
                })
            
            # 创建新节点
            node = Node.objects.create(
                name=data['name'],
                node_type=data['node_type'],
                node_id=data['node_id'],
                data_type=data.get('data_type'),
                value=data.get('value'),
                description=data.get('description', ''),
                variation_type=data.get('variation_type', 'none'),
                variation_interval=data.get('variation_interval', 1000),
                variation_min=data.get('variation_min'),
                variation_max=data.get('variation_max'),
                variation_step=data.get('variation_step'),
                variation_values=data.get('variation_values'),
                decimal_places=data.get('decimal_places', 2)
            )
            
            # 如果有默认服务器，自动添加到默认服务器
            default_server = OpcServer.objects.first()
            if default_server:
                ServerNode.objects.create(
                    server=default_server,
                    node=node,
                    enabled=True
                )
                
                # 如果服务器正在运行，标记需要重启
                if default_server.is_running:
                    messages.warning(
                        request, 
                        f'节点已添加到默认服务器，需要重启服务器才能生效'
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
                    'variation_values': node.variation_values,
                    'decimal_places': node.decimal_places
                }
            })
        except KeyError as e:
            return JsonResponse({
                'success': False,
                'error': f'缺少必要字段: {str(e)}'
            })
        except Exception as e:
            logger.error(f"Error creating node: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

def edit_node(request, node_id):
    """编辑总表中的节点"""
    node = get_object_or_404(Node, id=node_id)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # 检查节点ID是否已被其他节点使用
            if Node.objects.exclude(id=node_id).filter(node_id=data['node_id']).exists():
                return JsonResponse({
                    'success': False,
                    'error': '节点ID已被其他节点使用'
                })
            
            # 更新节点
            node.name = data['name']
            node.node_type = data['node_type']
            node.node_id = data['node_id']
            node.data_type = data.get('data_type')
            node.value = data.get('value')
            node.description = data.get('description', '')
            node.variation_type = data.get('variation_type', 'none')
            node.variation_interval = data.get('variation_interval', 1000)
            node.variation_min = data.get('variation_min')
            node.variation_max = data.get('variation_max')
            node.variation_step = data.get('variation_step')
            node.variation_values = data.get('variation_values')
            node.decimal_places = data.get('decimal_places', 2)
            node.save()
            
            # 检查是否需要重启使用此节点的服务器
            affected_servers = OpcServer.objects.filter(
                server_nodes__node=node,
                is_running=True
            ).distinct()
            
            if affected_servers.exists():
                messages.warning(
                    request, 
                    f'节点已更新，以下服务器需要重启才能应用更改：'
                    f'{", ".join(s.name for s in affected_servers)}'
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
                    'variation_values': node.variation_values,
                    'decimal_places': node.decimal_places
                }
            })
        except KeyError as e:
            return JsonResponse({
                'success': False,
                'error': f'缺少必要字段: {str(e)}'
            })
        except Exception as e:
            logger.error(f"Error updating node {node_id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

def delete_node(request, node_id):
    """删除总表中的节点"""
    node = get_object_or_404(Node, id=node_id)
    if request.method == 'POST':
        try:
            # 检查使用此节点的服务器
            affected_servers = OpcServer.objects.filter(
                server_nodes__node=node,
                is_running=True
            ).distinct()
            
            node_name = node.name
            node.delete()
            
            if affected_servers.exists():
                messages.warning(
                    request,
                    f'节点已删除，以下服务器需要重启才能应用更改：'
                    f'{", ".join(s.name for s in affected_servers)}'
                )
            
            return JsonResponse({
                'success': True,
                'data': {
                    'name': node_name,
                    'affected_servers': [s.name for s in affected_servers]
                }
            })
        except Exception as e:
            logger.error(f"Error deleting node {node_id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Invalid request method'
    })

# 服务器管理视图
class ServerListView(ListView):
    model = OpcServer
    template_name = 'opcua_manager/server_list.html'
    context_object_name = 'servers'
    paginate_by = 10
    ordering = ['name']  # 按名称排序

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 添加统计信息
        context['running_servers'] = self.model.objects.filter(is_running=True).count()
        context['total_nodes'] = ServerNode.objects.count()
        context['active_nodes'] = ServerNode.objects.filter(enabled=True).count()
        return context

def add_server(request):
    """添加新的OPC UA服务器"""
    if request.method == 'POST':
        try:
            server = OpcServer.objects.create(
                name=request.POST['name'],
                endpoint=request.POST['endpoint'],
                port=request.POST['port'],
                uri=request.POST['uri'],
                allow_anonymous=request.POST.get('allow_anonymous', True),
                username=request.POST.get('username', ''),
                password=request.POST.get('password', ''),
                min_publish_interval=request.POST.get('min_publish_interval', 500),
                default_namespace=request.POST.get('default_namespace', ''),
            )
            messages.success(request, f'服务器 {server.name} 创建成功')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error creating server: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def edit_server(request, server_id):
    """编辑服务器配置"""
    server = get_object_or_404(OpcServer, id=server_id)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                server.name = request.POST['name']
                server.endpoint = request.POST['endpoint']
                server.port = request.POST['port']
                server.uri = request.POST['uri']
                server.allow_anonymous = request.POST.get('allow_anonymous', True)
                server.username = request.POST.get('username', '')
                server.password = request.POST.get('password', '')
                server.min_publish_interval = request.POST.get('min_publish_interval', 500)
                server.default_namespace = request.POST.get('default_namespace', '')
                server.save()
                
                if server.is_running:
                    messages.warning(request, f'服务器配置已更新，需要重启才能应用更改')
                else:
                    messages.success(request, f'服务器 {server.name} 更新成功')
                
                return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error updating server {server_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def delete_server(request, server_id):
    """删除服务器"""
    server = get_object_or_404(OpcServer, id=server_id)
    if request.method == 'POST':
        try:
            # 如果服务器正在运行，先停止它
            if server.is_running:
                server_manager.stop_server(server_id)
            
            server_name = server.name
            server.delete()
            server_manager.remove_server(server_id)
            
            messages.success(request, f'服务器 {server_name} 已删除')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error deleting server {server_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# 服务器节点管理视图
def server_nodes(request, server_id):
    """显示服务器的节点配置"""
    server = get_object_or_404(OpcServer, id=server_id)
    nodes = ServerNode.objects.filter(server=server).select_related('node')
    
    # 分页
    paginator = Paginator(nodes, 10)
    page = request.GET.get('page')
    nodes = paginator.get_page(page)
    
    context = {
        'server': server,
        'nodes': nodes,
        'available_nodes': Node.objects.exclude(
            id__in=ServerNode.objects.filter(server=server).values_list('node_id', flat=True)
        )
    }
    return render(request, 'opcua_manager/server_nodes.html', context)

def add_server_node(request, server_id):
    """为服务器添加节点"""
    server = get_object_or_404(OpcServer, id=server_id)
    if request.method == 'POST':
        try:
            node_id = request.POST['node_id']
            node = get_object_or_404(Node, id=node_id)
            
            server_node = ServerNode.objects.create(
                server=server,
                node=node,
                enabled=request.POST.get('enabled', True),
                custom_name=request.POST.get('custom_name', ''),
                custom_node_id=request.POST.get('custom_node_id', ''),
                override_variation=request.POST.get('override_variation', False),
                custom_variation_type=request.POST.get('custom_variation_type', ''),
                custom_min_value=request.POST.get('custom_min_value'),
                custom_max_value=request.POST.get('custom_max_value'),
                custom_step=request.POST.get('custom_step'),
                custom_interval=request.POST.get('custom_interval'),
            )
            
            if server.is_running:
                messages.warning(request, f'节点已添加，需要重启服务器才能生效')
            else:
                messages.success(request, f'节点 {node.name} 已添加到服务器')
                
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error adding node to server {server_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def edit_server_node(request, server_id, node_id):
    """编辑服务器节点配置"""
    server_node = get_object_or_404(ServerNode, server_id=server_id, node_id=node_id)
    if request.method == 'POST':
        try:
            server_node.enabled = request.POST.get('enabled', True)
            server_node.custom_name = request.POST.get('custom_name', '')
            server_node.custom_node_id = request.POST.get('custom_node_id', '')
            server_node.override_variation = request.POST.get('override_variation', False)
            server_node.custom_variation_type = request.POST.get('custom_variation_type', '')
            server_node.custom_min_value = request.POST.get('custom_min_value')
            server_node.custom_max_value = request.POST.get('custom_max_value')
            server_node.custom_step = request.POST.get('custom_step')
            server_node.custom_interval = request.POST.get('custom_interval')
            server_node.save()
            
            if server_node.server.is_running:
                messages.warning(request, f'节点配置已更新，需要重启服务器才能生效')
            else:
                messages.success(request, f'节点 {server_node.node.name} 配置已更新')
                
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error updating server node {server_id}/{node_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def delete_server_node(request, server_id, node_id):
    """从服务器中删除节点"""
    server_node = get_object_or_404(ServerNode, server_id=server_id, node_id=node_id)
    if request.method == 'POST':
        try:
            node_name = server_node.node.name
            server_node.delete()
            
            if server_node.server.is_running:
                messages.warning(request, f'节点已删除，需要重启服务器才能生效')
            else:
                messages.success(request, f'节点 {node_name} 已从服务器中删除')
                
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error deleting server node {server_id}/{node_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# 服务器控制视图
def start_server(request, server_id):
    """启动服务器"""
    server = get_object_or_404(OpcServer, id=server_id)
    if request.method == 'POST':
        try:
            server_manager.start_server(server_id)
            messages.success(request, f'服务器 {server.name} 已启动')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error starting server {server_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def stop_server(request, server_id):
    """停止服务器"""
    server = get_object_or_404(OpcServer, id=server_id)
    if request.method == 'POST':
        try:
            server_manager.stop_server(server_id)
            messages.success(request, f'服务器 {server.name} 已停止')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error stopping server {server_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def restart_server(request, server_id):
    """重启服务器"""
    server = get_object_or_404(OpcServer, id=server_id)
    if request.method == 'POST':
        try:
            server_manager.restart_server(server_id)
            messages.success(request, f'服务器 {server.name} 已重启')
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error restarting server {server_id}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# API接口
def node_list_api(request):
    """获取节点列表API"""
    try:
        # 获取默认服务器状态
        default_server = OpcServer.objects.first()
        server_running = default_server.is_running if default_server else False
        
        # 获取所有节点数据
        nodes = []
        for node in Node.objects.all().order_by('name'):
            nodes.append({
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
                'variation_values': node.variation_values,
                'decimal_places': node.decimal_places
            })
        
        return JsonResponse({
            'success': True,
            'nodes': nodes,
            'server_running': server_running
        })
    except Exception as e:
        logger.error(f"Error in node_list_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

def server_list_api(request):
    """获取服务器列表API"""
    servers = OpcServer.objects.all()
    return JsonResponse({
        'servers': [{
            'id': server.id,
            'name': server.name,
            'endpoint': server.endpoint,
            'port': server.port,
            'is_running': server.is_running,
        } for server in servers]
    })

def server_nodes_api(request, server_id):
    """获取服务器节点列表API"""
    server_nodes = ServerNode.objects.filter(server_id=server_id).select_related('node')
    return JsonResponse({
        'nodes': [{
            'id': sn.id,
            'node_name': sn.get_effective_name(),
            'node_id': sn.get_effective_node_id(),
            'enabled': sn.enabled,
            'variation_settings': sn.get_effective_variation_settings(),
        } for sn in server_nodes]
    })

def server_status_api(request, server_id):
    """获取服务器状态API"""
    server = get_object_or_404(OpcServer, id=server_id)
    return JsonResponse({
        'is_running': server.is_running,
        'last_start_time': server.last_start_time.isoformat() if server.last_start_time else None,
        'node_count': server.server_nodes.count(),
        'enabled_node_count': server.server_nodes.filter(enabled=True).count(),
    })

def server_detail(request, server_id):
    """服务器详情页面"""
    server = get_object_or_404(OpcServer, id=server_id)
    
    # 获取服务器的节点统计信息
    nodes_stats = {
        'total': server.server_nodes.count(),
        'enabled': server.server_nodes.filter(enabled=True).count(),
        'disabled': server.server_nodes.filter(enabled=False).count(),
        'with_variation': server.server_nodes.filter(
            models.Q(override_variation=True, custom_variation_type__in=['random', 'linear', 'sine', 'step']) |
            models.Q(override_variation=False, node__variation_type__in=['random', 'linear', 'sine', 'step'])
        ).count()
    }
    
    # 获取最近的节点变更记录
    recent_changes = ServerNode.objects.filter(server=server).order_by('-updated_at')[:5]
    
    context = {
        'server': server,
        'nodes_stats': nodes_stats,
        'recent_changes': recent_changes,
        'server_nodes': server.server_nodes.select_related('node').all(),
    }
    
    return render(request, 'opcua_manager/server_detail.html', context)

def server_config_api(request):
    """服务器配置API"""
    try:
        default_server = OpcServer.objects.first()
        if not default_server:
            return JsonResponse({
                'success': False,
                'error': '未找到默认服务器'
            })
        
        if request.method == 'GET':
            # 返回当前配置
            return JsonResponse({
                'success': True,
                'config': {
                    'name': default_server.name,
                    'endpoint': default_server.endpoint,
                    'port': default_server.port,
                    'uri': default_server.uri,
                    'allow_anonymous': default_server.allow_anonymous,
                    'username': default_server.username,
                    'password': default_server.password,
                    'min_publish_interval': default_server.min_publish_interval,
                    'default_namespace': default_server.default_namespace
                }
            })
        elif request.method == 'POST':
            # 更新配置
            data = json.loads(request.body)
            
            default_server.name = data['name']
            default_server.endpoint = data['endpoint']
            default_server.port = data['port']
            default_server.uri = data['uri']
            default_server.allow_anonymous = data.get('allow_anonymous', True)
            default_server.username = data.get('username', '')
            default_server.password = data.get('password', '')
            default_server.min_publish_interval = data.get('min_publish_interval', 500)
            default_server.default_namespace = data.get('default_namespace', 1)
            default_server.save()
            
            return JsonResponse({
                'success': True,
                'message': '配置已更新'
            })
        
        return JsonResponse({
            'success': False,
            'error': 'Invalid request method'
        })
        
    except Exception as e:
        logger.error(f"Error in server_config_api: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })
