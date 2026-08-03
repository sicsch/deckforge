import json

import httpx
import layout_css
import openai
import pytest

from app import phases, state


def _fresh_state(monkeypatch, **overrides):
    fake_session_state = dict(state.DEFAULT_STATE)
    fake_session_state.update(overrides)
    monkeypatch.setattr(phases.st, "session_state", fake_session_state)
    return fake_session_state


class _FakeSpinner:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeClient:
    def __init__(self, result=None, error=None):
        self._result = result
        self._error = error
        self.calls = []

    def complete(self, system, messages):
        self.calls.append((system, messages))
        if self._error:
            raise self._error
        return self._result


_FILLED_SETUP = {
    "thema": "T",
    "zielgruppe": "Z",
    "ziel": "G",
    "wirkung": "W",
    "rohinhalte": "R",
}


def _stub_generation_widgets(monkeypatch):
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "subheader", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "file_uploader", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "text_input", lambda label, value, **k: value)
    monkeypatch.setattr(phases.st, "text_area", lambda label, value, **k: value)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())


def test_setup_to_structure_generates_via_llm(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="setup", guideline_md="# Guideline", setup=_FILLED_SETUP
    )
    _stub_generation_widgets(monkeypatch)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    monkeypatch.setattr(phases.st, "error", lambda *a, **k: None)
    monkeypatch.setattr(
        phases, "load_prompt", lambda path, replacements: f"PROMPT::{replacements}"
    )
    fake_client = _FakeClient(result="# Echte Struktur")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    phases.render_sidebar()

    assert session_state["phase"] == "structure"
    assert session_state["structure_md"] == "# Echte Struktur"
    assert session_state["error"] is None
    system_prompt, messages = fake_client.calls[0]
    assert "# Guideline" in system_prompt
    assert "Thema: T" in system_prompt
    assert messages == [{"role": "user", "content": "Erzeuge die Folienarchitektur."}]


def test_structure_generation_error_keeps_setup_phase_and_shows_message(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup", setup=_FILLED_SETUP)
    _stub_generation_widgets(monkeypatch)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    errors = []
    monkeypatch.setattr(phases.st, "error", lambda msg: errors.append(msg))
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(error=RuntimeError("boom"))
    )

    phases.render_sidebar()

    assert session_state["phase"] == "setup"
    assert session_state["structure_md"] is None
    assert session_state["error"] == "boom"
    assert any("boom" in msg for msg in errors)


def test_timeout_error_shows_understandable_message_not_raw_exception(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup", setup=_FILLED_SETUP)
    _stub_generation_widgets(monkeypatch)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    errors = []
    monkeypatch.setattr(phases.st, "error", lambda msg: errors.append(msg))
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    timeout_exc = openai.APITimeoutError(request=httpx.Request("POST", "https://x"))
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(error=timeout_exc))

    phases.render_sidebar()

    assert session_state["error"] == (
        "Zeitüberschreitung beim LLM-Aufruf. Bitte erneut versuchen."
    )
    assert any("Zeitüberschreitung" in msg for msg in errors)


def test_auth_error_shows_understandable_message_not_raw_exception(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup", setup=_FILLED_SETUP)
    _stub_generation_widgets(monkeypatch)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    errors = []
    monkeypatch.setattr(phases.st, "error", lambda msg: errors.append(msg))
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    response = httpx.Response(401, request=httpx.Request("POST", "https://x"))
    auth_exc = openai.AuthenticationError("nope", response=response, body=None)
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(error=auth_exc))

    phases.render_sidebar()

    assert (
        session_state["error"]
        == "Authentifizierung beim LLM-Provider fehlgeschlagen. Bitte erneut versuchen."
    )
    assert any("Authentifizierung" in msg for msg in errors)


_HTML_ERROR_PAGE = (
    "<HTML> <HEAD> <STYLE> table.stat td { font-size: 75% } </STYLE> </HEAD> "
    "<BODY> <TABLE border=0 cellPadding=1 width='80%'> <TR> <TD>"
    "<FONT face='Helvetica'><big>Keine gültige Antwort innerhalb der Frist"
    "</big></FONT></TD> </TR> </TABLE> </BODY> </HTML>"
)


def _run_setup_with_error(monkeypatch, exc):
    """Trigger one failing structure generation, return (state, shown errors)."""
    session_state = _fresh_state(monkeypatch, phase="setup", setup=_FILLED_SETUP)
    _stub_generation_widgets(monkeypatch)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    errors = []
    monkeypatch.setattr(phases.st, "error", lambda msg: errors.append(msg))
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(error=exc))

    phases.render_sidebar()

    return session_state, errors


def test_html_error_page_is_reduced_to_one_line(monkeypatch):
    response = httpx.Response(
        502, request=httpx.Request("POST", "https://example.invalid")
    )
    exc = openai.InternalServerError(_HTML_ERROR_PAGE, response=response, body=None)

    session_state, errors = _run_setup_with_error(monkeypatch, exc)

    message = session_state["error"]
    assert "HTTP 502" in message
    assert "<" not in message
    assert len(message) < 300
    assert any("HTTP 502" in msg for msg in errors)


