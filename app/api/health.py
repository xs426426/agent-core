"""
健康检查和状态API
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.config import settings
from app.utils import logger

router = APIRouter()

# Agent实例将在main.py中注入
_agent = None
_start_time = datetime.now()


def set_agent(agent):
    """设置Agent实例"""
    global _agent
    _agent = agent


@router.get("/health", summary="健康检查")
async def health_check():
    """
    健康检查接口

    Returns:
        服务健康状态
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - _start_time).total_seconds()
    }


@router.get("/status", summary="服务状态")
async def get_status():
    """
    获取服务详细状态

    Returns:
        详细状态信息
    """
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    stats = _agent.get_stats()

    return {
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - _start_time).total_seconds(),
        "configuration": {
            "llm_provider": stats["llm_provider"],
            "llm_model": stats["llm_model"],
            "backend_url": settings.backend_url,
            "max_conversation_history": settings.max_conversation_history
        },
        "statistics": {
            "total_tools": stats["total_tools"],
            "tool_categories": stats["tool_categories"],
            "active_conversations": stats["active_conversations"]
        }
    }


@router.get("/info", summary="服务信息")
async def get_info():
    """
    获取服务基本信息

    Returns:
        服务信息
    """
    return {
        "name": "Agent Core Service",
        "version": "1.0.0",
        "description": "通用智能体核心服务 - 完全独立、高可移植",
        "features": [
            "多LLM支持 (OpenAI, Claude, Ollama)",
            "插件化工具系统",
            "HTTP + WebSocket API",
            "会话管理",
            "实时工具调用"
        ],
        "documentation": "/docs",
        "support": {
            "http_endpoint": "/api/agent/chat",
            "websocket_endpoint": "/api/agent/ws/chat/{session_id}"
        }
    }
