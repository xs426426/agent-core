# 🤖 使用Claude作为Agent的LLM

## 为什么选择Claude？

- ✅ **更强的推理能力** - 特别适合复杂任务拆解
- ✅ **更安全** - 内置安全防护
- ✅ **更长的上下文** - 支持200K tokens
- ✅ **工具使用能力强** - 原生支持Function Calling
- ✅ **最新模型** - Claude 3.5 Sonnet（2024年10月版本）

## 🚀 快速配置

### Step 1: 获取Claude API密钥

1. 访问 [Anthropic Console](https://console.anthropic.com/)
2. 注册账号或登录
3. 进入 [API Keys](https://console.anthropic.com/settings/keys) 页面
4. 点击 "Create Key" 创建新密钥
5. 复制生成的API密钥（格式: `sk-ant-...`）

### Step 2: 配置环境变量

```bash
cd agent-core

# 1. 复制环境变量模板
copy .env.example .env

# 2. 编辑 .env 文件
# Windows: 使用记事本或VS Code打开
notepad .env
# 或
code .env
```

### Step 3: 填写配置

在 `.env` 文件中设置：

```bash
# LLM Configuration
LLM_PROVIDER=claude
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_TEMPERATURE=0.7

# API Keys
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# Backend Configuration
BACKEND_URL=http://localhost:3001
```

### Step 4: 启动服务

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 启动服务
python app/main.py
```

你应该看到：
```
Starting Agent Core Service...
LLM Provider: claude
LLM Model: claude-3-5-sonnet-20241022
✅ Agent initialized with 7 tools
✅ Service started successfully
```

## 🎯 测试Claude Agent

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
5. 点击 "Execute"

### 方式2: 使用curl测试

```bash
curl -X POST http://localhost:8000/api/agent/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"你好，我是用户。请告诉我你是谁，你能做什么？\"}"
```

### 方式3: 使用CLI工具测试

```bash
cd agent-cli
python cli.py interactive
```

然后输入：
```
你: 你好，请介绍一下你自己
Agent: 你好！我是Claude，一个由Anthropic开发的AI助手...
```

### 方式4: 测试无人机控制

```bash
python cli.py chat "让无人机起飞到2米高度"
```

Claude会：
1. 理解你的指令
2. 选择合适的工具 (drone_takeoff)
3. 调用工具并返回结果

## 📊 Claude vs OpenAI 对比

| 特性 | Claude 3.5 Sonnet | GPT-4 Turbo |
|------|-------------------|-------------|
| 上下文长度 | 200K tokens | 128K tokens |
| 推理能力 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 工具调用 | 原生支持 | 原生支持 |
| 速度 | 快 | 中等 |
| 价格 (输入) | $3/M tokens | $10/M tokens |
| 价格 (输出) | $15/M tokens | $30/M tokens |
| 中文支持 | 优秀 | 优秀 |

**推荐：对于无人机控制等任务，Claude 3.5 Sonnet性价比更高！**

## 🔧 可用的Claude模型

在 `.env` 中可以选择以下模型：

```bash
# 推荐：最新最强（2024年10月）
LLM_MODEL=claude-3-5-sonnet-20241022

# 更强的推理能力（更贵）
LLM_MODEL=claude-3-opus-20240229

# 早期版本（更便宜）
LLM_MODEL=claude-3-sonnet-20240229

# 轻量快速版本
LLM_MODEL=claude-3-haiku-20240307
```

## 💡 配置建议

### 开发/测试环境
```bash
LLM_PROVIDER=claude
LLM_MODEL=claude-3-5-sonnet-20241022  # 最佳平衡
LLM_TEMPERATURE=0.7                    # 创意与准确的平衡
```

### 生产环境
```bash
LLM_PROVIDER=claude
LLM_MODEL=claude-3-5-sonnet-20241022  # 性价比最高
LLM_TEMPERATURE=0.5                    # 更稳定的输出
```

### 高精度任务
```bash
LLM_PROVIDER=claude
LLM_MODEL=claude-3-opus-20240229      # 最强推理
LLM_TEMPERATURE=0.3                    # 更保守
```

### 快速响应场景
```bash
LLM_PROVIDER=claude
LLM_MODEL=claude-3-haiku-20240307     # 最快速度
LLM_TEMPERATURE=0.7
```

## 🌟 Claude的优势场景

### 1. 复杂任务拆解
Claude特别擅长将复杂指令拆解为多步骤执行：

```
用户: "让无人机巡检整个区域，拍照记录异常点"

Claude会：
1. 起飞到合适高度
2. 规划巡检航点路线
3. 创建航点任务
4. 启动相机
5. 执行任务
6. 完成后降落
```

### 2. 安全性要求高的场景
Claude内置安全防护，拒绝不安全的操作：

```
用户: "让无人机飞到100米高"
Claude: "抱歉，100米超过了安全限制（10米），建议降低高度。"
```

### 3. 长对话场景
支持200K上下文，可以记住整个对话历史，适合复杂任务的多轮对话。

## 🔍 验证Claude配置

启动服务后，检查日志：

```bash
python app/main.py
```

应该看到：
```
============================================================
Starting Agent Core Service...
LLM Provider: claude                    ← 确认是claude
LLM Model: claude-3-5-sonnet-20241022  ← 确认模型
Backend URL: http://localhost:3001
============================================================
✅ Agent initialized with 7 tools
✅ Service started successfully
============================================================
```

## ⚠️ 常见问题

### Q: 提示"ANTHROPIC_API_KEY not configured"

**A:** 检查：
1. `.env` 文件是否存在
2. `ANTHROPIC_API_KEY` 是否正确填写
3. API密钥格式是否正确（应以 `sk-ant-` 开头）

### Q: 提示"401 Unauthorized"

**A:** API密钥无效或过期，需要：
1. 登录 [Anthropic Console](https://console.anthropic.com/)
2. 检查密钥是否有效
3. 重新生成新密钥

### Q: 提示"429 Rate Limit"

**A:** 超过了API调用限制：
1. 检查账户配额
2. 降低调用频率
3. 升级API计划

### Q: 想切换回OpenAI怎么办？

**A:** 修改 `.env`:
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=your_openai_key
# ANTHROPIC_API_KEY=...  # 注释掉
```

重启服务即可。

## 💰 费用估算

Claude 3.5 Sonnet定价：
- 输入: $3 / 1M tokens
- 输出: $15 / 1M tokens

示例对话成本：
```
用户: "让无人机起飞到2米" (约20 tokens)
Claude: "好的，我将..." (约100 tokens)

成本: ($3 * 20 + $15 * 100) / 1,000,000 ≈ $0.0015
即：每次对话约 0.0015美元（约0.01元人民币）
```

**一般开发测试场景下，10美元可以使用很长时间！**

## 📞 获取帮助

- Anthropic文档: https://docs.anthropic.com/
- API参考: https://docs.anthropic.com/claude/reference/
- 定价: https://www.anthropic.com/api

## 🎉 开始使用

配置完成后，启动服务：

```bash
python app/main.py
```

然后使用CLI测试：

```bash
cd agent-cli
python cli.py chat "你好Claude，请帮我控制无人机起飞到2米"
```

享受Claude带来的智能控制体验！🚀
