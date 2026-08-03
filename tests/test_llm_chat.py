from types import SimpleNamespace

import pytest

from app.llm.chat import DEFAULT_TIMEOUT_SECONDS, complete_chat


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Neither switch may leak in from the developer's environment."""
    monkeypatch.delenv("LLM_STREAMING", raising=False)
    monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)


def _chunk(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content))]
    )


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.closed = True
        return False

    def __iter__(self):
        return iter(self._chunks)


def _response(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


class _FakeCompletions:
    def __init__(self, result):
        self._result = result
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self._result


class _FakeClient:
    def __init__(self, result):
        self.completions = _FakeCompletions(result)
        self.chat = SimpleNamespace(completions=self.completions)


def test_streaming_is_the_default_and_assembles_the_answer():
    stream = _FakeStream([_chunk("<html>"), _chunk("Hallo"), _chunk("</html>")])
    client = _FakeClient(stream)

    answer = complete_chat(
        client, "model-x", "SYSTEM", [{"role": "user", "content": "hi"}]
    )

    assert answer == "<html>Hallo</html>"
    assert client.completions.kwargs["stream"] is True
    assert stream.closed


def test_chunks_without_content_are_skipped():
    stream = _FakeStream(
        [
            SimpleNamespace(choices=[]),
            _chunk(None),
            _chunk("Text"),
        ]
    )
    client = _FakeClient(stream)

    assert complete_chat(client, "model-x", "SYSTEM", []) == "Text"


def test_system_prompt_is_prepended_to_the_messages():
    client = _FakeClient(_FakeStream([_chunk("ok")]))

    complete_chat(client, "model-x", "SYSTEM", [{"role": "user", "content": "hi"}])

    assert client.completions.kwargs["messages"] == [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "hi"},
    ]
    assert client.completions.kwargs["model"] == "model-x"


def test_streaming_off_takes_the_single_response_path(monkeypatch):
    monkeypatch.setenv("LLM_STREAMING", "0")
    client = _FakeClient(_response("Antwort"))

    assert complete_chat(client, "model-x", "SYSTEM", []) == "Antwort"
    assert "stream" not in client.completions.kwargs


def test_empty_answer_becomes_an_empty_string(monkeypatch):
    monkeypatch.setenv("LLM_STREAMING", "0")
    client = _FakeClient(_response(None))

    assert complete_chat(client, "model-x", "SYSTEM", []) == ""


def test_request_carries_the_default_timeout():
    client = _FakeClient(_FakeStream([_chunk("ok")]))

    complete_chat(client, "model-x", "SYSTEM", [])

    assert client.completions.kwargs["timeout"] == DEFAULT_TIMEOUT_SECONDS


def test_timeout_override_reaches_the_request(monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "42")
    client = _FakeClient(_FakeStream([_chunk("ok")]))

    complete_chat(client, "model-x", "SYSTEM", [])

    assert client.completions.kwargs["timeout"] == 42.0


@pytest.mark.parametrize("value", ["", "abc", "0", "-1"])
def test_unusable_timeout_falls_back_to_the_default(monkeypatch, value):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", value)
    client = _FakeClient(_FakeStream([_chunk("ok")]))

    complete_chat(client, "model-x", "SYSTEM", [])

    assert client.completions.kwargs["timeout"] == DEFAULT_TIMEOUT_SECONDS