def test_status_error_names_the_code_without_the_sdk_prefix(monkeypatch):
    response = httpx.Response(
        400, request=httpx.Request("POST", "https://example.invalid")
    )
    exc = openai.BadRequestError(
        "Error code: 400 - {'error': 'context_length_exceeded'}",
        response=response,
        body=None,
    )

    session_state, _ = _run_setup_with_error(monkeypatch, exc)

    assert session_state["error"] == "HTTP 400: {'error': 'context_length_exceeded'}"


def test_overlong_error_text_is_truncated(monkeypatch):
    session_state, _ = _run_setup_with_error(monkeypatch, RuntimeError("x" * 5000))

    message = session_state["error"]
    assert len(message) < 400
    assert message.endswith("[…]")


def test_retry_after_error_succeeds_without_reload(monkeypatch):
    """A second click in the same session (no reload) after a failed call
    must clear the error and generate the structure normally."""
    session_state = _fresh_state(monkeypatch, phase="setup", setup=_FILLED_SETUP)
    _stub_generation_widgets(monkeypatch)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    monkeypatch.setattr(phases.st, "error", lambda *a, **k: None)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")

    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(error=RuntimeError("boom"))
    )
    phases.render_sidebar()
    assert session_state["phase"] == "setup"
    assert session_state["error"] == "boom"

    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(result="# Struktur nach Retry")
    )
    phases.render_sidebar()

    assert session_state["phase"] == "structure"
    assert session_state["structure_md"] == "# Struktur nach Retry"
    assert session_state["error"] is None


class _FakeUpload:
    def __init__(self, name, content):
        self.name = name
        self._content = content.encode("utf-8")

    def getvalue(self):
        return self._content


def _stub_uploaders(monkeypatch, guideline=None, tokens=None):
    """Route each `file_uploader` call to its own fake upload, by label."""
    monkeypatch.setattr(
        phases.st,
        "file_uploader",
        lambda label, *a, **k: tokens if "Tokens" in label else guideline,
    )


