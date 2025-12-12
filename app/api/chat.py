"""
聊天API接口
提供HTTP和WebSocket两种通信方式
优化版：支持前端嵌入和流式响应
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Optional
import uuid
import json

from app.models import ChatRequest, ChatResponse
from app.utils import logger

router = APIRouter()

# Agent实例将在main.py中注入
_agent = None


def set_agent(agent):
    """设置Agent实例"""
    global _agent
    _agent = agent


# ============================================================
# HTTP接口
# ============================================================

@router.post("/chat", response_model=ChatResponse, summary="发送聊天消息")
async def chat(request: ChatRequest):
    """
    HTTP聊天接口

    发送消息给Agent并获取响应。适用于简单的请求-响应场景。

    **前端嵌入示例:**
    ```javascript
    fetch('/api/agent/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            message: '让无人机起飞到2米',
            session_id: 'user-123'
        })
    })
    ```
    """
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    session_id = request.session_id or str(uuid.uuid4())

    logger.info(f"HTTP Chat - Session: {session_id}, Message: {request.message}")

    result = await _agent.chat(
        user_input=request.message,
        session_id=session_id,
        metadata=request.metadata
    )

    return ChatResponse(
        success=result["success"],
        response=result.get("response", result.get("error", "未知错误")),
        session_id=session_id,
        intermediate_steps=result.get("intermediate_steps", []),
        error=result.get("error")
    )


@router.post("/chat/simple", summary="简化聊天接口")
async def chat_simple(message: str, session_id: Optional[str] = None):
    """
    简化的聊天接口

    直接通过查询参数发送消息，返回纯文本响应。
    适用于简单集成场景。

    **使用示例:**
    ```
    POST /api/agent/chat/simple?message=查询无人机状态&session_id=test
    ```
    """
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    session_id = session_id or str(uuid.uuid4())

    result = await _agent.chat(
        user_input=message,
        session_id=session_id
    )

    if result["success"]:
        return {"reply": result["response"], "session_id": session_id}
    else:
        return {"reply": result.get("error", "处理失败"), "session_id": session_id, "error": True}


# ============================================================
# WebSocket接口
# ============================================================

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket聊天接口

    建立WebSocket连接进行实时双向通信。

    **前端嵌入示例:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/agent/ws/chat/user-123');

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        switch(data.type) {
            case 'status': console.log('状态:', data.message); break;
            case 'response': console.log('回复:', data.message); break;
            case 'tool_call': console.log('工具调用:', data.tool); break;
            case 'error': console.error('错误:', data.message); break;
        }
    };

    ws.send(JSON.stringify({message: '让无人机起飞'}));
    ```

    **消息格式:**
    - 发送: `{"message": "...", "metadata": {...}}` 或纯文本
    - 接收:
        - `{"type": "connected", "session_id": "..."}` - 连接成功
        - `{"type": "status", "message": "..."}` - 状态消息
        - `{"type": "response", "message": "..."}` - AI响应
        - `{"type": "tool_call", "tool": "...", "result": "..."}` - 工具调用
        - `{"type": "error", "message": "..."}` - 错误消息
    """
    if _agent is None:
        await websocket.close(code=1011, reason="Agent not initialized")
        return

    await websocket.accept()
    logger.info(f"WebSocket connected: session={session_id}")

    # 发送连接成功消息
    await websocket.send_json({
        "type": "connected",
        "session_id": session_id,
        "message": "连接成功"
    })

    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"WebSocket message: session={session_id}, data={data}")

            # 解析消息
            try:
                message_data = json.loads(data)
                message = message_data.get("message", data)
                metadata = message_data.get("metadata", {})
            except json.JSONDecodeError:
                message = data
                metadata = {}

            # 发送思考状态
            await websocket.send_json({
                "type": "status",
                "message": "思考中..."
            })

            # 调用Agent
            result = await _agent.chat(
                user_input=message,
                session_id=session_id,
                metadata=metadata
            )

            # 发送工具调用信息
            for step in result.get("intermediate_steps", []):
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    await websocket.send_json({
                        "type": "tool_call",
                        "tool": action.tool if hasattr(action, 'tool') else "unknown",
                        "params": action.tool_input if hasattr(action, 'tool_input') else {},
                        "result": str(observation)
                    })

            # 发送响应
            if result["success"]:
                await websocket.send_json({
                    "type": "response",
                    "message": result["response"],
                    "session_id": session_id
                })
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": result.get("error", "未知错误"),
                    "session_id": session_id
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: session={session_id}, error={str(e)}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"服务器错误: {str(e)}"
            })
        except:
            pass
        finally:
            await websocket.close()


# ============================================================
# 会话管理接口
# ============================================================

@router.get("/conversations", summary="列出所有会话")
async def list_conversations():
    """列出所有活跃的会话ID"""
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    conversations = _agent.list_conversations()
    return {
        "count": len(conversations),
        "conversations": conversations
    }


@router.get("/conversations/{session_id}", summary="获取会话历史")
async def get_conversation(session_id: str):
    """获取指定会话的历史记录"""
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    conversation = _agent.get_conversation(session_id)

    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {
        "session_id": conversation.session_id,
        "message_count": len(conversation.messages),
        "messages": [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in conversation.messages
        ],
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat()
    }


@router.delete("/conversations/{session_id}", summary="删除会话")
async def delete_conversation(session_id: str):
    """删除指定会话"""
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    success = _agent.delete_conversation(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"message": "Conversation deleted successfully"}


@router.post("/conversations/{session_id}/clear", summary="清空会话历史")
async def clear_conversation(session_id: str):
    """清空指定会话的历史记录（保留会话）"""
    if _agent is None:
        raise HTTPException(status_code=500, detail="Agent not initialized")

    success = _agent.clear_conversation(session_id)

    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"message": "Conversation history cleared successfully"}
