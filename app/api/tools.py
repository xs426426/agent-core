"""
工具管理API接口
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.utils import logger

router = APIRouter()

# Agent实例将在main.py中注入
_agent = None


def set_agent(agent):
    """设置Agent实例"""
    global _agent
    _agent = agent


@router.get("/tools", summary="列出所有工具")
async def list_tools():
    """
    列出所有已注册的工具及其详细信息

    Returns:
        工具列表
    """
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    tools = _agent.get_tools()

    return {
        "count": len(tools),
        "tools": tools
    }


@router.get("/tools/{tool_name}", summary="获取工具详情")
async def get_tool(tool_name: str):
    """
    获取指定工具的详细信息

    Args:
        tool_name: 工具名称

    Returns:
        工具详情
    """
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    tools = _agent.get_tools()

    if tool_name not in tools:
        raise HTTPException(status_code=404, detail="Tool not found")

    return tools[tool_name]


@router.get("/tools/category/{category}", summary="按类别获取工具")
async def get_tools_by_category(category: str):
    """
    获取指定类别的所有工具

    Args:
        category: 工具类别 (例如: drone, vehicle, general)

    Returns:
        工具列表
    """
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    tools = _agent.tool_orchestrator.get_tools_by_category(category)

    if not tools:
        return {
            "category": category,
            "count": 0,
            "tools": []
        }

    tool_infos = []
    for tool in tools:
        tool_infos.append({
            "name": tool.name,
            "description": tool.description,
            "category": getattr(tool, "category", "general"),
            "parameters": getattr(tool, "parameters", [])
        })

    return {
        "category": category,
        "count": len(tool_infos),
        "tools": tool_infos
    }


@router.get("/categories", summary="列出所有工具类别")
async def list_categories():
    """
    列出所有工具类别及其工具数量

    Returns:
        类别统计
    """
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    categories = _agent.tool_orchestrator.list_categories()

    return {
        "count": len(categories),
        "categories": categories
    }
