"""
无人机控制工具集
对接真实的无人机后端 API (http://8.136.43.216)
包含：基础控制、任务管理、探索引擎、预设航线
"""
from typing import Dict, Any, List
from app.plugins.base_tool import BaseAgentTool, ToolParameter, ToolResult
from app.utils import logger


# ============================================================
# 基础控制工具
# ============================================================

class DroneTakeoffTool(BaseAgentTool):
    """无人机起飞工具"""

    name: str = "drone_takeoff"
    description: str = "控制无人机起飞到指定高度。使用场景：开始飞行任务前让无人机升空。"
    category: str = "drone_control"
    backend_name: str = "drone"
    requires_confirmation: bool = True

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="altitude",
            type="number",
            description="起飞目标高度（米），建议范围: 0.5-3米（室内）",
            required=True
        )
    ]

    async def execute(self, altitude: float) -> Dict[str, Any]:
        """执行起飞命令"""
        if altitude <= 0:
            return ToolResult.error_result("起飞高度必须大于0").to_dict()
        if altitude > 5:
            return ToolResult.error_result("室内起飞高度不建议超过5米").to_dict()

        logger.info(f"Takeoff command: altitude={altitude}m")

        result = await self.http_request(
            method="POST",
            endpoint="/api/command",
            json_data={
                "command": "takeoff",
                "altitude": altitude
            }
        )

        if result["success"]:
            return ToolResult.success_result(
                f"起飞命令已发送，目标高度 {altitude} 米",
                data={"altitude": altitude}
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "起飞命令失败")).to_dict()


class DroneLandTool(BaseAgentTool):
    """无人机降落工具"""

    name: str = "drone_land"
    description: str = "控制无人机降落。使用场景：任务完成或需要紧急降落时。"
    category: str = "drone_control"
    backend_name: str = "drone"
    requires_confirmation: bool = True

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """执行降落命令"""
        logger.info("Land command")

        result = await self.http_request(
            method="POST",
            endpoint="/api/command",
            json_data={"command": "land"}
        )

        if result["success"]:
            return ToolResult.success_result("降落命令已发送").to_dict()
        else:
            return ToolResult.error_result(result.get("error", "降落命令失败")).to_dict()


class DroneEmergencyStopTool(BaseAgentTool):
    """紧急停止工具"""

    name: str = "drone_emergency_stop"
    description: str = "紧急停止无人机所有动作。仅在紧急情况下使用！"
    category: str = "drone_control"
    backend_name: str = "drone"
    requires_confirmation: bool = True

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """执行紧急停止"""
        logger.info("EMERGENCY STOP command")

        result = await self.http_request(
            method="POST",
            endpoint="/api/command",
            json_data={"command": "emergency_stop"}
        )

        if result["success"]:
            return ToolResult.success_result("紧急停止命令已发送！").to_dict()
        else:
            return ToolResult.error_result(result.get("error", "紧急停止失败")).to_dict()


class DroneStatusTool(BaseAgentTool):
    """查询系统状态工具"""

    name: str = "get_drone_status"
    description: str = "获取无人机系统当前状态，包括MQTT连接状态、运行模式等。"
    category: str = "drone_status"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """查询状态"""
        logger.info("Querying drone status")

        result = await self.http_request(
            method="GET",
            endpoint="/api/status",
            timeout=5.0
        )

        if result["success"]:
            data = result.get("data", {})
            mqtt_status = data.get("mqtt", {})
            ws_status = data.get("websocket", {})

            status_msg = (
                f"MQTT连接: {'已连接' if mqtt_status.get('connected') else '未连接'}\n"
                f"Broker: {mqtt_status.get('broker', 'N/A')}\n"
                f"运行模式: {data.get('modeDescription', data.get('mode', '未知'))}\n"
                f"WebSocket客户端: {ws_status.get('clients', 0)}"
            )

            return ToolResult.success_result(
                "系统状态查询成功",
                data={"status_text": status_msg, "raw_data": data}
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "状态查询失败")).to_dict()


