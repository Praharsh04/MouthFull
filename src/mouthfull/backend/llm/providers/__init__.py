"""LLM Providers package.

Registers and exports all available LLM provider implementations.
"""

from __future__ import annotations

from mouthfull.backend.llm.llamacpp_llm import LlamaCppLLM
from mouthfull.backend.llm.providers.anthropic import AnthropicProvider
from mouthfull.backend.llm.providers.custom import CustomAPIProvider
from mouthfull.backend.llm.providers.gemini import GeminiProvider
from mouthfull.backend.llm.providers.ollama import OllamaProvider
from mouthfull.backend.llm.providers.openai import OpenAIProvider
from mouthfull.backend.llm.providers.openrouter import OpenRouterProvider

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
