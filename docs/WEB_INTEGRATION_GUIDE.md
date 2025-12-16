# Agent API 网页接入指南

本文档介绍如何将无人机 Agent 对话功能嵌入到自己的网页中。

---

## 目录

1. [API 概述](#1-api-概述)
2. [REST API 接入](#2-rest-api-接入)
3. [WebSocket 接入（推荐）](#3-websocket-接入推荐)
4. [完整示例代码](#4-完整示例代码)
5. [常见问题](#5-常见问题)

---

## 1. API 概述

Agent 服务提供两种接入方式：

| 方式 | 地址 | 特点 |
|------|------|------|
| REST API | `POST /api/agent/chat` | 简单易用，请求-响应模式 |
| WebSocket | `ws://.../api/agent/ws/chat/{session_id}` | 实时通信，支持状态推送 |

**服务地址**：`http://8.136.43.216:8000`（需确保 8000 端口已开放）

---

## 2. REST API 接入

### 2.1 发送消息

**请求**
```http
POST /api/agent/chat
Content-Type: application/json

{
    "message": "飞到坐标3,9,2",
    "session_id": "user-123"
}
```

**响应**
```json
{
    "response": "好的，正在控制无人机飞往坐标(3, 9, 2)...",
    "session_id": "user-123",
    "tool_calls": [
        {
            "tool": "drone_go_to",
            "args": {"x": 3, "y": 9, "z": 2},
            "result": "成功"
        }
    ]
}
```

### 2.2 清空会话

```http
DELETE /api/agent/conversations/{session_id}
```

### 2.3 健康检查

```http
GET /api/agent/health
```

### 2.4 JavaScript 示例

```javascript
const AGENT_URL = 'http://8.136.43.216:8000/api/agent/chat';

// 生成唯一会话ID
const sessionId = 'web-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);

async function sendMessage(message) {
    const response = await fetch(AGENT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: message,
            session_id: sessionId
        })
    });

    const data = await response.json();
    return data.response;
}

// 使用示例
sendMessage('起飞到1.5米高度').then(reply => {
    console.log('Agent:', reply);
});
```

---

## 3. WebSocket 接入（推荐）

WebSocket 方式支持实时状态推送，用户体验更好。

### 3.1 连接地址

```
ws://8.136.43.216:8000/api/agent/ws/chat/{session_id}
```

`{session_id}` 是会话标识，用于区分不同用户。建议格式：`user-{唯一ID}`

### 3.2 消息格式

**发送消息**
```json
{
    "message": "飞到3,9,2"
}
```

**接收消息类型**

| type | 说明 | 示例 |
|------|------|------|
| `connected` | 连接成功 | `{"type": "connected", "session_id": "user-123"}` |
| `status` | 处理状态 | `{"type": "status", "message": "正在调用工具..."}` |
| `response` | 最终回复 | `{"type": "response", "message": "已完成飞行"}` |
| `error` | 错误信息 | `{"type": "error", "message": "无法连接无人机"}` |

### 3.3 JavaScript 示例

```javascript
class DroneAgentClient {
    constructor(serverUrl = 'ws://8.136.43.216:8000') {
        this.serverUrl = serverUrl;
        this.ws = null;
        this.sessionId = 'web-' + Date.now();
        this.onMessage = null;  // 回调函数
        this.onStatus = null;
        this.onError = null;
    }

    // 连接服务器
    connect() {
        return new Promise((resolve, reject) => {
            const url = `${this.serverUrl}/api/agent/ws/chat/${this.sessionId}`;
            this.ws = new WebSocket(url);

            this.ws.onopen = () => {
                console.log('已连接到 Agent');
                resolve();
            };

            this.ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                if (this.onError) this.onError(error);
                reject(error);
            };

            this.ws.onclose = () => {
                console.log('连接已断开');
            };
        });
    }

    // 处理接收到的消息
    handleMessage(data) {
        switch (data.type) {
            case 'connected':
                console.log('会话ID:', data.session_id);
                break;
            case 'status':
                console.log('状态:', data.message);
                if (this.onStatus) this.onStatus(data.message);
                break;
            case 'response':
                console.log('回复:', data.message);
                if (this.onMessage) this.onMessage(data.message);
                break;
            case 'error':
                console.error('错误:', data.message);
                if (this.onError) this.onError(data.message);
                break;
        }
    }

    // 发送消息
    send(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ message }));
        } else {
            console.error('WebSocket 未连接');
        }
    }

    // 断开连接
    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// 使用示例
const agent = new DroneAgentClient();

agent.onMessage = (msg) => {
    document.getElementById('response').innerText = msg;
};

agent.onStatus = (status) => {
    document.getElementById('status').innerText = status;
};

agent.connect().then(() => {
    agent.send('起飞到1.5米');
});
```

---

## 4. 完整示例代码

### 4.1 简单对话框 (HTML + JavaScript)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>无人机 Agent 控制台</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .chat-container {
            width: 100%;
            max-width: 500px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .chat-header {
            background: #1a73e8;
            color: white;
            padding: 16px 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .chat-header h1 {
            font-size: 18px;
            font-weight: 500;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4caf50;
        }
        .status-dot.disconnected {
            background: #f44336;
        }
        .chat-messages {
            height: 400px;
            overflow-y: auto;
            padding: 20px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .message {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.4;
        }
        .message.user {
            background: #e3f2fd;
            align-self: flex-end;
            border-bottom-right-radius: 4px;
        }
        .message.agent {
            background: #f5f5f5;
            align-self: flex-start;
            border-bottom-left-radius: 4px;
        }
        .message.status {
            background: #fff3e0;
            align-self: center;
            font-size: 14px;
            color: #666;
        }
        .message.error {
            background: #ffebee;
            color: #c62828;
        }
        .chat-input {
            display: flex;
            padding: 16px;
            border-top: 1px solid #eee;
            gap: 10px;
        }
        .chat-input input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #ddd;
            border-radius: 24px;
            font-size: 16px;
            outline: none;
        }
        .chat-input input:focus {
            border-color: #1a73e8;
        }
        .chat-input button {
            padding: 12px 24px;
            background: #1a73e8;
            color: white;
            border: none;
            border-radius: 24px;
            font-size: 16px;
            cursor: pointer;
        }
        .chat-input button:hover {
            background: #1557b0;
        }
        .chat-input button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div class="status-dot" id="statusDot"></div>
            <h1>无人机 Agent</h1>
        </div>
        <div class="chat-messages" id="messages">
            <div class="message agent">你好！我是无人机控制 Agent，你可以用自然语言告诉我你想让无人机做什么。</div>
        </div>
        <div class="chat-input">
            <input type="text" id="input" placeholder="输入指令，如：飞到坐标3,9,2" />
            <button id="sendBtn" onclick="sendMessage()">发送</button>
        </div>
    </div>

    <script>
        // 配置
        const SERVER_URL = 'ws://8.136.43.216:8000';
        const SESSION_ID = 'web-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6);

        let ws = null;
        const messagesDiv = document.getElementById('messages');
        const input = document.getElementById('input');
        const sendBtn = document.getElementById('sendBtn');
        const statusDot = document.getElementById('statusDot');

        // 添加消息到聊天窗口
        function addMessage(text, type = 'agent') {
            const div = document.createElement('div');
            div.className = `message ${type}`;
            div.textContent = text;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // 连接 WebSocket
        function connect() {
            ws = new WebSocket(`${SERVER_URL}/api/agent/ws/chat/${SESSION_ID}`);

            ws.onopen = () => {
                statusDot.classList.remove('disconnected');
                console.log('已连接');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                switch (data.type) {
                    case 'connected':
                        addMessage('已连接到 Agent 服务', 'status');
                        break;
                    case 'status':
                        // 显示处理状态
                        addMessage(data.message, 'status');
                        break;
                    case 'response':
                        addMessage(data.message, 'agent');
                        sendBtn.disabled = false;
                        break;
                    case 'error':
                        addMessage(data.message, 'error');
                        sendBtn.disabled = false;
                        break;
                }
            };

            ws.onerror = (error) => {
                console.error('连接错误:', error);
                statusDot.classList.add('disconnected');
            };

            ws.onclose = () => {
                statusDot.classList.add('disconnected');
                addMessage('连接已断开，5秒后重连...', 'status');
                setTimeout(connect, 5000);
            };
        }

        // 发送消息
        function sendMessage() {
            const text = input.value.trim();
            if (!text) return;

            if (ws && ws.readyState === WebSocket.OPEN) {
                addMessage(text, 'user');
                ws.send(JSON.stringify({ message: text }));
                input.value = '';
                sendBtn.disabled = true;
            } else {
                addMessage('未连接到服务器', 'error');
            }
        }

        // 回车发送
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        // 启动连接
        connect();
    </script>
</body>
</html>
```

### 4.2 嵌入现有页面

如果要将 Agent 对话框嵌入到现有网页，可以使用 iframe 或直接嵌入组件。

**方法一：iframe 嵌入**
```html
<iframe src="agent-chat.html" width="400" height="600" frameborder="0"></iframe>
```

**方法二：作为浮动按钮**
```html
<style>
    .agent-float-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        border-radius: 50%;
        background: #1a73e8;
        color: white;
        border: none;
        cursor: pointer;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        font-size: 24px;
    }
    .agent-panel {
        position: fixed;
        bottom: 90px;
        right: 20px;
        width: 380px;
        height: 500px;
        display: none;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 5px 20px rgba(0,0,0,0.2);
    }
    .agent-panel.show {
        display: block;
    }
</style>

<button class="agent-float-btn" onclick="togglePanel()">💬</button>
<div class="agent-panel" id="agentPanel">
    <iframe src="agent-chat.html" width="100%" height="100%" frameborder="0"></iframe>
</div>

<script>
    function togglePanel() {
        document.getElementById('agentPanel').classList.toggle('show');
    }
</script>
```

---

## 5. 常见问题

### Q1: 无法连接到服务器？

1. 检查服务器是否运行：
   ```bash
   curl http://8.136.43.216:8000/api/agent/health
   ```

2. 检查阿里云安全组是否开放 8000 端口

3. 检查浏览器控制台是否有 CORS 错误

### Q2: WebSocket 连接被拒绝？

确保使用正确的协议：
- HTTP 服务用 `ws://`
- HTTPS 服务用 `wss://`

### Q3: 如何处理跨域问题？

Agent 服务已配置允许所有来源 (`allowed_origins: ["*"]`)，正常情况下不会有 CORS 问题。

如果仍有问题，可以：
1. 使用 Nginx 反向代理
2. 将前端部署在同一域名下

### Q4: 会话如何管理？

- 每个 `session_id` 代表一个独立的对话上下文
- 服务会保留最近 10 条对话历史
- 服务重启后会话清空（`memory_retention_days: 0`）
- 可调用 `DELETE /api/agent/conversations/{session_id}` 手动清空

### Q5: Agent 支持哪些指令？

自然语言指令示例：
- "起飞" / "起飞到1.5米"
- "降落"
- "飞到坐标3,9,2"
- "向前飞2米"
- "执行航点任务：(1,2,1) -> (3,4,1.5) -> (5,6,2)"
- "获取无人机状态"
- "悬停"

---

## 6. API 参考

### 6.1 REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/agent/chat` | 发送消息 |
| DELETE | `/api/agent/conversations/{session_id}` | 清空会话 |
| GET | `/api/agent/health` | 健康检查 |

### 6.2 WebSocket 事件

| 事件类型 | 方向 | 说明 |
|----------|------|------|
| `connected` | 服务端→客户端 | 连接成功 |
| `status` | 服务端→客户端 | 处理状态更新 |
| `response` | 服务端→客户端 | 最终回复 |
| `error` | 服务端→客户端 | 错误信息 |
| `message` | 客户端→服务端 | 用户消息 |

---

*最后更新：2025-12-16*
