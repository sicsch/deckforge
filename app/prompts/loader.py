"""Load prompt templates from 02-slide-structure/ and 03-html-generation/.

Prompts are source code (CLAUDE.md rule 5) and must be read from the
markdown files at runtime, never duplicated as string literals in Python.
"""

import re
from pathlib import Path

_PROMPT_BLOCK_RE = re.compile(r"## Prompt\s*\n```\n(.*?)\n```", re.DOTALL)
_PLACEHOLDER_RE = re.compile(r"\[HIER[^\]]*EINFÜGEN\]")


def load_prompt(template_path: str | Path, replacements: dict[str, str]) -> str:
    """Load the fenced ```-block under `## Prompt` and fill its placeholders.

    `replacements` keys must be the exact placeholder text as it appears in
    the template, e.g. `"[HIER Design-Guideline aus Schritt 1 EINFÜGEN]"`.
    Raises `ValueError` if any placeholder is left unresolved.
    """
    text = Path(template_path).read_text(encoding="utf-8")
    match = _PROMPT_BLOCK_RE.search(text)
    if not match:
        raise ValueError(f"No '## Prompt' code block found in {template_path}")
    prompt = match.group(1)

    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, value)

    remaining = _PLACEHOLDER_RE.findall(prompt)
    if remaining:
        raise ValueError(
            f"Unresolved placeholder(s) in {template_path}: {', '.join(remaining)}"
        )
    return prompt
