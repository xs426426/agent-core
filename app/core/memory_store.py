"""
持久化记忆存储模块
基于 SQLite 实现会话记忆的持久化存储
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager

from app.models import Message, MessageRole, Conversation
from app.config import settings
from app.utils import logger


class MemoryStore:
    """
    SQLite 持久化记忆存储
    支持会话历史的存储和恢复
    """

    def __init__(self, db_path: str = "data/memory.db"):
        """
        初始化存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # 启动时清理过期会话
        deleted = self.cleanup_expired_conversations()
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired conversations")

        logger.info(f"MemoryStore initialized: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 会话表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}'
                )
            """)

            # 消息表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    tool_calls TEXT,
                    tool_call_id TEXT,
                    FOREIGN KEY (session_id) REFERENCES conversations(session_id)
                )
            """)

            # 索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id, timestamp)
            """)

    def save_conversation(self, conversation: Conversation) -> None:
        """
        保存整个会话

        Args:
            conversation: 会话对象
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 插入或更新会话
            cursor.execute("""
                INSERT OR REPLACE INTO conversations
                (session_id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                conversation.session_id,
                conversation.created_at.isoformat(),
                conversation.updated_at.isoformat(),
                json.dumps(conversation.metadata)
            ))

            # 删除旧消息
            cursor.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (conversation.session_id,)
            )

            # 插入所有消息
            for msg in conversation.messages:
                cursor.execute("""
                    INSERT INTO messages
                    (session_id, role, content, timestamp, tool_calls, tool_call_id)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    conversation.session_id,
                    msg.role.value if isinstance(msg.role, MessageRole) else msg.role,
                    msg.content,
                    msg.timestamp.isoformat(),
                    json.dumps(msg.tool_calls) if msg.tool_calls else None,
                    msg.tool_call_id
                ))

    def save_message(self, session_id: str, message: Message) -> None:
        """
        保存单条消息（增量保存）

        Args:
            session_id: 会话ID
            message: 消息对象
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 确保会话存在
            cursor.execute(
                "SELECT session_id FROM conversations WHERE session_id = ?",
                (session_id,)
            )
            if not cursor.fetchone():
                now = datetime.now().isoformat()
                cursor.execute("""
                    INSERT INTO conversations (session_id, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, '{}')
                """, (session_id, now, now))

            # 插入消息
            cursor.execute("""
                INSERT INTO messages
                (session_id, role, content, timestamp, tool_calls, tool_call_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                message.role.value if isinstance(message.role, MessageRole) else message.role,
                message.content,
                message.timestamp.isoformat(),
                json.dumps(message.tool_calls) if message.tool_calls else None,
                message.tool_call_id
            ))

            # 更新会话时间
            cursor.execute("""
                UPDATE conversations SET updated_at = ? WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))

    def load_conversation(self, session_id: str) -> Optional[Conversation]:
        """
        加载会话

        Args:
            session_id: 会话ID

        Returns:
            会话对象，不存在则返回 None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 查询会话
            cursor.execute(
                "SELECT * FROM conversations WHERE session_id = ?",
                (session_id,)
            )
            conv_row = cursor.fetchone()
            if not conv_row:
                return None

            # 查询消息
            cursor.execute("""
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY timestamp ASC
            """, (session_id,))
            msg_rows = cursor.fetchall()

            # 构建消息列表
            messages = []
            for row in msg_rows:
                msg = Message(
                    role=MessageRole(row['role']),
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    tool_calls=json.loads(row['tool_calls']) if row['tool_calls'] else None,
                    tool_call_id=row['tool_call_id']
                )
                messages.append(msg)

            # 构建会话对象
            conversation = Conversation(
                session_id=session_id,
                messages=messages,
                created_at=datetime.fromisoformat(conv_row['created_at']),
                updated_at=datetime.fromisoformat(conv_row['updated_at']),
                metadata=json.loads(conv_row['metadata'])
            )

            return conversation

    def delete_conversation(self, session_id: str) -> bool:
        """
        删除会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功删除
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,)
            )
            cursor.execute(
                "DELETE FROM conversations WHERE session_id = ?",
                (session_id,)
            )
            return cursor.rowcount > 0

    def clear_conversation(self, session_id: str) -> bool:
        """
        清空会话消息（保留会话记录）

        Args:
            session_id: 会话ID

        Returns:
            是否成功清空
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM messages WHERE session_id = ?",
                (session_id,)
            )
            cursor.execute("""
                UPDATE conversations SET updated_at = ? WHERE session_id = ?
            """, (datetime.now().isoformat(), session_id))
            return True

    def list_conversations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        列出所有会话

        Args:
            limit: 最大返回数量

        Returns:
            会话列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.session_id, c.created_at, c.updated_at,
                       COUNT(m.id) as message_count
                FROM conversations c
                LEFT JOIN messages m ON c.session_id = m.session_id
                GROUP BY c.session_id
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (limit,))

            return [dict(row) for row in cursor.fetchall()]

    def get_recent_messages(
        self,
        session_id: str,
        limit: int = 50
    ) -> List[Message]:
        """
        获取最近的消息

        Args:
            session_id: 会话ID
            limit: 消息数量限制

        Returns:
            消息列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))

            messages = []
            for row in reversed(cursor.fetchall()):
                msg = Message(
                    role=MessageRole(row['role']),
                    content=row['content'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    tool_calls=json.loads(row['tool_calls']) if row['tool_calls'] else None,
                    tool_call_id=row['tool_call_id']
                )
                messages.append(msg)

            return messages

    def cleanup_expired_conversations(self, retention_days: int = None) -> int:
        """
        清理超过保留期限的会话

        Args:
            retention_days: 保留天数，默认使用配置值

        Returns:
            删除的会话数量
        """
        if retention_days is None:
            retention_days = settings.memory_retention_days

        cutoff_date = (datetime.now() - timedelta(days=retention_days)).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 查找过期会话
            cursor.execute("""
                SELECT session_id FROM conversations
                WHERE updated_at < ?
            """, (cutoff_date,))

            expired_sessions = [row['session_id'] for row in cursor.fetchall()]

            if not expired_sessions:
                return 0

            # 删除过期会话的消息
            for session_id in expired_sessions:
                cursor.execute(
                    "DELETE FROM messages WHERE session_id = ?",
                    (session_id,)
                )

            # 删除过期会话
            cursor.execute("""
                DELETE FROM conversations WHERE updated_at < ?
            """, (cutoff_date,))

            deleted_count = len(expired_sessions)
            logger.info(
                f"Deleted {deleted_count} expired conversations "
                f"(older than {retention_days} days)"
            )

            return deleted_count


# 全局实例
memory_store = MemoryStore()