def test_guideline_upload_fills_state(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    monkeypatch.setattr(phases.st, "success", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "warning", lambda *a, **k: None)
    _stub_uploaders(monkeypatch, guideline=_FakeUpload("guideline.md", "# Guideline"))

    phases.render_sidebar()

    assert session_state["guideline_md"] == "# Guideline"
    assert session_state["guideline_name"] == "guideline.md"


def test_guideline_reupload_overwrites_previous(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="setup",
        guideline_md="# Old",
        guideline_name="old.md",
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    monkeypatch.setattr(phases.st, "success", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "warning", lambda *a, **k: None)
    _stub_uploaders(monkeypatch, guideline=_FakeUpload("new.md", "# New"))

    phases.render_sidebar()

    assert session_state["guideline_md"] == "# New"
    assert session_state["guideline_name"] == "new.md"


def test_guideline_with_tokens_and_headings_reports_detection(monkeypatch):
    guideline = (
        "# Guideline\n\n"
        ":root {\n"
        "  --color-primary: #1A73E8;\n"
        "  --font-body: \"Example Sans\";\n"
        "}\n\n"
        "## Titelfolie\n\n"
        "### Inhaltsfolie\n"
    )
    session_state = _fresh_state(
        monkeypatch, phase="setup", guideline_md=guideline, guideline_name="g.md"
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    monkeypatch.setattr(phases.st, "file_uploader", lambda *a, **k: None)
    warnings = []
    successes = []
    monkeypatch.setattr(phases.st, "warning", lambda msg: warnings.append(msg))
    monkeypatch.setattr(phases.st, "success", lambda msg: successes.append(msg))

    phases.render_sidebar()

    assert not warnings
    assert any("--color-primary" in msg for msg in successes)
    assert any("Titelfolie" in msg for msg in successes)
    # the detected types stay available for the structure iteration (#86)
    assert session_state["slide_types"] == ["Titelfolie", "Inhaltsfolie"]


def test_unstructured_guideline_triggers_warning_but_does_not_block(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="setup",
        guideline_md="Nur Fließtext, keine Struktur.",
        setup=_FILLED_SETUP,
    )
    _stub_generation_widgets(monkeypatch)
    warnings = []
    monkeypatch.setattr(phases.st, "warning", lambda msg: warnings.append(msg))
    monkeypatch.setattr(phases.st, "success", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "error", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(result="# Struktur")
    )

    phases.render_sidebar()

    assert len(warnings) == 2
    assert session_state["phase"] == "structure"


def test_no_upload_keeps_state_untouched(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    monkeypatch.setattr(phases.st, "file_uploader", lambda *a, **k: None)

    phases.render_sidebar()

    assert session_state["guideline_md"] is None
    assert session_state["guideline_name"] is None


def test_setup_form_writes_session_state_and_persists_across_rerun(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "subheader", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "file_uploader", lambda *a, **k: None)
    monkeypatch.setattr(
        phases.st,
        "text_input",
        lambda label, value, **k: "Thema" if "Thema" in label else value,
    )
    monkeypatch.setattr(phases.st, "text_area", lambda *a, **k: "Stichpunkte")
    captured_button_kwargs = {}
    monkeypatch.setattr(
        phases.st,
        "button",
        lambda *a, **k: captured_button_kwargs.update(k) or False,
    )

    phases.render_sidebar()

    assert session_state["setup"]["thema"] == "Thema"
    assert session_state["setup"]["rohinhalte"] == "Stichpunkte"
    # Zielgruppe/Ziel/Wirkung stayed empty -> required fields incomplete
    assert captured_button_kwargs["disabled"] is True


def test_setup_form_enables_button_once_required_fields_filled(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="setup",
        setup={
            "thema": "T",
            "zielgruppe": "Z",
            "ziel": "G",
            "wirkung": "W",
            "rohinhalte": "",
        },
    )
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "subheader", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "file_uploader", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "text_input", lambda label, value, **k: value)
    monkeypatch.setattr(
        phases.st, "text_area", lambda label, value, **k: value
    )
    captured_button_kwargs = {}
    monkeypatch.setattr(
        phases.st,
        "button",
        lambda *a, **k: captured_button_kwargs.update(k) or False,
    )

    phases.render_sidebar()

    assert captured_button_kwargs["disabled"] is False
    assert session_state["setup"]["thema"] == "T"


def test_structure_to_deck_only_after_confirm_click(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="structure", deck_html="<p>Alter Stand</p>"
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)

    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    phases.render_sidebar()
    assert session_state["phase"] == "structure"

    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    phases.render_sidebar()
    assert session_state["phase"] == "deck"
    # generation itself happens on the next render of the deck phase, not here
    assert session_state["deck_html"] is None


def test_deck_phase_auto_generates_html_on_first_render(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html=None,
        structure_md="# Struktur",
        guideline_md="# Guideline",
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    captured_replacements = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured_replacements.append((path, replacements))
        or "PROMPT",
    )
    fake_client = _FakeClient()
    replies = ["# Preflight-Plan", "<html>Deck</html>"]
    fake_client.complete = lambda system, messages: (
        fake_client.calls.append((system, messages))
        or replies[len(fake_client.calls) - 1]
    )
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Deck</html>"
    assert session_state["deck_preflight"] == "# Preflight-Plan"
    assert session_state["error"] is None
    assert session_state["phase"] == "deck"
    path, replacements = captured_replacements[0]
    assert path == phases.HTML_DECK_PROMPT
    assert replacements == {
        phases._GUIDELINE_PLACEHOLDER: "# Guideline",
        phases._LAYOUT_CSS_PLACEHOLDER: phases._NO_LAYOUT_CSS,
        phases._STRUCTURE_BRIEFING_PLACEHOLDER: "# Struktur",
    }
    # Two calls: preflight plan first, then code with that plan in context.
    assert len(fake_client.calls) == 2
    plan_system, plan_messages = fake_client.calls[0]
    assert plan_system == "PROMPT"
    assert plan_messages == [
        {"role": "user", "content": phases._PREFLIGHT_INSTRUCTION}
    ]
    code_system, code_messages = fake_client.calls[1]
    assert code_system == "PROMPT"
    assert code_messages == [
        {"role": "user", "content": phases._PREFLIGHT_INSTRUCTION},
        {"role": "assistant", "content": "# Preflight-Plan"},
        {"role": "user", "content": phases._CODE_INSTRUCTION},
    ]


def test_deck_html_not_regenerated_once_present(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html="<html>Schon da</html>"
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    fake_client = _FakeClient(result="<html>Neu</html>")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Schon da</html>"
    assert fake_client.calls == []


def test_deck_generation_error_reverts_to_structure_phase(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html=None, structure_md="# Struktur"
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(error=RuntimeError("boom"))
    )

    phases.render_sidebar()

    assert session_state["phase"] == "structure"
    assert session_state["deck_html"] is None
    assert session_state["error"] == "boom"
    assert session_state["error_scope"] == "deck_generation"


def test_deck_generation_error_is_not_labelled_as_a_failed_change(monkeypatch):
    """The failure drops back into the structure phase — where a fixed
    "Änderung fehlgeschlagen" would name the wrong step."""
    _fresh_state(monkeypatch, phase="deck", deck_html=None, structure_md="# Struktur")
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(error=RuntimeError("boom"))
    )
    phases.render_sidebar()

    errors = []
    _stub_chat_widgets(monkeypatch, [], errors=errors)
    phases.render_sidebar()

    assert errors == ["Deck-Generierung fehlgeschlagen: boom"]


def _deck_generation_state(monkeypatch, deck_reply):
    """Deck phase about to auto-generate, with the model answering `deck_reply`."""
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html=None, structure_md="# Struktur"
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    fake_client = _FakeClient()
    replies = ["# Preflight-Plan", deck_reply]
    fake_client.complete = lambda system, messages: (
        fake_client.calls.append((system, messages))
        or replies[len(fake_client.calls) - 1]
    )
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)
    return session_state


def test_fenced_generation_answer_is_unwrapped_before_it_becomes_the_deck(monkeypatch):
    session_state = _deck_generation_state(
        monkeypatch, "```html\n<html>Deck</html>\n```"
    )

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Deck</html>"
    assert session_state["error"] is None


def test_generation_answer_with_prose_before_the_fence_is_unwrapped(monkeypatch):
    session_state = _deck_generation_state(
        monkeypatch, "Gern, hier das Deck:\n\n```html\n<html>Deck</html>\n```\n"
    )

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Deck</html>"


def test_generation_answer_without_html_root_errors_instead_of_downloading(monkeypatch):
    session_state = _deck_generation_state(
        monkeypatch, "Ich brauche mehr Informationen zur Zielgruppe."
    )

    phases.render_sidebar()

    assert session_state["deck_html"] is None
    assert "kein HTML-Dokument" in session_state["error"]
    assert session_state["phase"] == "structure"


def _stub_chat_widgets(monkeypatch, chat_inputs, errors=None, css_only=False):
    """Stub chat_input to return each value from `chat_inputs` in turn (None
    after exhaustion), plus the other widgets `_render_structure_sidebar`
    touches. `css_only` is what the deck sidebar's style-only checkbox says."""
    inputs = iter(chat_inputs)
    monkeypatch.setattr(phases.st, "checkbox", lambda *a, **k: css_only)
    monkeypatch.setattr(
        phases.st, "chat_input", lambda *a, **k: next(inputs, None)
    )
    monkeypatch.setattr(phases.st, "chat_message", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    if errors is not None:
        monkeypatch.setattr(phases.st, "error", lambda msg: errors.append(msg))
    else:
        monkeypatch.setattr(phases.st, "error", lambda *a, **k: None)


def test_structure_chat_iteration_updates_structure_and_logs_chat(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="structure",
        structure_md="# Alte Struktur",
        structure_chat=[],
    )
    _stub_chat_widgets(monkeypatch, ["Ändere Folie 3"])
    captured_replacements = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured_replacements.append(replacements)
        or "PROMPT",
    )
    fake_client = _FakeClient(result="# Neue Struktur")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    phases.render_sidebar()

    assert session_state["structure_md"] == "# Neue Struktur"
    assert session_state["error"] is None
    assert session_state["structure_chat"] == [
        {"role": "user", "content": "Ändere Folie 3"},
        {"role": "assistant", "content": "Struktur aktualisiert."},
    ]
    # prompt gets current structure + change request, not full chat history
    assert captured_replacements[0] == {
        phases._STRUCTURE_PLACEHOLDER: "# Alte Struktur",
        phases._CHANGE_REQUEST_PLACEHOLDER: "Ändere Folie 3",
        phases._SLIDE_TYPES_PLACEHOLDER: "",
    }
    system_prompt, messages = fake_client.calls[0]
    assert messages == [{"role": "user", "content": "Ändere Folie 3"}]


def _run_structure_iteration_with_real_template(monkeypatch, slide_types):
    """One structure iteration through the real prompt template — returns the
    system prompt that reached the client. Unstubbed `load_prompt` on purpose,
    so template and code can't drift apart on the new placeholder (#86)."""
    _fresh_state(
        monkeypatch,
        phase="structure",
        structure_md="# Alte Struktur",
        structure_chat=[],
        slide_types=slide_types,
    )
    _stub_chat_widgets(monkeypatch, ["Füg eine Vergleichsfolie ein"])
    fake_client = _FakeClient(result="# Neue Struktur")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    phases.render_sidebar()

    return fake_client.calls[0][0]


def test_structure_iteration_prompt_carries_guideline_slide_types(monkeypatch):
    prompt = _run_structure_iteration_with_real_template(
        monkeypatch, ["Titelfolie", "Vergleichsfolie"]
    )

    assert "Titelfolie, Vergleichsfolie" in prompt
    assert "# Alte Struktur" in prompt
    assert "[HIER" not in prompt


def test_structure_iteration_without_slide_types_leaves_prompt_unchanged(monkeypatch):
    with_types = _run_structure_iteration_with_real_template(
        monkeypatch, ["Titelfolie"]
    )
    without_types = _run_structure_iteration_with_real_template(monkeypatch, [])

    assert "Folientypen der Design-Guideline" not in without_types
    assert "[HIER" not in without_types
    # the extra context is the type line and nothing else
    assert without_types == with_types.replace(
        "Folientypen der Design-Guideline: Titelfolie", ""
    )


def test_structure_chat_three_consecutive_iterations_no_context_loss(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="structure", structure_md="# v1", structure_chat=[]
    )
    requests = ["Änderung 1", "Änderung 2", "Änderung 3"]
    results = iter(["# v2", "# v3", "# v4"])
    fake_client = _FakeClient()
    fake_client.complete = lambda system, messages: (
        fake_client.calls.append((system, messages)) or next(results)
    )
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    for i, request in enumerate(requests):
        _stub_chat_widgets(monkeypatch, [request])
        phases.render_sidebar()
        assert session_state["error"] is None
        # each call's message list holds only the latest request, never prior ones
        assert fake_client.calls[i][1] == [{"role": "user", "content": request}]

    assert session_state["structure_md"] == "# v4"
    assert len(session_state["structure_chat"]) == 6


def test_structure_chat_error_keeps_previous_structure(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="structure",
        structure_md="# Stand vor Fehler",
        structure_chat=[],
    )
    errors = []
    _stub_chat_widgets(monkeypatch, ["kaputte Änderung"], errors=errors)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(error=RuntimeError("boom"))
    )

    phases.render_sidebar()

    assert session_state["structure_md"] == "# Stand vor Fehler"
    assert session_state["error"] == "boom"
    assert any("boom" in msg for msg in errors)


def test_deck_chat_iteration_updates_deck_and_logs_chat(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html="<html>Alt</html>",
        deck_pdf=b"stale-pdf-bytes",
        deck_chat=[],
        deck_history=[],
    )
    _stub_chat_widgets(monkeypatch, ["Abstand unter der Headline zu groß"])
    captured_replacements = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured_replacements.append((path, replacements))
        or "PROMPT",
    )
    fake_client = _FakeClient(result="<html>Neu</html>")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Neu</html>"
    assert session_state["deck_pdf"] is None  # stale PDF must not survive an edit
    assert session_state["error"] is None
    assert session_state["deck_chat"] == [
        {"role": "user", "content": "Abstand unter der Headline zu groß"},
        {"role": "assistant", "content": "Deck aktualisiert."},
    ]
    # previous deck snapshot goes into deck_history before being overwritten
    assert len(session_state["deck_history"]) == 1
    snapshot = session_state["deck_history"][0]
    assert snapshot["html"] == "<html>Alt</html>"
    assert snapshot["label"] == "Abstand unter der Headline zu groß"
    assert snapshot["timestamp"]
    # prompt gets current deck + change request, not full chat history
    path, replacements = captured_replacements[0]
    assert path == phases.HTML_DECK_CHAT_PROMPT
    assert replacements == {
        phases._DECK_HTML_PLACEHOLDER: "<html>Alt</html>",
        phases._CHANGE_REQUEST_PLACEHOLDER: "Abstand unter der Headline zu groß",
    }
    system_prompt, messages = fake_client.calls[0]
    assert messages == [
        {"role": "user", "content": "Abstand unter der Headline zu groß"}
    ]