# ============================================================
# 任务控制工具
# ============================================================

class DroneMissionTool(BaseAgentTool):
    """发布航点任务工具"""

    name: str = "drone_mission"
    description: str = (
        "创建并发布无人机航点飞行任务。可以设置多个航点让无人机依次飞过。"
        "使用场景：巡检路线、区域扫描、固定路径飞行等。"
        "航点格式: [{\"x\":0,\"y\":0,\"z\":1.5}, {\"x\":5,\"y\":0,\"z\":1.5}]"
    )
    category: str = "drone_mission"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="waypoints",
            type="array",
            description="航点列表，每个航点格式为 {x, y, z}（米）",
            required=True
        ),
        ToolParameter(
            name="speed",
            type="number",
            description="飞行速度 (m/s)，建议范围: 0.3-1.0",
            required=False,
            default=0.5
        ),
        ToolParameter(
            name="mission_id",
            type="string",
            description="任务ID标识",
            required=False,
            default="mission_001"
        )
    ]

    async def execute(self, waypoints: List[Dict], speed: float = 0.5, mission_id: str = "mission_001") -> Dict[str, Any]:
        """发布航点任务"""
        if not waypoints or len(waypoints) == 0:
            return ToolResult.error_result("航点列表不能为空").to_dict()

        # 支持两种格式: [{x,y,z}] 或 [[x,y,z]]
        formatted_waypoints = []
        for i, wp in enumerate(waypoints):
            if isinstance(wp, dict):
                if not all(k in wp for k in ['x', 'y', 'z']):
                    return ToolResult.error_result(f"航点 {i} 格式错误，必须包含 x, y, z").to_dict()
                formatted_waypoints.append(wp)
            elif isinstance(wp, list) and len(wp) == 3:
                formatted_waypoints.append({"x": wp[0], "y": wp[1], "z": wp[2]})
            else:
                return ToolResult.error_result(f"航点 {i} 格式错误").to_dict()

        if speed <= 0 or speed > 2:
            return ToolResult.error_result("速度必须在 0-2 m/s 范围内").to_dict()

        logger.info(f"Creating mission: {len(formatted_waypoints)} waypoints, speed={speed}m/s")

        result = await self.http_request(
            method="POST",
            endpoint="/api/mission",
            json_data={
                "id": mission_id,
                "type": "waypoint",
                "waypoints": formatted_waypoints,
                "speed": speed
            }
        )

        if result["success"]:
            return ToolResult.success_result(
                f"已创建包含 {len(formatted_waypoints)} 个航点的任务，速度 {speed}m/s",
                data={"mission_id": mission_id, "waypoint_count": len(formatted_waypoints), "speed": speed}
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "创建任务失败")).to_dict()


class DroneMissionControlTool(BaseAgentTool):
    """任务执行控制工具"""

    name: str = "drone_mission_control"
    description: str = "控制无人机任务的执行状态：启动(start)、暂停(pause)、恢复(resume)、取消(cancel)任务。"
    category: str = "drone_mission"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="action",
            type="string",
            description="操作类型",
            required=True,
            enum=["start", "pause", "resume", "cancel", "clear"]
        ),
        ToolParameter(
            name="mission_id",
            type="string",
            description="任务ID",
            required=False,
            default="mission_001"
        )
    ]

    async def execute(self, action: str, mission_id: str = "mission_001") -> Dict[str, Any]:
        """控制任务执行"""
        action = action.lower()
        action_map = {
            "start": "启动",
            "pause": "暂停",
            "resume": "恢复",
            "cancel": "取消",
            "clear": "清除"
        }

        logger.info(f"Mission control: action={action}, mission_id={mission_id}")

        result = await self.http_request(
            method="POST",
            endpoint="/api/execution",
            json_data={
                "mission_id": mission_id,
                "action": action
            }
        )

        if result["success"]:
            return ToolResult.success_result(
                f"任务已{action_map.get(action, action)}",
                data={"action": action, "mission_id": mission_id}
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "操作失败")).to_dict()


