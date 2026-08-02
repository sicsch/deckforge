import pytest

from app.llm.client import get_client


@pytest.fixture(autouse=True)
def _stub_azure_credential(monkeypatch):
    """Azure tests must not perform real Entra ID auth."""
    monkeypatch.setattr("app.llm.azure.DefaultAzureCredential", lambda: object())
    monkeypatch.setattr(
        "app.llm.azure.get_bearer_token_provider",
        lambda credential, scope: lambda: "test-token",
    )


def test_get_client_dispatches_to_azure(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "azure")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

    from app.llm.azure import AzureOpenAIClient

    assert isinstance(get_client(), AzureOpenAIClient)


def test_get_client_dispatches_to_anthropic(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    from app.llm.anthropic import AnthropicClient

    assert isinstance(get_client(), AnthropicClient)


def test_get_client_defaults_to_azure_when_unset(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

    from app.llm.azure import AzureOpenAIClient

    assert isinstance(get_client(), AzureOpenAIClient)


def test_get_client_raises_on_unknown_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "bogus")

    with pytest.raises(ValueError, match="bogus"):
        get_client()
