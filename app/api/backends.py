"""
后端服务管理API
提供动态注册、查询后端服务的接口
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.config import backend_registry
from app.utils import logger

router = APIRouter()


class BackendRegisterRequest(BaseModel):
    """后端注册请求"""
    name: str
    url: str
    description: str = ""
    timeout: float = 10.0


class BackendResponse(BaseModel):
    """后端信息响应"""
    name: str
    url: str
    description: str
    timeout: float


@router.get("/backends", summary="列出所有后端")
async def list_backends():
    """
    获取所有已注册的后端服务列表

    返回每个后端的名称、URL、描述和超时配置
    """
    backends = backend_registry.list_backends()
    return {
        "count": len(backends),
        "backends": backends
    }


@router.get("/backends/{name}", summary="获取后端详情")
async def get_backend(name: str):
    """
    获取指定后端的详细信息

    Args:
        name: 后端名称
    """
    backend = backend_registry.get(name)
    if not backend:
        raise HTTPException(status_code=404, detail=f"Backend '{name}' not found")

    return backend.to_dict()


@router.post("/backends", summary="注册新后端")
async def register_backend(request: BackendRegisterRequest):
    """
    动态注册一个新的后端服务

    注册后，可以创建关联此后端的工具

    **示例请求:**
    ```json
    {
        "name": "smart_home",
        "url": "http://localhost:4000",
        "description": "智能家居控制后端",
        "timeout": 10.0
    }
    ```
    """
    # 检查是否已存在
    existing = backend_registry.get(request.name)
    if existing:
        logger.info(f"Updating backend: {request.name}")
    else:
        logger.info(f"Registering new backend: {request.name}")

    backend_registry.register(
        name=request.name,
        url=request.url,
        description=request.description,
        timeout=request.timeout
    )

    return {
        "message": f"Backend '{request.name}' registered successfully",
        "backend": backend_registry.get(request.name).to_dict()
    }


@router.delete("/backends/{name}", summary="注销后端")
async def unregister_backend(name: str):
    """
    注销一个后端服务

    注意：注销后，关联此后端的工具将无法正常工作

    Args:
        name: 后端名称
    """
    if name == "drone":
        raise HTTPException(
            status_code=400,
            detail="Cannot unregister default 'drone' backend"
        )

    success = backend_registry.unregister(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Backend '{name}' not found")

    logger.info(f"Unregistered backend: {name}")
    return {"message": f"Backend '{name}' unregistered successfully"}


@router.post("/backends/{name}/test", summary="测试后端连接")
async def test_backend(name: str):
    """
    测试后端服务的连接状态

    尝试连接后端并返回结果

    Args:
        name: 后端名称
    """
    import httpx

    backend = backend_registry.get(name)
    if not backend:
        raise HTTPException(status_code=404, detail=f"Backend '{name}' not found")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # 尝试请求后端根路径或健康检查端点
            for endpoint in ["/health", "/api/health", "/"]:
                try:
                    response = await client.get(f"{backend.url}{endpoint}")
                    return {
                        "name": name,
                        "url": backend.url,
                        "status": "connected",
                        "endpoint": endpoint,
                        "status_code": response.status_code
                    }
                except:
                    continue

            return {
                "name": name,
                "url": backend.url,
                "status": "unreachable",
                "message": "无法连接到后端服务"
            }

    except httpx.TimeoutException:
        return {
            "name": name,
            "url": backend.url,
            "status": "timeout",
            "message": "连接超时"
        }
    except Exception as e:
        return {
            "name": name,
            "url": backend.url,
            "status": "error",
            "message": str(e)
        }