# ============================================================
# 探索引擎工具
# ============================================================

class DroneExplorationStartTool(BaseAgentTool):
    """启动自主探索"""

    name: str = "drone_exploration_start"
    description: str = (
        "启动无人机自主探索模式。无人机会自动规划路径探索未知区域，构建地图。"
        "使用场景：室内环境探测、自动建图、区域搜索等。"
    )
    category: str = "drone_exploration"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="start_x",
            type="number",
            description="探索起点X坐标（米）",
            required=False,
            default=0
        ),
        ToolParameter(
            name="start_y",
            type="number",
            description="探索起点Y坐标（米）",
            required=False,
            default=0
        ),
        ToolParameter(
            name="start_z",
            type="number",
            description="探索高度（米）",
            required=False,
            default=1.5
        ),
        ToolParameter(
            name="max_distance",
            type="number",
            description="最大探索距离（米）",
            required=False,
            default=20
        )
    ]

    async def execute(self, start_x: float = 0, start_y: float = 0, start_z: float = 1.5, max_distance: float = 20) -> Dict[str, Any]:
        """启动探索"""
        logger.info(f"Starting exploration from ({start_x}, {start_y}, {start_z})")

        result = await self.http_request(
            method="POST",
            endpoint="/api/exploration/start",
            json_data={
                "startPosition": {"x": start_x, "y": start_y, "z": start_z},
                "maxDistance": max_distance,
                "explorationHeight": start_z
            }
        )

        if result["success"]:
            return ToolResult.success_result(
                f"自主探索已启动，起点({start_x}, {start_y}, {start_z})，最大距离{max_distance}米",
                data=result.get("data")
            ).to_dict()
        else:
            error_msg = result.get("error", "")
            if "已在进行中" in str(error_msg):
                return ToolResult.error_result("探索已在进行中，请先停止当前探索").to_dict()
            return ToolResult.error_result(error_msg or "启动探索失败").to_dict()


class DroneExplorationStopTool(BaseAgentTool):
    """停止探索"""

    name: str = "drone_exploration_stop"
    description: str = "停止无人机自主探索任务。"
    category: str = "drone_exploration"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """停止探索"""
        logger.info("Stopping exploration")

        result = await self.http_request(
            method="POST",
            endpoint="/api/exploration/stop"
        )

        if result["success"]:
            return ToolResult.success_result("探索已停止").to_dict()
        else:
            return ToolResult.error_result(result.get("error", "停止探索失败")).to_dict()


class DroneExplorationPauseTool(BaseAgentTool):
    """暂停/恢复探索"""

    name: str = "drone_exploration_pause"
    description: str = "暂停或恢复无人机探索任务。"
    category: str = "drone_exploration"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="action",
            type="string",
            description="操作类型: pause(暂停) 或 resume(恢复)",
            required=True,
            enum=["pause", "resume"]
        )
    ]

    async def execute(self, action: str) -> Dict[str, Any]:
        """暂停/恢复探索"""
        action = action.lower()
        endpoint = f"/api/exploration/{action}"

        logger.info(f"Exploration {action}")

        result = await self.http_request(
            method="POST",
            endpoint=endpoint
        )

        if result["success"]:
            msg = "探索已暂停" if action == "pause" else "探索已恢复"
            return ToolResult.success_result(msg).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "操作失败")).to_dict()


