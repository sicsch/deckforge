# deckforge

Präsentationen im designated Design mit KI erstellen — über HTML statt PowerPoint.

Der Ansatz: Statt eine KI ein schwer kontrollierbares `.pptx` bauen zu lassen,
werden Design-Vorgaben (Farben, Schriften, Layout-Raster) als maschinenlesbare
Tokens aus vorhandenen Quellen extrahiert und als explizite Guideline an einen
HTML-Deck-Generator übergeben. Das Ergebnis lässt sich im Browser prüfen und
als PDF exportieren.

**deckforge ist designagnostisch.** Das Repository enthält keine Corporate-
Design-Daten. Die Guideline entsteht zur Laufzeit aus den Quellen, die du
bereitstellst — für jede Organisation, jedes Design.

## Workflow

| Schritt | Was passiert | Ergebnis |
|---|---|---|
| **1. Guideline** | Design-Tokens aus Folienmaster und Referenzdokument extrahieren und zusammen mit der Referenz selbst zu einer Guideline verdichten | `guideline.md` mit CSS-Tokens |
| **2. Struktur** | Aus Thema, Zielgruppe und Inhalten eine Dramaturgie und Folienarchitektur ableiten | `structure.md` |
| **3. Deck** | Aus Guideline + Struktur ein HTML/CSS-Deck generieren, iterativ verfeinern | `deck.html` |
| **4. Export** | HTML-Deck als PDF rendern | `deck.pdf` |

## Zwei Nutzungsarten

**CLI (verfügbar).** Jeder Schritt einzeln über Skripte und Prompt-Templates.
Schritt 1 und 4 sind Python-Skripte, Schritt 2 und 3 sind Prompt-Vorlagen für
einen beliebigen Chatbot — auch ohne Tool-Zugriff nutzbar.

**Streamlit-App (in Entwicklung).** Schritte 2–4 in einem iterativen UI:
Eingabe und Chat links, Live-Vorschau des gerenderten Decks rechts. Siehe
`docs/tech-spec.md` für die Spezifikation.

## Status

| Komponente | Stand |
|---|---|
| Schritt 1 — Extraktionsskripte + Synthese-Prompt | fertig |
| Schritt 2 — Folienstruktur-Prompt | fertig |
| Schritt 3 — HTML-Generierungs-Prompt | fertig |
| Schritt 4 — PDF-Export-Skript | fertig |
| Streamlit-App | geplant, siehe `docs/tech-spec.md` |

## Setup

```bash
uv sync
uv run playwright install chromium   # nur für PDF-Export nötig
```

Für die App zusätzlich `.env` anlegen (Vorlage: `.env.example`).

## Nutzung (CLI)

```bash
# Schritt 1 — Design-Tokens extrahieren
uv run 01-design-guideline/extract_pdf_design.py referenz.pdf --render-pages 8
uv run 01-design-guideline/extract_pptx_theme.py folienmaster.potx
# Seitenbilder + beide JSON-Outputs + synthesis_prompt.md in einen Chatbot
# geben, der Bilder lesen kann → guideline.md

# Schritt 2 — Folienstruktur
# slide_architect_prompt.md + guideline.md + Thema/Zielgruppe in Chatbot
# → structure.md

# Schritt 3 — HTML-Deck
# html_deck_prompt.md + guideline.md + structure.md in Chatbot
# → deck.html

# Schritt 4 — PDF
uv run 04-pdf-export/export_to_pdf.py deck.html deck.pdf
```

## Struktur

```
01-design-guideline/    Extraktionsskripte (PDF, PPTX) + Synthese-Prompt
02-slide-structure/     Prompt-Template: Präsentations-Architekt
03-html-generation/     Prompt-Template: HTML-Deck-Generator
04-pdf-export/          Playwright-basierter PDF-Export
app/                    Streamlit-App (in Entwicklung)
docs/                   Technische Spezifikation
```

## Lizenz

MIT — siehe `LICENSE`.
