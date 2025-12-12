# 🔌 使用第三方Claude API代理配置指南

如果你使用的是第三方Claude API代理服务（如micu.wiki、chatanywhere等），按照以下步骤配置。

## 📝 你的配置信息

根据你提供的信息：
- **模型**: Claude Opus 4.5
- **API密钥**: `cr_4a23b2bbb7a6131c2e923e98e7d4f765bdaf869958d26e73727c27a8b6e4ac90`
- **API地址**: `https://claude.micu.wiki/`

## ⚙️ 配置步骤

### Step 1: 创建 `.env` 文件

```bash
cd agent-core

# 复制模板
copy .env.example .env
```

### Step 2: 编辑 `.env` 文件

使用记事本或VS Code打开 `.env` 文件，填写以下内容：

```bash
# LLM Configuration
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229
LLM_TEMPERATURE=0.7

# Custom API Base URL (第三方代理)
ANTHROPIC_API_BASE=https://claude.micu.wiki

# API Keys (你的第三方API密钥)
ANTHROPIC_API_KEY=cr_4a23b2bbb7a6131c2e923e98e7d4f765bdaf869958d26e73727c27a8b6e4ac90

# Backend Configuration
BACKEND_URL=http://localhost:3001

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Feature Flags
ENABLE_TOOL_CONFIRMATION=false
ENABLE_STREAMING=true
MAX_CONVERSATION_HISTORY=50
```

### Step 3: 关键配置说明

#### 1. 模型名称 (`LLM_MODEL`)

虽然你的服务提供的是"Opus 4.5"，但在API调用时需要使用标准的模型名称。可选：

```bash
# 推荐：Claude 3 Opus (最强推理)
LLM_MODEL=claude-3-opus-20240229

# 或：Claude 3.5 Sonnet (性价比最高)
LLM_MODEL=claude-3-5-sonnet-20241022

# 或：Claude 3 Sonnet
LLM_MODEL=claude-3-sonnet-20240229
```

**建议：先使用 `claude-3-opus-20240229`**，如果代理不支持，再尝试其他模型。

#### 2. API Base URL (`ANTHROPIC_API_BASE`)

**重要：不要在URL末尾加斜杠！**

```bash
# ✅ 正确
ANTHROPIC_API_BASE=https://claude.micu.wiki

# ❌ 错误
ANTHROPIC_API_BASE=https://claude.micu.wiki/
```

#### 3. API Key (`ANTHROPIC_API_KEY`)

直接使用第三方服务提供的密钥：

```bash
ANTHROPIC_API_KEY=cr_4a23b2bbb7a6131c2e923e98e7d4f765bdaf869958d26e73727c27a8b6e4ac90
```

## 🚀 启动服务

### 1. 安装依赖

```bash
cd agent-core

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动Agent服务

```bash
python app/main.py
```

你应该看到：

```
============================================================
Starting Agent Core Service...
LLM Provider: claude
LLM Model: claude-3-opus-20240229
Using custom Anthropic API base: https://claude.micu.wiki
Backend URL: http://localhost:3001
============================================================
✅ Agent initialized with 7 tools
✅ Service started successfully
============================================================
```

**关键点：检查是否有 "Using custom Anthropic API base" 这一行！**

## 🧪 测试配置

### 方式1: 使用API文档测试

1. 打开浏览器访问: http://localhost:8000/docs
2. 找到 `POST /api/agent/chat` 接口
3. 点击 "Try it out"
4. 输入测试消息：

```json
{
  "message": "你好，请介绍一下你自己"
}
```

5. 点击 "Execute"，查看响应

### 方式2: 使用curl测试

```bash
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"你好\"}"
```

### 方式3: 使用CLI工具测试

```bash
cd agent-cli
python cli.py chat "你好"
```

### 方式4: 测试无人机控制

```bash
python cli.py chat "让无人机起飞到2米"
```

## ⚠️ 常见问题排查

### 问题1: 提示 "ANTHROPIC_API_KEY not configured"

**原因**: `.env` 文件不存在或未正确加载

**解决**:
1. 确认 `.env` 文件在 `agent-core/` 目录下
2. 检查文件名是否正确（Windows可能隐藏了扩展名）
3. 重启服务

### 问题2: 提示 "401 Unauthorized"

**原因**: API密钥无效

**解决**:
1. 检查 `ANTHROPIC_API_KEY` 是否正确复制（无多余空格）
2. 联系第三方服务商确认密钥是否有效
3. 确认密钥是否有余额/配额

### 问题3: 提示 "Connection Error" 或 "Timeout"

**原因**: API地址不正确或网络问题

**解决**:
1. 检查 `ANTHROPIC_API_BASE` 是否正确（去掉末尾斜杠）
2. 在浏览器中访问 `https://claude.micu.wiki` 确认服务可用
3. 检查网络连接
4. 尝试使用VPN（如果需要）

