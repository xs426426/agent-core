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
        """执行起飞命令 - 通过创建任务实现"""
        if altitude <= 0:
            return ToolResult.error_result("起飞高度必须大于0").to_dict()
        if altitude > 5:
            return ToolResult.error_result("室内起飞高度不建议超过5米").to_dict()

        logger.info(f"Takeoff command: altitude={altitude}m")

        # 创建包含起飞任务的 Mission
        # 使用 Protobuf 格式: Mission { id, tasks: [{ take_off: {} }] }
        # 注意: protobuf.js verify() 使用 proto 原始字段名 (snake_case)
        mission_data = {
            "id": f"takeoff_{int(altitude * 100)}",
            "tasks": [
                {"take_off": {}},  # 起飞任务 (snake_case)
                {
                    "auto_pilot": {  # snake_case
                        "position": {"x": 0, "y": 0, "z": altitude},
                        "yaw": 0
                    }
                }  # 悬停到目标高度
            ]
        }

        result = await self.http_request(
            method="POST",
            endpoint="/api/mission",
            json_data=mission_data
        )

        if not result["success"]:
            return ToolResult.error_result(result.get("error", "创建起飞任务失败")).to_dict()

        # 启动任务执行
        exec_result = await self.http_request(
            method="POST",
            endpoint="/api/execution",
            json_data={
                "id": mission_data["id"],
                "action": 0  # START = 0
            }
        )

        if exec_result["success"]:
            return ToolResult.success_result(
                f"起飞命令已发送，目标高度 {altitude} 米",
                data={"altitude": altitude}
            ).to_dict()
        else:
            return ToolResult.error_result(exec_result.get("error", "启动起飞任务失败")).to_dict()


class DroneLandTool(BaseAgentTool):
    """无人机降落工具"""

    name: str = "drone_land"
    description: str = "控制无人机降落。使用场景：任务完成或需要紧急降落时。"
    category: str = "drone_control"
    backend_name: str = "drone"
    requires_confirmation: bool = True

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """执行降落命令 - 通过创建降落任务实现"""
        logger.info("Land command")

        # 创建包含降落任务的 Mission
        # 注意: protobuf.js verify() 使用 proto 原始字段名 (snake_case)
        mission_data = {
            "id": "land_mission",
            "tasks": [
                {"land": {}}  # 降落任务 (land 本身就没有下划线)
            ]
        }

        result = await self.http_request(
            method="POST",
            endpoint="/api/mission",
            json_data=mission_data
        )

        if not result["success"]:
            return ToolResult.error_result(result.get("error", "创建降落任务失败")).to_dict()

        # 启动任务执行
        exec_result = await self.http_request(
            method="POST",
            endpoint="/api/execution",
            json_data={
                "id": mission_data["id"],
                "action": 0  # START = 0
            }
        )

        if exec_result["success"]:
            return ToolResult.success_result("降落命令已发送").to_dict()
        else:
            return ToolResult.error_result(exec_result.get("error", "启动降落任务失败")).to_dict()


class DroneEmergencyStopTool(BaseAgentTool):
    """紧急停止工具"""

    name: str = "drone_emergency_stop"
    description: str = "紧急停止无人机所有动作。仅在紧急情况下使用！"
    category: str = "drone_control"
    backend_name: str = "drone"
    requires_confirmation: bool = True

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """执行紧急停止 - 通过停止当前任务实现"""
        logger.info("EMERGENCY STOP command")

        # 停止当前任务
        result = await self.http_request(
            method="POST",
            endpoint="/api/execution",
            json_data={
                "id": "emergency",
                "action": 3  # STOP = 3
            }
        )

        if result["success"]:
            return ToolResult.success_result("紧急停止命令已发送！").to_dict()
        else:
            return ToolResult.error_result(result.get("error", "紧急停止失败")).to_dict()


