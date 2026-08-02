"""LLMClient implementation backed by Azure OpenAI Chat Completions."""

import os

from openai import AzureOpenAI


class AzureOpenAIClient:
    def __init__(self) -> None:
        self._client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
        self._deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    def complete(self, system: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return response.choices[0].message.content
