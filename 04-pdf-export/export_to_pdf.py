"""
Rendert eine HTML-Präsentation (aus Schritt 3) als PDF.

Nutzt Playwright (Headless Chrome), damit CSS-Print-Regeln
(@media print, page-break-after, print-color-adjust) korrekt
angewendet werden - konsistenter als der manuelle
Browser-Drucken-Weg.

Benoetigt:
    pip install playwright
    playwright install chromium

Aufruf:
    python export_to_pdf.py deck.html deck.pdf
    python export_to_pdf.py deck.html deck.pdf --width 1920 --height 1080
"""

import sys
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def export(html_path: str, pdf_path: str, width: int, height: int, landscape: bool):
    html_file = Path(html_path).resolve()
    if not html_file.exists():
        print(f"Fehler: {html_file} nicht gefunden.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"file://{html_file}")

        # Sicherstellen, dass Web-Fonts geladen sind, bevor gerendert wird
        page.wait_for_load_state("networkidle")
        page.evaluate("document.fonts.ready")

        page.pdf(
            path=pdf_path,
            width=f"{width}px",
            height=f"{height}px",
            landscape=landscape,
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    print(f"Fertig: {pdf_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HTML-Deck zu PDF exportieren")
    parser.add_argument("html_path", help="Pfad zur HTML-Datei")
    parser.add_argument("pdf_path", help="Zielpfad der PDF-Datei")
    parser.add_argument("--width", type=int, default=1920, help="Seitenbreite in px (Default: 1920, entspricht 16:9)")
    parser.add_argument("--height", type=int, default=1080, help="Seitenhöhe in px (Default: 1080, entspricht 16:9)")
    parser.add_argument("--portrait", action="store_true", help="Hochformat statt Querformat")
    args = parser.parse_args()

    export(args.html_path, args.pdf_path, args.width, args.height, landscape=not args.portrait)
