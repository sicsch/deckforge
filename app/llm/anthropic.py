"""LLMClient implementation backed by the Anthropic Messages API."""

import os

import anthropic


class AnthropicClient:
    def __init__(self) -> None:
        self._client = anthropic.Anthropic()
        self._model = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

    def complete(self, system: str, messages: list[dict]) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=16000,
            system=system,
            messages=messages,
        )
        return next(block.text for block in response.content if block.type == "text")
