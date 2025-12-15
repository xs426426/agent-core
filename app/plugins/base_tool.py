"""
工具基类
所有自定义工具都应继承此类
支持动态后端配置和通用HTTP调用
"""
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import BaseTool as LangChainBaseTool
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
import httpx
import time
import hashlib
import json
from app.utils import logger
from app.config import backend_registry


# 全局去重缓存：存储最近执行的工具调用
# 格式: {call_hash: (timestamp, result)}
_tool_call_cache: Dict[str, tuple] = {}
# 缓存过期时间（秒）- 同一调用在此时间内不会重复执行
CACHE_EXPIRY_SECONDS = 3.0


class ToolParameter(BaseModel):
    """工具参数定义"""
    name: str = Field(..., description="参数名称")
    type: str = Field(..., description="参数类型: string, number, boolean, array, object")
    description: str = Field(..., description="参数描述")
    required: bool = Field(True, description="是否必需")
    default: Any = Field(None, description="默认值")
    enum: Optional[List[Any]] = Field(None, description="枚举值列表")


def _create_args_schema(tool_name: str, parameters: List[ToolParameter]) -> Type[BaseModel]:
    """
    从 ToolParameter 列表动态创建 Pydantic 模型作为 args_schema

    这是 LangChain 工具调用所必需的 - 没有 args_schema，LLM 无法正确生成工具调用参数
    """
    if not parameters:
        # 无参数工具
        return create_model(f"{tool_name}Args")

    # 类型映射
    type_map = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    field_definitions = {}
    for param in parameters:
        python_type = type_map.get(param.type, str)

        # 构建 Field 参数
        if param.required:
            if param.default is not None:
                field_definitions[param.name] = (
                    python_type,
                    Field(default=param.default, description=param.description)
                )
            else:
                field_definitions[param.name] = (
                    python_type,
                    Field(..., description=param.description)
                )
        else:
            # 可选参数
            default_val = param.default if param.default is not None else None
            field_definitions[param.name] = (
                Optional[python_type],
                Field(default=default_val, description=param.description)
            )

    return create_model(f"{tool_name}Args", **field_definitions)


class ToolResult(BaseModel):
    """工具执行结果标准格式"""
    success: bool = Field(..., description="是否执行成功")
    message: Optional[str] = Field(None, description="执行消息")
    error: Optional[str] = Field(None, description="错误信息")
    data: Any = Field(None, description="返回数据")

    @classmethod
    def success_result(cls, message: str, data: Any = None) -> "ToolResult":
        """创建成功结果"""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_result(cls, error: str) -> "ToolResult":
        """创建失败结果"""
        return cls(success=False, error=error)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump(exclude_none=True)


