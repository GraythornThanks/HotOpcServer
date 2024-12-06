from django.urls import path
from . import views

urlpatterns = [
    # 节点列表页面（首页）
    path('', views.NodeListView.as_view(), name='node-list'),
    
    # 节点管理API
    path('node/list/', views.node_list, name='node-list-api'),
    path('node/add/', views.add_node, name='node-add'),
    path('node/<int:node_id>/edit/', views.edit_node, name='node-edit'),
    path('node/<int:node_id>/delete/', views.delete_node, name='node-delete'),
    
    # 服务器管理API
    path('server/list/', views.server_list, name='server-list'),
    path('server/add/', views.add_server, name='server-add'),
    path('server/<int:server_id>/edit/', views.edit_server, name='server-edit'),
    path('server/<int:server_id>/delete/', views.delete_server, name='server-delete'),
    path('server/<int:server_id>/start/', views.start_server, name='server-start'),
    path('server/<int:server_id>/stop/', views.stop_server, name='server-stop'),
    path('server/<int:server_id>/status/', views.server_status, name='server-status'),
    
    # 新增的服务器管理API
    path('server/test-connection/', views.test_server_connection, name='server-test-connection'),
    path('server/import/', views.import_servers, name='server-import'),
    path('server/export/', views.export_servers, name='server-export'),
    path('server/batch-start/', views.batch_start_servers, name='server-batch-start'),
    path('server/batch-stop/', views.batch_stop_servers, name='server-batch-stop'),
    path('server/batch-delete/', views.batch_delete_servers, name='server-batch-delete'),
]
