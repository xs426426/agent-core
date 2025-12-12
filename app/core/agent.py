"""
智能体核心引擎
基于 LangGraph 构建的通用 Agent
使用 create_react_agent 支持 OpenAI 兼容 API (如 DeepSeek)
"""
from typing import List, Dict, Any, Optional
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import BaseTool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.llm_engine import LLMEngine
from app.core.tool_orchestrator import ToolOrchestrator
from app.core.memory_store import MemoryStore
from app.models import Conversation, MessageRole, Message
from app.config import settings
from app.utils import logger


class IntelligentAgent:
    """
    通用智能体核心类
    可扩展、可移植、独立运行
    """

    # 系统提示词
    SYSTEM_PROMPT = """你是一个智能无人机控制助手。你可以理解自然语言指令并通过调用工具来控制无人机。

重要规则：
1. 当用户请求查询无人机状态时，你必须调用 get_drone_status 工具
2. 当用户请求起飞时，你必须调用 drone_takeoff 工具
3. 当用户请求降落时，你必须调用 drone_land 工具
4. 不要编造任何数据，所有信息必须来自工具调用的返回结果
5. 如果工具调用失败，请告诉用户实际的错误信息

请根据用户的请求选择合适的工具并执行。
"""

    def __init__(
        self,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tools: Optional[List[BaseTool]] = None,
        max_iterations: int = 10
    ):
        """
        初始化智能体

        Args:
            llm_provider: LLM提供商
            model: 模型名称
            temperature: 温度参数
            tools: 初始工具列表
            max_iterations: 最大迭代次数
        """
        logger.info("Initializing IntelligentAgent...")

        # 初始化LLM
        self.llm = LLMEngine.create_llm(
            provider=llm_provider,
            model=model,
            temperature=temperature
        )

        # 初始化工具调度器
        self.tool_orchestrator = ToolOrchestrator()

        # 注册初始工具
        if tools:
            self.tool_orchestrator.register_tools(tools)

        # 会话管理（内存缓存）
        self.conversations: Dict[str, Conversation] = {}

        # 持久化存储
        self.memory_store = MemoryStore()

        # Agent配置
        self.max_iterations = max_iterations

        # 创建Agent
        self.agent = self._create_agent()

        logger.info(
            f"IntelligentAgent initialized with {len(self.tool_orchestrator)} tools"
        )

    def _create_agent(self):
        """创建 LangGraph React Agent"""
        tools = self.tool_orchestrator.get_all_tools()

        # 使用 langgraph 的 create_react_agent
        agent = create_react_agent(
            model=self.llm,
            tools=tools,
            prompt=self.SYSTEM_PROMPT
        )

        return agent

    def _get_or_create_conversation(self, session_id: str) -> Conversation:
        """获取或创建对话会话（优先从持久化存储加载）"""
        # 先检查内存缓存
        if session_id in self.conversations:
            return self.conversations[session_id]

        # 尝试从数据库加载
        conversation = self.memory_store.load_conversation(session_id)
        if conversation:
            self.conversations[session_id] = conversation
            logger.info(f"Loaded conversation from storage: {session_id}")
            return conversation

        # 创建新会话
        conversation = Conversation(session_id=session_id)
        self.conversations[session_id] = conversation
        logger.info(f"Created new conversation: {session_id}")
        return conversation

    def _format_messages(self, conversation: Conversation) -> List:
        """格式化对话历史为消息列表"""
        messages = []
        for msg in conversation.get_history(limit=settings.max_conversation_history):
            if msg.role == MessageRole.USER:
                messages.append(HumanMessage(content=msg.content))
            elif msg.role == MessageRole.ASSISTANT:
                messages.append(AIMessage(content=msg.content))
        return messages

    async def chat(
        self,
        user_input: str,
        session_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入（异步）

        Args:
            user_input: 用户输入消息
            session_id: 会话ID
            metadata: 附加元数据

        Returns:
            包含响应和执行信息的字典
        """
        logger.info(f"[{session_id}] User: {user_input}")

        try:
            # 获取对话会话
            conversation = self._get_or_create_conversation(session_id)

            # 添加用户消息到历史
            user_message = Message(role=MessageRole.USER, content=user_input)
            conversation.add_message(MessageRole.USER, user_input)

            # 持久化保存用户消息
            self.memory_store.save_message(session_id, user_message)

            # 构建消息列表
            messages = self._format_messages(conversation)
            # 添加当前消息
            messages.append(HumanMessage(content=user_input))

            # 调用 Agent
            result = await self.agent.ainvoke({"messages": messages})

            # 提取响应
            response_messages = result.get("messages", [])
            response_text = "抱歉，我无法处理这个请求。"

            # 获取最后一个 AI 消息作为响应
            for msg in reversed(response_messages):
                if isinstance(msg, AIMessage) and msg.content:
                    response_text = msg.content
                    break

            # 添加助手响应到历史
            assistant_message = Message(role=MessageRole.ASSISTANT, content=response_text)
            conversation.add_message(MessageRole.ASSISTANT, response_text)

            # 持久化保存助手响应
            self.memory_store.save_message(session_id, assistant_message)

            logger.info(f"[{session_id}] Assistant: {response_text}")

            return {
                "success": True,
                "response": response_text,
                "session_id": session_id,
                "intermediate_steps": []
            }

        except Exception as e:
            error_msg = f"处理消息时发生错误: {str(e)}"
            logger.error(f"[{session_id}] Error: {error_msg}", exc_info=True)

            return {
                "success": False,
                "error": error_msg,
                "session_id": session_id,
                "intermediate_steps": []
            }

    def chat_sync(
        self,
        user_input: str,
        session_id: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        处理用户输入（同步版本，用于非异步环境）

        Args:
            user_input: 用户输入消息
            session_id: 会话ID
            metadata: 附加元数据

        Returns:
            包含响应和执行信息的字典
        """
        import asyncio
        return asyncio.run(self.chat(user_input, session_id, metadata))

    def register_tool(self, tool: BaseTool) -> None:
        """
        动态注册新工具

        Args:
            tool: 工具实例
        """
        self.tool_orchestrator.register_tool(tool)
        # 重建Agent以包含新工具
        self.agent = self._create_agent()
        logger.info(f"Tool registered and agent rebuilt: {tool.name}")

    def register_tools(self, tools: List[BaseTool]) -> None:
        """批量注册工具"""
        for tool in tools:
            self.register_tool(tool)

    def unregister_tool(self, tool_name: str) -> bool:
        """注销工具"""
        result = self.tool_orchestrator.unregister_tool(tool_name)
        if result:
            self.agent = self._create_agent()
            logger.info(f"Tool unregistered and agent rebuilt: {tool_name}")
        return result

    def get_tools(self) -> Dict[str, Dict]:
        """获取所有工具信息"""
        return self.tool_orchestrator.list_tools()

    def get_conversation(self, session_id: str) -> Optional[Conversation]:
        """获取对话会话"""
        return self.conversations.get(session_id)

    def clear_conversation(self, session_id: str) -> bool:
        """清空对话历史"""
        if session_id in self.conversations:
            self.conversations[session_id].clear_history()
            # 同步清空数据库
            self.memory_store.clear_conversation(session_id)
            logger.info(f"Cleared conversation: {session_id}")
            return True
        return False

    def delete_conversation(self, session_id: str) -> bool:
        """删除对话会话"""
        if session_id in self.conversations:
            del self.conversations[session_id]
        # 同步删除数据库记录
        result = self.memory_store.delete_conversation(session_id)
        if result:
            logger.info(f"Deleted conversation: {session_id}")
        return result

    def list_conversations(self) -> List[str]:
        """列出所有会话ID（包括持久化的）"""
        # 从数据库获取所有会话
        db_conversations = self.memory_store.list_conversations()
        return [c['session_id'] for c in db_conversations]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_tools": len(self.tool_orchestrator),
            "tool_categories": self.tool_orchestrator.list_categories(),
            "active_conversations": len(self.conversations),
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model
        }
