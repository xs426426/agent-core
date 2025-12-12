# Agent Core - 通用智能体核心服务

> 完全独立、高可移植的AI Agent服务，可用于任何客户端（Web、CLI、移动端、聊天机器人等）

## 🎯 核心特性

- **完全独立**: 零前端依赖，纯后端服务
- **高可移植**: 标准HTTP/WebSocket接口，任何客户端可用
- **插件化**: 基于工具插件的扩展架构
- **多模型支持**: Claude（推荐）、OpenAI、本地模型（Ollama）
- **实时通信**: WebSocket流式响应
- **生产级**: 完整的错误处理、日志、会话管理

> 💡 **推荐使用Claude 3.5 Sonnet** - 更强的推理能力、更低的成本！查看 [CLAUDE_SETUP.md](CLAUDE_SETUP.md) 了解配置方法。

## 🏗️ 架构设计

```
Agent Core (独立服务)
    ↓ REST API / WebSocket
┌─────────┬─────────┬─────────┬─────────┐
│ Web前端  │ CLI工具  │ 移动App  │ 聊天机器人│
└─────────┴─────────┴─────────┴─────────┘
```

## 📦 项目结构

```
agent-core/
├── app/
│   ├── main.py                 # FastAPI应用入口
│   ├── config.py               # 配置管理
│   ├── core/
│   │   ├── agent.py            # Agent核心引擎
│   │   ├── llm_engine.py       # LLM适配器
│   │   ├── task_planner.py     # 任务规划器
│   │   └── tool_orchestrator.py # 工具调度器
│   ├── models/
│   │   ├── conversation.py     # 对话数据模型
│   │   ├── task.py            # 任务数据模型
│   │   └── tool.py            # 工具定义模型
│   ├── plugins/
│   │   ├── base_tool.py       # 工具基类
│   │   ├── drone_tools.py     # 无人机工具集
│   │   └── vehicle_tools.py   # 车辆工具集（示例）
│   ├── api/
│   │   ├── chat.py            # 聊天接口
│   │   ├── tools.py           # 工具管理接口
│   │   └── health.py          # 健康检查
│   └── utils/
│       ├── logger.py          # 日志工具
│       └── validators.py      # 验证器
├── tests/
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd agent-core
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，添加你的API密钥
```

### 3. 启动服务

```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

服务将运行在 `http://localhost:8000`

API文档: `http://localhost:8000/docs`

## 📡 API使用示例

### HTTP接口（任何客户端可用）

```bash
# 发送聊天消息
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "让无人机起飞到2米高度",
    "session_id": "test-session-001"
  }'
```

### WebSocket接口（实时双向通信）

```python
import websocket
import json

ws = websocket.create_connection("ws://localhost:8000/api/agent/ws/chat/session-001")
ws.send("让无人机起飞到2米")
result = json.loads(ws.recv())
print(result)
```

### Python SDK

```python
import requests

response = requests.post(
    'http://localhost:8000/api/agent/chat',
    json={
        'message': '查询无人机状态',
        'session_id': 'python-client-001'
    }
)
print(response.json()['response'])
```

## 🔧 多客户端使用场景

### 1. Web前端（React/Vue）

```javascript
// WebSocket实时通信
const ws = new WebSocket('ws://localhost:8000/api/agent/ws/chat/web-session');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.message);
};
ws.send('让无人机起飞');
```

### 2. 命令行CLI

```bash
# 使用提供的CLI工具
python agent-cli/cli.py chat "让无人机起飞到2米"
```

### 3. 移动应用（Flutter/React Native）

```dart
// Flutter WebSocket
final channel = WebSocketChannel.connect(
  Uri.parse('ws://your-server:8000/api/agent/ws/chat/mobile-session')
);
channel.sink.add('查询无人机状态');
```

### 4. 企业微信/钉钉机器人

```python
# Webhook集成
@app.route('/wecom/webhook', methods=['POST'])
def wecom_bot():
    user_msg = request.json['text']
    response = requests.post('http://agent-core:8000/api/agent/chat',
                            json={'message': user_msg})
    return response.json()['response']
```

## 🛠️ 添加自定义工具

创建新工具非常简单，继承 `BaseAgentTool` 类即可：

```python
from app.plugins.base_tool import BaseAgentTool, ToolParameter

class CustomTool(BaseAgentTool):
    name = "custom_tool"
    description = "你的工具描述"
    category = "custom"

    parameters = [
        ToolParameter(
            name="param1",
            type="string",
            description="参数描述",
            required=True
        )
    ]

    async def execute(self, param1: str) -> dict:
        # 实现你的工具逻辑
        return {
            "success": True,
            "message": f"执行成功: {param1}"
        }
```

然后在 `app/main.py` 中注册：

```python
from app.plugins.custom_tools import CustomTool

agent.register_tool(CustomTool())
```

## 🐳 Docker部署

```bash
# 构建镜像
docker build -t agent-core:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e BACKEND_URL=http://your-drone-backend:3001 \
  --name agent-core \
  agent-core:latest
```

使用 Docker Compose:

```bash
docker-compose up -d
```

## 🔑 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `LLM_PROVIDER` | LLM提供商 (openai/claude/ollama) | openai |
| `LLM_MODEL` | 模型名称 | gpt-4-turbo-preview |
| `LLM_TEMPERATURE` | 温度参数 | 0.7 |
| `OPENAI_API_KEY` | OpenAI API密钥 | - |
| `ANTHROPIC_API_KEY` | Anthropic API密钥 | - |
| `BACKEND_URL` | 无人机后端URL | http://localhost:3001 |
| `LOG_LEVEL` | 日志级别 | INFO |

## 📊 性能指标

- 平均响应时间: < 2秒（取决于LLM延迟）
- 并发支持: 100+ WebSocket连接
- 内存占用: ~200MB (基础)
- CPU使用: 低（主要等待LLM响应）

## 🔒 安全建议

1. **API密钥管理**: 使用环境变量或密钥管理服务
2. **访问控制**: 生产环境添加认证中间件
3. **HTTPS**: 生产环境启用SSL/TLS
4. **限流**: 添加rate limiting防止滥用

## 📝 开发路线图

- [x] 基础Agent引擎
- [x] 无人机工具集
- [x] HTTP + WebSocket API
- [ ] 工具执行确认机制
- [ ] 多模态输入支持（语音、图像）
- [ ] 会话持久化（数据库）
- [ ] 分布式部署支持
- [ ] 监控和可观测性

## 🤝 贡献

欢迎提交Issue和Pull Request！

## 📄 许可证

MIT License

## 📧 联系方式

如有问题，请提交Issue或联系维护者。

---

**注意**: 这是一个完全独立的服务，可以脱离任何前端独立运行和部署！
