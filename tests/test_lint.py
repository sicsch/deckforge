from app import lint

# Generic placeholder design — no real corporate values (CLAUDE.md rule 1).
GUIDELINE = """
# Beispiel-Guideline

```css
:root {
  --color-primary: #1A73E8;
  --color-surface: #FFFFFF;
  --font-heading: "Example Sans", sans-serif;
  --font-body: "Example Serif", serif;
}
```
"""

CLEAN_DECK = """<html><head><style>
.slide { background: #ffffff; color: var(--color-primary); }
.slide h1 { font-family: "Example Sans", sans-serif; color: rgb(26, 115, 232); }
</style></head><body>
<div class="slide"><h1>Titel</h1></div>
</body></html>"""

DEVIATING_DECK = """<html><head><style>
.slide { background: #ffffff; }
</style></head><body>
<div class="slide kpi-row" style="color: #ff0000">
<h1 style="font-family: 'Wrong Face', serif">[FEHLT: Umsatzzahl]</h1>
<p>rgb(255, 0, 0)</p>
</div>
<a href="#abcdef">Sprungmarke</a>
</body></html>"""


def test_compliant_deck_yields_empty_report():
    assert lint.lint_deck(CLEAN_DECK, GUIDELINE) == []


def test_deviating_deck_reports_every_category():
    findings = lint.lint_deck(DEVIATING_DECK, GUIDELINE)
    report = "\n".join(findings)
    assert "#ff0000" in report
    assert "rgb(255, 0, 0)" in report
    assert "'Wrong Face'" in report
    assert "Inline-Style" in report
    assert "'kpi-row'" in report
    assert "[FEHLT: Umsatzzahl]" in report
    # An id reference is not a color.
    assert "abcdef" not in report
    assert all(finding.startswith("Zeile ") for finding in findings)


def test_findings_are_sorted_by_line():
    lines = [
        int(finding.split()[1].rstrip(":"))
        for finding in lint.lint_deck(DEVIATING_DECK, GUIDELINE)
    ]
    assert lines == sorted(lines)


def test_shorthand_hex_and_rgb_match_the_same_token():
    guideline = ":root { --color-primary: #FFF; }"
    assert lint.lint_deck("<p>#ffffff rgb(255, 255, 255)</p>", guideline) == []


def test_without_tokens_color_and_font_checks_are_skipped():
    findings = lint.lint_deck('<p style="color: #ff0000">x</p>', "# Ohne Tokens")
    assert findings == ["Zeile 1: Inline-Style statt Klasse oder CSS-Variable"]


def test_empty_deck_yields_empty_report():
    assert lint.lint_deck("", GUIDELINE) == []


def test_guideline_tokens_reads_root_block():
    assert lint.guideline_tokens(GUIDELINE)["--color-primary"] == "#1A73E8"


def test_format_report_lists_every_finding():
    report = lint.format_report(["Zeile 1: A", "Zeile 2: B"])
    assert "- Zeile 1: A" in report
    assert "- Zeile 2: B" in report
