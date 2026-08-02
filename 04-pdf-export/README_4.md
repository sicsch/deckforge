# Schritt 4: PDF-Export

Rendert das fertige HTML-Deck (aus Schritt 3) als versendbares PDF.

## Dateien

- `export_to_pdf.py` — Playwright-basierter Export. Rendert mit echtem
  Headless-Chrome, damit `@media print`-Regeln, Seitenumbrüche und
  Hintergrundfarben korrekt übernommen werden.

## Nutzung

```bash
pip install playwright
playwright install chromium

python export_to_pdf.py deck.html deck.pdf
```

Optionen:
- `--width` / `--height`: Seitengröße in px (Default 1920x1080 = 16:9)
- `--portrait`: Hochformat statt Querformat

## Manuelle Alternative (ohne Python-Setup)

Falls Playwright nicht installiert werden kann/darf:

1. HTML-Datei im Browser öffnen
2. Strg/Cmd+P (Drucken)
3. Ziel: "Als PDF speichern"
4. Layout: Querformat
5. Ränder: Keine
6. Hintergrundgrafiken: aktivieren
7. Skalierung: 100 %

Playwright liefert konsistentere Ergebnisse (kein Browser-abhängiges
Rendering, kein manuelles Anpassen der Druckeinstellungen nötig), ist
aber für Einzeldecks nicht zwingend nötig.
