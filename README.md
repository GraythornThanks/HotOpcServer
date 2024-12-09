# HotOpcServer - OPC UA服务器管理系统

一个基于Django和Vue.js的Web应用，用于管理和监控OPC UA服务器。支持节点管理、自动变化、批量操作等功能。

## 功能特性

### 服务器管理
- 服务器配置管理（名称、端口、URI等）
- 安全设置（匿名访问、用户认证）
- 运行状态监控
- 一键启动/停止/重启

### 节点管理
- 支持变量、对象和方法节点类型
- 丰富的数据类型支持（Double、Float、Int32等）
- 节点值实时更新
- 节点描述和元数据管理

### 自动变化功能
- 多种变化类型：
  - 随机变化
  - 线性变化
  - 循环变化
  - 离散变化
- 可配置变化参数：
  - 变化范围
  - 变化步长
  - 变化间隔
  - 小数位数
  - 循环模式

### 批量操作
- 模板化批量创建节点
- 序号自动递增
- 预览功能
- 重复检查
- 格式验证

### 其他特性
- 响应式Web界面
- 实时数据更新
- 错误处理和提示
- 操作确认机制
- 安全性验证

## 安装说明

### 系统要求
- Python 3.8+
- Django 5.0+
- Node.js 14+（用于前端开发）
- 支持的操作系统：Windows、Linux、macOS

### 安装步骤

1. 克隆仓库
```bash
git clone [repository-url]
cd HotOpcServer
```

2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 初始化数据库
```bash
python manage.py migrate
```

5. 创建超级用户（可选）
```bash
python manage.py createsuperuser
```

6. 启动服务器
```bash
python manage.py runserver
```

## 使用说明

### 服务器配置
1. 点击"服务器配置"按钮
2. 设置基本参数：
   - 服务器名称
   - 端口号（1024-65535）
   - URI（urn:格式）
   - 主机地址
3. 配置安全选项：
   - 是否允许匿名访问
   - 设置用户名密码
4. 调整高级选项：
   - 最小发布间隔
   - 默认命名空间
5. 保存配置并重启服务器

### 节点管理
1. 单个节点创建：
   - 点击"添加节点"
   - 填写节点信息
   - 设置变化参数（可选）
   - 保存节点

2. 批量节点创建：
   - 点击"批量添加"
   - 设置节点模板
   - 指定序号范围
   - 预览并创建

3. 节点编辑：
   - 点击节点的"编辑"按钮
   - 修改相关参数
   - 保存更改

4. 节点删除：
   - 点击节点的"删除"按钮
   - 确认删除操作

### 自动变化配置
1. 选择变化类型：
   - 随机变化
   - 线性变化
   - 循环变化
   - 离散变化

2. 设置变化参数：
   - 最小值和最大值
   - 变化步长
   - 变化间隔
   - 小数位数（浮点类型）

3. 特殊变化类型：
   - 离散变化：设置值集合
   - 循环变化：设置循环方向

### 快速规则
提供多种预设规则模板：
- 温度模拟
- 压力模拟
- 流量模拟
- 电流模拟
- 电压模拟
- 功率模拟
- 偏差模拟
- 湿度模拟
- 报警状态
- 开关状态
- 计数器
- 正弦波

## 注意事项

1. 节点ID格式：
   - 必须符合OPC UA规范
   - 支持的格式：
     - 字符串标识符：ns=1;s=mynode
     - 数字标识符：ns=1;i=1000
   - 批量创建时必须包含{n}占位符

2. 数据类型限制：
   - 确保值在数据类型允许的范围内
   - 特殊类型（如DateTime）需要符合格式要求

3. 性能考虑：
   - 变化间隔不要设置过小（建议≥100ms）
   - 批量创建时注意节点数量
   - 合理设置发布间隔

4. 安全性：
   - 建议在生产环境中禁用匿名访问
   - 使用强密码
   - 注意网络访问控制

## 技术支持

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件至[support-email]
- 访问项目Wiki

## 许可证

本项目采用[许可证类型]许可证。详见LICENSE文件。

# HotOpcServer

这是一个基于Django和OPC UA的服务器项目，用于管理和监控OPC UA设备。

## 项目结构

```
HotOpcServer/
├── manage.py                # Django项目的管理脚本，用于运行各种Django命令
├── requirements.txt         # 项目依赖包列表
├── db.sqlite3              # SQLite数据库文件
├── debug.log               # 调试日志文件
│
├── HotOpcServer/          # 项目配置目录
│   ├── __init__.py
│   ├── settings.py        # Django项目的主要配置文件
│   ├── urls.py            # 项目级URL配置
│   ├── asgi.py            # ASGI应用配置（异步服务器网关接口）
│   └── wsgi.py            # WSGI应用配置（Web服务器网关接口）
│
├── opcua_manager/         # OPC UA管理应用
│   ├── __init__.py
│   ├── admin.py          # Django管理界面配置
│   ├── apps.py           # 应用配置
│   ├── models.py         # 数据模型定义
│   ├── views.py          # 视图函数和业务逻辑
│   ├── urls.py           # 应用级URL路由配置
│   ├── opcua_server.py   # OPC UA服务器核心实现
│   └── tests.py          # 测试用例
│
└── templates/            # HTML模板文件目录
```

## 主要文件说明

### 核心配置文件
- `manage.py`: Django项目的命令行工具，用于执行各种管理命令
- `requirements.txt`: 项目依赖包清单，包含所需的Python包
- `HotOpcServer/settings.py`: Django项目的主配置文件，包含数据库、中间件等配置

### OPC UA管理应用
- `opcua_manager/models.py`: 定义了项目的数据模型，包括OPC UA设备、节点等实体
- `opcua_manager/views.py`: 包含应用的视图函数，处理Web请求和业务逻辑
- `opcua_manager/opcua_server.py`: OPC UA服务器的核心实现，处理OPC UA通信和数据交换
- `opcua_manager/urls.py`: 定义应用级的URL路由规则

### Web服务器配置
- `HotOpcServer/wsgi.py`: Web服务器网关接口配置，用于生产环境部署
- `HotOpcServer/asgi.py`: 异步服务器网关接口配置，支持WebSocket等异步通信

### 其他
- `templates/`: 存放HTML模板文件，用于Web界面展示
- `db.sqlite3`: SQLite数据库文件，存储应用数据
- `debug.log`: 调试日志文件，记录运行时的日志信息