def test_fenced_iteration_answer_is_unwrapped(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html="<html>Alt</html>",
        deck_chat=[],
        deck_history=[],
    )
    _stub_chat_widgets(monkeypatch, ["Mehr Weißraum"])
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases,
        "get_client",
        lambda: _FakeClient(result="```html\n<html>Neu</html>\n```"),
    )

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Neu</html>"
    assert session_state["error"] is None


def test_iteration_answer_without_html_root_keeps_previous_deck(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html="<html>Alt</html>",
        deck_chat=[],
        deck_history=[],
    )
    errors = []
    _stub_chat_widgets(monkeypatch, ["Mehr Weißraum"], errors=errors)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(result="Was genau meinst du?")
    )

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Alt</html>"
    assert session_state["deck_history"] == []
    assert "kein HTML-Dokument" in session_state["error"]
    assert any("kein HTML-Dokument" in msg for msg in errors)


def test_deck_chat_three_consecutive_iterations_no_context_loss(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html="<html>v1</html>", deck_chat=[]
    )
    requests = ["Änderung 1", "Änderung 2", "Änderung 3"]
    results = iter(["<html>v2</html>", "<html>v3</html>", "<html>v4</html>"])
    fake_client = _FakeClient()
    fake_client.complete = lambda system, messages: (
        fake_client.calls.append((system, messages)) or next(results)
    )
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    for i, request in enumerate(requests):
        _stub_chat_widgets(monkeypatch, [request])
        phases.render_sidebar()
        assert session_state["error"] is None
        assert fake_client.calls[i][1] == [{"role": "user", "content": request}]

    assert session_state["deck_html"] == "<html>v4</html>"
    assert [snap["html"] for snap in session_state["deck_history"]] == [
        "<html>v1</html>",
        "<html>v2</html>",
        "<html>v3</html>",
    ]
    assert len(session_state["deck_chat"]) == 6


