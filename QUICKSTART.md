# 🚀 快速启动指南

## 前置要求

- Python 3.10+
- OpenAI API密钥（或其他LLM提供商）
- （可选）Docker 和 Docker Compose

## 方式1: 本地开发启动（推荐开始）

### Step 1: 安装依赖

```bash
cd agent-core

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### Step 2: 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env  # Linux/Mac
# copy .env.example .env  # Windows

# 编辑.env文件
```

**推荐：使用Claude（我）作为LLM！** 🤖

编辑 `.env` 文件，配置以下内容：

```bash
# 使用Claude（推荐）
LLM_PROVIDER=claude
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key-here
BACKEND_URL=http://localhost:3001

# 或使用OpenAI
# LLM_PROVIDER=openai
# LLM_MODEL=gpt-4-turbo-preview
# OPENAI_API_KEY=sk-your-key-here
```

**如何获取Claude API密钥？**
1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 注册并创建API密钥
3. 复制密钥（格式: `sk-ant-...`）到 `.env` 文件

详细的Claude配置指南，请查看：[CLAUDE_SETUP.md](CLAUDE_SETUP.md)

### Step 3: 启动服务

```bash
# 开发模式（支持热重载）
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或者直接运行
python app/main.py
```

### Step 4: 验证服务

打开浏览器访问：
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/agent/health
- 服务信息: http://localhost:8000/api/agent/info

## 方式2: Docker启动（推荐生产）

### Step 1: 准备环境变量

在项目根目录创建 `.env` 文件：
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Step 2: 启动所有服务

```bash
cd drone-web-control

# 启动所有服务（Agent + 无人机后端 + 前端）
docker-compose up -d

# 查看日志
docker-compose logs -f agent-core

# 停止服务
docker-compose down
```

### 单独启动Agent服务

```bash
cd agent-core

# 构建镜像
docker build -t agent-core:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key \
  -e BACKEND_URL=http://localhost:3001 \
  --name agent-core \
  agent-core:latest

# 查看日志
docker logs -f agent-core
```

## 测试Agent服务

### 1. 使用curl测试

```bash
# 健康检查
curl http://localhost:8000/api/agent/health

# 发送聊天消息
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "你好"}'

# 查询工具列表
curl http://localhost:8000/api/agent/tools
```

### 2. 使用CLI工具测试

```bash
cd agent-cli

# 交互模式
python cli.py interactive

# 单次对话
python cli.py chat "让无人机起飞到2米"

# 查看状态
python cli.py status
```

### 3. 使用Python SDK测试

```python
import requests

response = requests.post(
    'http://localhost:8000/api/agent/chat',
    json={'message': '查询无人机状态'}
)

print(response.json()['response'])
```

### 4. 使用浏览器测试

访问 http://localhost:8000/docs 使用Swagger UI进行交互测试。

## 集成到你的Web前端

### React示例（在你现有的client项目中）

```javascript
// 1. 安装uuid（如果还没有）
// npm install uuid

// 2. 创建Agent服务封装
// client/src/services/agent.js
import { v4 as uuidv4 } from 'uuid';

class AgentService {
  constructor() {
    this.baseURL = process.env.REACT_APP_AGENT_API || 'http://localhost:8000';
    this.sessionId = uuidv4();
  }

  async chat(message) {
    const response = await fetch(`${this.baseURL}/api/agent/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        session_id: this.sessionId
      })
    });
    return response.json();
  }

  connectWebSocket(onMessage) {
    const ws = new WebSocket(
      `ws://${this.baseURL.replace('http://', '')}/api/agent/ws/chat/${this.sessionId}`
    );

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
    };

    return ws;
  }
}

export default new AgentService();

// 3. 在组件中使用
// client/src/components/AgentChat.js
import React, { useState, useEffect } from 'react';
import agentService from '../services/agent';

function AgentChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [ws, setWs] = useState(null);

  useEffect(() => {
    const websocket = agentService.connectWebSocket((data) => {
      if (data.type === 'response') {
        setMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
      }
    });

    setWs(websocket);
    return () => websocket.close();
  }, []);

  const handleSend = () => {
    if (!input.trim() || !ws) return;

    setMessages(prev => [...prev, { role: 'user', content: input }]);
    ws.send(input);
    setInput('');
  };

  return (
    <div>
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role}>
            {msg.content}
          </div>
        ))}
      </div>
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={handleSend}>发送</button>
    </div>
  );
}

export default AgentChat;
```

## 常见问题

### Q: 提示"OPENAI_API_KEY not configured"

**A:** 需要在 `.env` 文件中配置你的OpenAI API密钥：
```
OPENAI_API_KEY=sk-your-key-here
```

### Q: 提示"连接无人机后端超时"

**A:** 检查以下几点：
1. 无人机后端服务是否已启动（默认端口3001）
2. `.env` 中的 `BACKEND_URL` 是否正确配置
3. 网络连接是否正常

### Q: 想使用Claude或本地模型怎么办？

**A:** 修改 `.env` 配置：

使用Claude:
```
LLM_PROVIDER=claude
LLM_MODEL=claude-3-sonnet-20240229
ANTHROPIC_API_KEY=your_anthropic_key
```

使用本地Ollama:
```
LLM_PROVIDER=ollama
LLM_MODEL=llama2
# 需要先安装并启动Ollama服务
```

### Q: 如何添加自定义工具？

**A:** 参考 [app/plugins/drone_tools.py](app/plugins/drone_tools.py)，创建新的工具类：

```python
from app.plugins.base_tool import BaseAgentTool, ToolParameter

class MyCustomTool(BaseAgentTool):
    name = "my_tool"
    description = "我的自定义工具"
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
        # 实现你的逻辑
        return {
            "success": True,
            "message": f"执行成功: {param1}"
        }
```

然后在 [app/main.py](app/main.py) 中注册：
```python
from app.plugins.my_tools import MyCustomTool

# 在lifespan函数中
agent = IntelligentAgent(
    tools=[
        # ... 其他工具
        MyCustomTool()
    ]
)
```

### Q: 支持多用户并发吗？

**A:** 是的！每个用户使用不同的 `session_id` 即可独立对话，互不干扰。

### Q: 如何部署到生产环境？

**A:** 推荐使用Docker Compose:

1. 配置生产环境变量
2. 使用反向代理（Nginx）配置HTTPS
3. 添加认证中间件
4. 启用日志收集和监控

```bash
# 生产模式启动
docker-compose -f docker-compose.prod.yml up -d
```

## 下一步

- 📖 阅读完整文档: [README.md](README.md)
- 🛠️ 查看工具开发指南: [app/plugins/README.md](app/plugins/)
- 💻 尝试CLI工具: [agent-cli/README.md](../agent-cli/README.md)
- 🌐 集成到你的应用

## 技术支持

遇到问题？
1. 查看日志: `docker-compose logs -f agent-core`
2. 检查API文档: http://localhost:8000/docs
3. 提交Issue或联系维护者
