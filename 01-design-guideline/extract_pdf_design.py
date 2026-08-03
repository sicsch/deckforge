"""
Extrahiert Design-relevante Werte aus einem PDF (z.B. Geschäftsbericht):
Schriftarten, Schriftgrößen, Farben, Seitenmaße.

Benötigt: pip install pymupdf

Aufruf:
    python extract_pdf_design.py "Geschaeftsbericht.pdf"
    python extract_pdf_design.py "Geschaeftsbericht.pdf" --render-pages 8

Output:
    pdf_design_tokens.json  (im selben Ordner)
    pdf_pages/page-NN.png   (nur mit --render-pages)
"""

import argparse
import json
from collections import Counter
from pathlib import Path

import fitz  # PyMuPDF

# ~144 dpi bei A4 — genug, um Raster und Weißraum zu erkennen, ohne dass die
# Bilder zu groß für den Upload in einen Chatbot werden.
_RENDER_ZOOM = 2.0


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
                    r, g, b = (int(c * 255) for c in fill[:3])
                    drawing_colors[f"#{r:02X}{g:02X}{b:02X}"] += 1
                stroke = d.get("color")
                if stroke:
                    r, g, b = (int(c * 255) for c in stroke[:3])
                    drawing_colors[f"#{r:02X}{g:02X}{b:02X}"] += 1
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


def render_pages(pdf_path: str, count: int, out_dir: str) -> list[Path]:
    """Write the first `count` pages as PNG.

    The token JSON holds frequencies, not design: no grid, no white space, no
    components, no image language. The guideline prompt (Schritt 1) needs the
    pages themselves for that — this writes them in a form that can be
    attached to a chat.
    """
    doc = fitz.open(pdf_path)
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    matrix = fitz.Matrix(_RENDER_ZOOM, _RENDER_ZOOM)

    written = []
    for index in range(min(count, len(doc))):
        target = directory / f"page-{index + 1:02d}.png"
        doc[index].get_pixmap(matrix=matrix).save(target)
        written.append(target)
    return written


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Design-Tokens aus einem PDF extrahieren."
    )
    parser.add_argument("pdf", help="Pfad zur PDF-Datei")
    parser.add_argument(
        "max_pages",
        nargs="?",
        type=int,
        default=40,
        help="Wie viele Seiten analysiert werden (Standard: 40)",
    )
    parser.add_argument(
        "--render-pages",
        type=int,
        default=0,
        metavar="N",
        help="Die ersten N Seiten zusätzlich als PNG ablegen, "
        "um sie dem Synthese-Prompt als Designreferenz mitzugeben",
    )
    parser.add_argument(
        "--render-dir",
        default="pdf_pages",
        help="Zielordner für die Seitenbilder (Standard: pdf_pages)",
    )
    args = parser.parse_args()

    data = extract(args.pdf, args.max_pages)

    out_path = "pdf_design_tokens.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    if args.render_pages:
        pages = render_pages(args.pdf, args.render_pages, args.render_dir)
        print(f"{len(pages)} Seitenbilder geschrieben nach: {args.render_dir}/")

    print(f"Fertig. Ergebnis geschrieben nach: {out_path}")
    print(f"Analysierte Seiten: {data['pages_analyzed']}")
    print(f"Top 5 Farben (Text): {[c['hex'] for c in data['text_colors_ranked'][:5]]}")
    top_grafik = [c["hex"] for c in data["drawing_fill_stroke_colors_ranked"][:5]]
    print(f"Top 5 Farben (Grafik): {top_grafik}")
    print(f"Top 5 Fonts: {[c['font'] for c in data['fonts_ranked'][:5]]}")
