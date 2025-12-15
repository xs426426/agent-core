"""Plugins package"""
from app.plugins.base_tool import BaseAgentTool, ToolParameter, ToolResult
from app.plugins.drone_tools import (
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
from app.plugins.generic_tools import (
    GenericApiTool,
    ToolFactory
)

__all__ = [
    # 基类
    "BaseAgentTool",
    "ToolParameter",
    "ToolResult",
    # 通用工具
    "GenericApiTool",
    "ToolFactory",
    # 无人机 - 基础控制
    "DroneTakeoffTool",
    "DroneLandTool",
    "DroneEmergencyStopTool",
    "DroneFlyDirectionTool",
    "DroneGoToTool",
    "DroneStatusTool",
    # 无人机 - 任务控制
    "DroneMissionTool",
    "DroneMissionControlTool",
    # 无人机 - 探索引擎
    "DroneExplorationStartTool",
    "DroneExplorationStopTool",
    "DroneExplorationPauseTool",
    "DroneExplorationStatusTool",
    # 无人机 - 预设航线
    "DroneListRoutesTool",
    "DroneLoadRouteTool",
    "DroneSaveRouteTool"
]
