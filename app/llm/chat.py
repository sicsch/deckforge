"""Shared chat-completion execution for the OpenAI-compatible providers."""

import os

from openai import OpenAI

DEFAULT_TIMEOUT_SECONDS = 300.0
_FALSY = {"0", "false", "no", "off"}


def timeout_seconds() -> float:
    """Per-request timeout, overridable via LLM_TIMEOUT_SECONDS.

    The SDK default is ten minutes, which turns a stalled request into a
    frozen app. An unparsable or non-positive value falls back to the default
    instead of raising — a typo in `.env` must not break every call.
    """
    try:
        value = float(os.getenv("LLM_TIMEOUT_SECONDS", ""))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def streaming_enabled() -> bool:
    """Whether to stream the answer. On unless LLM_STREAMING says otherwise."""
    return os.getenv("LLM_STREAMING", "1").strip().lower() not in _FALSY


def complete_chat(
    client: OpenAI, model: str, system: str, messages: list[dict]
) -> str:
    """Run one chat completion and return the assembled answer.

    Streams by default. A non-streaming request stays silent — no headers, no
    body — until the answer is generated in full, so long generations (the
    preflight plan, the whole deck) can exceed the response deadline of a
    gateway in between and come back as an HTTP error page instead of an
    answer. Streaming puts headers and the first chunk on the wire within
    seconds. Callers see the same finished string either way.

    `LLM_STREAMING=0` restores the single-response call for gateways that
    buffer server-sent events rather than passing them through.
    """
    payload = [{"role": "system", "content": system}, *messages]
    if not streaming_enabled():
        response = client.chat.completions.create(
            model=model, messages=payload, timeout=timeout_seconds()
        )
        return response.choices[0].message.content or ""

    parts: list[str] = []
    with client.chat.completions.create(
        model=model, messages=payload, stream=True, timeout=timeout_seconds()
    ) as stream:
        for chunk in stream:
            # Content-filter chunks carry no choices at all.
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                parts.append(delta)
    return "".join(parts)
