Kopiere den folgenden Prompt in einen Chatbot, der Bilder lesen kann. Hänge
zusätzlich an:

1. **Die Designreferenz selbst** — als PDF oder als Seitenbilder
   (`extract_pdf_design.py --render-pages 8` legt sie als PNG ab). Ohne sie
   kann das Modell Raster, Weißraum, Komponenten und Bildsprache nicht
   ableiten: in den Token-JSONs steht davon nichts drin.
2. `pdf_design_tokens.json` und `pptx_design_tokens.json`

---

Du bekommst eine Designreferenz als Dokument oder Seitenbilder und zwei JSON-
Dateien mit automatisiert extrahierten Design-Werten:

1. **Designreferenz** (Bilder/PDF) — ein Dokument, das im gewünschten Design
   bereits gut aussieht. Quelle für die Gestaltungslogik: Raster, Weißraum,
   Komponentenaufbau, Farbeinsatz, Bildsprache, Diagrammlogik.
2. `pdf_design_tokens.json` — Häufigkeiten von Schriften, Schriftgrößen,
   Text- und Grafikfarben aus demselben Dokument. Gegenprobe für das, was du
   im Bild siehst.
3. `pptx_design_tokens.json` — aus einem freigegebenen Folienmaster: Theme-
   Farben, Heading-/Body-Font, Folienformat, Textstile je Gliederungsebene
   (`text_styles`), Layouts mit Platzhalter-Positionen und -Typen
   (`type_name`) sowie Hintergrundfüllung je Layout (`background`).

Farbwerte im Folienmaster-JSON stehen als `#RRGGBB` oder als `scheme:<name>`
— letztere löst du über `theme_colors` auf. Fonts `+mj-lt` / `+mn-lt` stehen
für `heading_font` / `body_font`. Ein `background` mit `"fill": "inherited"`
erbt vom `master_background`.

Aufgabe: Erstelle daraus eine Design-Guideline für HTML-Präsentationen im
jeweiligen Corporate Design.

Arbeitsteilung der Quellen — daran hältst du dich:
- **Verbindliche Werte** (Farben, Schriften, Typo-Skala, Seitenformat) kommen
  aus dem Folienmaster. Er ist offiziell freigegeben.
- **Die Gestaltungslogik** (Raster, Weißraum, Komponentenaufbau, Farbeinsatz,
  Bildsprache, Diagrammfarben) kommt aus der Designreferenz. Der Folienmaster
  hat dazu nichts zu sagen — er enthält leere Platzhalterkästen, keine
  Gestaltung. Leite Gestaltungsregeln niemals aus Platzhalter-Positionen ab.
- Weichen Werte zwischen beiden ab, gilt der Master. Nenne den Konflikt
  trotzdem und sag, welchen Wert du übernommen hast.
- Keine Floskeln, alles als konkrete Regeln + Werte. Markiere Annahmen dort,
  wo Daten oder Referenz unklar oder unvollständig sind.

Liefere als Markdown:

- **North Star**: Wirkung, 1-Satz-Prinzip, 3-5 Merkmale
- **Farben**: die Werte aus den Theme-Farben, dazu Einsatzregeln — welche
  Farbe trägt Flächen, welche ist Akzent, wie oft darf der Akzent je Folie
  vorkommen, wann wird eine Folie invertiert (heller Text auf dunkler
  Fläche), in welcher Reihenfolge werden Diagrammfarben vergeben. Dazu No-Gos.
- **Typo-Skalen** (H1/H2/Body/Label/Sonstige): Basis sind `text_styles` aus
  dem Folienmaster je Gliederungsebene. Die Referenz liefert die Gegenprobe,
  ob die Sprünge zwischen den Stufen in der Praxis so aussehen.
- **Layout-System**: Seitenformat und Aspect Ratio aus dem Folienmaster; aus
  der Referenz Grid (Spalten, Rinnen), Seitenränder, Weißraum-Regel,
  Kopf- und Fußzone.
- **Komponenten**: Aufbau und Regeln je Komponente, abgeleitet aus der
  Referenz. Verwende ausschließlich diese Namen, damit Schritt 3 sie bauen
  kann: `card`, `kpi`, `table`, `quote`, `statement`, `process`, `chart`.
  Je Komponente: Aufbau, wann sie verwendet wird, Abstände, Farbeinsatz.
  Kommt eine in der Referenz nicht vor, leite sie aus deren Formensprache ab
  und markiere sie als Annahme.
- **Bildsprache**: Icons, Bilder, Freisteller vs. Vollflächen — und die
  Farblogik für Diagramme (Reihenfolge, Anzahl gleichzeitiger Farben, wie
  eine Reihe hervorgehoben wird).
- **Folientypen**: 6-10 Stück, je mit Zweck, Layout und Visual-Logik. Das ist
  die Auswahl, aus der Schritt 2 wählt — decke den typischen Bogen einer
  Präsentation ab (Titel, Agenda, Kernaussage, Vergleich, Zahlen, Prozess,
  Zitat, Abschluss). Übernimm nicht die Layout-Namen des Folienmasters;
  benenne stattdessen je Folientyp die Komponenten, aus denen er besteht.
- **10 Hard Rules**, prüfbar formuliert (z.B. „Der Akzentton steht je Folie
  auf höchstens einer Fläche" statt „sparsam einsetzen")
- **QC-Checkliste**
- **CSS Tokens** (colors/typography/spacing/radius/shadow/lines/other) als
  fertiges CSS-Variablen-Snippet (`:root { --... }`)
- **Anhang: Master-Layouts** — die Layout-Namen aus `layouts` mit ihren
  Platzhaltertypen, unkommentiert aufgelistet. Der Anhang wird nur gebraucht,
  wenn ein Deck die Geometrie des Folienmasters strikt einhalten muss; im
  Normalfall arbeitet Schritt 3 mit den Folientypen oben.

[HIER Designreferenz als Datei oder Seitenbilder ANHÄNGEN]

[HIER pdf_design_tokens.json EINFÜGEN]

[HIER pptx_design_tokens.json EINFÜGEN]