class DroneFlyDirectionTool(BaseAgentTool):
    """方向飞行工具"""

    name: str = "drone_fly_direction"
    description: str = (
        "控制无人机向指定方向飞行指定距离。"
        "支持方向：前(forward/x+)、后(backward/x-)、左(left/y+)、右(right/y-)、上(up/z+)、下(down/z-)。"
        "需要先知道当前位置，可以通过 get_drone_status 获取。"
        "使用场景：简单的方向控制，如'向前飞3米'。"
    )
    category: str = "drone_control"
    backend_name: str = "drone"
    requires_confirmation: bool = True

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="direction",
            type="string",
            description="飞行方向: forward(前), backward(后), left(左), right(右), up(上), down(下)",
            required=True,
            enum=["forward", "backward", "left", "right", "up", "down"]
        ),
        ToolParameter(
            name="distance",
            type="number",
            description="飞行距离（米），范围: 0.5-10米",
            required=True
        ),
        ToolParameter(
            name="current_x",
            type="number",
            description="当前X坐标（米）",
            required=True
        ),
        ToolParameter(
            name="current_y",
            type="number",
            description="当前Y坐标（米）",
            required=True
        ),
        ToolParameter(
            name="current_z",
            type="number",
            description="当前Z坐标/高度（米）",
            required=True
        ),
        ToolParameter(
            name="speed",
            type="number",
            description="飞行速度 (m/s)",
            required=False,
            default=0.5
        )
    ]

    async def execute(
        self,
        direction: str,
        distance: float,
        current_x: float,
        current_y: float,
        current_z: float,
        speed: float = 0.5
    ) -> Dict[str, Any]:
        """执行方向飞行"""
        if distance <= 0 or distance > 10:
            return ToolResult.error_result("飞行距离必须在 0.5-10 米范围内").to_dict()

        direction = direction.lower()

        # 计算目标位置
        target_x = current_x
        target_y = current_y
        target_z = current_z

        direction_map = {
            "forward": ("x", 1, "前"),
            "backward": ("x", -1, "后"),
            "left": ("y", 1, "左"),
            "right": ("y", -1, "右"),
            "up": ("z", 1, "上"),
            "down": ("z", -1, "下")
        }

        if direction not in direction_map:
            return ToolResult.error_result(f"不支持的方向: {direction}").to_dict()

        axis, sign, cn_dir = direction_map[direction]

        if axis == "x":
            target_x = current_x + (distance * sign)
        elif axis == "y":
            target_y = current_y + (distance * sign)
        elif axis == "z":
            target_z = current_z + (distance * sign)
            if target_z < 0.3:
                return ToolResult.error_result("目标高度过低，最低高度为0.3米").to_dict()
            if target_z > 5:
                return ToolResult.error_result("室内目标高度不建议超过5米").to_dict()

        logger.info(f"Fly {direction} {distance}m: ({current_x},{current_y},{current_z}) -> ({target_x},{target_y},{target_z})")

        # 创建 Line 任务
        # 注意: protobuf.js verify() 使用 proto 原始字段名 (snake_case)
        mission_data = {
            "id": f"fly_{direction}_{int(distance*100)}",
            "tasks": [
                {
                    "line": {
                        "start": {"x": current_x, "y": current_y, "z": current_z},
                        "end": {"x": target_x, "y": target_y, "z": target_z},
                        "yaw_mode": 0,  # FIXED - 保持当前航向 (snake_case)
                        "yaw_fixed": 0,  # snake_case
                        "max_speed": speed,  # snake_case
                        "max_accel": 0.5  # snake_case
                    }
                }
            ]
        }

        result = await self.http_request(
            method="POST",
            endpoint="/api/mission",
            json_data=mission_data
        )

        if not result["success"]:
            return ToolResult.error_result(result.get("error", "创建飞行任务失败")).to_dict()

        # 启动任务
        exec_result = await self.http_request(
            method="POST",
            endpoint="/api/execution",
            json_data={
                "id": mission_data["id"],
                "action": 0  # START
            }
        )

        if exec_result["success"]:
            return ToolResult.success_result(
                f"已发送向{cn_dir}飞行 {distance} 米的指令，目标位置: ({target_x:.2f}, {target_y:.2f}, {target_z:.2f})",
                data={
                    "direction": direction,
                    "distance": distance,
                    "target": {"x": target_x, "y": target_y, "z": target_z}
                }
            ).to_dict()
        else:
            return ToolResult.error_result(exec_result.get("error", "启动飞行任务失败")).to_dict()

