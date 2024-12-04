# HotOpcServer

HotOpcServer 是一个基于Django和python-opcua的Web管理界面的OPC UA服务器。它提供了直观的Web界面来管理OPC UA节点，支持多种数据类型，包括数值、字符串、布尔值和数组等。

## 功能特点

- 基于Web的OPC UA节点管理界面
- 支持多种数据类型（Double, Float, Int32, Int64, UInt16, UInt32, UInt64, Boolean, String, DateTime, ByteString, Array）
- 实时节点值更新
- 服务器启动/停止控制
- 节点的增删改查操作
- 支持Int16类型的数组

## 环境要求

- Python 3.8+
- Django 4.2+
- python-opcua

## 安装步骤

1. 克隆仓库：
   ```bash
   git clone <repository-url>
   cd HotOpcServer
   ```

2. 创建虚拟环境：
   ```bash
   python -m venv .venv
   ```

3. 激活虚拟环境：
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

5. 初始化数据库：
   ```bash
   python manage.py migrate
   ```

## 启动服务器

1. 启动Django开发服务器：
   ```bash
   python manage.py runserver
   ```

2. 访问Web界面：
   - 打开浏览器访问 http://localhost:8000
   - 点击"添加节点"按钮创建新的OPC UA节点
   - 使用"启动服务器"按钮启动OPC UA服务器

## OPC UA服务器配置

- 默认端口：4840
- 默认地址：opc.tcp://0.0.0.0:4840/freeopcua/server/

## 使用说明

1. 创建节点：
   - 点击"添加节点"按钮
   - 填写节点信息（名称、类型、数据类型等）
   - 点击保存

2. 编辑节点：
   - 在节点列表中点击"编辑"按钮
   - 修改节点信息
   - 点击保存

3. 删除节点：
   - 在节点列表中点击"删除"按钮
   - 确认删除操作

4. 启动/停止服务器：
   - 使用界面上的"启动服务器"/"停止服务器"按钮

## 数据类型支持

- 数值类型：Double, Float, Int32, Int64, UInt16, UInt32, UInt64
- 布尔类型：Boolean
- 字符串：String
- 日期时间：DateTime
- 字节串：ByteString
- 数组：Int16类型的数组，例如 [1, 2, 3]

## 注意事项

- 数组类型的值必须是有效的JSON数组格式
- Int16数组的值范围：-32768 到 32767
- 服务器启动后，节点的数据类型无法修改
- 确保防火墙允许4840端口的访问 