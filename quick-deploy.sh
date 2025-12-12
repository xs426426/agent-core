#!/bin/bash

# Agent Core 服务器部署脚本
# 适用于 2核4GB Ubuntu服务器
# 使用方法：sudo bash quick-deploy.sh

set -e

echo "=========================================="
echo "🚀 Agent Core 快速部署"
echo "适配：2核4GB服务器"
echo "=========================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检查root权限
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}❌ 请使用root用户运行: sudo bash quick-deploy.sh${NC}"
  exit 1
fi

echo -e "${YELLOW}📋 开始部署流程...${NC}"
echo ""

# 1. 系统更新
echo -e "${GREEN}[1/8]${NC} 更新系统软件包..."
apt-get update -qq
apt-get upgrade -y -qq

# 2. 安装Docker
echo -e "${GREEN}[2/8]${NC} 安装Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    echo -e "  ✅ Docker安装完成"
else
    echo -e "  ✅ Docker已安装"
fi

# 3. 安装Docker Compose
echo -e "${GREEN}[3/8]${NC} 安装Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt-get install -y docker-compose
    echo -e "  ✅ Docker Compose安装完成"
else
    echo -e "  ✅ Docker Compose已安装"
fi

# 4. 配置环境变量
echo -e "${GREEN}[4/8]${NC} 配置环境变量..."
echo ""
echo -e "${YELLOW}请选择LLM提供商:${NC}"
echo "  1) OpenAI (推荐)"
echo "  2) Claude"
echo "  3) Ollama (本地，免费但占用资源)"
read -p "请选择 [1-3]: " llm_choice

case $llm_choice in
  1)
    LLM_PROVIDER="openai"
    echo -e "${YELLOW}推荐模型: gpt-3.5-turbo (便宜快速) 或 gpt-4 (质量更好)${NC}"
    read -p "请输入模型名称 [gpt-3.5-turbo]: " llm_model
    LLM_MODEL=${llm_model:-gpt-3.5-turbo}
    read -sp "请输入OpenAI API密钥: " api_key
    echo ""
    OPENAI_API_KEY=$api_key
    ;;
  2)
    LLM_PROVIDER="claude"
    read -p "请输入Claude模型名称 [claude-3-5-sonnet-20241022]: " llm_model
    LLM_MODEL=${llm_model:-claude-3-5-sonnet-20241022}
    read -sp "请输入Anthropic API密钥: " api_key
    echo ""
    ANTHROPIC_API_KEY=$api_key
    read -p "API代理地址 (可选，直接回车跳过): " api_base
    ANTHROPIC_API_BASE=$api_base
    ;;
  3)
    LLM_PROVIDER="ollama"
    LLM_MODEL="llama2"
    echo -e "${YELLOW}⚠️  警告：Ollama会占用较多内存，可能影响性能${NC}"
    read -p "是否继续? [y/N]: " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
      echo "取消部署"
      exit 0
    fi
    ;;
  *)
    echo "无效选择"
    exit 1
    ;;
esac

read -p "无人机后端地址 [http://localhost:3001]: " backend_url
BACKEND_URL=${backend_url:-http://localhost:3001}

# 创建.env文件
cat > .env << EOF
# LLM Configuration
LLM_PROVIDER=$LLM_PROVIDER
LLM_MODEL=$LLM_MODEL
LLM_TEMPERATURE=0.7

EOF

if [ ! -z "$OPENAI_API_KEY" ]; then
  echo "OPENAI_API_KEY=$OPENAI_API_KEY" >> .env
fi

if [ ! -z "$ANTHROPIC_API_KEY" ]; then
  echo "ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY" >> .env
fi

if [ ! -z "$ANTHROPIC_API_BASE" ]; then
  echo "ANTHROPIC_API_BASE=$ANTHROPIC_API_BASE" >> .env
fi

cat >> .env << EOF

# Backend Configuration
BACKEND_URL=$BACKEND_URL

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Feature Flags
ENABLE_TOOL_CONFIRMATION=false
ENABLE_STREAMING=true
MAX_CONVERSATION_HISTORY=50
EOF

echo -e "  ✅ 环境变量配置完成"

# 5. 如果选择Ollama，安装它
if [ "$LLM_PROVIDER" == "ollama" ]; then
  echo -e "${GREEN}[5/8]${NC} 安装Ollama..."
  curl https://ollama.ai/install.sh | sh
  systemctl start ollama
  systemctl enable ollama
  ollama pull llama2
  echo -e "  ✅ Ollama安装完成"
else
  echo -e "${GREEN}[5/8]${NC} 跳过Ollama安装"
fi

# 6. 构建Docker镜像
echo -e "${GREEN}[6/8]${NC} 构建Docker镜像..."
docker-compose -f docker-compose.prod.yml build

# 7. 配置防火墙
echo -e "${GREEN}[7/8]${NC} 配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw --force enable
    ufw allow 22/tcp
    ufw allow 8000/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo -e "  ✅ 防火墙规则已添加"
fi

# 8. 启动服务
echo -e "${GREEN}[8/8]${NC} 启动服务..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo -e "${YELLOW}⏳ 等待服务启动 (30秒)...${NC}"
sleep 30

# 健康检查
echo ""
echo -e "${GREEN}🔍 健康检查...${NC}"
if curl -f http://localhost:8000/api/agent/health &> /dev/null; then
    PUBLIC_IP=$(curl -s ifconfig.me)

    echo ""
    echo -e "${GREEN}=========================================="
    echo "✅ 部署成功！"
    echo "==========================================${NC}"
    echo ""
    echo -e "${YELLOW}访问信息:${NC}"
    echo "  🌐 公网访问: http://$PUBLIC_IP:8000"
    echo "  📚 API文档: http://$PUBLIC_IP:8000/docs"
    echo "  ❤️  健康检查: http://$PUBLIC_IP:8000/api/agent/health"
    echo ""
    echo -e "${YELLOW}常用命令:${NC}"
    echo "  查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "  重启服务: docker-compose -f docker-compose.prod.yml restart"
    echo "  查看状态: docker-compose -f docker-compose.prod.yml ps"
    echo ""
    echo -e "${YELLOW}系统资源:${NC}"
    docker stats --no-stream
    echo ""
    echo -e "${GREEN}=========================================${NC}"
else
    echo -e "${RED}❌ 服务启动失败${NC}"
    echo ""
    echo -e "${YELLOW}查看日志:${NC}"
    docker-compose -f docker-compose.prod.yml logs --tail=50
    exit 1
fi
