"""
LLM引擎适配器
支持多种LLM提供商: OpenAI, Claude, Ollama
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_community.llms import Ollama
from app.config import settings
from app.utils import logger


class LLMEngine:
    """LLM引擎管理类"""

    @staticmethod
    def create_llm(
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        **kwargs
    ):
        """
        创建LLM实例

        Args:
            provider: LLM提供商 (openai/claude/ollama)
            model: 模型名称
            temperature: 温度参数
            **kwargs: 其他参数

        Returns:
            LLM实例

        Raises:
            ValueError: 不支持的提供商
        """
        provider = provider or settings.llm_provider
        model = model or settings.llm_model
        temperature = temperature if temperature is not None else settings.llm_temperature

        logger.info(f"Creating LLM: provider={provider}, model={model}, temperature={temperature}")

        if provider == "openai":
            return LLMEngine._create_openai(model, temperature, **kwargs)
        elif provider == "claude":
            return LLMEngine._create_claude(model, temperature, **kwargs)
        elif provider == "ollama":
            return LLMEngine._create_ollama(model, temperature, **kwargs)
        else:
            raise ValueError(
                f"Unsupported LLM provider: {provider}. "
                f"Supported providers: openai, claude, ollama"
            )

    @staticmethod
    def _create_openai(model: str, temperature: float, **kwargs):
        """创建OpenAI LLM (也支持DeepSeek等兼容API)"""
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        params = {
            "model": model,
            "temperature": temperature,
            "openai_api_key": settings.openai_api_key,
        }

        # 如果配置了自定义API端点（DeepSeek等兼容服务）
        if settings.openai_api_base:
            params["openai_api_base"] = settings.openai_api_base
            logger.info(f"Using custom OpenAI API base: {settings.openai_api_base}")

        params.update(kwargs)
        return ChatOpenAI(**params)

    @staticmethod
    def _create_claude(model: str, temperature: float, **kwargs):
        """创建Claude LLM"""
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY not configured")

        # 构建参数
        claude_params = {
            "model": model,
            "temperature": temperature,
            "anthropic_api_key": settings.anthropic_api_key,
        }

        # 如果配置了自定义API端点（第三方代理）
        if settings.anthropic_api_base:
            claude_params["anthropic_api_url"] = settings.anthropic_api_base
            logger.info(f"Using custom Anthropic API base: {settings.anthropic_api_base}")

        # 合并额外参数
        claude_params.update(kwargs)

        return ChatAnthropic(**claude_params)

    @staticmethod
    def _create_ollama(model: str, temperature: float, **kwargs):
        """创建Ollama LLM (本地模型)"""
        return Ollama(
            model=model,
            temperature=temperature,
            **kwargs
        )

    @staticmethod
    def get_default_llm():
        """获取默认LLM实例"""
        return LLMEngine.create_llm()
