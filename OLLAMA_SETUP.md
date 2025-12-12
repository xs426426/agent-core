# 使用Ollama本地模型配置指南

## 🎯 为什么选择Ollama？

- ✅ **完全免费** - 无需API密钥，无使用限制
- ✅ **隐私保护** - 数据不离开本地
- ✅ **离线可用** - 不依赖网络连接
- ✅ **快速响应** - 本地推理，无网络延迟

## 📥 安装Ollama

### Windows

1. 访问 https://ollama.com/download
2. 下载Windows安装包
3. 运行安装程序

### 验证安装

```bash
ollama --version
```

## 🤖 下载模型

### 推荐模型

```bash
# 轻量快速（推荐开始）
ollama pull llama2:7b

# 中等性能
ollama pull llama2:13b

# 最强性能（需要更多内存）
ollama pull llama2:70b

# 专门优化的模型
ollama pull mistral
ollama pull codellama
```

## ⚙️ 配置Agent使用Ollama

编辑 `agent-core/.env`:

```bash
# LLM Configuration
LLM_PROVIDER=ollama
LLM_MODEL=llama2
LLM_TEMPERATURE=0.7

# 注释掉Claude配置
# ANTHROPIC_API_BASE=https://claude.micu.wiki
# ANTHROPIC_API_KEY=...

# Backend Configuration
BACKEND_URL=http://localhost:3001
```

## 🚀 启动服务

### 1. 启动Ollama服务

```bash
ollama serve
```

保持这个终端运行。

### 2. 启动Agent服务

打开新终端：

```bash
cd agent-core
python -m app.main
```

### 3. 测试

```bash
cd agent-cli
python cli.py chat "你好"
```

## 📊 模型对比

| 模型 | 大小 | 内存需求 | 速度 | 质量 |
|------|------|----------|------|------|
| llama2:7b | 3.8GB | 8GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| llama2:13b | 7.3GB | 16GB | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| mistral | 4.1GB | 8GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

## 💡 优化建议

### 调整温度参数

```bash
# 更准确（适合无人机控制）
LLM_TEMPERATURE=0.3

# 更有创意（适合对话）
LLM_TEMPERATURE=0.9
```

### 使用GPU加速

如果有NVIDIA显卡，Ollama会自动使用GPU加速，大幅提升速度。

## ⚠️ 注意事项

1. **首次使用会下载模型** - llama2:7b约3.8GB，需要时间
2. **内存需求** - 确保有足够的RAM
3. **性能** - 本地模型比Claude/GPT-4稍弱，但对于无人机控制足够

## 🔄 切换回Claude

如果以后获得了正确的API密钥，只需修改 `.env`:

```bash
LLM_PROVIDER=claude
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=你的新密钥
```

## 🎯 实际测试结果

使用llama2进行无人机控制：

```
用户: 让无人机起飞到2米
Ollama: 好的，我将控制无人机起飞到2米高度。
[调用工具: drone_takeoff(altitude=2)]
✅ 无人机起飞命令已发送
```

**完全可用！** 🚀
