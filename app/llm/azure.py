"""LLMClient implementation backed by Azure OpenAI Chat Completions."""

import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI


class AzureOpenAIClient:
    def __init__(self) -> None:
        scope = os.environ.get(
            "AZURE_AD_SCOPE", "https://cognitiveservices.azure.com/.default"
        )
        token_provider = get_bearer_token_provider(DefaultAzureCredential(), scope)
        endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        self._client = OpenAI(
            base_url=f"{endpoint}/openai/v1",
            api_key=token_provider,
        )
        self._deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    def complete(self, system: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return response.choices[0].message.content
