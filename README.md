# AmiyaBot 群聊管理 API 插件

该插件为 AmiyaBot 提供了群聊管理的 RESTful API 接口，允许通过 HTTP 请求管理群组状态和功能。

## 功能特性

- 获取群组启用状态列表
- 设置群组启用/停用状态
- 获取群组功能启用状态列表
- 设置群组功能启用/停用状态

## API 接口

### 1. 获取群启用状态列表

**接口**: `GET /group/getGroupActiveList`

**描述**: 获取所有群组的启用状态信息

**响应示例**:
```json
[
  {
    "group_id": 123456789,
    "active": true,
    "sleep_time": 0
  },
  {
    "group_id": 987654321,
    "active": false,
    "sleep_time": 1672531200
  }
]
```

### 2. 设置群启用状态

**接口**: `POST /group/setGroupActive`

**描述**: 设置指定群组的启用状态

**请求参数**:
```json
{
  "group_id": 123456789,
  "active": true
}
```

**响应示例**:
```json
{
  "status": true
}
```

### 3. 获取群功能启用状态列表

**接口**: `GET /group/getGroupFunctionList`

**描述**: 获取指定群组中所有功能的启用状态

**请求参数**:
- `group_id` (查询参数或路由参数): 群组ID

**响应示例**:
```json
{
  "group_id": 123456789,
  "0": {
    "name": "插件名称1",
    "plugin_id": "plugin-id-1",
    "disabled": false
  },
  "1": {
    "name": "插件名称2",
    "plugin_id": "plugin-id-2",
    "disabled": true
  }
}
```

### 4. 设置群功能启用状态

**接口**: `POST /group/setFunctionActive`

**描述**: 设置指定群组中特定功能的启用状态

**请求参数**:
```json
{
  "group_id": 123456789,
  "plugin_id": "plugin-id-1",
  "disabled": false
}
```

**响应示例**:
```json
{
  "status": true
}
```

## 安装与配置

### 安装方法

1. 将插件文件夹 `amiyabot-group-api` 复制到 AmiyaBot 的 `plugins` 目录下
2. 重启 AmiyaBot 服务

### 配置说明

该插件无需额外配置，安装后即可使用。

## 使用示例

### 使用 curl 调用 API

```bash
# 获取群组状态列表
curl -X GET "http://localhost:5080/group/getGroupActiveList"

# 设置群组启用状态
curl -X POST "http://localhost:5080/group/setGroupActive" \
  -H "Content-Type: application/json" \
  -d '{"group_id": 123456789, "active": true}'

# 获取群组功能列表
curl -X GET "http://localhost:5080/group/getGroupFunctionList?group_id=123456789"

# 设置群组功能状态
curl -X POST "http://localhost:5080/group/setFunctionActive" \
  -H "Content-Type: application/json" \
  -d '{"group_id": 123456789, "plugin_id": "plugin-id-1", "disabled": false}'
```

### 使用 Python 调用 API

```python
import requests

# 基础配置
BASE_URL = "http://localhost:5080"

# 获取群组状态列表
response = requests.get(f"{BASE_URL}/group/getGroupActiveList")
groups = response.json()
print(f"群组列表: {groups}")

# 设置群组启用状态
data = {"group_id": 123456789, "active": True}
response = requests.post(f"{BASE_URL}/group/setGroupActive", json=data)
result = response.json()
print(f"设置结果: {result}")

# 获取群组功能列表
response = requests.get(f"{BASE_URL}/group/getGroupFunctionList", params={"group_id": 123456789})
functions = response.json()
print(f"功能列表: {functions}")

# 设置群组功能状态
data = {"group_id": 123456789, "plugin_id": "plugin-id-1", "disabled": False}
response = requests.post(f"{BASE_URL}/group/setFunctionActive", json=data)
result = response.json()
print(f"设置结果: {result}")
```

## 错误处理

所有接口都包含错误处理机制：

- **400 Bad Request**: 请求参数错误或缺失
- **500 Internal Server Error**: 服务器内部错误

错误响应格式:
```json
{
  "code": 400,
  "data": {},
  "message": "错误描述信息"
}
```

## 注意事项

1. 群组ID应为整数类型
2. 插件ID必须存在于 AmiyaBot 的插件列表中
3. 停用群组时会记录当前时间作为睡眠时间
4. 重新激活群组时会清除睡眠时间

## 版本信息

- **版本**: 0.0.1
- **插件ID**: `amiyabot-group-api`
- **插件名称**: API-群聊管理
- **描述**: 提供群聊管理相关的 API 接口

## 许可证

该插件遵循 AmiyaBot 的许可证协议。

## 技术支持

如有问题或建议，请参考 AmiyaBot 官方文档或联系开发者。

[github](https://github.com/2436238575/amiyabot-group-api)