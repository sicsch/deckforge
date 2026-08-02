import httpx
import openai

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


def test_guideline_upload_fills_state(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    monkeypatch.setattr(phases.st, "success", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "warning", lambda *a, **k: None)
    monkeypatch.setattr(
        phases.st,
        "file_uploader",
        lambda *a, **k: _FakeUpload("guideline.md", "# Guideline"),
    )

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
    monkeypatch.setattr(
        phases.st,
        "file_uploader",
        lambda *a, **k: _FakeUpload("new.md", "# New"),
    )

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
    _fresh_state(
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
    session_state = _fresh_state(monkeypatch, phase="structure")
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)

    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    phases.render_sidebar()
    assert session_state["phase"] == "structure"

    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    phases.render_sidebar()
    assert session_state["phase"] == "deck"
    assert session_state["deck_html"]


def _stub_chat_widgets(monkeypatch, chat_inputs, errors=None):
    """Stub chat_input to return each value from `chat_inputs` in turn (None
    after exhaustion), plus the other widgets `_render_structure_sidebar`
    touches."""
    inputs = iter(chat_inputs)
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
    }
    system_prompt, messages = fake_client.calls[0]
    assert messages == [{"role": "user", "content": "Ändere Folie 3"}]


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


def test_deck_back_to_structure(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="deck", deck_html="<p>x</p>")
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)

    phases.render_sidebar()

    assert session_state["phase"] == "structure"


def test_phase_indicator_renders_no_widget(monkeypatch):
    _fresh_state(monkeypatch, phase="structure")
    captured = {}
    monkeypatch.setattr(phases.st, "info", lambda msg: captured.setdefault("msg", msg))

    phases.render_phase_indicator()

    assert "**Struktur**" in captured["msg"]
    assert "Setup" in captured["msg"]
    assert "Deck" in captured["msg"]