def test_deck_history_restore_replaces_deck_html(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html="<html>v3</html>",
        deck_chat=[],
        deck_history=[
            {"label": "Änderung 1", "html": "<html>v1</html>", "timestamp": "t1"},
            {"label": "Änderung 2", "html": "<html>v2</html>", "timestamp": "t2"},
        ],
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "chat_input", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases.st, "error", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "selectbox", lambda *a, **k: 0)
    monkeypatch.setattr(
        phases.st, "button", lambda label, **k: label == "Wiederherstellen"
    )

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>v1</html>"


def test_deck_chat_error_keeps_previous_deck_and_history(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html="<html>Stand vor Fehler</html>",
        deck_chat=[],
        deck_history=[],
    )
    errors = []
    _stub_chat_widgets(monkeypatch, ["kaputte Änderung"], errors=errors)
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(error=RuntimeError("boom"))
    )

    phases.render_sidebar()

    assert session_state["deck_html"] == "<html>Stand vor Fehler</html>"
    assert session_state["deck_history"] == []
    assert session_state["error"] == "boom"
    assert any("boom" in msg for msg in errors)


def test_deck_chat_hides_master_css_from_the_model_and_restores_it(monkeypatch):
    """Issue #79: der generierte Block geht nicht raus und kommt unveraendert
    zurueck, selbst wenn das Modell an seiner Stelle CSS schreiben will."""
    master_block = (
        f"<style>\n{layout_css.MASTER_CSS_MARKER}\n"
        ".slide { width: var(--slide-width); }\n</style>"
    )
    original = f"<html><head>{master_block}</head><body>v1</body></html>"
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html=original, deck_chat=[]
    )
    _stub_chat_widgets(monkeypatch, ["Headline groesser"])
    captured = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured.append(replacements) or "PROMPT",
    )
    # Modell ersetzt den Platzhalter durch eigenes Positionierungs-CSS
    answer = (
        "<html><head><style>.slide { width: 1280px; }</style></head>"
        "<body>v2</body></html>"
    )
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(result=answer))

    phases.render_sidebar()

    sent = captured[0][phases._DECK_HTML_PLACEHOLDER]
    assert layout_css.MASTER_CSS_MARKER not in sent
    assert layout_css.MASTER_CSS_PLACEHOLDER in sent

    deck_html = session_state["deck_html"]
    assert master_block in deck_html
    assert "v2" in deck_html


def _deck_with_own_css(css=".x { color: red; }", body="<section>Folie</section>"):
    master_block = (
        f"<style>\n{layout_css.MASTER_CSS_MARKER}\n"
        ".slide { width: var(--slide-width); }\n</style>"
    )
    return (
        f"<html><head>{master_block}<style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )


def test_style_only_iteration_sends_css_and_keeps_markup_identical(monkeypatch):
    """Issue #84: der Stil-Pfad ueberträgt nur den CSS-Block, das Markup
    bleibt byte-identisch."""
    original = _deck_with_own_css()
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html=original, deck_chat=[], deck_history=[]
    )
    _stub_chat_widgets(monkeypatch, ["Headline blau"], css_only=True)
    captured = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured.append((path, replacements)) or "PROMPT",
    )
    fake_client = _FakeClient(result="```css\n.x { color: blue; }\n```")
    monkeypatch.setattr(phases, "get_client", lambda: fake_client)

    phases.render_sidebar()

    path, replacements = captured[0]
    assert path == phases.CSS_ITERATION_PROMPT
    assert replacements == {
        phases._DECK_CSS_PLACEHOLDER: ".x { color: red; }",
        phases._CHANGE_REQUEST_PLACEHOLDER: "Headline blau",
    }
    # no markup and no master CSS in the prompt at all
    sent = replacements[phases._DECK_CSS_PLACEHOLDER]
    assert "<section>" not in sent
    assert layout_css.MASTER_CSS_MARKER not in sent

    deck_html = session_state["deck_html"]
    assert deck_html == original.replace("color: red;", "color: blue;")
    assert deck_html.split("<body>")[1] == original.split("<body>")[1]


def test_structure_change_still_takes_the_full_path(monkeypatch):
    """Ohne die Stil-Weiche geht weiterhin das ganze Deck an das Modell."""
    original = _deck_with_own_css()
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html=original, deck_chat=[], deck_history=[]
    )
    _stub_chat_widgets(monkeypatch, ["Folie 2 entfernen"], css_only=False)
    captured = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured.append((path, replacements)) or "PROMPT",
    )
    answer = _deck_with_own_css(body="<section>Andere Folie</section>")
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(result=answer))

    phases.render_sidebar()

    path, replacements = captured[0]
    assert path == phases.HTML_DECK_CHAT_PROMPT
    assert "<section>Folie</section>" in replacements[phases._DECK_HTML_PLACEHOLDER]
    assert "Andere Folie" in session_state["deck_html"]


def test_style_only_iteration_falls_back_without_own_css(monkeypatch):
    """Kein eigener <style>-Block: nichts zum Iterieren, also der volle Weg."""
    original = "<html><body><section>Folie</section></body></html>"
    _fresh_state(
        monkeypatch, phase="deck", deck_html=original, deck_chat=[], deck_history=[]
    )
    _stub_chat_widgets(monkeypatch, ["Headline blau"], css_only=True)
    captured = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured.append((path, replacements)) or "PROMPT",
    )
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(result=original))

    phases.render_sidebar()

    assert captured[0][0] == phases.HTML_DECK_CHAT_PROMPT


def test_deck_chat_preserves_print_css_rules(monkeypatch):
    """Sample check per issue #37: @media print survives a targeted iteration."""
    original = (
        "<html><style>@media print { .slide { break-after: page; } }"
        "</style></html>"
    )
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html=original, deck_chat=[]
    )
    _stub_chat_widgets(monkeypatch, ["Abstand unter der Headline zu groß"])
    monkeypatch.setattr(phases, "load_prompt", lambda path, replacements: "PROMPT")
    updated = original.replace(
        "break-after: page;", "break-after: page; margin-top: 0;"
    )
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(result=updated))

    phases.render_sidebar()

    assert "@media print" in session_state["deck_html"]