### 问题4: 提示 "Model not found" 或 "Invalid model"

**原因**: 第三方代理不支持该模型名称

**解决**: 尝试更换模型名称：

```bash
# 方案1: 使用Opus
LLM_MODEL=claude-3-opus-20240229

# 方案2: 使用Sonnet 3.5
LLM_MODEL=claude-3-5-sonnet-20241022

# 方案3: 使用Sonnet 3
LLM_MODEL=claude-3-sonnet-20240229

# 方案4: 使用Haiku (如果代理支持)
LLM_MODEL=claude-3-haiku-20240307
```

### 问题5: 代理服务返回错误

**检查步骤**:

1. 查看详细日志：
```bash
# 启动时查看完整日志
python app/main.py
```

2. 查看错误信息，常见错误：
   - `insufficient_quota`: 配额不足，需要充值
   - `rate_limit_error`: 调用频率过高，稍后重试
   - `invalid_api_key`: API密钥格式错误或已失效

## 💡 第三方API代理注意事项

### 1. 稳定性
第三方代理服务可能不如官方API稳定，可能出现：
- 偶尔的连接超时
- 响应速度较慢
- 服务中断

### 2. 安全性
- ⚠️ 不要在生产环境中使用未经验证的第三方服务
- ⚠️ 不要分享你的API密钥给他人
- ⚠️ 定期更换API密钥

### 3. 成本
- 查询余额和计费方式
- 设置使用限额
- 监控API调用次数

### 4. 切换回官方API

如果需要切换到官方Anthropic API，修改 `.env`:

```bash
# 使用官方API
LLM_PROVIDER=claude
LLM_MODEL=claude-3-5-sonnet-20241022
# ANTHROPIC_API_BASE=  # 注释掉或删除
ANTHROPIC_API_KEY=sk-ant-your-official-key
```

## 📊 验证配置正确性

启动服务后，检查日志输出：

### ✅ 正确的日志示例

```
============================================================
Starting Agent Core Service...
LLM Provider: claude
LLM Model: claude-3-opus-20240229
Using custom Anthropic API base: https://claude.micu.wiki  ← 关键！
Backend URL: http://localhost:3001
============================================================
Creating LLM: provider=claude, model=claude-3-opus-20240229, temperature=0.7
✅ Agent initialized with 7 tools
✅ Service started successfully
============================================================
```

**关键检查点**:
- ✅ "Using custom Anthropic API base" 出现
- ✅ 模型名称正确
- ✅ 没有错误提示

### ❌ 错误的日志示例

```
Creating LLM: provider=claude, model=claude-3-opus-20240229, temperature=0.7
❌ Failed to initialize Agent: ANTHROPIC_API_KEY not configured
```

说明 `.env` 文件未加载或配置错误。

## 🎯 完整配置示例（适用于你的情况）

创建 `agent-core/.env` 文件：

```bash
# === LLM配置 ===
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229
LLM_TEMPERATURE=0.7

# === 第三方API代理 ===
ANTHROPIC_API_BASE=https://claude.micu.wiki
ANTHROPIC_API_KEY=cr_4a23b2bbb7a6131c2e923e98e7d4f765bdaf869958d26e73727c27a8b6e4ac90

# === 无人机后端 ===
BACKEND_URL=http://localhost:3001

# === 服务配置 ===
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# === 功能开关 ===
ENABLE_TOOL_CONFIRMATION=false
ENABLE_STREAMING=true
MAX_CONVERSATION_HISTORY=50
```

保存后，启动服务：

```bash
python app/main.py
```

## 🆘 仍然有问题？

1. 检查 `.env` 文件是否保存
2. 检查是否在正确的目录 (`agent-core/`)
3. 重启终端/命令行
4. 重新激活虚拟环境
5. 查看完整错误日志

如果问题仍未解决，提供完整的错误日志以便排查。
