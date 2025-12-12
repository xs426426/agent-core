#!/bin/bash

# Agent Core 一键部署脚本（适用于Ubuntu/Debian服务器）
# 使用方法：bash deploy.sh

set -e  # 遇到错误立即退出

echo "=========================================="
echo "Agent Core 云端部署脚本"
echo "=========================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
  echo "请使用root用户运行此脚本: sudo bash deploy.sh"
  exit 1
fi

# 1. 安装Docker
echo "📦 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    echo "✅ Docker安装完成"
else
    echo "✅ Docker已安装"
fi

# 2. 安装Docker Compose
echo "📦 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt-get update
    apt-get install -y docker-compose
    echo "✅ Docker Compose安装完成"
else
    echo "✅ Docker Compose已安装"
fi

# 3. 创建项目目录
echo "📁 创建项目目录..."
PROJECT_DIR="/opt/agent-core"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# 4. 配置环境变量
echo "⚙️  配置环境变量..."
if [ ! -f .env ]; then
    echo "请输入LLM提供商 (openai/claude):"
    read LLM_PROVIDER

    echo "请输入模型名称 (如 gpt-3.5-turbo):"
    read LLM_MODEL

    echo "请输入API密钥:"
    read -s API_KEY

    echo "请输入无人机后端URL (如 http://localhost:3001):"
    read BACKEND_URL

    cat > .env << EOF
LLM_PROVIDER=$LLM_PROVIDER
LLM_MODEL=$LLM_MODEL
OPENAI_API_KEY=$API_KEY
BACKEND_URL=$BACKEND_URL
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO
EOF

    echo "✅ 环境变量配置完成"
else
    echo "✅ .env文件已存在"
fi

# 5. 拉取镜像或构建
echo "🐳 准备Docker镜像..."
if [ -f Dockerfile ]; then
    echo "从本地Dockerfile构建..."
    docker-compose -f docker-compose.prod.yml build
else
    echo "请确保Dockerfile存在于当前目录"
    exit 1
fi

# 6. 启动服务
echo "🚀 启动服务..."
docker-compose -f docker-compose.prod.yml up -d

# 7. 配置防火墙
echo "🔥 配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 8000/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "✅ 防火墙规则已添加"
fi

# 8. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 9. 健康检查
echo "🔍 健康检查..."
if curl -f http://localhost:8000/api/agent/health &> /dev/null; then
    echo "✅ 服务启动成功！"

    # 获取公网IP
    PUBLIC_IP=$(curl -s ifconfig.me)

    echo ""
    echo "=========================================="
    echo "部署完成！"
    echo "=========================================="
    echo "访问地址: http://$PUBLIC_IP:8000"
    echo "API文档: http://$PUBLIC_IP:8000/docs"
    echo "健康检查: http://$PUBLIC_IP:8000/api/agent/health"
    echo ""
    echo "查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo "=========================================="
else
    echo "❌ 服务启动失败，查看日志:"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi
