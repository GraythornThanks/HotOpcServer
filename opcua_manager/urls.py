from django.urls import path
from . import views

urlpatterns = [
    # 节点列表页面（首页）
    path('', views.NodeListView.as_view(), name='node-list'),
    
    # 节点管理API
    path('node/add/', views.NodeCreateView.as_view(), name='node-create'),
    path('node/<int:pk>/edit/', views.NodeUpdateView.as_view(), name='node-update'),
    path('node/<int:pk>/delete/', views.NodeDeleteView.as_view(), name='node-delete'),
    
    # 服务器控制
    path('server/start/', views.start_server, name='server-start'),
    path('server/stop/', views.stop_server, name='server-stop'),
]
