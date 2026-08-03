"""Deterministic check of a generated deck against the guideline's design tokens.

Pure regex scan, no extra LLM call (tech-spec section 11, risk "LLM hält sich
nicht an CSS-Tokens der Guideline"). The token source is the `:root` block of
the uploaded guideline — the only machine-readable design contract the app has.
"""

import re

_ROOT_BLOCK_RE = re.compile(r":root\s*\{([^}]*)\}", re.DOTALL)
_CSS_VAR_RE = re.compile(r"(--[\w-]+)\s*:\s*([^;}]*)")
_STYLE_BLOCK_RE = re.compile(r"<style[^>]*>(.*?)</style>", re.DOTALL | re.IGNORECASE)
_HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_RGB_RE = re.compile(r"rgba?\(\s*(\d+)\s*[,\s]\s*(\d+)\s*[,\s]\s*(\d+)[^)]*\)")
_FONT_FAMILY_RE = re.compile(r"font-family\s*:\s*([^;}<]+)")
_FAMILY_RE = re.compile(r"""\s*(?:"([^"]*)"|'([^']*)'|([^,"'>]+))""")
_CLASS_ATTR_RE = re.compile(r"""class\s*=\s*["']([^"']*)["']""")
_CLASS_SELECTOR_RE = re.compile(r"\.(-?[A-Za-z_][\w-]*)")
_INLINE_STYLE_RE = re.compile(r"""style\s*=\s*["']""")
_MISSING_MARKER_RE = re.compile(r"\[FEHLT:[^\]]*\]")

# Keyword families are never a corporate font — flagging them would be noise.
_GENERIC_FAMILIES = frozenset(
    {
        "sans-serif",
        "serif",
        "monospace",
        "cursive",
        "fantasy",
        "system-ui",
        "ui-sans-serif",
        "ui-serif",
        "ui-monospace",
        "ui-rounded",
        "inherit",
        "initial",
        "unset",
        "revert",
    }
)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _normalize_hex(value: str) -> str:
    """Lowercase hex color, 3-digit shorthand expanded, alpha channel dropped."""
    digits = value.lstrip("#").lower()
    if len(digits) in (3, 4):
        digits = "".join(d * 2 for d in digits)
    return "#" + digits[:6]


def _rgb_to_hex(red: str, green: str, blue: str) -> str:
    return f"#{int(red):02x}{int(green):02x}{int(blue):02x}"


def _colors_in(text: str) -> set[str]:
    colors = {_normalize_hex(m.group()) for m in _HEX_RE.finditer(text)}
    colors |= {_rgb_to_hex(*m.groups()) for m in _RGB_RE.finditer(text)}
    return colors


def _families_in(value: str) -> list[str]:
    """Split a font-family value into concrete family names, generics dropped.

    Handles quoted and bare names and stops at the `"` or `>` that ends an
    inline style attribute — the value regex can't tell those apart itself.
    """
    families = []
    for quoted, single, bare in _FAMILY_RE.findall(value):
        family = (quoted or single or bare).strip()
        if family and family.lower() not in _GENERIC_FAMILIES:
            families.append(family)
    return families


def guideline_tokens(markdown: str) -> dict[str, str]:
    """CSS custom properties declared in the guideline's `:root` block(s)."""
    tokens = {}
    for block in _ROOT_BLOCK_RE.findall(markdown):
        for name, value in _CSS_VAR_RE.findall(block):
            tokens[name] = value.strip()
    return tokens


def lint_deck(html: str, guideline_md: str | None) -> list[str]:
    """Report deviations of `html` from the guideline tokens, sorted by line.

    An empty list means the deck is compliant. Color and font checks are
    skipped when the guideline carries no tokens — the setup phase already
    warns about that, repeating it per finding would only be noise.
    """
    if not html:
        return []

    tokens = guideline_tokens(guideline_md or "")
    allowed_colors = _colors_in(" ".join(tokens.values()))
    allowed_fonts = {
        family.lower()
        for name, value in tokens.items()
        if "font" in name
        for family in _families_in(value)
    }

    findings: list[tuple[int, str]] = []

    if allowed_colors:
        for match in _HEX_RE.finditer(html):
            if match.start() and html[match.start() - 1] in "\"'":
                continue  # id reference like href="#abcdef", not a color
            _flag_color(findings, html, match.start(), match.group(), allowed_colors)
        for match in _RGB_RE.finditer(html):
            _flag_color(findings, html, match.start(), match.group(), allowed_colors)

    if allowed_fonts:
        for match in _FONT_FAMILY_RE.finditer(html):
            for family in _families_in(match.group(1)):
                if family.startswith("var("):
                    continue
                if family.lower() not in allowed_fonts:
                    findings.append(
                        (
                            _line_of(html, match.start()),
                            f"Schrift {family!r} ist keine Theme-Schrift "
                            f"(erlaubt: {', '.join(sorted(allowed_fonts))})",
                        )
                    )

    for match in _INLINE_STYLE_RE.finditer(html):
        findings.append(
            (
                _line_of(html, match.start()),
                "Inline-Style statt Klasse oder CSS-Variable",
            )
        )

    for name, line in _unknown_classes(html):
        findings.append(
            (line, f"CSS-Klasse {name!r} wird verwendet, aber nie definiert")
        )

    for match in _MISSING_MARKER_RE.finditer(html):
        findings.append(
            (_line_of(html, match.start()), f"Unaufgelöster Marker {match.group()}")
        )

    findings.sort()
    return [f"Zeile {line}: {message}" for line, message in findings]


def _flag_color(
    findings: list[tuple[int, str]],
    html: str,
    pos: int,
    literal: str,
    allowed: set[str],
) -> None:
    if literal.startswith("#"):
        color = _normalize_hex(literal)
    else:
        color = _rgb_to_hex(*_RGB_RE.match(literal).groups())
    if color not in allowed:
        findings.append(
            (
                _line_of(html, pos),
                f"Farbe {literal} ({color}) ist nicht in der Palette",
            )
        )


def _unknown_classes(html: str) -> list[tuple[str, int]]:
    """Classes used in markup but never defined in a `<style>` block."""
    defined = set()
    for block in _STYLE_BLOCK_RE.findall(html):
        defined.update(_CLASS_SELECTOR_RE.findall(block))

    seen = set()
    unknown = []
    for match in _CLASS_ATTR_RE.finditer(html):
        for name in match.group(1).split():
            if name not in defined and name not in seen:
                seen.add(name)
                unknown.append((name, _line_of(html, match.start())))
    return unknown


def format_report(findings: list[str]) -> str:
    """Render findings as a change request the deck iteration can consume."""
    return (
        "Das Deck weicht an folgenden Stellen vom Corporate Design ab. "
        "Behebe jede Abweichung, ohne Inhalte oder Folienreihenfolge zu ändern:\n"
        + "\n".join(f"- {finding}" for finding in findings)
    )
