"""
Extrahiert Design-relevante Werte aus einem PDF (z.B. Geschäftsbericht):
Schriftarten, Schriftgrößen, Farben, Seitenmaße.

Benötigt: pip install pymupdf

Aufruf:
    python extract_pdf_design.py "Geschaeftsbericht.pdf"

Output:
    pdf_design_tokens.json  (im selben Ordner)
"""

import sys
import json
import fitz  # PyMuPDF
from collections import Counter


def rgb_int_to_hex(color_int: int) -> str:
    """PyMuPDF liefert Farben als int; in Hex umwandeln."""
    r = (color_int >> 16) & 255
    g = (color_int >> 8) & 255
    b = color_int & 255
    return f"#{r:02X}{g:02X}{b:02X}"


def extract(pdf_path: str, max_pages: int = 40):
    doc = fitz.open(pdf_path)
    n_pages = min(len(doc), max_pages)

    fonts = Counter()
    font_sizes = Counter()
    text_colors = Counter()
    page_sizes = Counter()
    drawing_colors = Counter()

    for i in range(n_pages):
        page = doc[i]
        page_sizes[(round(page.rect.width), round(page.rect.height))] += 1

        # Text: Fonts, Größen, Farben
        raw = page.get_text("dict")
        for block in raw.get("blocks", []):
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    fonts[span.get("font", "unknown")] += 1
                    font_sizes[round(span.get("size", 0), 1)] += 1
                    color = span.get("color", 0)
                    if color:
                        text_colors[rgb_int_to_hex(color)] += 1

        # Vektorgrafiken: Fill-/Stroke-Farben (Balken, Flächen, Linien)
        try:
            drawings = page.get_drawings()
            for d in drawings:
                fill = d.get("fill")
                if fill:
                    hexcol = "#{:02X}{:02X}{:02X}".format(
                        int(fill[0] * 255), int(fill[1] * 255), int(fill[2] * 255)
                    )
                    drawing_colors[hexcol] += 1
                stroke = d.get("color")
                if stroke:
                    hexcol = "#{:02X}{:02X}{:02X}".format(
                        int(stroke[0] * 255), int(stroke[1] * 255), int(stroke[2] * 255)
                    )
                    drawing_colors[hexcol] += 1
        except Exception:
            pass

    result = {
        "source_file": pdf_path,
        "pages_analyzed": n_pages,
        "page_sizes_pt": [
            {"width": w, "height": h, "count": c}
            for (w, h), c in page_sizes.most_common()
        ],
        "fonts_ranked": [
            {"font": f, "occurrences": c} for f, c in fonts.most_common(15)
        ],
        "font_sizes_ranked": [
            {"size_pt": s, "occurrences": c} for s, c in font_sizes.most_common(15)
        ],
        "text_colors_ranked": [
            {"hex": h, "occurrences": c} for h, c in text_colors.most_common(15)
        ],
        "drawing_fill_stroke_colors_ranked": [
            {"hex": h, "occurrences": c} for h, c in drawing_colors.most_common(20)
        ],
    }
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_pdf_design.py <pdf-datei> [max_pages]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 40

    data = extract(pdf_path, max_pages)

    out_path = "pdf_design_tokens.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Fertig. Ergebnis geschrieben nach: {out_path}")
    print(f"Analysierte Seiten: {data['pages_analyzed']}")
    print(f"Top 5 Farben (Text): {[c['hex'] for c in data['text_colors_ranked'][:5]]}")
    print(f"Top 5 Farben (Grafik): {[c['hex'] for c in data['drawing_fill_stroke_colors_ranked'][:5]]}")
    print(f"Top 5 Fonts: {[c['font'] for c in data['fonts_ranked'][:5]]}")
