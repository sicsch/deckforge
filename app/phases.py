"""Phase-dependent rendering and transitions for deckforge's Streamlit app."""

import json
import re
from datetime import datetime

import layout_css
import lint
import openai
import streamlit as st
from export import pdf
from llm.client import get_client
from prompts.loader import load_prompt

SLIDE_ARCHITECT_PROMPT = "02-slide-structure/slide_architect_prompt.md"
STRUCTURE_CHAT_PROMPT = "02-slide-structure/structure_chat_prompt.md"
HTML_DECK_PROMPT = "03-html-generation/html_deck_prompt.md"
HTML_DECK_CHAT_PROMPT = "03-html-generation/html_deck_chat_prompt.md"
CSS_ITERATION_PROMPT = "03-html-generation/css_iteration_prompt.md"
_GUIDELINE_PLACEHOLDER = "[HIER Design-Guideline aus Schritt 1 EINFÜGEN]"
_BRIEFING_PLACEHOLDER = "[HIER Thema/Zielgruppe/Ziel/Wirkung/Inhalte EINFÜGEN]"
_STRUCTURE_PLACEHOLDER = "[HIER Aktuelle Folienstruktur EINFÜGEN]"
_CHANGE_REQUEST_PLACEHOLDER = "[HIER Änderungswunsch EINFÜGEN]"
_DECK_HTML_PLACEHOLDER = "[HIER Aktuelles HTML-Deck EINFÜGEN]"
_DECK_CSS_PLACEHOLDER = "[HIER Aktuelles Deck-CSS EINFÜGEN]"
_STRUCTURE_BRIEFING_PLACEHOLDER = (
    "[HIER Folienstruktur + HTML-Briefing aus Schritt 2 EINFÜGEN]"
)
_LAYOUT_LIST_PLACEHOLDER = "[HIER Verfügbare Folienlayouts EINFÜGEN]"
_LAYOUT_CSS_PLACEHOLDER = (
    "[HIER Layout-CSS und Layout-Liste aus dem Folienmaster EINFÜGEN]"
)
_NO_LAYOUTS = (
    "Kein Folienmaster hinterlegt — es gibt keine Layout-Liste. "
    "Richte dich allein nach den Folientypen der Design-Guideline."
)
_NO_LAYOUT_CSS = (
    "Kein Folienmaster-CSS vorhanden — baue das Design-System selbst aus den "
    "Tokens der Design-Guideline."
)
_PREFLIGHT_INSTRUCTION = (
    "Erzeuge Phase 1: den Preflight-Plan als Markdown. Noch kein HTML, "
    "noch kein CSS."
)
_CODE_INSTRUCTION = (
    "Der Plan ist bestätigt. Erzeuge Phase 2: das vollständige HTML-Deck "
    "nach diesem Plan. Gib ausschließlich das in sich valide HTML-Dokument "
    "zurück — keinen Plan, keine Erklärungen."
)

_ROHINHALTE_HELP = (
    "Je konkreter hier, desto konkreter die Folien — das Modell darf nichts "
    "dazuerfinden.\n\n"
    "**Gut:** Stichpunkte, Zahlen mit Einheit und Zeitraum, Zitate, Namen, "
    "bestehende Textabschnitte. Gern roh und unsortiert.\n\n"
    "**Wörtlich übernommen** wird, was du in Anführungszeichen setzt oder mit "
    "`Headline:` markierst — z.B. `Headline: Umsatz wächst zweistellig`.\n\n"
    "**Fehlt etwas**, erscheint es auf der Folie als `[FEHLT: ...]` statt als "
    "erfundene Zahl. Das ist Absicht — dann ergänzen und neu generieren."
)

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

