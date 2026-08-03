"""Deterministic layout CSS built from extracted slide-master tokens.

The slide master already carries every box the deck is allowed to use. This
module turns `pptx_design_tokens.json` (output of
`01-design-guideline/extract_pptx_theme.py`) into a finished `<style>` block
plus a machine-readable layout catalog, so the model places content into
known slots instead of inventing layout CSS on every run.

Geometry is emitted as a percentage of the slide, never in cm — the deck
scales, the proportions of the master do not change.
"""

import re
import unicodedata

# The generated deck uses a fixed pixel canvas; the master only decides its
# aspect ratio. 1920 wide matches the size the HTML prompt already asks for.
SLIDE_WIDTH_PX = 1920
_CM_PER_INCH = 2.54
_PT_PER_INCH = 72
_DEFAULT_ASPECT = 16 / 9

# Placeholder types that follow the master's titleStyle; everything else that
# holds text follows bodyStyle.
_TITLE_TYPES = frozenset({"TITLE", "CENTER_TITLE", "CTR_TITLE"})

# <a:*/@algn> values as they appear in a master's txStyles
_ALIGN = {"l": "left", "ctr": "center", "r": "right", "just": "justify"}

# Scheme color aliases used in shape/background references
_SCHEME_ALIASES = {"tx1": "dk1", "bg1": "lt1", "tx2": "dk2", "bg2": "lt2"}

_SYS_SUFFIX_RE = re.compile(r"\s*\(sysClr:[^)]*\)\s*$")
_NON_SLUG_RE = re.compile(r"[^a-z0-9]+")

# Content components. A slide master knows single boxes, not multi-column
# content blocks — without these the model improvises them silently. Scoped
# under `.ph` so they can only ever act inside a placeholder box.
COMPONENT_CSS = """/* Komponenten — nur innerhalb eines Platzhalters (.ph) wirksam */
.ph .cards,
.ph .kpis {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 2%;
  height: 100%;
}
.ph .kpis { align-items: center; }
.ph .card {
  display: grid;
  align-content: start;
  gap: 0.4em;
  padding: 1em;
  border: 1px solid currentColor;
}
.ph .card-title { font-family: var(--font-heading); }
.ph .kpi { display: grid; gap: 0.2em; }
.ph .kpi-value {
  font-family: var(--font-heading);
  font-size: var(--title-size-1, inherit);
  line-height: 1;
}
.ph .kpi-label { font-size: var(--body-size-2, var(--body-size-1, inherit)); }
.ph .data-table {
  width: 100%;
  border-collapse: collapse;
}
.ph .data-table th,
.ph .data-table td {
  padding: 0.4em 0.6em;
  text-align: left;
  border-bottom: 1px solid currentColor;
}
.ph .data-table th { font-family: var(--font-heading); }
.ph .quote {
  display: grid;
  align-content: center;
  gap: 0.6em;
  height: 100%;
}
.ph .quote-text {
  font-family: var(--font-heading);
  font-size: var(--title-size-1, inherit);
}
.ph .quote-source { font-size: var(--body-size-2, var(--body-size-1, inherit)); }"""

# Marker line of the generated block, used both when writing it and when
# finding it again in a deck that came back from the model.
MASTER_CSS_MARKER = "/* Automatisch aus dem Folienmaster erzeugt — nicht verändern. */"

# What the model sees instead of the block during an iteration. Sending the
# block costs context on every round and invites edits to it (Issue #79).
MASTER_CSS_PLACEHOLDER = "<!-- FOLIENMASTER-CSS: unverändert übernehmen -->"

_MASTER_CSS_RE = re.compile(
    r"<style>\s*/\* Automatisch aus dem Folienmaster erzeugt.*?</style>", re.DOTALL
)

COMPONENT_CLASSES = (
    "cards",
    "card",
    "card-title",
    "kpis",
    "kpi",
    "kpi-value",
    "kpi-label",
    "data-table",
    "quote",
    "quote-text",
    "quote-source",
)


def cm_to_percent(value_cm: float | None, total_cm: float | None) -> float | None:
    """Position or size in cm as a percentage of the slide edge it sits on.

    Returns None when either value is missing — a placeholder without geometry
    gets no rule rather than a wrong one.
    """
    if value_cm is None or not total_cm:
        return None
    return round(value_cm / total_cm * 100, 3)


