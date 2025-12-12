"""
工具调度器
负责工具的注册、管理和调度
"""
from typing import List, Dict, Optional
from langchain.tools import BaseTool
from app.utils import logger


class ToolOrchestrator:
    """工具调度器"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}
        logger.info("ToolOrchestrator initialized")

    def register_tool(self, tool: BaseTool) -> None:
        """
        注册工具

        Args:
            tool: 工具实例
        """
        tool_name = tool.name
        if tool_name in self._tools:
            logger.warning(f"Tool {tool_name} already registered, overwriting")

        self._tools[tool_name] = tool

        # 按类别分组
        category = getattr(tool, "category", "general")
        if category not in self._categories:
            self._categories[category] = []
        if tool_name not in self._categories[category]:
            self._categories[category].append(tool_name)

        logger.info(f"Registered tool: {tool_name} (category: {category})")

    def register_tools(self, tools: List[BaseTool]) -> None:
        """批量注册工具"""
        for tool in tools:
            self.register_tool(tool)

    def unregister_tool(self, tool_name: str) -> bool:
        """
        注销工具

        Args:
            tool_name: 工具名称

        Returns:
            是否成功注销
        """
        if tool_name in self._tools:
            tool = self._tools[tool_name]
            category = getattr(tool, "category", "general")

            del self._tools[tool_name]
            if category in self._categories:
                self._categories[category].remove(tool_name)

            logger.info(f"Unregistered tool: {tool_name}")
            return True

        logger.warning(f"Tool {tool_name} not found")
        return False

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取单个工具"""
        return self._tools.get(tool_name)

    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """获取指定类别的工具"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def list_tools(self) -> Dict[str, Dict]:
        """
        列出所有工具信息

        Returns:
            工具信息字典
        """
        tools_info = {}
        for name, tool in self._tools.items():
            tools_info[name] = {
                "name": name,
                "description": tool.description,
                "category": getattr(tool, "category", "general"),
                "parameters": getattr(tool, "parameters", [])
            }
        return tools_info

    def list_categories(self) -> Dict[str, int]:
        """
        列出所有类别及其工具数量

        Returns:
            类别统计字典
        """
        return {
            category: len(tools)
            for category, tools in self._categories.items()
        }

    def clear_tools(self) -> None:
        """清空所有工具"""
        self._tools.clear()
        self._categories.clear()
        logger.info("All tools cleared")

    def __len__(self) -> int:
        """返回工具数量"""
        return len(self._tools)

    def __contains__(self, tool_name: str) -> bool:
        """检查工具是否存在"""
        return tool_name in self._tools
