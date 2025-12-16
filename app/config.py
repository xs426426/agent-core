"""
配置管理模块
使用 pydantic-settings 管理环境变量
支持多后端配置
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import json
import os

# 强制加载 .env 文件到环境变量
load_dotenv(override=True)


class BackendConfig:
    """后端服务配置"""
    def __init__(self, name: str, url: str, description: str = "", timeout: float = 10.0):
        self.name = name
        self.url = url.rstrip('/')  # 移除末尾斜杠
        self.description = description
        self.timeout = timeout

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "timeout": self.timeout
        }


class BackendRegistry:
    """
    后端服务注册表
    管理多个后端服务的配置
    """
    def __init__(self):
        self._backends: Dict[str, BackendConfig] = {}

    def register(self, name: str, url: str, description: str = "", timeout: float = 10.0) -> None:
        """注册一个后端服务"""
        self._backends[name] = BackendConfig(name, url, description, timeout)

    def get(self, name: str) -> Optional[BackendConfig]:
        """获取后端配置"""
        return self._backends.get(name)

    def get_url(self, name: str) -> Optional[str]:
        """获取后端URL"""
        backend = self._backends.get(name)
        return backend.url if backend else None

    def list_backends(self) -> Dict[str, Dict[str, Any]]:
        """列出所有已注册的后端"""
        return {name: config.to_dict() for name, config in self._backends.items()}

    def unregister(self, name: str) -> bool:
        """注销一个后端服务"""
        if name in self._backends:
            del self._backends[name]
            return True
        return False


class Settings(BaseSettings):
    """应用配置"""

    # LLM Configuration
    llm_provider: str = "openai"  # openai, claude, ollama
    llm_model: str = "gpt-4-turbo-preview"
    llm_temperature: float = 0.1  # 降低temperature减少重复调用的随机性

    # Custom API Base URLs (for third-party proxies)
    anthropic_api_base: Optional[str] = None
    openai_api_base: Optional[str] = None

    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Vision Model Configuration (for camera analysis)
    qwen_api_key: Optional[str] = None  # 通义千问VL API Key
    ollama_url: str = "http://localhost:11434"  # 本地Ollama服务地址

    # 默认后端配置（兼容旧配置）
    backend_url: str = "http://localhost:3001"

    # 多后端配置 (JSON格式)
    # 格式: {"drone": {"url": "http://localhost:3001", "description": "无人机后端"}, ...}
    backends_config: Optional[str] = None

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    # Database (Optional)
    database_url: Optional[str] = None

    # Redis (Optional)
    redis_url: Optional[str] = None

    # Security
    api_key: Optional[str] = None
    allowed_origins: list[str] = ["*"]  # 默认允许所有来源，方便嵌入

    # Feature Flags
    enable_tool_confirmation: bool = False
    enable_streaming: bool = True
    max_conversation_history: int = 10  # 减少历史消息，避免错误累积

    # Memory Retention
    memory_retention_days: int = 0  # 设为0：不持久化，关闭后清空

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# 全局配置实例
settings = Settings()

# 全局后端注册表
backend_registry = BackendRegistry()


def init_backends():
    """
    初始化后端注册表
    优先从 backends_config 读取，否则使用默认的 backend_url
    """
    # 注册默认后端（无人机）
    backend_registry.register(
        name="drone",
        url=settings.backend_url,
        description="无人机控制后端",
        timeout=10.0
    )

    # 如果有多后端配置，解析并注册
    if settings.backends_config:
        try:
            backends = json.loads(settings.backends_config)
            for name, config in backends.items():
                if isinstance(config, dict):
                    backend_registry.register(
                        name=name,
                        url=config.get("url", ""),
                        description=config.get("description", ""),
                        timeout=config.get("timeout", 10.0)
                    )
                elif isinstance(config, str):
                    # 简化格式: {"name": "url"}
                    backend_registry.register(name=name, url=config)
        except json.JSONDecodeError:
            pass  # 配置格式错误，忽略


# 初始化后端
init_backends()
