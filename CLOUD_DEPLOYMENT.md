# ☁️ 云端部署完整指南

本指南提供多种云端部署方案，选择适合你的一种。

## 📋 部署前准备

### 必需：
1. ✅ Git仓库（GitHub/GitLab）
2. ✅ LLM API密钥（OpenAI/Claude/或部署Ollama）

### 推荐准备：
- 域名（可选，用于自定义访问地址）
- SSL证书（大多数平台自动提供）

---

## 🚀 方案1: Railway部署（推荐新手）

**优势：** 免费额度、一键部署、自动HTTPS

### Step 1: 推送代码到GitHub

```bash
cd agent-core

# 初始化Git（如果还没有）
git init
git add .
git commit -m "Initial commit: Agent Core Service"

# 创建GitHub仓库后
git remote add origin https://github.com/你的用户名/agent-core.git
git push -u origin main
```

### Step 2: 部署到Railway

1. 访问 https://railway.app/
2. 注册/登录（支持GitHub登录）
3. 点击 "New Project" → "Deploy from GitHub repo"
4. 选择你的 `agent-core` 仓库
5. Railway会自动检测Dockerfile并开始构建

### Step 3: 配置环境变量

在Railway项目设置中添加：

```bash
# 必需配置
LLM_PROVIDER=openai  # 或 claude
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=你的OpenAI密钥

# 可选配置
BACKEND_URL=你的无人机后端地址
LOG_LEVEL=INFO
```

### Step 4: 获取访问URL

部署完成后，Railway会提供：
- 公网URL: `https://your-app-name.up.railway.app`
- 可绑定自定义域名

### Step 5: 测试

```bash
curl https://your-app-name.up.railway.app/api/agent/health
```

**成本：** 免费（500小时/月），超出后约$5/月

---

## 🌏 方案2: 阿里云/腾讯云 ECS部署

**优势：** 国内访问快、稳定可靠

### Step 1: 购买云服务器

**配置推荐：**
- CPU: 2核
- 内存: 4GB
- 系统: Ubuntu 22.04
- 带宽: 1-3Mbps

**成本：** 约¥30-80/月（学生优惠更便宜）

### Step 2: 安装Docker

```bash
# SSH连接到服务器后
ssh root@你的服务器IP

# 安装Docker
curl -fsSL https://get.docker.com | sh
systemctl start docker
systemctl enable docker

# 安装Docker Compose
apt install docker-compose -y
```

### Step 3: 上传项目文件

```bash
# 在本地
cd agent-core
tar -czf agent-core.tar.gz .

# 上传到服务器
scp agent-core.tar.gz root@你的服务器IP:/root/

# 在服务器上
cd /root
tar -xzf agent-core.tar.gz
cd agent-core
```

### Step 4: 配置环境变量

```bash
# 创建 .env 文件
cat > .env << EOF
LLM_PROVIDER=openai
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=你的API密钥
BACKEND_URL=http://localhost:3001
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF
```

### Step 5: 使用Docker Compose部署

创建 `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  agent-core:
    build: .
    container_name: agent-core-prod
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
    networks:
      - agent-network

  # 可选：Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - agent-core
    restart: unless-stopped
    networks:
      - agent-network

networks:
  agent-network:
    driver: bridge
```

### Step 6: 启动服务

```bash
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose logs -f agent-core

# 检查状态
docker-compose ps
```

### Step 7: 配置防火墙

```bash
# 开放端口
ufw allow 8000/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### Step 8: 访问测试

```bash
curl http://你的服务器IP:8000/api/agent/health
```

---

## 🐳 方案3: Docker Hub + 任意VPS

**优势：** 灵活、可迁移

### Step 1: 构建并推送镜像

```bash
cd agent-core

# 登录Docker Hub
docker login

# 构建镜像
docker build -t 你的用户名/agent-core:latest .

