"""
通用工具模板
提供快速创建新后端工具的模板和工厂类
"""
from typing import Dict, Any, List, Optional, Callable, Awaitable
from app.plugins.base_tool import BaseAgentTool, ToolParameter, ToolResult
from app.config import backend_registry
from app.utils import logger


class GenericApiTool(BaseAgentTool):
    """
    通用API调用工具

    用于快速创建简单的API调用工具，无需继承

    使用示例:
    ```python
    # 创建一个简单的GET请求工具
    status_tool = GenericApiTool(
        name="get_device_status",
        description="获取设备状态",
        backend_name="iot",
        endpoint="/api/device/status",
        method="GET"
    )

    # 创建一个带参数的POST请求工具
    control_tool = GenericApiTool(
        name="set_light",
        description="控制灯光",
        backend_name="smart_home",
        endpoint="/api/light/control",
        method="POST",
        parameters=[
            ToolParameter(name="brightness", type="number", description="亮度0-100"),
            ToolParameter(name="color", type="string", description="颜色")
        ]
    )
    ```
    """

    # 必须在实例化时设置
    name: str = "generic_tool"
    description: str = "通用API工具"

    # API配置
    endpoint: str = "/"
    method: str = "GET"

    # 响应处理
    success_message: str = "操作成功"

    def __init__(
        self,
        name: str,
        description: str,
        backend_name: str,
        endpoint: str,
        method: str = "GET",
        category: str = "general",
        parameters: List[ToolParameter] = None,
        success_message: str = "操作成功",
        requires_confirmation: bool = False,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.name = name
        self.description = description
        self.backend_name = backend_name
        self.endpoint = endpoint
        self.method = method.upper()
        self.category = category
        self.parameters = parameters or []
        self.success_message = success_message
        self.requires_confirmation = requires_confirmation

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行API调用"""
        logger.info(f"GenericApiTool executing: {self.name}, endpoint={self.endpoint}, params={kwargs}")

        # 构建请求
        json_data = kwargs if self.method in ["POST", "PUT", "PATCH"] else None
        params = kwargs if self.method == "GET" else None

        result = await self.http_request(
            method=self.method,
            endpoint=self.endpoint,
            json_data=json_data,
            params=params
        )

        if result["success"]:
            return ToolResult.success_result(
                self.success_message,
                data=result.get("data")
            ).to_dict()
        else:
            return ToolResult.error_result(result.get("error", "操作失败")).to_dict()


class ToolFactory:
    """
    工具工厂类

    提供批量创建工具的便捷方法

    使用示例:
    ```python
    factory = ToolFactory("iot", "http://localhost:4000")

    # 从配置创建工具
    tools = factory.create_from_config([
        {
            "name": "get_sensor_data",
            "description": "获取传感器数据",
            "endpoint": "/api/sensors",
            "method": "GET"
        },
        {
            "name": "control_actuator",
            "description": "控制执行器",
            "endpoint": "/api/actuators/control",
            "method": "POST",
            "parameters": [
                {"name": "device_id", "type": "string", "description": "设备ID"},
                {"name": "action", "type": "string", "description": "操作类型"}
            ]
        }
    ])
    ```
    """

    def __init__(self, backend_name: str, backend_url: str = None, description: str = ""):
        """
        初始化工具工厂

        Args:
            backend_name: 后端名称
            backend_url: 后端URL（可选，如果提供则自动注册）
            description: 后端描述
        """
        self.backend_name = backend_name

        # 如果提供了URL，自动注册后端
        if backend_url:
            backend_registry.register(
                name=backend_name,
                url=backend_url,
                description=description
            )

    def create_tool(
        self,
        name: str,
        description: str,
        endpoint: str,
        method: str = "GET",
        category: str = None,
        parameters: List[Dict] = None,
        success_message: str = "操作成功",
        requires_confirmation: bool = False
    ) -> GenericApiTool:
        """
        创建单个工具

        Args:
            name: 工具名称
            description: 工具描述
            endpoint: API端点
            method: HTTP方法
            category: 分类（默认使用后端名称）
            parameters: 参数列表
            success_message: 成功消息
            requires_confirmation: 是否需要确认

        Returns:
            GenericApiTool实例
        """
        # 转换参数格式
        tool_params = []
        if parameters:
            for p in parameters:
                tool_params.append(ToolParameter(
                    name=p.get("name"),
                    type=p.get("type", "string"),
                    description=p.get("description", ""),
                    required=p.get("required", True),
                    default=p.get("default"),
                    enum=p.get("enum")
                ))

        return GenericApiTool(
            name=name,
            description=description,
            backend_name=self.backend_name,
            endpoint=endpoint,
            method=method,
            category=category or self.backend_name,
            parameters=tool_params,
            success_message=success_message,
            requires_confirmation=requires_confirmation
        )

    def create_from_config(self, config: List[Dict]) -> List[GenericApiTool]:
        """
        从配置列表批量创建工具

        Args:
            config: 工具配置列表

        Returns:
            工具实例列表
        """
        tools = []
        for tool_config in config:
            tool = self.create_tool(**tool_config)
            tools.append(tool)
        return tools

    def create_crud_tools(
        self,
        resource_name: str,
        resource_description: str,
        base_endpoint: str,
        id_param: str = "id"
    ) -> List[GenericApiTool]:
        """
        创建标准CRUD工具集

        Args:
            resource_name: 资源名称（英文，用于工具命名）
            resource_description: 资源描述（中文，用于工具描述）
            base_endpoint: 基础API端点
            id_param: ID参数名

        Returns:
            包含增删改查的工具列表
        """
        tools = []

        # 列表查询
        tools.append(self.create_tool(
            name=f"list_{resource_name}",
            description=f"获取{resource_description}列表",
            endpoint=base_endpoint,
            method="GET"
        ))

        # 详情查询
        tools.append(self.create_tool(
            name=f"get_{resource_name}",
            description=f"获取{resource_description}详情",
            endpoint=f"{base_endpoint}/{{{id_param}}}",
            method="GET",
            parameters=[{"name": id_param, "type": "string", "description": f"{resource_description}ID"}]
        ))

        # 创建
        tools.append(self.create_tool(
            name=f"create_{resource_name}",
            description=f"创建{resource_description}",
            endpoint=base_endpoint,
            method="POST",
            parameters=[{"name": "data", "type": "object", "description": f"{resource_description}数据"}]
        ))

        # 更新
        tools.append(self.create_tool(
            name=f"update_{resource_name}",
            description=f"更新{resource_description}",
            endpoint=f"{base_endpoint}/{{{id_param}}}",
            method="PUT",
            parameters=[
                {"name": id_param, "type": "string", "description": f"{resource_description}ID"},
                {"name": "data", "type": "object", "description": "更新数据"}
            ]
        ))

        # 删除
        tools.append(self.create_tool(
            name=f"delete_{resource_name}",
            description=f"删除{resource_description}",
            endpoint=f"{base_endpoint}/{{{id_param}}}",
            method="DELETE",
            parameters=[{"name": id_param, "type": "string", "description": f"{resource_description}ID"}],
            requires_confirmation=True
        ))

        return tools


# ============================================================
# 示例：如何快速接入新后端
# ============================================================

def create_smart_home_tools() -> List[BaseAgentTool]:
    """
    示例：创建智能家居控制工具

    这个示例展示如何快速为新后端创建工具集
    """
    # 创建工厂并注册后端
    factory = ToolFactory(
        backend_name="smart_home",
        backend_url="http://localhost:4000",
        description="智能家居控制后端"
    )

    # 从配置创建工具
    tools = factory.create_from_config([
        {
            "name": "get_home_status",
            "description": "获取智能家居整体状态",
            "endpoint": "/api/status",
            "method": "GET",
            "success_message": "状态获取成功"
        },
        {
            "name": "control_light",
            "description": "控制灯光开关和亮度",
            "endpoint": "/api/lights/control",
            "method": "POST",
            "parameters": [
                {"name": "room", "type": "string", "description": "房间名称"},
                {"name": "action", "type": "string", "description": "操作", "enum": ["on", "off", "dim"]},
                {"name": "brightness", "type": "number", "description": "亮度(0-100)", "required": False}
            ],
            "success_message": "灯光控制成功"
        },
        {
            "name": "set_temperature",
            "description": "设置空调温度",
            "endpoint": "/api/climate/temperature",
            "method": "POST",
            "parameters": [
                {"name": "room", "type": "string", "description": "房间名称"},
                {"name": "temperature", "type": "number", "description": "目标温度(16-30)"}
            ],
            "success_message": "温度设置成功"
        }
    ])

    return tools


def create_iot_sensor_tools() -> List[BaseAgentTool]:
    """
    示例：创建IoT传感器工具
    """
    factory = ToolFactory(
        backend_name="iot_sensors",
        backend_url="http://localhost:5000",
        description="IoT传感器数据后端"
    )

    # 使用CRUD工具快速创建
    sensor_tools = factory.create_crud_tools(
        resource_name="sensor",
        resource_description="传感器",
        base_endpoint="/api/sensors"
    )

    # 添加自定义工具
    custom_tools = factory.create_from_config([
        {
            "name": "get_sensor_reading",
            "description": "获取传感器最新读数",
            "endpoint": "/api/sensors/reading",
            "method": "GET",
            "parameters": [
                {"name": "sensor_id", "type": "string", "description": "传感器ID"},
                {"name": "type", "type": "string", "description": "数据类型", "enum": ["temperature", "humidity", "pressure"]}
            ]
        },
        {
            "name": "set_sensor_alert",
            "description": "设置传感器报警阈值",
            "endpoint": "/api/sensors/alert",
            "method": "POST",
            "parameters": [
                {"name": "sensor_id", "type": "string", "description": "传感器ID"},
                {"name": "min_value", "type": "number", "description": "最小阈值"},
                {"name": "max_value", "type": "number", "description": "最大阈值"}
            ]
        }
    ])

    return sensor_tools + custom_tools