class BaseAgentTool(LangChainBaseTool):
    """
    Agent工具基类

    继承此类以创建新工具，需要实现：
    - name: 工具名称
    - description: 工具描述
    - execute: 实际执行逻辑

    可选配置：
    - category: 工具分类
    - parameters: 参数定义
    - requires_confirmation: 是否需要用户确认
    - backend_name: 关联的后端名称（用于多后端支持）
    """

    # 工具元数据
    category: str = "general"
    parameters: List[ToolParameter] = []
    requires_confirmation: bool = False

    # 后端配置
    backend_name: str = "default"  # 关联的后端名称

    # LangChain要求的属性
    return_direct: bool = False

    def __init__(self, **data):
        """初始化工具，自动生成 args_schema"""
        super().__init__(**data)
        # 动态生成 args_schema（LangChain 需要这个来生成工具调用的参数模式）
        # 即使是无参数工具也需要设置空的 args_schema
        self.args_schema = _create_args_schema(self.name, self.parameters)

    def get_backend_url(self) -> Optional[str]:
        """获取关联后端的URL"""
        backend = backend_registry.get(self.backend_name)
        if backend:
            return backend.url
        # 兼容：尝试获取默认后端
        default_backend = backend_registry.get("drone")
        return default_backend.url if default_backend else None

    def get_backend_timeout(self) -> float:
        """获取关联后端的超时时间"""
        backend = backend_registry.get(self.backend_name)
        return backend.timeout if backend else 10.0

    async def http_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        通用HTTP请求方法

        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点路径 (如 /api/drone/takeoff)
            json_data: JSON请求体
            params: URL查询参数
            timeout: 超时时间（秒），默认使用后端配置的超时时间

        Returns:
            响应数据字典，包含 success, data, status_code, error 等字段
        """
        base_url = self.get_backend_url()
        if not base_url:
            return {"success": False, "error": f"后端 '{self.backend_name}' 未配置"}

        url = f"{base_url}{endpoint}"
        timeout = timeout or self.get_backend_timeout()

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    json=json_data,
                    params=params
                )

                result = {
                    "success": 200 <= response.status_code < 300,
                    "status_code": response.status_code,
                }

                # 尝试解析JSON响应
                try:
                    result["data"] = response.json()
                except:
                    result["data"] = response.text

                if not result["success"]:
                    result["error"] = f"HTTP {response.status_code}: {response.text}"

                return result

        except httpx.TimeoutException:
            return {"success": False, "error": f"连接后端超时 ({timeout}秒)"}
        except httpx.ConnectError:
            return {"success": False, "error": f"无法连接到后端: {base_url}"}
        except Exception as e:
            return {"success": False, "error": f"请求异常: {str(e)}"}

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        实际执行逻辑（子类必须实现）

        Args:
            **kwargs: 工具参数

        Returns:
            执行结果字典，格式：
            {
                "success": bool,
                "message": str,  # 成功时的消息
                "error": str,    # 失败时的错误信息
                "data": Any      # 可选的附加数据
            }
        """
        raise NotImplementedError("Subclass must implement execute() method")

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """同步执行入口（LangChain调用）"""
        import asyncio

        logger.info(f"Executing tool: {self.name} with params: {kwargs}")

        try:
            result = asyncio.run(self.execute(**kwargs))
            return self._format_result(result)
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {str(e)}", exc_info=True)
            return self._format_result({
                "success": False,
                "error": f"执行失败: {str(e)}"
            })

    async def _arun(
        self,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
        **kwargs
    ) -> str:
        """异步执行入口（LangChain调用）- 带去重缓存"""
        global _tool_call_cache

        # 生成调用哈希（工具名 + 参数）
        call_key = f"{self.name}:{json.dumps(kwargs, sort_keys=True, default=str)}"
        call_hash = hashlib.md5(call_key.encode()).hexdigest()

        current_time = time.time()

        # 清理过期缓存
        expired_keys = [
            k for k, (ts, _) in _tool_call_cache.items()
            if current_time - ts > CACHE_EXPIRY_SECONDS
        ]
        for k in expired_keys:
            del _tool_call_cache[k]

        # 检查是否有重复调用
        if call_hash in _tool_call_cache:
            cached_time, cached_result = _tool_call_cache[call_hash]
            time_diff = current_time - cached_time
            logger.warning(
                f"========== DUPLICATE TOOL CALL BLOCKED: {self.name} ==========\n"
                f"Same call was made {time_diff:.2f}s ago. Returning cached result."
            )
            return cached_result

        logger.info(f"========== TOOL CALL: {self.name} ==========")
        logger.info(f"Params: {kwargs}")

        try:
            result = await self.execute(**kwargs)
            formatted_result = self._format_result(result)

            # 缓存结果
            _tool_call_cache[call_hash] = (current_time, formatted_result)

            logger.info(f"========== TOOL DONE: {self.name} - Success: {result.get('success')} ==========")
            return formatted_result
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {str(e)}", exc_info=True)
            error_result = self._format_result({
                "success": False,
                "error": f"执行失败: {str(e)}"
            })
            # 错误结果也缓存，防止重复错误调用
            _tool_call_cache[call_hash] = (current_time, error_result)
            return error_result

    def _format_result(self, result: Dict[str, Any]) -> str:
        """格式化返回结果为字符串"""
        if result.get("success"):
            message = result.get("message", "执行成功")
            data = result.get("data")

            if data:
                return f"✅ {message}\n数据: {data}"
            return f"✅ {message}"
        else:
            error = result.get("error", "执行失败")
            return f"❌ {error}"

    def get_parameters_schema(self) -> Dict[str, Any]:
        """获取参数schema（用于API文档）"""
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param in self.parameters:
            schema["properties"][param.name] = {
                "type": param.type,
                "description": param.description
            }

            if param.default is not None:
                schema["properties"][param.name]["default"] = param.default

            if param.enum:
                schema["properties"][param.name]["enum"] = param.enum

            if param.required:
                schema["required"].append(param.name)

        return schema

    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """验证参数"""
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return False, f"缺少必需参数: {param.name}"

            if param.name in kwargs and param.enum:
                if kwargs[param.name] not in param.enum:
                    return False, f"参数 {param.name} 的值必须是 {param.enum} 之一"

        return True, None

    def get_tool_info(self) -> Dict[str, Any]:
        """获取工具信息"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "backend": self.backend_name,
            "requires_confirmation": self.requires_confirmation,
            "parameters": self.get_parameters_schema()
        }
