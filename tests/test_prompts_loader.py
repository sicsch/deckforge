"""Guard the seam between the prompt templates and the code that fills them.

CLAUDE.md warns about a template and its loader drifting apart. The checks
here derive both sides from `app.phases` and the template files themselves,
so a renamed placeholder or a new template fails the test run instead of a
user's button click (Issue #87).
"""

from pathlib import Path

import layout_css
import pytest

from app import phases
from app.prompts import loader
from app.prompts.loader import load_prompt


def _string_constants(suffix: str) -> set[str]:
    return {
        value
        for name, value in vars(phases).items()
        if name.endswith(suffix) and isinstance(value, str)
    }


PROMPT_PATHS = sorted(_string_constants("_PROMPT"))
CODE_PLACEHOLDERS = _string_constants("_PLACEHOLDER")


def _template_placeholders(template_path: str) -> set[str]:
    """The placeholders inside a template's `## Prompt` block."""
    text = Path(template_path).read_text(encoding="utf-8")
    block = loader._PROMPT_BLOCK_RE.search(text)
    assert block, f"{template_path} has no '## Prompt' block"
    return set(loader._PLACEHOLDER_RE.findall(block.group(1)))


def test_every_prompt_constant_points_at_an_existing_template():
    assert PROMPT_PATHS
    missing = [path for path in PROMPT_PATHS if not Path(path).is_file()]
    assert not missing


@pytest.mark.parametrize("template_path", PROMPT_PATHS)
def test_template_placeholders_all_have_a_constant_in_phases(template_path):
    """A placeholder renamed in the template no longer matches the code."""
    unknown = _template_placeholders(template_path) - CODE_PLACEHOLDERS
    assert not unknown, f"{template_path}: no constant in app/phases.py for {unknown}"


@pytest.mark.parametrize("template_path", PROMPT_PATHS)
def test_load_prompt_resolves_every_placeholder_of_the_template(template_path):
    placeholders = sorted(_template_placeholders(template_path))
    values = {p: f"VALUE{index}" for index, p in enumerate(placeholders)}
    prompt = load_prompt(template_path, values)
    for value in values.values():
        assert value in prompt
    assert "[HIER" not in prompt
    assert "## Prompt" not in prompt  # only the fenced block is returned


def test_no_placeholder_constant_is_missing_from_the_templates():
    """A placeholder renamed in the code no longer matches any template."""
    in_templates = set().union(*(_template_placeholders(p) for p in PROMPT_PATHS))
    assert not CODE_PLACEHOLDERS - in_templates


def test_chat_prompt_names_the_marker_the_code_inserts():
    """Template und Code duerfen beim Folienmaster-Platzhalter nicht
    auseinanderlaufen (Issue #79)."""
    prompt = load_prompt(
        phases.HTML_DECK_CHAT_PROMPT,
        {
            phases._DECK_HTML_PLACEHOLDER: "DECK",
            phases._CHANGE_REQUEST_PLACEHOLDER: "CHANGE",
        },
    )
    assert layout_css.MASTER_CSS_PLACEHOLDER in prompt


def test_missing_placeholder_raises_clear_error():
    with pytest.raises(ValueError, match="Unresolved placeholder"):
        load_prompt(phases.SLIDE_ARCHITECT_PROMPT, {})


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_prompt("does/not/exist.md", {})
