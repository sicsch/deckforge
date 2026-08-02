"""Phase-dependent rendering and transitions for deckforge's Streamlit app."""

import streamlit as st

PHASES = ("setup", "structure", "deck")
PHASE_LABELS = {
    "setup": "Setup",
    "structure": "Struktur",
    "deck": "Deck",
}


def render_phase_indicator() -> None:
    """Show the current phase as plain text — no widget, so no phase is clickable."""
    current = st.session_state["phase"]
    labels = [
        f"**{PHASE_LABELS[p]}**" if p == current else PHASE_LABELS[p] for p in PHASES
    ]
    st.info(" → ".join(labels))


def render_sidebar() -> None:
    """Render the control column for the current phase."""
    phase = st.session_state["phase"]
    if phase == "setup":
        _render_setup_sidebar()
    elif phase == "structure":
        _render_structure_sidebar()
    elif phase == "deck":
        _render_deck_sidebar()


def render_preview() -> None:
    """Render the preview column for the current phase."""
    phase = st.session_state["phase"]
    if phase == "setup":
        st.write("Noch keine Struktur generiert.")
    elif phase == "structure":
        st.markdown(st.session_state["structure_md"] or "")
    elif phase == "deck":
        st.components.v1.html(
            st.session_state["deck_html"] or "", height=600, scrolling=True
        )


def _render_setup_sidebar() -> None:
    uploaded = st.file_uploader("Design-Guideline (Markdown)", type=["md"])
    if uploaded is not None:
        st.session_state["guideline_md"] = uploaded.getvalue().decode("utf-8")
        st.session_state["guideline_name"] = uploaded.name

    if st.session_state["guideline_md"]:
        st.caption(
            f"{st.session_state['guideline_name']} "
            f"({len(st.session_state['guideline_md'])} Zeichen)"
        )

    st.write("Platzhalter: Formularfelder folgen in #24–#25.")
    if st.button("Struktur generieren"):
        st.session_state["structure_md"] = (
            "# Platzhalter-Struktur\n\nDummy-Inhalt bis #30."
        )
        st.session_state["phase"] = "structure"
        st.rerun()


def _render_structure_sidebar() -> None:
    st.write("Platzhalter: Chat-Iteration folgt in #32.")
    if st.button("Struktur bestätigen → Deck bauen", type="primary"):
        st.session_state["deck_html"] = "<p>Platzhalter-Deck bis #36.</p>"
        st.session_state["phase"] = "deck"
        st.rerun()


def _render_deck_sidebar() -> None:
    st.write("Platzhalter: Chat-Iteration, Downloads, Versionshistorie folgen in #36+.")
    st.caption("Zurückspringen verwirft den aktuellen HTML-Stand.")
    if st.button("Zurück zur Struktur"):
        st.session_state["phase"] = "structure"
        st.rerun()
