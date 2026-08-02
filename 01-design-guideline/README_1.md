# Schritt 1: Design-Guideline-Extraktion

Extrahiert Design-Tokens aus zwei möglichen Quellen und führt sie zu einer
einheitlichen Markdown-Design-Guideline mit CSS-Variablen zusammen.

## Dateien

- `extract_pdf_design.py` — Fonts, Schriftgrößen, Text-/Grafikfarben aus
  einem PDF (z.B. Geschäftsbericht). Benötigt `pymupdf`.
- `extract_pptx_theme.py` — Theme-Farben, Fonts, Layouts, Platzhalter-
  Positionen aus einem Folienmaster (.pptx/.potx). Benötigt `python-pptx`.
- `synthesis_prompt.md` — Fertiger Prompt, um beide JSON-Outputs in einem
  Chatbot (auch ohne Tool-Zugriff) zu einer Markdown-Design-Guideline
  zusammenzuführen.

## Nutzung

```bash
pip install pymupdf python-pptx

python extract_pdf_design.py "Geschaeftsbericht.pdf"
python extract_pptx_theme.py "Folienmaster.potx"
```

Beide erzeugten JSON-Dateien anschließend gemeinsam mit dem Inhalt von
`synthesis_prompt.md` in einen Chatbot geben.

## Priorität bei Konflikten

Folienmaster > Geschäftsbericht/PDF. Der Master ist die offiziell
freigegebene Quelle für Präsentationen; das PDF liefert nur ergänzende
Hinweise (z.B. Diagramm-Farblogik, Bildsprache).
