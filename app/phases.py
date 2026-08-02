"""Phase-dependent rendering and transitions for deckforge's Streamlit app."""

import re

import openai
import streamlit as st
from llm.client import get_client
from prompts.loader import load_prompt

SLIDE_ARCHITECT_PROMPT = "02-slide-structure/slide_architect_prompt.md"
STRUCTURE_CHAT_PROMPT = "02-slide-structure/structure_chat_prompt.md"
_GUIDELINE_PLACEHOLDER = "[HIER Design-Guideline aus Schritt 1 EINFÜGEN]"
_BRIEFING_PLACEHOLDER = "[HIER Thema/Zielgruppe/Ziel/Wirkung/Inhalte EINFÜGEN]"
_STRUCTURE_PLACEHOLDER = "[HIER Aktuelle Folienstruktur EINFÜGEN]"
_CHANGE_REQUEST_PLACEHOLDER = "[HIER Änderungswunsch EINFÜGEN]"

_LLM_ERROR_MESSAGES = (
    (openai.APITimeoutError, "Zeitüberschreitung beim LLM-Aufruf."),
    (openai.AuthenticationError, "Authentifizierung beim LLM-Provider fehlgeschlagen."),
    (openai.RateLimitError, "Rate Limit beim LLM-Provider erreicht."),
)


def _describe_llm_error(exc: Exception) -> str:
    """Map known transient/auth failures to an understandable German message.

    Falls back to str(exc) for anything else — never a raw stacktrace, but
    also never invented text for errors we don't recognize.
    """
    for exc_type, message in _LLM_ERROR_MESSAGES:
        if isinstance(exc, exc_type):
            return f"{message} Bitte erneut versuchen."
    return str(exc)


PHASES = ("setup", "structure", "deck")
PHASE_LABELS = {
    "setup": "Setup",
    "structure": "Struktur",
    "deck": "Deck",
}

_ROOT_BLOCK_RE = re.compile(r":root\s*\{([^}]*)\}", re.DOTALL)
_CSS_VAR_RE = re.compile(r"(--[\w-]+)\s*:")
_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)


def _validate_guideline(markdown: str) -> tuple[list[str], list[str]]:
    """Heuristic scan (tech-spec risk 11): CSS custom properties inside a
    `:root { ... }` block, plus H2/H3 headings as slide-type candidates.
    Informational only — never raises, an unstructured file just yields
    empty lists.
    """
    tokens = []
    for block in _ROOT_BLOCK_RE.findall(markdown):
        tokens.extend(_CSS_VAR_RE.findall(block))
    slide_types = _HEADING_RE.findall(markdown)
    return tokens, slide_types


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
        tokens, slide_types = _validate_guideline(st.session_state["guideline_md"])
        if tokens:
            st.success(f"{len(tokens)} CSS-Tokens erkannt: {', '.join(tokens)}")
        else:
            st.warning(
                "Keine CSS-Tokens gefunden — Ergebnisse könnten vom "
                "Corporate Design abweichen."
            )
        if slide_types:
            st.success(
                f"{len(slide_types)} Folientypen erkannt: {', '.join(slide_types)}"
            )
        else:
            st.warning("Keine Folientyp-Überschriften gefunden.")

    st.subheader("Angaben zur Präsentation")
    setup = st.session_state["setup"]
    setup["thema"] = st.text_input("Thema", value=setup["thema"], key="setup_thema")
    setup["zielgruppe"] = st.text_input(
        "Zielgruppe", value=setup["zielgruppe"], key="setup_zielgruppe"
    )
    setup["ziel"] = st.text_input("Ziel", value=setup["ziel"], key="setup_ziel")
    setup["wirkung"] = st.text_input(
        "Gewünschte Wirkung", value=setup["wirkung"], key="setup_wirkung"
    )
    setup["rohinhalte"] = st.text_area(
        "Rohinhalte (Stichpunkte, bestehender Text)",
        value=setup["rohinhalte"],
        key="setup_rohinhalte",
    )

    required_filled = all(
        setup[field].strip() for field in ("thema", "zielgruppe", "ziel", "wirkung")
    )
    if not required_filled:
        st.caption("Thema, Zielgruppe, Ziel und Wirkung sind Pflichtfelder.")

    if st.button("Struktur generieren", disabled=not required_filled):
        with st.spinner("Struktur wird generiert..."):
            try:
                structure_md = _generate_structure(
                    setup, st.session_state["guideline_md"]
                )
            except Exception as exc:
                st.session_state["error"] = _describe_llm_error(exc)
            else:
                st.session_state["structure_md"] = structure_md
                st.session_state["structure_version"] += 1
                st.session_state["error"] = None
                st.session_state["phase"] = "structure"
                st.rerun()

    if st.session_state["error"]:
        st.error(f"Strukturgenerierung fehlgeschlagen: {st.session_state['error']}")


def _generate_structure(setup: dict, guideline_md: str | None) -> str:
    """Fill the slide-architect prompt template and run it via the LLM client."""
    briefing = (
        f"Thema: {setup['thema']}\n"
        f"Zielgruppe: {setup['zielgruppe']}\n"
        f"Ziel: {setup['ziel']}\n"
        f"Gewünschte Wirkung: {setup['wirkung']}\n"
        f"Vorhandene Inhalte:\n{setup['rohinhalte']}"
    )
    prompt = load_prompt(
        SLIDE_ARCHITECT_PROMPT,
        {
            _GUIDELINE_PLACEHOLDER: guideline_md or "",
            _BRIEFING_PLACEHOLDER: briefing,
        },
    )
    return get_client().complete(
        prompt, [{"role": "user", "content": "Erzeuge die Folienarchitektur."}]
    )


def _generate_structure_iteration(structure_md: str, change_request: str) -> str:
    """Fill the chat-iteration prompt with the current structure and run it.

    Only the current `structure_md` and the latest change request go into the
    prompt — never the full chat history (Kontextfenster-Disziplin, siehe
    CLAUDE.md).
    """
    prompt = load_prompt(
        STRUCTURE_CHAT_PROMPT,
        {
            _STRUCTURE_PLACEHOLDER: structure_md,
            _CHANGE_REQUEST_PLACEHOLDER: change_request,
        },
    )
    return get_client().complete(prompt, [{"role": "user", "content": change_request}])


def _render_structure_sidebar() -> None:
    for message in st.session_state["structure_chat"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    change_request = st.chat_input("Änderungswunsch zur Struktur")
    if change_request:
        st.session_state["structure_chat"].append(
            {"role": "user", "content": change_request}
        )
        with st.spinner("Struktur wird aktualisiert..."):
            try:
                structure_md = _generate_structure_iteration(
                    st.session_state["structure_md"], change_request
                )
            except Exception as exc:
                st.session_state["error"] = _describe_llm_error(exc)
            else:
                st.session_state["structure_md"] = structure_md
                st.session_state["structure_version"] += 1
                st.session_state["error"] = None
                st.session_state["structure_chat"].append(
                    {"role": "assistant", "content": "Struktur aktualisiert."}
                )
        st.rerun()

    if st.session_state["error"]:
        st.error(f"Änderung fehlgeschlagen: {st.session_state['error']}")

    with st.expander("Struktur manuell bearbeiten"):
        edited_md = st.text_area(
            "Markdown-Quelltext",
            value=st.session_state["structure_md"] or "",
            height=300,
            key=f"structure_editor_{st.session_state['structure_version']}",
        )
        if st.button("Manuelle Änderung übernehmen"):
            st.session_state["structure_md"] = edited_md
            st.session_state["structure_version"] += 1
            st.session_state["error"] = None
            st.rerun()

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
