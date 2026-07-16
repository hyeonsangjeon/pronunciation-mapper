"""명시적 provider 선택. Azure 장애 시 Ollama 자동 전환은 하지 않습니다."""

import os
from typing import Any

from ..errors import UnsupportedProviderError
from .azure_foundry import AzureFoundryProvider
from .base import DecisionProvider
from .ollama import OllamaProvider


def create_provider(name: str | None = None, **kwargs: Any) -> DecisionProvider:
    provider_name = (name or os.getenv("PRONUNCIATION_MAPPER_PROVIDER") or "azure").lower().replace("_", "-")
    if provider_name in {"azure", "foundry", "azure-foundry", "microsoft-foundry"}:
        return AzureFoundryProvider(**kwargs)
    if provider_name in {"ollama", "local"}:
        return OllamaProvider(**kwargs)
    if provider_name in {"openai", "anthropic", "claude"}:
        raise UnsupportedProviderError(
            f"{provider_name} is reference-only in V2; choose 'azure' or 'ollama'"
        )
    raise UnsupportedProviderError(f"unsupported provider: {provider_name}")