# 推送到Docker Hub
docker push 你的用户名/agent-core:latest
```

### Step 2: 在服务器上拉取并运行

```bash
# SSH到服务器
ssh user@服务器IP

# 拉取镜像
docker pull 你的用户名/agent-core:latest

# 运行容器
docker run -d \
  --name agent-core \
  -p 8000:8000 \
  -e LLM_PROVIDER=openai \
  -e LLM_MODEL=gpt-3.5-turbo \
  -e OPENAI_API_KEY=你的密钥 \
  -e BACKEND_URL=http://localhost:3001 \
  --restart unless-stopped \
  你的用户名/agent-core:latest

# 查看日志
docker logs -f agent-core
```

---

## 🔒 安全配置（推荐）

### 1. 添加API认证

编辑 `.env`:

```bash
API_KEY=你的随机密钥
```

修改代码添加认证中间件（可选）。

### 2. 配置HTTPS

使用Let's Encrypt免费证书：

```bash
# 安装certbot
apt install certbot python3-certbot-nginx -y

# 获取证书
certbot --nginx -d your-domain.com
```

### 3. 限流配置

防止API滥用，在Nginx配置中添加：

```nginx
limit_req_zone $binary_remote_addr zone=agent_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=agent_limit burst=20;
    proxy_pass http://agent-core:8000;
}
```

---

## 📊 监控和维护

### 1. 查看日志

```bash
# Docker日志
docker logs -f agent-core

# 持久化日志
docker logs agent-core > /var/log/agent-core.log
```

### 2. 自动备份

```bash
# 创建备份脚本
cat > /root/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker save agent-core:latest | gzip > /backup/agent-core_$DATE.tar.gz
# 删除7天前的备份
find /backup -name "agent-core_*.tar.gz" -mtime +7 -delete
EOF

chmod +x /root/backup.sh

# 添加到crontab（每天凌晨2点）
echo "0 2 * * * /root/backup.sh" | crontab -
```

### 3. 自动更新

```bash
# 创建更新脚本
cat > /root/update.sh << 'EOF'
#!/bin/bash
cd /root/agent-core
git pull
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
EOF

chmod +x /root/update.sh
```

---

## 🌐 绑定域名

### 使用Cloudflare（推荐）

1. 在Cloudflare添加你的域名
2. 创建A记录指向服务器IP
3. 开启CDN和SSL

### Nginx配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 💰 成本对比

| 方案 | 月成本 | 流量 | 性能 | 适用 |
|------|--------|------|------|------|
| Railway | ¥0-35 | 100GB | 中 | 个人测试 |
| 阿里云轻量 | ¥30-50 | 1TB | 高 | 小团队 |
| 腾讯云 | ¥40-80 | 1TB | 高 | 生产环境 |
| AWS/Azure | ¥70-200 | 按量 | 最高 | 企业级 |

---

## 🔧 故障排查

### 容器无法启动

```bash
# 查看详细日志
docker logs agent-core

# 检查端口占用
netstat -tlnp | grep 8000

# 重新构建
docker-compose up --build
```

### 无法访问

```bash
# 检查防火墙
ufw status

# 检查服务状态
curl localhost:8000/api/agent/health

# 检查网络
docker network ls
```

### 性能问题

```bash
# 查看资源使用
docker stats agent-core

# 升级配置或优化代码
```

---

## ✅ 部署检查清单

- [ ] 代码推送到Git仓库
- [ ] 配置环境变量（LLM密钥）
- [ ] Dockerfile已测试
- [ ] 端口已开放（8000）
- [ ] 健康检查通过
- [ ] HTTPS已配置（可选）
- [ ] API认证已设置（推荐）
- [ ] 监控和日志配置
- [ ] 备份方案设置

---

## 🎯 推荐方案总结

**快速测试：** Railway（免费，5分钟部署）
**国内项目：** 阿里云/腾讯云（稳定，访问快）
**灵活控制：** Docker + VPS（最自由）

需要我帮你配置哪个方案？我可以提供详细的步骤指导！
