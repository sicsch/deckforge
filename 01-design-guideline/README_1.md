# Schritt 1: Design-Guideline-Extraktion

Führt eine Designreferenz und die Design-Tokens zweier Quellen zu einer
Markdown-Design-Guideline mit CSS-Variablen zusammen.

## Dateien

- `extract_pdf_design.py` — Fonts, Schriftgrößen, Text-/Grafikfarben aus
  einem PDF (z.B. Geschäftsbericht). Mit `--render-pages N` legt es die
  ersten N Seiten zusätzlich als PNG ab. Benötigt `pymupdf`.
- `extract_pptx_theme.py` — Theme-Farben, Fonts, Layouts, Platzhalter-
  Positionen und -Typen, Textstile je Gliederungsebene und Hintergrund-
  füllung je Layout aus einem Folienmaster (.pptx/.potx). Benötigt
  `python-pptx`.
- `synthesis_prompt.md` — Fertiger Prompt, um Referenz und JSON-Outputs in
  einem Chatbot zu einer Markdown-Design-Guideline zusammenzuführen.

## Nutzung

```bash
pip install pymupdf python-pptx

python extract_pdf_design.py "Geschaeftsbericht.pdf" --render-pages 8
python extract_pptx_theme.py "Folienmaster.potx"
```

Danach in einen Chatbot geben, **der Bilder lesen kann**:

1. den Inhalt von `synthesis_prompt.md`
2. die Seitenbilder aus `pdf_pages/` (oder das PDF selbst)
3. `pdf_design_tokens.json` und `pptx_design_tokens.json`

## Arbeitsteilung der Quellen

**Der Folienmaster liefert die Werte.** Farben, Schriften, Typo-Skala und
Seitenformat kommen aus ihm — er ist die offiziell freigegebene Quelle.

**Die Referenz liefert die Gestaltungslogik.** Raster, Weißraum,
Komponentenaufbau, Farbeinsatz, Bildsprache und Diagrammfarben stehen im
Folienmaster nicht drin: er enthält leere Platzhalterkästen. Deshalb geht die
Referenz als Bild mit ins Modell und nicht nur als Token-JSON — aus
Häufigkeitstabellen lässt sich keine Gestaltung ableiten.

Weichen Werte zwischen beiden ab, gilt der Master; der Konflikt wird in der
Guideline benannt.

## Was rauskommt

Eine `guideline.md` mit North Star, Farb- und Typo-Regeln, Layout-System,
Komponenten (`card`, `kpi`, `table`, `quote`, `statement`, `process`,
`chart`), Bildsprache, 6-10 Folientypen, Hard Rules, QC-Checkliste und einem
`:root`-Block mit allen CSS-Tokens. Die Folientypen sind die Auswahl für
Schritt 2, die Komponenten das Baukastenset für Schritt 3.

Die Layout-Namen des Folienmasters stehen nur noch im Anhang — sie werden
gebraucht, wenn ein Deck dessen Geometrie strikt einhalten soll.
