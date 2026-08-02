"""LLMClient implementation backed by Azure OpenAI Chat Completions."""

import os

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI

_AZURE_AD_SCOPE = "https://cognitiveservices.azure.com/.default"


class AzureOpenAIClient:
    def __init__(self) -> None:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), _AZURE_AD_SCOPE
        )
        self._client = AzureOpenAI(
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_ad_token_provider=token_provider,
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )
        self._deployment = os.environ["AZURE_OPENAI_DEPLOYMENT"]

    def complete(self, system: str, messages: list[dict]) -> str:
        response = self._client.chat.completions.create(
            model=self._deployment,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return response.choices[0].message.content