def _stub_structure_edit_widgets(monkeypatch, edited_value, save_clicked):
    """Stub the manual-edit expander/text_area plus the widgets the rest of
    `_render_structure_sidebar` touches, so only the save button fires."""
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "chat_input", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "chat_message", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "expander", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "text_area", lambda label, value, **k: edited_value)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases.st, "error", lambda *a, **k: None)
    monkeypatch.setattr(
        phases.st,
        "button",
        lambda label, **k: (
            save_clicked if label == "Manuelle Änderung übernehmen" else False
        ),
    )


def test_manual_structure_edit_updates_structure_and_bumps_version(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="structure", structure_md="# Alt", structure_version=2
    )
    _stub_structure_edit_widgets(monkeypatch, "# Manuell bearbeitet", save_clicked=True)

    phases.render_sidebar()

    assert session_state["structure_md"] == "# Manuell bearbeitet"
    assert session_state["structure_version"] == 3


def test_manual_edit_not_saved_without_button_click(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="structure", structure_md="# Alt", structure_version=0
    )
    _stub_structure_edit_widgets(monkeypatch, "# Entwurf", save_clicked=False)

    phases.render_sidebar()

    assert session_state["structure_md"] == "# Alt"
    assert session_state["structure_version"] == 0


def test_manual_edit_then_chat_iteration_uses_edited_version(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="structure",
        structure_md="# Alt",
        structure_chat=[],
        structure_version=0,
    )
    _stub_structure_edit_widgets(monkeypatch, "# Manuell bearbeitet", save_clicked=True)
    phases.render_sidebar()
    assert session_state["structure_md"] == "# Manuell bearbeitet"

    _stub_chat_widgets(monkeypatch, ["Ändere Titel"])
    monkeypatch.setattr(phases.st, "expander", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "text_area", lambda label, value, **k: value)
    captured_replacements = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured_replacements.append(replacements)
        or "PROMPT",
    )
    monkeypatch.setattr(
        phases, "get_client", lambda: _FakeClient(result="# Neue Struktur")
    )

    phases.render_sidebar()

    assert (
        captured_replacements[0][phases._STRUCTURE_PLACEHOLDER]
        == "# Manuell bearbeitet"
    )


_HISTORY_ENTRY = {"label": "v1", "html": "<p>x</p>", "timestamp": "2026-01-01T00:00:00"}


def test_deck_back_button_only_shows_warning_first(monkeypatch):
    session_state = _fresh_state(
        monkeypatch, phase="deck", deck_html="<p>x</p>", deck_history=[_HISTORY_ENTRY]
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)

    phases.render_sidebar()

    assert session_state["phase"] == "deck"
    assert session_state["confirm_back_to_structure"] is True
    assert session_state["deck_html"] == "<p>x</p>"


def test_deck_back_to_structure_after_confirm_clears_deck_state(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html="<p>x</p>",
        deck_chat=[{"role": "user", "content": "x"}],
        deck_history=[_HISTORY_ENTRY],
        confirm_back_to_structure=True,
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "warning", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(
        phases.st,
        "button",
        lambda label, **k: label == "Ja, zurück zur Struktur",
    )

    phases.render_sidebar()

    assert session_state["phase"] == "structure"
    assert session_state["confirm_back_to_structure"] is False
    assert session_state["deck_html"] is None
    assert session_state["deck_chat"] == []
    assert session_state["deck_history"] == []


def test_deck_back_to_structure_cancel_keeps_deck_state(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        deck_html="<p>x</p>",
        deck_history=[_HISTORY_ENTRY],
        confirm_back_to_structure=True,
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "warning", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(
        phases.st, "button", lambda label, **k: label == "Abbrechen"
    )

    phases.render_sidebar()

    assert session_state["phase"] == "deck"
    assert session_state["confirm_back_to_structure"] is False
    assert session_state["deck_html"] == "<p>x</p>"
    assert session_state["deck_history"] == [_HISTORY_ENTRY]


_LINT_GUIDELINE = ":root { --color-primary: #1A73E8; }"
_LINT_DECK = '<p style="color: #ff0000">x</p>'


def test_lint_report_can_be_sent_back_as_change_request(monkeypatch):
    session_state = _fresh_state(
        monkeypatch,
        phase="deck",
        guideline_md=_LINT_GUIDELINE,
        deck_html=_LINT_DECK,
        deck_chat=[],
        deck_history=[],
    )
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "expander", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    captured = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured.append(replacements) or "PROMPT",
    )
    monkeypatch.setattr(
        phases,
        "get_client",
        lambda: _FakeClient(result='<section class="slide">fixed</section>'),
    )

    phases._render_lint_report()

    assert session_state["deck_html"] == '<section class="slide">fixed</section>'
    assert "#ff0000" in captured[0][phases._CHANGE_REQUEST_PLACEHOLDER]
    assert session_state["deck_history"][0]["html"] == _LINT_DECK


def test_lint_report_stays_silent_for_a_compliant_deck(monkeypatch):
    _fresh_state(
        monkeypatch,
        phase="deck",
        guideline_md=_LINT_GUIDELINE,
        deck_html='<style>.slide{color:#1a73e8}</style><p class="slide">x</p>',
    )
    successes = []
    monkeypatch.setattr(phases.st, "success", successes.append)
    monkeypatch.setattr(
        phases.st,
        "expander",
        lambda *a, **k: pytest.fail("expander shown for a compliant deck"),
    )

    phases._render_lint_report()

    assert successes == ["Design-Prüfung: keine Abweichungen von den Tokens gefunden."]


_TOKENS_JSON = """{
  "slide_width_cm": 33.87, "slide_height_cm": 19.05, "aspect_ratio": 1.778,
  "theme_colors": {"dk1": "#111111", "lt1": "#FFFFFF", "accent1": "#1A73E8"},
  "theme_fonts": {"heading_font": "Example Sans", "body_font": "Example Sans"},
  "text_styles": {"title": [{"level": 1, "font_size_pt": 40.0,
                             "color": "scheme:tx1", "align": "l", "font": null}],
                  "body": [{"level": 1, "font_size_pt": 20.0,
                            "color": "scheme:tx1", "align": "l", "font": null}]},
  "master_background": {"fill": "solid", "color": "#FFFFFF"},
  "layouts": [
    {"master_index": 0, "layout_name": "Titel",
     "background": {"fill": "inherited", "color": null},
     "placeholders": [{"idx": 0, "type": "TITLE (1)", "type_name": "TITLE",
                       "type_id": 1, "name": "Title 1", "left_cm": 3.39,
                       "top_cm": 1.9, "width_cm": 27.1, "height_cm": 3.81}]},
    {"master_index": 0, "layout_name": "Karteileiche",
     "background": {"fill": "inherited", "color": null},
     "placeholders": [{"idx": 0, "type": "BODY (2)", "type_name": "BODY",
                       "type_id": 2, "name": "Body 1", "left_cm": 1.0,
                       "top_cm": 1.0, "width_cm": 10.0, "height_cm": 5.0}]}
  ]
}"""


def _stub_layout_widgets(monkeypatch, tokens_upload=None, selection=None):
    _stub_uploaders(monkeypatch, tokens=tokens_upload)
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "subheader", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "success", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "warning", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "error", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "text_input", lambda label, value, **k: value)
    monkeypatch.setattr(phases.st, "text_area", lambda label, value, **k: value)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    monkeypatch.setattr(
        phases.st,
        "multiselect",
        lambda label, options, default, **k: (
            default if selection is None else selection
        ),
    )