_HEADING_RE = re.compile(r"^#{2,3}\s+(.+?)\s*$", re.MULTILINE)
_FENCE_RE = re.compile(r"```(?:html)?[^\n]*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_HTML_ROOT_RE = re.compile(r"<(?:html|section)\b", re.IGNORECASE)


def _clean_deck_html(answer: str) -> str:
    """Unwrap a fenced model answer and refuse anything that isn't a deck.

    The prompt asks for the bare HTML document; a model that wraps it in a
    ```html block or prefixes it with prose would otherwise end up in the
    preview, the download and the PDF verbatim (#85). An answer without an
    HTML root element is a failure, not a deck — raising here routes it
    through the existing error display.
    """
    text = (answer or "").strip()
    if not text.startswith("<"):
        match = _FENCE_RE.search(text)
        if match:
            text = match.group(1).strip()
    if not _HTML_ROOT_RE.search(text):
        raise ValueError(
            "Die Antwort des Modells enthält kein HTML-Dokument. "
            "Bitte erneut versuchen."
        )
    return text


def _validate_guideline(markdown: str) -> tuple[list[str], list[str]]:
    """Heuristic scan (tech-spec risk 11): CSS custom properties inside a
    `:root { ... }` block, plus H2/H3 headings as slide-type candidates.
    Informational only — never raises, an unstructured file just yields
    empty lists.
    """
    tokens = list(lint.guideline_tokens(markdown))
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


def _render_structure_download_button() -> None:
    structure_md = st.session_state["structure_md"] or ""
    st.download_button(
        "Struktur herunterladen",
        data=structure_md,
        file_name="structure.md",
        mime="text/markdown",
        disabled=not structure_md,
    )


def render_preview() -> None:
    """Render the preview column for the current phase."""
    phase = st.session_state["phase"]
    if phase == "setup":
        st.write("Noch keine Struktur generiert.")
    elif phase == "structure":
        _render_structure_download_button()
        st.markdown(st.session_state["structure_md"] or "")
    elif phase == "deck":
        _render_structure_download_button()
        deck_html = st.session_state["deck_html"] or ""
        st.download_button(
            "Deck herunterladen",
            data=deck_html,
            file_name="deck.html",
            mime="text/html",
            disabled=not deck_html,
        )
        preview_tab, source_tab = st.tabs(["Vorschau", "Quellcode"])
        with preview_tab:
            st.components.v1.html(deck_html, height=600, scrolling=True)
        with source_tab:
            st.code(deck_html, language="html")


def _render_layout_selection() -> None:
    """Upload of the extracted master tokens plus the layout opt-in.

    Slide masters routinely carry unused layouts; only the ones ticked here
    reach the prompts and the generated CSS (Issue #78).
    """
    uploaded = st.file_uploader(
        "Design-Tokens des Folienmasters (JSON)",
        type=["json"],
        help="Output von `01-design-guideline/extract_pptx_theme.py`.",
    )
    if uploaded is not None and uploaded.name != st.session_state["tokens_name"]:
        try:
            tokens = json.loads(uploaded.getvalue().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            st.error(f"Token-Datei nicht lesbar: {exc}")
        else:
            st.session_state["tokens"] = tokens
            st.session_state["tokens_name"] = uploaded.name
            st.session_state["selected_layouts"] = [
                entry["slug"] for entry in layout_css.layouts(tokens)
            ]
            # Widget-State verwerfen, damit die neue Vorauswahl greift
            st.session_state.pop("setup_layouts", None)

    tokens = st.session_state["tokens"]
    if not tokens:
        return

    entries = layout_css.layouts(tokens)
    if not entries:
        st.warning("Die Token-Datei enthält keine Folienlayouts.")
        return

    labels = {entry["slug"]: entry["name"] for entry in entries}
    st.session_state["selected_layouts"] = st.multiselect(
        "Erlaubte Folienlayouts",
        options=list(labels),
        default=st.session_state["selected_layouts"],
        format_func=labels.get,
        key="setup_layouts",
    )
    if not st.session_state["selected_layouts"]:
        st.warning("Ohne ausgewähltes Layout entsteht kein Layout-CSS.")


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
        st.download_button(
            "Guideline erneut herunterladen",
            data=st.session_state["guideline_md"].encode("utf-8"),
            file_name=st.session_state["guideline_name"],
            mime="text/markdown",
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

    _render_layout_selection()

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
        help=_ROHINHALTE_HELP,
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


def _layout_catalog() -> str:
    """The master's layout list as prompt text, or the no-master fallback."""
    tokens = st.session_state["tokens"]
    if not tokens:
        return _NO_LAYOUTS
    return layout_css.catalog_markdown(tokens, st.session_state["selected_layouts"])


def _layout_css_block() -> str:
    """The generated `<style>` block plus its catalog, or the fallback.

    Deterministic output of `layout_css` — the model receives it as a finished
    block and is told not to touch it (Issue #78).
    """
    tokens = st.session_state["tokens"]
    if not tokens:
        return _NO_LAYOUT_CSS
    selected = st.session_state["selected_layouts"]
    return (
        "Übernimm den folgenden <style>-Block wörtlich und unverändert in das "
        "Deck:\n\n"
        f"{layout_css.build_css(tokens, selected)}\n\n"
        f"{layout_css.catalog_markdown(tokens, selected)}"
    )


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
            _LAYOUT_LIST_PLACEHOLDER: _layout_catalog(),
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


def _generate_deck_html(
    structure_md: str, guideline_md: str | None
) -> tuple[str, str]:
    """Fill the HTML-deck prompt with guideline + confirmed structure and run it.

    Two calls, matching the two phases the prompt template describes: the
    preflight plan first, then the code with that plan in context. The plan
    is fed back as an assistant turn, so the guideline and the structure are
    sent once per call rather than repeated inside a single prompt.

    Returns `(preflight_plan, deck_html)` — the plan names the layout risks
    the model saw, which is worth showing rather than discarding.
    """
    prompt = load_prompt(
        HTML_DECK_PROMPT,
        {
            _GUIDELINE_PLACEHOLDER: guideline_md or "",
            _LAYOUT_CSS_PLACEHOLDER: _layout_css_block(),
            _STRUCTURE_BRIEFING_PLACEHOLDER: structure_md,
        },
    )
    client = get_client()
    preflight = [{"role": "user", "content": _PREFLIGHT_INSTRUCTION}]
    plan = client.complete(prompt, preflight)
    deck_html = client.complete(
        prompt,
        [
            *preflight,
            {"role": "assistant", "content": plan},
            {"role": "user", "content": _CODE_INSTRUCTION},
        ],
    )
    return plan, _clean_deck_html(deck_html)


def _generate_deck_html_iteration(deck_html: str, change_request: str) -> str:
    """Fill the deck chat-iteration prompt with the current HTML and run it.

    Only the current `deck_html` and the latest change request go into the
    prompt — never the full chat history (Kontextfenster-Disziplin, siehe
    CLAUDE.md). The generated master CSS is cut out beforehand and put back
    afterwards: it costs context on every round and must not drift (#79).
    """
    stripped_html, master_css = layout_css.split_master_css(deck_html)
    prompt = load_prompt(
        HTML_DECK_CHAT_PROMPT,
        {
            _DECK_HTML_PLACEHOLDER: stripped_html,
            _CHANGE_REQUEST_PLACEHOLDER: change_request,
        },
    )
    updated = get_client().complete(
        prompt, [{"role": "user", "content": change_request}]
    )
    return layout_css.restore_master_css(_clean_deck_html(updated), master_css)


def _generate_deck_css_iteration(deck_html: str, change_request: str) -> str:
    """Style-only iteration: only the deck's own CSS block travels to the model.

    The markup never leaves the app, so it stays byte-identical and the round
    costs a few KB instead of the whole deck (#84). A deck without its own
    `<style>` block has nothing to iterate on — then the full path runs.
    """
    css = layout_css.deck_css(deck_html)
    if not css.strip():
        return _generate_deck_html_iteration(deck_html, change_request)
    prompt = load_prompt(
        CSS_ITERATION_PROMPT,
        {
            _DECK_CSS_PLACEHOLDER: css,
            _CHANGE_REQUEST_PLACEHOLDER: change_request,
        },
    )
    updated = get_client().complete(
        prompt, [{"role": "user", "content": change_request}]
    )
    return layout_css.replace_deck_css(deck_html, layout_css.clean_css(updated))


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

    if st.button(
        "Struktur bestätigen → Deck bauen",
        type="primary",
        disabled=not st.session_state["structure_md"],
    ):
        st.session_state["deck_html"] = None
        st.session_state["deck_pdf"] = None
        st.session_state["phase"] = "deck"
        st.rerun()


def _render_pdf_export() -> None:
    """PDF export via Playwright — optional, see 04-pdf-export/README_4.md.

    Playwright isn't a hard dependency (not every laptop can install it, see
    tech-spec risk 11), so this shows a hint pointing at the manual
    browser-print path instead of a button when it's unavailable.
    """
    if not pdf.is_playwright_available():
        st.info(
            "PDF-Export benötigt lokal installiertes Playwright/Chromium. "
            "Anleitung für den manuellen Weg über den Browser-Druckdialog: "
            "`04-pdf-export/README_4.md`."
        )
        return

    if st.button("PDF exportieren"):
        with st.spinner("PDF wird erzeugt..."):
            try:
                st.session_state["deck_pdf"] = pdf.export_html_to_pdf(
                    st.session_state["deck_html"]
                )
            except Exception as exc:
                st.error(f"PDF-Export fehlgeschlagen: {exc}")

    if st.session_state["deck_pdf"]:
        st.download_button(
            "PDF herunterladen",
            data=st.session_state["deck_pdf"],
            file_name="deck.pdf",
            mime="application/pdf",
        )


def _apply_deck_change(change_request: str, css_only: bool = False) -> None:
    """Run one deck iteration and record it in chat + version history.

    `css_only` takes the cheap path from #84 — only the CSS block goes out and
    comes back. Everything else keeps the full path, where the model sees the
    markup it is supposed to change.
    """
    st.session_state["deck_chat"].append({"role": "user", "content": change_request})
    with st.spinner("Deck wird aktualisiert..."):
        try:
            iterate = (
                _generate_deck_css_iteration
                if css_only
                else _generate_deck_html_iteration
            )
            deck_html = iterate(st.session_state["deck_html"], change_request)
        except Exception as exc:
            st.session_state["error"] = _describe_llm_error(exc)
        else:
            st.session_state["deck_history"].append(
                {
                    "label": change_request[:60],
                    "html": st.session_state["deck_html"],
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
            )
            st.session_state["deck_html"] = deck_html
            st.session_state["deck_pdf"] = None
            st.session_state["error"] = None
            st.session_state["deck_chat"].append(
                {"role": "assistant", "content": "Deck aktualisiert."}
            )


def _render_lint_report() -> None:
    """Show the deterministic token check and offer to feed it back to the model."""
    findings = lint.lint_deck(
        st.session_state["deck_html"] or "", st.session_state["guideline_md"]
    )
    if not findings:
        st.success("Design-Prüfung: keine Abweichungen von den Tokens gefunden.")
        return

    with st.expander(f"Design-Prüfung: {len(findings)} Abweichungen", expanded=True):
        for finding in findings:
            st.write(f"- {finding}")
        if st.button("Befund an das Modell zurückgeben"):
            _apply_deck_change(lint.format_report(findings))
            st.rerun()


def _render_deck_sidebar() -> None:
    if st.session_state["deck_html"] is None:
        with st.spinner("Deck wird generiert (erst Preflight-Plan, dann Code)..."):
            try:
                preflight, deck_html = _generate_deck_html(
                    st.session_state["structure_md"], st.session_state["guideline_md"]
                )
            except Exception as exc:
                st.session_state["error"] = _describe_llm_error(exc)
                st.session_state["phase"] = "structure"
                st.rerun()
            else:
                st.session_state["deck_preflight"] = preflight
                st.session_state["deck_html"] = deck_html
                st.session_state["deck_pdf"] = None
                st.session_state["error"] = None

    for message in st.session_state["deck_chat"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    css_only = st.checkbox(
        "Nur Styles ändern",
        help="Schickt nur den CSS-Block an das Modell — schneller, und das "
        "Folien-Markup bleibt unverändert. Für Änderungen an Inhalten, "
        "Folienreihenfolge oder Layout ausschalten.",
    )
    change_request = st.chat_input("Änderungswunsch zum Deck")
    if change_request:
        _apply_deck_change(change_request, css_only=css_only)
        st.rerun()

    if st.session_state["error"]:
        st.error(f"Änderung fehlgeschlagen: {st.session_state['error']}")

    _render_lint_report()

    if st.session_state["deck_preflight"]:
        with st.expander("Preflight-Plan (Komponenten und Layout-Risiken)"):
            st.markdown(st.session_state["deck_preflight"])

    if st.session_state["deck_history"]:
        with st.expander("Versionshistorie"):
            history = st.session_state["deck_history"]
            selected = st.selectbox(
                "Früherer Stand",
                range(len(history)),
                format_func=lambda i: (
                    f"{history[i]['timestamp']} — {history[i]['label']}"
                ),
                index=len(history) - 1,
            )
            if st.button("Wiederherstellen"):
                st.session_state["deck_html"] = history[selected]["html"]
                st.session_state["deck_pdf"] = None
                st.session_state["error"] = None
                st.rerun()

    _render_pdf_export()

    if st.session_state["confirm_back_to_structure"]:
        st.warning(
            "Zurückspringen verwirft den aktuellen HTML-Stand und die "
            "Versionshistorie. Fortfahren?"
        )
        if st.button("Ja, zurück zur Struktur", type="primary"):
            st.session_state["deck_html"] = None
            st.session_state["deck_pdf"] = None
            st.session_state["deck_preflight"] = None
            st.session_state["deck_chat"] = []
            st.session_state["deck_history"] = []
            st.session_state["confirm_back_to_structure"] = False
            st.session_state["phase"] = "structure"
            st.rerun()
        if st.button("Abbrechen"):
            st.session_state["confirm_back_to_structure"] = False
            st.rerun()
    else:
        st.caption("Zurückspringen verwirft den aktuellen HTML-Stand.")
        if st.button("Zurück zur Struktur"):
            st.session_state["confirm_back_to_structure"] = True
            st.rerun()
