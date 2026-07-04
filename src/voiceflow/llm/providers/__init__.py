"""LLM Providers package.

Registers and exports all available LLM provider implementations.
"""

from __future__ import annotations

from voiceflow.llm.llamacpp_llm import LlamaCppLLM
from voiceflow.llm.providers.anthropic import AnthropicProvider
from voiceflow.llm.providers.custom import CustomAPIProvider
from voiceflow.llm.providers.gemini import GeminiProvider
from voiceflow.llm.providers.ollama import OllamaProvider
from voiceflow.llm.providers.openai import OpenAIProvider
from voiceflow.llm.providers.openrouter import OpenRouterProvider

PROVIDERS = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "openrouter": OpenRouterProvider,
    "custom": CustomAPIProvider,
    "llamacpp": LlamaCppLLM,
}

def get_provider(name: str):
    """Retrieve a provider class by name."""
    if name not in PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {name}. Available: {list(PROVIDERS.keys())}")
    return PROVIDERS[name]
