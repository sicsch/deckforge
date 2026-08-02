"""Provider abstraction for the LLM backend."""

import os
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, system: str, messages: list[dict]) -> str: ...


def get_client() -> LLMClient:
    """Return the LLMClient implementation selected via LLM_PROVIDER."""
    provider = os.getenv("LLM_PROVIDER", "azure")
    if provider == "azure":
        from app.llm.azure import AzureOpenAIClient

        return AzureOpenAIClient()
    elif provider == "anthropic":
        from app.llm.anthropic import AnthropicClient

        return AnthropicClient()
    raise ValueError(f"Unbekannter Provider: {provider}")