def slugify(name: str) -> str:
    """ASCII kebab-case slug usable as a CSS class name."""
    ascii_name = (
        unicodedata.normalize("NFKD", name or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = _NON_SLUG_RE.sub("-", ascii_name.lower()).strip("-")
    return slug or "layout"


def _hex(value: str | None) -> str | None:
    """Strip the `(sysClr: ...)` annotation the extractor appends."""
    if not value:
        return None
    return _SYS_SUFFIX_RE.sub("", value).strip() or None


def _resolve_color(value: str | None, theme_colors: dict) -> str | None:
    """Resolve `#RRGGBB` or `scheme:<name>` against the theme palette."""
    if not value:
        return None
    if value.startswith("scheme:"):
        key = value.split(":", 1)[1]
        key = _SCHEME_ALIASES.get(key, key)
        if key not in theme_colors:
            return None
        return f"var(--color-{key})"
    return _hex(value)


def _slide_px(tokens: dict) -> tuple[int, int]:
    aspect = tokens.get("aspect_ratio")
    if not aspect:
        width_cm = tokens.get("slide_width_cm")
        height_cm = tokens.get("slide_height_cm")
        aspect = width_cm / height_cm if width_cm and height_cm else _DEFAULT_ASPECT
    return SLIDE_WIDTH_PX, round(SLIDE_WIDTH_PX / aspect)


def _px_per_pt(tokens: dict) -> float:
    """Scale factor between master point sizes and the pixel canvas."""
    height_cm = tokens.get("slide_height_cm")
    _, height_px = _slide_px(tokens)
    if not height_cm:
        return 1.0
    height_pt = height_cm / _CM_PER_INCH * _PT_PER_INCH
    return height_px / height_pt


def _style_level(tokens: dict, kind: str, level: int) -> dict | None:
    for entry in tokens.get("text_styles", {}).get(kind, []):
        if entry.get("level") == level:
            return entry
    return None


def layouts(tokens: dict, selected: list[str] | None = None) -> list[dict]:
    """Machine-readable catalog of the master's layouts and their slots.

    `selected` filters by layout slug; None means every layout. Each entry
    carries the CSS class names step 3 has to use, so the catalog and the
    generated CSS can never drift apart.
    """
    result = []
    used_slugs: set[str] = set()
    for layout in tokens.get("layouts", []):
        slug = slugify(layout.get("layout_name", ""))
        if slug in used_slugs:
            slug = f"{slug}-{len(used_slugs)}"
        used_slugs.add(slug)
        if selected is not None and slug not in selected:
            continue

        slots = []
        for ph in layout.get("placeholders", []):
            type_name = ph.get("type_name") or "BODY"
            slots.append(
                {
                    "name": ph.get("name"),
                    "type": type_name,
                    "css_class": f"slot-{slugify(type_name)}-{ph.get('idx')}",
                    "left_pct": cm_to_percent(
                        ph.get("left_cm"), tokens.get("slide_width_cm")
                    ),
                    "top_pct": cm_to_percent(
                        ph.get("top_cm"), tokens.get("slide_height_cm")
                    ),
                    "width_pct": cm_to_percent(
                        ph.get("width_cm"), tokens.get("slide_width_cm")
                    ),
                    "height_pct": cm_to_percent(
                        ph.get("height_cm"), tokens.get("slide_height_cm")
                    ),
                }
            )
        result.append(
            {
                "name": layout.get("layout_name"),
                "css_class": f"layout-{slug}",
                "slug": slug,
                "background": layout.get("background", {}),
                "slots": slots,
            }
        )
    return result


def _root_block(tokens: dict) -> str:
    width_px, height_px = _slide_px(tokens)
    px_per_pt = _px_per_pt(tokens)
    lines = [
        f"  --slide-width: {width_px}px;",
        f"  --slide-height: {height_px}px;",
    ]

    fonts = tokens.get("theme_fonts", {})
    if fonts.get("heading_font"):
        lines.append(f'  --font-heading: "{fonts["heading_font"]}", sans-serif;')
    if fonts.get("body_font"):
        lines.append(f'  --font-body: "{fonts["body_font"]}", sans-serif;')

    for name, value in tokens.get("theme_colors", {}).items():
        if name.startswith("_"):
            continue
        color = _hex(value)
        if color:
            lines.append(f"  --color-{name}: {color};")

    for kind in ("title", "body"):
        for entry in tokens.get("text_styles", {}).get(kind, []):
            level = entry["level"]
            if entry.get("font_size_pt"):
                size_px = round(entry["font_size_pt"] * px_per_pt, 1)
                lines.append(f"  --{kind}-size-{level}: {size_px}px;")
            color = _resolve_color(entry.get("color"), tokens.get("theme_colors", {}))
            if color:
                lines.append(f"  --{kind}-color-{level}: {color};")

    return ":root {\n" + "\n".join(lines) + "\n}"


def _base_block(tokens: dict) -> str:
    background = _resolve_color(
        tokens.get("master_background", {}).get("color"), tokens.get("theme_colors", {})
    )
    slide_rules = [
        "  position: relative;",
        "  box-sizing: border-box;",
        "  width: var(--slide-width);",
        "  height: var(--slide-height);",
        "  overflow: hidden;",
    ]
    if tokens.get("theme_fonts", {}).get("body_font"):
        slide_rules.append("  font-family: var(--font-body);")
    if background:
        slide_rules.append(f"  background: {background};")
    return (
        ".slide {\n" + "\n".join(slide_rules) + "\n}\n"
        "\n"
        ".ph {\n"
        "  position: absolute;\n"
        "  box-sizing: border-box;\n"
        "  margin: 0;\n"
        "}"
    )


def _slot_rule(layout_class: str, slot: dict, tokens: dict) -> str | None:
    geometry = [
        ("left", slot["left_pct"]),
        ("top", slot["top_pct"]),
        ("width", slot["width_pct"]),
        ("height", slot["height_pct"]),
    ]
    declarations = [f"  {prop}: {pct}%;" for prop, pct in geometry if pct is not None]
    if not declarations:
        return None

    kind = "title" if slot["type"] in _TITLE_TYPES else "body"
    level = _style_level(tokens, kind, 1)
    if level:
        if level.get("font_size_pt"):
            declarations.append(f"  font-size: var(--{kind}-size-1);")
        if _resolve_color(level.get("color"), tokens.get("theme_colors", {})):
            declarations.append(f"  color: var(--{kind}-color-1);")
        if level.get("align") in _ALIGN:
            declarations.append(f"  text-align: {_ALIGN[level['align']]};")
    if kind == "title" and tokens.get("theme_fonts", {}).get("heading_font"):
        declarations.append("  font-family: var(--font-heading);")

    return (
        f".{layout_class} .{slot['css_class']} {{\n" + "\n".join(declarations) + "\n}"
    )


def build_css(tokens: dict, selected: list[str] | None = None) -> str:
    """Complete `<style>` block for the master's layouts.

    Goes into the deck verbatim; the model fills the slots but never edits
    these rules.
    """
    catalog = layouts(tokens, selected)
    blocks = [
        "<style>",
        MASTER_CSS_MARKER,
        _root_block(tokens),
        "",
        _base_block(tokens),
    ]

    theme_colors = tokens.get("theme_colors", {})

    for layout in catalog:
        blocks.append("")
        blocks.append(f"/* Layout: {layout['name']} */")
        background = _resolve_color(layout["background"].get("color"), theme_colors)
        if background:
            blocks.append(f".{layout['css_class']} {{\n  background: {background};\n}}")
        for slot in layout["slots"]:
            rule = _slot_rule(layout["css_class"], slot, tokens)
            if rule:
                blocks.append(rule)

    blocks += ["", COMPONENT_CSS, "</style>"]
    return "\n".join(blocks)


def split_master_css(deck_html: str) -> tuple[str, str]:
    """Cut the generated block out of a deck, leaving a placeholder comment.

    Returns `(deck_without_block, block)`. A deck built without a slide master
    has no block — then the html comes back unchanged and the block is empty.
    """
    match = _MASTER_CSS_RE.search(deck_html or "")
    if not match:
        return deck_html, ""
    stripped = (
        deck_html[: match.start()] + MASTER_CSS_PLACEHOLDER + deck_html[match.end() :]
    )
    return stripped, match.group()


def restore_master_css(deck_html: str, block: str) -> str:
    """Put the generated block back where the placeholder comment sits.

    The model is told to keep the comment in place; if it dropped it anyway,
    the block goes in before `</head>` (or at the front) rather than being
    lost — a deck without its master CSS has no layout at all.
    """
    if not block:
        return deck_html
    if MASTER_CSS_PLACEHOLDER in deck_html:
        return deck_html.replace(MASTER_CSS_PLACEHOLDER, block, 1)
    if _MASTER_CSS_RE.search(deck_html):
        # Model reproduced a block of its own — replace it with the original.
        return _MASTER_CSS_RE.sub(lambda _: block, deck_html, count=1)
    if "</head>" in deck_html:
        return deck_html.replace("</head>", f"{block}\n</head>", 1)
    return f"{block}\n{deck_html}"


def catalog_markdown(tokens: dict, selected: list[str] | None = None) -> str:
    """The layout catalog as prompt text for steps 2 and 3."""
    entries = layouts(tokens, selected)
    if not entries:
        return "Keine Folienlayouts verfügbar."

    lines = ["Verfügbare Folienlayouts aus dem Folienmaster:", ""]
    for layout in entries:
        section = f'`<section class="slide {layout["css_class"]}">`'
        lines.append(f"- **{layout['name']}** — {section}")
        for slot in layout["slots"]:
            if slot["left_pct"] is None:
                continue
            lines.append(
                f'  - `<div class="ph {slot["css_class"]}">` — '
                f"{slot['type']} ({slot['name']})"
            )
    lines += [
        "",
        "Komponenten für das Innenleben eines Inhaltsplatzhalters "
        "(nur innerhalb von `.ph` wirksam): "
        + ", ".join(f"`{name}`" for name in COMPONENT_CLASSES)
        + ".",
    ]
    return "\n".join(lines)
