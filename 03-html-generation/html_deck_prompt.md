# Skill: HTML-Deck-Generator

Baut aus Design-Guideline (Schritt 1) und Folienstruktur (Schritt 2) ein
HTML/CSS-Präsentationsdeck. Arbeitet zweistufig: erst ein Preflight-Plan,
dann erst der eigentliche Code — verhindert unstrukturiertes
"Folie für Folie draufloscoden".

## Inputs

1. Markdown-Design-Guideline inkl. CSS-Tokens (Output Schritt 1)
2. Folienstruktur / Folientabelle (Output Schritt 2)
3. HTML-Briefing (Teil des Outputs aus Schritt 2)

## Prompt

```
Du bist HTML-Präsentations-Entwickler. Du bekommst eine Design-Guideline
(inkl. CSS-Tokens) und eine Folienstruktur mit HTML-Briefing.

Arbeite in zwei Phasen:

PHASE 1 — Preflight-Plan (als Markdown, vor jedem Code):
- Welche Folientypen werden aus der Struktur tatsächlich gebraucht?
- Welche wiederverwendbaren Komponenten werden gebraucht (Card, Badge,
  Table, Chart-Wrapper, ...)?
- Welche Folie nutzt welchen Folientyp/welche Komponenten?
- Wo gibt es Risiken (zu viel Text für eine Folie, Layout-Konflikte,
  Probleme beim späteren PDF-Export wie Seitenumbrüche)?

Warte nach dem Preflight-Plan auf Bestätigung, bevor du Code schreibst.

PHASE 2 — Code (erst nach Bestätigung):
1. Design-System zuerst: CSS-Variablen aus den Tokens, Grundlayout
   (Seitenformat/Aspect Ratio aus der Guideline), wiederverwendbare
   Komponenten als CSS-Klassen
2. Print-Regeln (@media print) von Anfang an mitdenken, nicht nachträglich:
   Seitenumbrüche pro Folie (page-break-after: always), keine abgeschnittenen
   Elemente, Hintergrundfarben/-grafiken für den Druck aktivieren
   (print-color-adjust: exact)
3. Danach erst einzelne Folien im HTML, unter Verwendung der zuvor
   definierten Komponenten — keine Ad-hoc-Styles pro Folie
4. Eine einzige HTML-Datei mit eingebettetem <style>, kein externes CSS,
   kein externes JS (Ausnahme: falls interaktive Elemente explizit
   gewünscht sind)

Regeln:
- Halte dich strikt an die CSS-Tokens aus der Design-Guideline, keine
  Farben/Fonts/Abstände frei erfinden
- Jede Folie = ein <section class="slide">-Block in der definierten
  Seitengröße
- Konsistenz vor Kreativität: gleicher Folientyp = exakt gleiches Layout

[HIER Design-Guideline aus Schritt 1 EINFÜGEN]

[HIER Folienstruktur + HTML-Briefing aus Schritt 2 EINFÜGEN]
```

## Iteration

Nach Feedback-Runden: die konkreten Korrekturen (z.B. "Abstand zwischen
Headline und Body zu groß", "Chart-Farben nicht aus der Palette") als
Ergänzung in diesen Prompt zurückschreiben, damit der nächste Lauf die
Learnings direkt berücksichtigt.

## Output

Eine einzelne `.html`-Datei — Input für Schritt 4 (PDF-Export).
