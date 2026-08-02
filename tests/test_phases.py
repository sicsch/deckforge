from app import phases, state


def _fresh_state(monkeypatch, **overrides):
    fake_session_state = dict(state.DEFAULT_STATE)
    fake_session_state.update(overrides)
    monkeypatch.setattr(phases.st, "session_state", fake_session_state)
    return fake_session_state


def test_setup_to_structure_via_dummy_trigger(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: True)
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "file_uploader", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "rerun", lambda: None)

    phases.render_sidebar()

    assert session_state["phase"] == "structure"
    assert session_state["structure_md"]


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
    monkeypatch.setattr(
        phases.st,
        "file_uploader",
        lambda *a, **k: _FakeUpload("new.md", "# New"),
    )

    phases.render_sidebar()

    assert session_state["guideline_md"] == "# New"
    assert session_state["guideline_name"] == "new.md"


def test_no_upload_keeps_state_untouched(monkeypatch):
    session_state = _fresh_state(monkeypatch, phase="setup")
    monkeypatch.setattr(phases.st, "write", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "caption", lambda *a, **k: None)
    monkeypatch.setattr(phases.st, "button", lambda *a, **k: False)
    monkeypatch.setattr(phases.st, "file_uploader", lambda *a, **k: None)

    phases.render_sidebar()

    assert session_state["guideline_md"] is None
    assert session_state["guideline_name"] is None


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
