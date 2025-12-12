"""
对话数据模型
"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class Message(BaseModel):
    """单条消息"""
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None

    class Config:
        use_enum_values = True


class Conversation(BaseModel):
    """对话会话"""
    session_id: str
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = {}

    def add_message(self, role: MessageRole, content: str, **kwargs) -> None:
        """添加消息到对话历史"""
        message = Message(role=role, content=content, **kwargs)
        self.messages.append(message)
        self.updated_at = datetime.now()

    def get_history(self, limit: Optional[int] = None) -> List[Message]:
        """获取对话历史"""
        if limit:
            return self.messages[-limit:]
        return self.messages

    def clear_history(self) -> None:
        """清空对话历史"""
        self.messages = []
        self.updated_at = datetime.now()


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., description="用户输入消息")
    session_id: Optional[str] = Field(None, description="会话ID，不提供则自动生成")
    metadata: dict = Field(default_factory=dict, description="附加元数据")


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool
    response: str
    session_id: str
    intermediate_steps: List[dict] = []
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
