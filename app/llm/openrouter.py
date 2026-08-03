"""LLMClient implementation backed by OpenRouter (OpenAI-compatible API)."""

import os

from openai import OpenAI

from .chat import complete_chat

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    def __init__(self) -> None:
        self._client = OpenAI(
            base_url=_OPENROUTER_BASE_URL,
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
        self._model = os.environ["OPENROUTER_MODEL"]

    def complete(self, system: str, messages: list[dict]) -> str:
        return complete_chat(self._client, self._model, system, messages)
