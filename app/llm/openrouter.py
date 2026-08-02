"""LLMClient implementation backed by OpenRouter (OpenAI-compatible API)."""

import os

from openai import OpenAI

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterClient:
    def __init__(self) -> None:
        self._client = OpenAI(
            base_url=_OPENROUTER_BASE_URL,
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
        self._model = os.environ["OPENROUTER_MODEL"]

    def complete(self, system: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return response.choices[0].message.content