def test_token_upload_preselects_every_layout(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    _stub_layout_widgets(
        monkeypatch, tokens_upload=_FakeUpload("pptx_design_tokens.json", _TOKENS_JSON)
    )

    phases.render_sidebar()

    assert session_state["tokens_name"] == "pptx_design_tokens.json"
    assert session_state["selected_layouts"] == ["titel", "karteileiche"]


def test_broken_token_file_reports_error_and_keeps_state(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    _stub_layout_widgets(monkeypatch, tokens_upload=_FakeUpload("broken.json", "{nope"))
    errors = []
    monkeypatch.setattr(phases.st, "error", errors.append)

    phases.render_sidebar()

    assert session_state["tokens"] is None
    assert session_state["tokens_name"] is None
    assert any("nicht lesbar" in msg for msg in errors)


def test_deselected_layout_reaches_neither_css_nor_catalog(monkeypatch):
    _fresh_state(
        monkeypatch,
        phase="setup",
        tokens=json.loads(_TOKENS_JSON),
        tokens_name="t.json",
        selected_layouts=["titel"],
    )
    _stub_layout_widgets(monkeypatch, selection=["titel"])

    phases.render_sidebar()
    css = phases._layout_css_block()
    catalog = phases._layout_catalog()

    assert ".layout-titel " in css
    assert "layout-karteileiche" not in css
    assert "Karteileiche" not in catalog
    assert "Titel" in catalog


def test_structure_prompt_carries_the_layout_catalog(monkeypatch):
    _fresh_state(
        monkeypatch,
        phase="setup",
        setup=_FILLED_SETUP,
        tokens=json.loads(_TOKENS_JSON),
        tokens_name="t.json",
        selected_layouts=["titel"],
    )
    _stub_layout_widgets(monkeypatch, selection=["titel"])
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    monkeypatch.setattr(phases.st, "spinner", lambda *a, **k: _FakeSpinner())
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    captured = []
    monkeypatch.setattr(
        phases,
        "load_prompt",
        lambda path, replacements: captured.append(replacements) or "PROMPT",
    )
    monkeypatch.setattr(phases, "get_client", lambda: _FakeClient(result="# S"))

    phases.render_sidebar()

    catalog = captured[0][phases._LAYOUT_LIST_PLACEHOLDER]
    assert "layout-titel" in catalog and "Karteileiche" not in catalog


def test_phase_indicator_renders_no_widget(monkeypatch):
    _fresh_state(monkeypatch, phase="structure")
    captured = {}
    monkeypatch.setattr(phases.st, "info", lambda msg: captured.setdefault("msg", msg))

    phases.render_phase_indicator()

    assert "**Struktur**" in captured["msg"]
    assert "Setup" in captured["msg"]
    assert "Deck" in captured["msg"]
