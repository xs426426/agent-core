"""
FastAPI应用入口
完全独立的Agent服务 - 支持多后端配置
对接真实无人机后端 API
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings, backend_registry
from app.core import IntelligentAgent
from app.plugins import (
    # 基础控制
    DroneTakeoffTool,
    DroneLandTool,
    DroneEmergencyStopTool,
    DroneFlyDirectionTool,
    DroneGoToTool,
    DroneStatusTool,
    # 任务控制
    DroneMissionTool,
    DroneMissionControlTool,
    # 探索引擎
    DroneExplorationStartTool,
    DroneExplorationStopTool,
    DroneExplorationPauseTool,
    DroneExplorationStatusTool,
    # 预设航线
    DroneListRoutesTool,
    DroneLoadRouteTool,
    DroneSaveRouteTool
)
from app.api import chat, tools, health, backends
from app.utils import logger


# 全局Agent实例
agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global agent

    # 启动时初始化
    logger.info("=" * 60)
    logger.info("Starting Agent Core Service...")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"LLM Model: {settings.llm_model}")
    logger.info("=" * 60)

    # 显示已注册的后端
    registered_backends = backend_registry.list_backends()
    logger.info(f"Registered backends: {len(registered_backends)}")
    for name, config in registered_backends.items():
        logger.info(f"  - {name}: {config['url']}")

    try:
        # 初始化所有工具 (15个工具)
        drone_tools = [
            # 基础控制 (6个)
            DroneTakeoffTool(),
            DroneLandTool(),
            DroneEmergencyStopTool(),
            DroneFlyDirectionTool(),
            DroneGoToTool(),
            DroneStatusTool(),
            # 任务控制 (2个)
            DroneMissionTool(),
            DroneMissionControlTool(),
            # 探索引擎 (4个)
            DroneExplorationStartTool(),
            DroneExplorationStopTool(),
            DroneExplorationPauseTool(),
            DroneExplorationStatusTool(),
            # 预设航线 (3个)
            DroneListRoutesTool(),
            DroneLoadRouteTool(),
            DroneSaveRouteTool()
        ]

        # 创建Agent实例
        agent = IntelligentAgent(
            llm_provider=settings.llm_provider,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            tools=drone_tools
        )

        # 注入Agent到API路由
        chat.set_agent(agent)
        tools.set_agent(agent)
        health.set_agent(agent)

        logger.info(f"Agent initialized with {len(drone_tools)} tools")
        logger.info("Service started successfully")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to initialize Agent: {str(e)}", exc_info=True)
        raise

    yield

    # 关闭时清理
    logger.info("Shutting down Agent Core Service...")


# 创建FastAPI应用
app = FastAPI(
    title="Agent Core Service",
    description=(
        "## 通用智能体核心服务\n\n"
        "完全独立、高可移植的AI Agent后端服务。\n\n"
        "### 功能特性\n"
        "- 多后端支持：可动态注册多个设备/服务后端\n"
        "- 语义理解：通过自然语言控制各种设备\n"
        "- 工具插件：灵活的工具扩展机制\n"
        "- 多种接口：HTTP/WebSocket双模式\n\n"
        "### 可用工具\n"
        "- **基础控制**: 起飞、降落、紧急停止、状态查询\n"
        "- **任务管理**: 创建航点任务、启动/暂停/取消任务\n"
        "- **自主探索**: 启动/停止/暂停探索、查询探索状态\n"
        "- **预设航线**: 列出/加载/保存预设航线\n\n"
        "### 快速开始\n"
        "1. 通过 `/api/agent/chat` 发送对话\n"
        "2. 通过 `/api/agent/ws/chat/{session_id}` 建立WebSocket连接\n"
        "3. 通过 `/api/agent/backends` 管理后端服务"
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置 - 允许所有来源以便前端嵌入
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins if settings.allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(
    chat.router,
    prefix="/api/agent",
    tags=["Chat - 对话接口"]
)

app.include_router(
    tools.router,
    prefix="/api/agent",
    tags=["Tools - 工具管理"]
)

app.include_router(
    backends.router,
    prefix="/api/agent",
    tags=["Backends - 后端管理"]
)

app.include_router(
    health.router,
    prefix="/api/agent",
    tags=["Health - 健康检查"]
)


# 根路径
@app.get("/", tags=["Root"])
async def root():
    """根路径 - 服务信息和使用指南"""
    return {
        "service": "Agent Core",
        "version": "2.0.0",
        "status": "running",
        "description": "通用智能体核心服务 - 无人机控制",
        "documentation": "/docs",
        "backends": backend_registry.list_backends(),
        "tools": {
            "control": ["drone_takeoff", "drone_land", "drone_emergency_stop", "drone_fly_direction", "drone_go_to", "get_drone_status"],
            "mission": ["drone_mission", "drone_mission_control"],
            "exploration": ["drone_exploration_start", "drone_exploration_stop", "drone_exploration_pause", "drone_exploration_status"],
            "routes": ["drone_list_routes", "drone_load_route", "drone_save_route"]
        },
        "endpoints": {
            "chat_http": "POST /api/agent/chat",
            "chat_websocket": "WS /api/agent/ws/chat/{session_id}",
            "tools": "GET /api/agent/tools",
            "backends": "GET /api/agent/backends",
            "health": "GET /api/agent/health"
        },
        "examples": {
            "起飞": "让无人机起飞到1.5米",
            "降落": "让无人机降落",
            "状态": "查询无人机状态",
            "探索": "启动自主探索",
            "任务": "创建一个从(0,0,1.5)到(5,0,1.5)的航点任务"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower()
    )