class DroneStatusTool(BaseAgentTool):
    """查询无人机状态和位置工具"""

    name: str = "get_drone_status"
    description: str = "获取无人机当前状态，包括位置坐标(x,y,z)、姿态、速度等实时数据。用于了解无人机在哪里。"
    category: str = "drone_status"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = []

    async def execute(self) -> Dict[str, Any]:
        """查询无人机状态和位置"""
        logger.info("Querying drone status and odometry")

        # 先获取位姿数据
        odometry_result = await self.http_request(
            method="GET",
            endpoint="/api/drone/odometry",
            timeout=5.0
        )

        # 再获取系统状态
        status_result = await self.http_request(
            method="GET",
            endpoint="/api/status",
            timeout=5.0
        )

        if not odometry_result["success"] and not status_result["success"]:
            return ToolResult.error_result("状态查询失败").to_dict()

        # 解析位姿数据
        pos = odometry_result.get("data", {}).get("position", {})
        orient = odometry_result.get("data", {}).get("orientation", {})
        vel = odometry_result.get("data", {}).get("velocity", {})
        is_stale = odometry_result.get("data", {}).get("isStale", True)

        # 解析系统状态
        status_data = status_result.get("data", {})
        mqtt_status = status_data.get("mqtt", {})

        # 构建状态消息
        status_parts = []

        # 位置信息
        if pos and not is_stale:
            status_parts.append(f"当前位置: x={pos.get('x', 0):.2f}m, y={pos.get('y', 0):.2f}m, z={pos.get('z', 0):.2f}m")
        elif is_stale:
            status_parts.append("位置数据: 暂无实时数据（无人机可能未启动）")

        # 速度信息
        if vel and not is_stale:
            speed = (vel.get('x', 0)**2 + vel.get('y', 0)**2 + vel.get('z', 0)**2) ** 0.5
            if speed > 0.01:
                status_parts.append(f"当前速度: {speed:.2f} m/s")

        # 系统状态
        if mqtt_status:
            status_parts.append(f"MQTT连接: {'已连接' if mqtt_status.get('connected') else '未连接'}")
        status_parts.append(f"运行模式: {status_data.get('modeDescription', status_data.get('mode', '未知'))}")

        status_msg = "\n".join(status_parts)

        return ToolResult.success_result(
            "状态查询成功",
            data={
                "status_text": status_msg,
                "position": pos if not is_stale else None,
                "orientation": orient if not is_stale else None,
                "velocity": vel if not is_stale else None,
                "is_stale": is_stale,
                "system_status": status_data
            }
        ).to_dict()


