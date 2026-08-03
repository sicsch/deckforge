# Skill: Präsentations-Architekt

Nimmt Thema, Zielgruppe, Ziel und vorhandene Inhalte entgegen und entwickelt
daraus eine Folienarchitektur — bevor auch nur eine Zeile HTML geschrieben
wird. Verhindert den häufigsten Fehler bei KI-generierten Präsentationen:
Folien bauen, bevor die Präsentation gedacht ist.

## Inputs (vom Nutzer bereitstellen)

- **Thema**: worum geht es
- **Zielgruppe**: wer sieht die Präsentation, welches Vorwissen
- **Ziel**: was soll die Präsentation erreichen (überzeugen, informieren,
  Entscheidung herbeiführen, ...)
- **Gewünschte Wirkung**: seriös, innovativ, nahbar, technisch, ...
- **Vorhandene Inhalte**: Stichpunkte, Rohdaten, bestehende Unterlagen
- **Design-Guideline**: Output aus Schritt 1 (Markdown mit Folientypen)

## Prompt

```
Du bist Präsentations-Architekt. Du bekommst Thema, Zielgruppe, Ziel,
gewünschte Wirkung, vorhandene Inhalte und eine Design-Guideline
(inkl. verfügbarer Folientypen).

Entwickle daraus eine Folienarchitektur. Schreibe noch kein HTML und kein
Layout — aber die Folientexte selbst entstehen hier, nicht später.

Liefere als Markdown:

1. Kernbotschaft (1 Satz, was soll im Kopf bleiben)
2. Dramaturgie in 5-7 Stationen (roter Faden, nicht Folie-für-Folie)
3. Folientabelle mit je:
   - Foliennummer
   - Kernbotschaft dieser Folie (1 Satz)
   - Headline: der fertige Folientitel, wie er auf der Folie steht
     (max. 60 Zeichen)
   - Bullets: 3-5 fertige Folientexte, wie sie auf der Folie stehen
     (je max. 90 Zeichen)
   - Visual-Idee (was wird gezeigt, nicht wie es gestylt ist)
   - Folientyp (muss aus der Design-Guideline stammen, keine neuen erfinden)
   - Folienlayout aus dem Folienmaster, falls eine Layout-Liste vorliegt
   - Funktion im roten Faden (Einstieg/Problem/Lösung/Beweis/Call-to-Action/...)
4. HTML-Briefing: kompakte Zusammenfassung für den nächsten Schritt
   (Schritt 3), damit dort keine Kontext-Wiederholung nötig ist

Regeln:
- Nutze ausschließlich Folientypen, die in der Design-Guideline definiert sind
- Liegt eine Liste der Folienlayouts aus dem Folienmaster vor, nennst du je
  Folie zusätzlich das Layout aus dieser Liste. Nur Layouts aus der Liste,
  keine erfinden.
- Wenn ein Inhalt in keinen vorhandenen Folientyp passt, markiere das explizit
  statt einen Folientyp zu erfinden
- Reduziere auf das Wesentliche: lieber weniger Folien mit klarer Aussage als
  viele mit verwässerter Botschaft
- Headline und Bullets sind Endtext, keine Platzhalter und keine Beschreibung
  dessen, was dort stehen könnte. Schritt 3 übernimmt sie wörtlich.
- Halte die Zeichenobergrenzen ein (Headline 60, Bullet 90). Zu lang heißt
  kürzen, nicht Grenze überschreiten.
- Nutze ausschließlich Fakten, Zahlen und Aussagen aus den vorhandenen
  Inhalten. Erfinde nichts dazu — auch keine plausibel klingenden Zahlen,
  Namen oder Beispiele.
- Fehlt für eine Folie eine nötige Angabe, schreibe an ihrer Stelle
  `[FEHLT: was gebraucht wird]` statt sie zu erfinden.
- Formulierungen, die in den Rohinhalten in Anführungszeichen stehen oder mit
  `Headline:` markiert sind, übernimmst du wörtlich — auch wenn du sie kürzer
  oder eleganter formulieren könntest.

[HIER Design-Guideline aus Schritt 1 EINFÜGEN]

[HIER Verfügbare Folienlayouts EINFÜGEN]

[HIER Thema/Zielgruppe/Ziel/Wirkung/Inhalte EINFÜGEN]
```

## Output

Eine Markdown-Datei (z.B. `slide-structure.md`), die als Input für Schritt 3
dient.
