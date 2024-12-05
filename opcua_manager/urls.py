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
    
    # 服务器控制
    path('server/start/', views.start_server, name='server-start'),
    path('server/stop/', views.stop_server, name='server-stop'),
]
