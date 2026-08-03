import layout_css
import pytest

from app.prompts.loader import load_prompt

SLIDE_ARCHITECT = "02-slide-structure/slide_architect_prompt.md"
HTML_DECK = "03-html-generation/html_deck_prompt.md"
HTML_DECK_CHAT = "03-html-generation/html_deck_chat_prompt.md"


def test_loads_slide_architect_prompt_from_file():
    prompt = load_prompt(
        SLIDE_ARCHITECT,
        {
            "[HIER Design-Guideline aus Schritt 1 EINFÜGEN]": "GUIDELINE",
            "[HIER Verfügbare Folienlayouts EINFÜGEN]": "LAYOUTS",
            "[HIER Thema/Zielgruppe/Ziel/Wirkung/Inhalte EINFÜGEN]": "BRIEFING",
        },
    )
    assert "GUIDELINE" in prompt
    assert "LAYOUTS" in prompt
    assert "BRIEFING" in prompt
    assert "[HIER" not in prompt
    assert "## Prompt" not in prompt  # only the fenced block is returned


def test_loads_html_deck_prompt_from_file():
    prompt = load_prompt(
        HTML_DECK,
        {
            "[HIER Design-Guideline aus Schritt 1 EINFÜGEN]": "GUIDELINE",
            "[HIER Layout-CSS und Layout-Liste aus dem Folienmaster EINFÜGEN]": "CSS",
            "[HIER Folienstruktur + HTML-Briefing aus Schritt 2 EINFÜGEN]": "STRUCTURE",
        },
    )
    assert "GUIDELINE" in prompt
    assert "CSS" in prompt
    assert "STRUCTURE" in prompt
    assert "[HIER" not in prompt


def test_chat_prompt_names_the_marker_the_code_inserts():
    """Template und Code duerfen beim Folienmaster-Platzhalter nicht
    auseinanderlaufen (Issue #79)."""
    prompt = load_prompt(
        HTML_DECK_CHAT,
        {
            "[HIER Aktuelles HTML-Deck EINFÜGEN]": "DECK",
            "[HIER Änderungswunsch EINFÜGEN]": "CHANGE",
        },
    )
    assert layout_css.MASTER_CSS_PLACEHOLDER in prompt


def test_missing_placeholder_raises_clear_error():
    with pytest.raises(ValueError, match="Unresolved placeholder"):
        load_prompt(SLIDE_ARCHITECT, {})


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("does/not/exist.md", {})
