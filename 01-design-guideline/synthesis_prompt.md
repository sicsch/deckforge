Kopiere den folgenden Prompt in deinen Chatbot (ohne Tools). Füge darunter
den Inhalt von `pdf_design_tokens.json` und `pptx_design_tokens.json` ein.

---

Du bekommst zwei JSON-Dateien mit automatisiert extrahierten Design-Werten:

1. `pdf_design_tokens.json` — aus einem Geschäftsbericht (PDF), enthält
   Schriftarten, Schriftgrößen, Text- und Grafikfarben nach Häufigkeit
2. `pptx_design_tokens.json` — aus einem internen Folienmaster (PPTX),
   enthält Theme-Farben, Heading-/Body-Font, Folienformat, Layouts mit
   Platzhalter-Positionen

Aufgabe: Erstelle daraus eine Design-Guideline für HTML-Präsentationen im
jeweiligen Corporate Design.

Regeln:
- Der Folienmaster (pptx_design_tokens.json) ist die Source of Truth für
  Farben, Fonts und Layout-Raster, da er offiziell für Präsentationen
  freigegeben ist.
- Das PDF (Geschäftsbericht) nutzt du nur ergänzend: für Diagramm-/
  Chart-Farblogik, Bildsprache, und um zu prüfen, ob die im Master
  definierten Farben in der Praxis konsistent verwendet werden.
- Wenn Werte zwischen beiden Quellen abweichen, liste den Konflikt explizit
  auf und markiere, welchen Wert du übernommen hast und warum.
- Keine Floskeln, alles als konkrete Regeln + Werte. Markiere Annahmen
  dort, wo die extrahierten Daten unklar oder unvollständig sind.

Liefere als Markdown:
- North Star (Wirkung, 1-Satz-Prinzip, 3-5 Merkmale)
- Farben + Regeln + No-Gos (mit Hex-Werten aus den Theme-Farben)
- Typo-Skalen (H1/H2/Body/Label/Sonstige) basierend auf den häufigsten
  Font-Größen und den Theme-Fonts
- Layout-System (Seitenformat/Aspect Ratio aus dem Folienmaster, Grid,
  Ränder, Weißraum, Footer, Sonstige)
- Komponenten (Card/Badge/Table/Framework/Sonstige): Aufbau + Regeln,
  abgeleitet aus den Platzhalter-Positionen der Layouts
- Bildsprache (Icons/Bilder/Diagramm-Farblogik aus dem Geschäftsbericht)
- 6–10 Folientypen (Zweck, Layout, Visual-Logik, Sonstige), abgeleitet aus
  den vorhandenen Folienmaster-Layouts
- 10 Hard Rules + QC-Checkliste
- CSS Tokens (colors/typography/spacing/radius/shadow/lines/other) als
  fertiges CSS-Variablen-Snippet (:root { --... })

[HIER pdf_design_tokens.json EINFÜGEN]

[HIER pptx_design_tokens.json EINFÜGEN]