class DroneGoToTool(BaseAgentTool):
    """直接前往指定坐标工具"""

    name: str = "drone_go_to"
    description: str = (
        "控制无人机直接飞到指定的三维坐标位置。"
        "使用场景：用户说'前往x,y,z'、'飞到坐标(x,y,z)'、'去位置x,y,z'等。"
        "这是最简单的点到点飞行方式。"
    )
    category: str = "drone_control"
    backend_name: str = "drone"
    requires_confirmation: bool = True

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="x",
            type="number",
            description="目标X坐标（米）",
            required=True
        ),
        ToolParameter(
            name="y",
            type="number",
            description="目标Y坐标（米）",
            required=True
        ),
        ToolParameter(
            name="z",
            type="number",
            description="目标Z坐标/高度（米），建议范围0.5-5米",
            required=True
        ),
        ToolParameter(
            name="speed",
            type="number",
            description="飞行速度 (m/s)，默认0.5",
            required=False,
            default=0.5
        )
    ]

    async def execute(self, x: float, y: float, z: float, speed: float = 0.5) -> Dict[str, Any]:
        """执行前往指定坐标"""
        # 参数验证
        if z < 0.3:
            return ToolResult.error_result("目标高度过低，最低高度为0.3米").to_dict()
        if z > 5:
            return ToolResult.error_result("室内目标高度不建议超过5米").to_dict()
        if speed <= 0 or speed > 2:
            return ToolResult.error_result("速度必须在 0-2 m/s 范围内").to_dict()

        logger.info(f"Go to position: ({x}, {y}, {z}) at speed {speed}m/s")

        # 创建 auto_pilot 任务直接飞到目标位置
        # 注意: protobuf.js verify() 使用 proto 原始字段名 (snake_case)
        mission_data = {
            "id": f"goto_{int(x*100)}_{int(y*100)}_{int(z*100)}",
            "tasks": [
                {
                    "auto_pilot": {  # snake_case
                        "position": {"x": x, "y": y, "z": z},
                        "yaw": 0
                    }
                }
            ]
        }

        result = await self.http_request(
            method="POST",
            endpoint="/api/mission",
            json_data=mission_data
        )

        if not result["success"]:
            return ToolResult.error_result(result.get("error", "创建飞行任务失败")).to_dict()

        # 启动任务
        exec_result = await self.http_request(
            method="POST",
            endpoint="/api/execution",
            json_data={
                "id": mission_data["id"],
                "action": 0  # START
            }
        )

        if exec_result["success"]:
            return ToolResult.success_result(
                f"已发送飞往坐标 ({x}, {y}, {z}) 的指令，飞行速度 {speed} m/s",
                data={"target": {"x": x, "y": y, "z": z}, "speed": speed}
            ).to_dict()
        else:
            return ToolResult.error_result(exec_result.get("error", "启动飞行任务失败")).to_dict()


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
        """发布航点任务 - 使用 Protobuf Line 任务格式"""
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

        # 构建 Protobuf Mission 格式
        # 将航点列表转换为 Line 任务列表（每两个相邻航点构成一条线段）
        # 注意: protobuf.js verify() 使用 proto 原始字段名 (snake_case)
        tasks = []

        # 将航点转换为 Line 任务
        for i, wp in enumerate(formatted_waypoints):
            if i == 0:
                # 第一个点使用 auto_pilot 飞到
                tasks.append({
                    "auto_pilot": {  # snake_case
                        "position": {"x": wp["x"], "y": wp["y"], "z": wp["z"]},
                        "yaw": 0
                    }
                })
            else:
                # 后续点使用 Line 从前一点飞到当前点
                prev_wp = formatted_waypoints[i - 1]
                tasks.append({
                    "line": {
                        "start": {"x": prev_wp["x"], "y": prev_wp["y"], "z": prev_wp["z"]},
                        "end": {"x": wp["x"], "y": wp["y"], "z": wp["z"]},
                        "yaw_mode": 1,  # TARGET - 指向目标 (snake_case)
                        "max_speed": speed,  # snake_case
                        "max_accel": 0.5  # snake_case
                    }
                })

        mission_data = {
            "id": mission_id,
            "tasks": tasks
        }

        result = await self.http_request(
            method="POST",
            endpoint="/api/mission",
            json_data=mission_data
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
    description: str = "控制无人机任务的执行状态：启动(start)、暂停(pause)、恢复(resume)、取消(stop)、清除(clear)任务。"
    category: str = "drone_mission"
    backend_name: str = "drone"

    parameters: List[ToolParameter] = [
        ToolParameter(
            name="action",
            type="string",
            description="操作类型",
            required=True,
            enum=["start", "pause", "resume", "stop", "clear"]
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
        """控制任务执行 - 使用 Protobuf Execution 格式"""
        action = action.lower()

        # Protobuf Execution.Action 枚举值
        # START = 0, PAUSE = 1, RESUME = 2, STOP = 3, CLEAR = 4
        action_to_enum = {
            "start": 0,
            "pause": 1,
            "resume": 2,
            "stop": 3,
            "clear": 4
        }

        action_to_chinese = {
            "start": "启动",
            "pause": "暂停",
            "resume": "恢复",
            "stop": "停止",
            "clear": "清除"
        }

        if action not in action_to_enum:
            return ToolResult.error_result(f"不支持的操作: {action}").to_dict()

        logger.info(f"Mission control: action={action}, mission_id={mission_id}")

        result = await self.http_request(
            method="POST",
            endpoint="/api/execution",
            json_data={
                "id": mission_id,
                "action": action_to_enum[action]  # 使用数字枚举值
            }
        )

        if result["success"]:
            return ToolResult.success_result(
                f"任务已{action_to_chinese.get(action, action)}",
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
