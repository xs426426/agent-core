# 真机部署配置指南

本文档记录从测试环境切换到真机环境时需要修改的配置和代码。

---

## 1. 系统提示词 - 当前版本（测试环境）

位置：`app/core/agent.py` 的 `SYSTEM_PROMPT`

当前配置：
- 使用 `drone_go_to` 处理单点飞行
- 使用 `drone_mission` 处理多航点任务
- **禁用** `drone_fly_direction`（最后一行提示）
- LLM 自己计算方向飞行的目标坐标

---

## 2. 方向飞行工具切换

### 当前状态（测试环境）
- `drone_fly_direction` 工具代码保留但提示词中禁用
- 方向飞行由 LLM 计算后使用 `drone_go_to` 或 `drone_mission`

### 真机部署时
如果后端 `get_drone_status` 能返回位置坐标，可以启用 `drone_fly_direction`：

修改系统提示词，删除这行：
```
- 不要使用 drone_fly_direction 工具（测试环境禁用）
```

并添加：
```
- "向前/后/左/右飞x米" → 先调用 get_drone_status 获取位置，再调用 drone_fly_direction
```

### 前提条件
- 后端 `get_drone_status` API 必须返回无人机当前位置坐标（x, y, z）

---

## 2. 后端 URL 配置

### 当前状态（测试环境）
```env
# .env 文件
DRONE_BACKEND_URL=http://8.136.43.216
```

### 真机部署时
修改为真机后端地址：
```env
DRONE_BACKEND_URL=http://<真机IP地址>:<端口>
```

---

## 3. Protobuf 消息格式

### 重要提示
protobuf.js 的 `verify()` 方法使用 proto 文件中的**原始字段名**（snake_case），不会自动转换为 camelCase。

### 当前配置（正确）
所有工具中的 protobuf 消息字段使用 snake_case：
- `take_off` (不是 `takeOff`)
- `auto_pilot` (不是 `autoPilot`)
- `yaw_mode` (不是 `yawMode`)

### 真机部署时
确保与后端 proto 定义一致，检查以下文件：
- `app/plugins/drone_tools.py` 中的 `mission_data` 结构

---

## 4. 工具参数说明

### drone_fly_direction 工具参数
```python
parameters = [
    direction: str,    # forward/backward/left/right/up/down
    distance: float,   # 0.5-10米
    current_x: float,  # 当前X坐标（必需）
    current_y: float,  # 当前Y坐标（必需）
    current_z: float,  # 当前Z坐标（必需）
    speed: float = 0.5 # 可选
]
```

### 坐标系约定
- 前 (forward) = X+
- 后 (backward) = X-
- 左 (left) = Y+
- 右 (right) = Y-
- 上 (up) = Z+
- 下 (down) = Z-

---

## 5. 高度限制

### 当前配置
- `drone_go_to`: z 范围 0.3-5 米
- `drone_takeoff`: altitude 范围 0.3-3 米

### 真机部署时
根据实际场地调整高度限制，修改 `app/plugins/drone_tools.py`：
```python
# DroneGoToTool.execute()
if z < 0.3:
    return ToolResult.error_result("目标高度过低，最低高度为0.3米").to_dict()
if z > 5:  # 根据实际场地调整
    return ToolResult.error_result("室内目标高度不建议超过5米").to_dict()
```

---

## 6. LLM 配置

### 当前配置
```env
LLM_PROVIDER=openai
LLM_MODEL=deepseek-chat
OPENAI_API_BASE=https://api.deepseek.com
LLM_TEMPERATURE=0.1
```

### 真机部署时
可以保持不变，或根据需要调整 temperature 值。

---

## 7. 检查清单

真机部署前请确认：

- [ ] 后端 URL 已更新为真机地址
- [ ] `get_drone_status` API 返回位置坐标
- [ ] 系统提示词已切换（如需使用 drone_fly_direction）
- [ ] 高度限制符合实际场地
- [ ] protobuf 字段名与后端一致（snake_case）
- [ ] 测试起飞、降落、前往坐标等基本功能

---

## 8. 相关文件

- `app/core/agent.py` - 系统提示词
- `app/plugins/drone_tools.py` - 无人机工具定义
- `app/plugins/base_tool.py` - 工具基类
- `app/config.py` - 配置管理
- `.env` - 环境变量

---

*最后更新：2025-12-13*
