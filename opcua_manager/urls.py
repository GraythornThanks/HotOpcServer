from django.urls import path
from . import views

urlpatterns = [
    # 首页重定向到服务器列表
    path('', views.ServerListView.as_view(), name='index'),
    
    # 节点总表管理
    path('nodes/', views.NodeListView.as_view(), name='node-list'),
    path('nodes/add/', views.add_node, name='node-add'),
    path('nodes/<int:node_id>/edit/', views.edit_node, name='node-edit'),
    path('nodes/<int:node_id>/delete/', views.delete_node, name='node-delete'),
    
    # 服务器管理
    path('servers/', views.ServerListView.as_view(), name='server-list'),
    path('servers/add/', views.add_server, name='server-add'),
    path('servers/<int:server_id>/', views.server_detail, name='server-detail'),
    path('servers/<int:server_id>/edit/', views.edit_server, name='server-edit'),
    path('servers/<int:server_id>/delete/', views.delete_server, name='server-delete'),
    
    # 服务器节点管理
    path('servers/<int:server_id>/nodes/', views.server_nodes, name='server-nodes'),
    path('servers/<int:server_id>/nodes/add/', views.add_server_node, name='server-node-add'),
    path('servers/<int:server_id>/nodes/<int:node_id>/edit/', views.edit_server_node, name='server-node-edit'),
    path('servers/<int:server_id>/nodes/<int:node_id>/delete/', views.delete_server_node, name='server-node-delete'),
    
    # 服务器控制
    path('servers/<int:server_id>/start/', views.start_server, name='server-start'),
    path('servers/<int:server_id>/stop/', views.stop_server, name='server-stop'),
    path('servers/<int:server_id>/restart/', views.restart_server, name='server-restart'),
    
    # API接口
    path('api/nodes/', views.node_list_api, name='api-node-list'),
    path('api/servers/', views.server_list_api, name='api-server-list'),
    path('api/servers/<int:server_id>/nodes/', views.server_nodes_api, name='api-server-nodes'),
    path('api/servers/<int:server_id>/status/', views.server_status_api, name='api-server-status'),
    path('server/config/', views.server_config_api, name='server-config'),
]
