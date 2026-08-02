"""
Extrahiert Design-Tokens aus einem PowerPoint-Folienmaster (.potx oder .pptx):
Theme-Farben, Schriftfamilien, Layout-Namen, Platzhalter-Positionen.

Benoetigt: pip install python-pptx

Aufruf:
    python extract_pptx_theme.py "Folienmaster.potx"

Output:
    pptx_design_tokens.json  (im selben Ordner)
"""

import json
import sys

from pptx import Presentation
from pptx.util import Emu


def emu_to_cm(value):
    if value is None:
        return None
    return round(Emu(value).cm, 2)


def extract_theme_colors(prs):
    """Liest die 12 Theme-Farben (Accent1-6, Dark1/2, Light1/2, Hyperlink,
    FollowedHyperlink)."""
    colors = {}
    try:
        # python-pptx legt Theme-Farben nicht direkt offen; über den Theme-Part gehen
        master = prs.slide_masters[0]
        theme_part = master.part.part_related_by(
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
        )
        xml = theme_part.blob.decode("utf-8", errors="ignore")

        import re

        # sucht srgbClr Werte innerhalb der clrScheme
        scheme_match = re.search(r"<a:clrScheme.*?</a:clrScheme>", xml, re.DOTALL)
        if scheme_match:
            scheme_xml = scheme_match.group(0)
            entries = re.findall(
                r'<a:(\w+)>\s*<a:srgbClr val="([0-9A-Fa-f]{6})"', scheme_xml
            )
            for name, hexval in entries:
                colors[name] = f"#{hexval.upper()}"
            # sysClr (z.B. für dk1/lt1 die windowText/window referenzieren)
            sys_entries = re.findall(
                r'<a:(\w+)>\s*<a:sysClr val="(\w+)" lastClr="([0-9A-Fa-f]{6})"',
                scheme_xml,
            )
            for name, sysname, hexval in sys_entries:
                colors[name] = f"#{hexval.upper()} (sysClr: {sysname})"
    except Exception as e:
        colors["_error"] = str(e)
    return colors


def extract_theme_fonts(prs):
    fonts = {}
    try:
        master = prs.slide_masters[0]
        theme_part = master.part.part_related_by(
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
        )
        xml = theme_part.blob.decode("utf-8", errors="ignore")

        import re

        major = re.search(
            r'<a:majorFont>.*?<a:latin typeface="([^"]+)"', xml, re.DOTALL
        )
        minor = re.search(
            r'<a:minorFont>.*?<a:latin typeface="([^"]+)"', xml, re.DOTALL
        )
        fonts["heading_font"] = major.group(1) if major else None
        fonts["body_font"] = minor.group(1) if minor else None
    except Exception as e:
        fonts["_error"] = str(e)
    return fonts


def extract_layouts(prs):
    layouts = []
    for master_idx, master in enumerate(prs.slide_masters):
        for layout in master.slide_layouts:
            placeholders = []
            for ph in layout.placeholders:
                placeholders.append(
                    {
                        "idx": ph.placeholder_format.idx,
                        "type": str(ph.placeholder_format.type),
                        "name": ph.name,
                        "left_cm": emu_to_cm(ph.left),
                        "top_cm": emu_to_cm(ph.top),
                        "width_cm": emu_to_cm(ph.width),
                        "height_cm": emu_to_cm(ph.height),
                    }
                )
            layouts.append(
                {
                    "master_index": master_idx,
                    "layout_name": layout.name,
                    "placeholders": placeholders,
                }
            )
    return layouts


def extract(pptx_path: str):
    prs = Presentation(pptx_path)

    slide_width_cm = emu_to_cm(prs.slide_width)
    slide_height_cm = emu_to_cm(prs.slide_height)

    result = {
        "source_file": pptx_path,
        "slide_width_cm": slide_width_cm,
        "slide_height_cm": slide_height_cm,
        "aspect_ratio": (
            round(prs.slide_width / prs.slide_height, 3) if prs.slide_height else None
        ),
        "theme_colors": extract_theme_colors(prs),
        "theme_fonts": extract_theme_fonts(prs),
        "layouts": extract_layouts(prs),
    }
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pptx_theme.py <pptx-oder-potx-datei>")
        sys.exit(1)

    pptx_path = sys.argv[1]
    data = extract(pptx_path)

    out_path = "pptx_design_tokens.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Fertig. Ergebnis geschrieben nach: {out_path}")
    print(f"Folienformat: {data['slide_width_cm']} x {data['slide_height_cm']} cm")
    print(f"Theme-Farben: {data['theme_colors']}")
    print(f"Theme-Fonts: {data['theme_fonts']}")
    print(f"Anzahl Layouts gefunden: {len(data['layouts'])}")