class DroneExplorationStatusTool(BaseAgentTool):
    """查询探索状态"""

    name: str = "drone_exploration_status"
    description: str = "获取当前探索任务的详细状态：进度、已探索面积、当前位置等。"
    category: str = "drone_exploration"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """查询探索状态"""
        logger.info("Querying exploration status")

        result = await self.http_request(
            method="GET",
            endpoint="/api/exploration/status",
            timeout=5.0
        )

        if result["success"]:
            data = result.get("data", {})
            pos = data.get("currentPosition", {})

            status_msg = (
                f"探索状态: {'进行中' if data.get('isExploring') else '已停止'}\n"
                f"探索进度: {data.get('progress', 0):.1f}%\n"
                f"已探索面积: {data.get('exploredArea', 0):.1f} m²\n"
                f"当前位置: ({pos.get('x', 0):.2f}, {pos.get('y', 0):.2f}, {pos.get('z', 0):.2f})\n"
                f"前沿点数量: {data.get('frontierCount', 0)}\n"
                f"探索时长: {data.get('duration', 0) / 1000:.0f} 秒"
            )

            return ToolResult.success_result(
                "探索状态查询成功",
                data={"status_text": status_msg, "raw_data": data}
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "状态查询失败")).to_dict()


# ============================================================
# 预设航线工具
# ============================================================

class DroneListRoutesTool(BaseAgentTool):
    """列出预设航线"""

    name: str = "drone_list_routes"
    description: str = "获取所有已保存的预设航线列表。"
    category: str = "drone_routes"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """列出航线"""
        logger.info("Listing preset routes")

        result = await self.http_request(
            method="GET",
            endpoint="/api/preset-routes"
        )

        if result["success"]:
            data = result.get("data", {})
            routes = data.get("routes", {})

            if not routes:
                return ToolResult.success_result("暂无预设航线").to_dict()

            route_list = []
            for route_id, info in routes.items():
                route_list.append(f"- {route_id}: {info.get('name', '未命名')} ({info.get('waypointCount', 0)}个航点)")

            return ToolResult.success_result(
                f"找到 {len(routes)} 条预设航线:\n" + "\n".join(route_list),
                data=routes
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "获取航线失败")).to_dict()


class DroneLoadRouteTool(BaseAgentTool):
    """加载预设航线"""

    name: str = "drone_load_route"
    description: str = "加载指定的预设航线详情，获取航点坐标，可用于执行任务。"
    category: str = "drone_routes"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="route_id",
            type="string",
            description="航线ID",
            required=True
        )
    ]

    async def execute(self, route_id: str) -> Dict[str, Any]:
        """加载航线"""
        logger.info(f"Loading route: {route_id}")

        result = await self.http_request(
            method="GET",
            endpoint=f"/api/preset-routes/{route_id}"
        )

        if result["success"]:
            data = result.get("data", {})
            route = data.get("route", {})
            waypoints = route.get("waypoints", [])

            return ToolResult.success_result(
                f"航线 '{route.get('name', route_id)}' 已加载，包含 {len(waypoints)} 个航点",
                data=route
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "加载航线失败")).to_dict()


class DroneSaveRouteTool(BaseAgentTool):
    """保存预设航线"""

    name: str = "drone_save_route"
    description: str = "保存航点列表为预设航线，方便以后复用。"
    category: str = "drone_routes"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="route_id",
            type="string",
            description="航线ID（唯一标识）",
            required=True
        ),
        ToolParameter(
            name="name",
            type="string",
            description="航线名称",
            required=True
        ),
        ToolParameter(
            name="waypoints",
            type="array",
            description="航点列表 [{x,y,z}, ...]",
            required=True
        ),
        ToolParameter(
            name="description",
            type="string",
            description="航线描述",
            required=False,
            default=""
        )
    ]

    async def execute(self, route_id: str, name: str, waypoints: List[Dict], description: str = "") -> Dict[str, Any]:
        """保存航线"""
        logger.info(f"Saving route: {route_id}")

        result = await self.http_request(
            method="POST",
            endpoint=f"/api/preset-routes/{route_id}",
            json_data={
                "name": name,
                "description": description,
                "waypoints": waypoints
            }
        )

        if result["success"]:
            return ToolResult.success_result(
                f"航线 '{name}' 已保存，ID: {route_id}",
                data={"route_id": route_id, "name": name}
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "保存航线失败")).to_dict()
