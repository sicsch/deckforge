from app import state


def test_init_state_populates_defaults(monkeypatch):
    fake_session_state = {}
    monkeypatch.setattr(state.st, "session_state", fake_session_state)

    state.init_state()

    assert fake_session_state == state.DEFAULT_STATE


def test_init_state_does_not_overwrite_existing(monkeypatch):
    fake_session_state = {"phase": "structure"}
    monkeypatch.setattr(state.st, "session_state", fake_session_state)

    state.init_state()

    assert fake_session_state["phase"] == "structure"
