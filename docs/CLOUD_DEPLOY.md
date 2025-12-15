# 云端部署指南

本文档提供将 Agent 服务部署到云服务器的完整步骤。

---

## 1. 服务器要求

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 1核 | 2核 |
| 内存 | 2GB | 4GB |
| 硬盘 | 20GB | 40GB |
| 系统 | Ubuntu 20.04+ / CentOS 7+ | Ubuntu 22.04 |

---

## 2. 快速部署（Docker）

### 2.1 安装 Docker

```bash
# Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2.2 克隆项目

```bash
git clone https://github.com/xs426426/agent-core.git
cd agent-core
```

### 2.3 配置环境变量

创建 `.env` 文件：

```bash
cat > .env << 'EOF'
# DeepSeek API 配置
OPENAI_API_KEY=your-deepseek-api-key
OPENAI_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-chat
LLM_TEMPERATURE=0.1

# 无人机后端地址
BACKEND_URL=http://8.136.43.216

# 日志级别
LOG_LEVEL=INFO
EOF
```

### 2.4 启动服务

```bash
# 仅启动 Agent 服务（推荐测试用）
docker-compose -f docker-compose.prod.yml up -d

# 启动 Agent + Nginx（生产环境）
docker-compose -f docker-compose.prod.yml --profile with-nginx up -d
```

### 2.5 查看状态

```bash
# 查看容器状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f agent-core

# 健康检查
curl http://localhost:8000/api/agent/health
```

---

## 3. 测试服务

```bash
# 发送测试请求
curl -X POST "http://your-server-ip:8000/api/agent/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "飞到3,9,2", "session_id": "test"}'
```

---

## 4. 开放端口

确保云服务器安全组/防火墙开放以下端口：

| 端口 | 用途 | 必需 |
|------|------|------|
| 8000 | Agent API | 是（不用Nginx时） |
| 80 | HTTP（Nginx） | 可选 |
| 443 | HTTPS（Nginx） | 可选 |

### 阿里云安全组配置

1. 登录阿里云控制台
2. 进入 ECS → 安全组
3. 添加入方向规则：端口 8000，协议 TCP，源 0.0.0.0/0

---

## 5. 常用命令

```bash
# 停止服务
docker-compose -f docker-compose.prod.yml down

# 重启服务
docker-compose -f docker-compose.prod.yml restart

# 更新代码并重新部署
git pull
docker-compose -f docker-compose.prod.yml up -d --build

# 查看资源占用
docker stats

# 清理无用镜像
docker system prune -f
```

---

## 6. 前端嵌入示例

### 6.1 JavaScript (REST API)

```javascript
const AGENT_URL = 'http://your-server-ip:8000/api/agent/chat';

async function sendCommand(message) {
    const response = await fetch(AGENT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            message: message,
            session_id: 'web-user-' + Date.now()
        })
    });
    const data = await response.json();
    return data.response;
}

// 使用示例
sendCommand('飞到3,9,2').then(reply => {
    console.log('Agent:', reply);
});
```

### 6.2 WebSocket（实时通信）

```javascript
const ws = new WebSocket('ws://your-server-ip:8000/api/agent/ws/chat/user-123');

ws.onopen = () => {
    console.log('已连接');
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    switch (data.type) {
        case 'connected':
            console.log('会话ID:', data.session_id);
            break;
        case 'status':
            console.log('状态:', data.message);
            break;
        case 'response':
            console.log('回复:', data.message);
            break;
        case 'error':
            console.error('错误:', data.message);
            break;
    }
};

// 发送消息
function send(message) {
    ws.send(JSON.stringify({ message }));
}

send('起飞到1.5米');
```

---

## 7. 监控与日志

### 查看实时日志

```bash
docker-compose -f docker-compose.prod.yml logs -f --tail=100 agent-core
```

### 设置日志轮转

```bash
cat > /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
sudo systemctl restart docker
```

---

## 8. 故障排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 无法连接 | 端口未开放 | 检查安全组/防火墙 |
| API 超时 | DeepSeek API 慢 | 检查网络或换区域 |
| 工具调用失败 | 后端不可达 | 检查 BACKEND_URL |
| 内存不足 | 容器资源限制 | 增加服务器内存 |

---

## 9. 生产环境建议

1. **使用 HTTPS** - 配置 SSL 证书
2. **设置域名** - 避免直接暴露 IP
3. **限流保护** - Nginx 配置请求限制
4. **备份数据** - 定期备份 data 目录
5. **监控告警** - 配置健康检查告警

---

*最后更新：2025-12-13*
