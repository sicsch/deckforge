# Skill: HTML-Deck-Iteration per Chat

Nimmt ein bestehendes HTML-Deck und einen Änderungswunsch entgegen und
liefert das überarbeitete Deck zurück — ohne die Konversation neu
aufzurollen. Nur der aktuelle Stand und der jeweilige Änderungswunsch gehen
in den Prompt, nicht der komplette Chatverlauf (Kontextfenster-Disziplin,
siehe CLAUDE.md).

## Inputs (von der App bereitgestellt)

- **Aktuelles HTML-Deck**: der bisherige Stand aus Schritt 3
- **Änderungswunsch**: die Freitext-Nachricht des Nutzers aus dem Chat

## Prompt

```
Du bist HTML-Präsentations-Entwickler. Du bekommst ein bestehendes
HTML-Deck und einen Änderungswunsch dazu.

Wende den Änderungswunsch gezielt an und gib das vollständige,
überarbeitete HTML-Dokument zurück.

Regeln:
- Ändere nur, was der Änderungswunsch verlangt — der Rest bleibt erhalten
  (kein komplettes Neu-Generieren des Decks von Grund auf)
- Die @media-print-Regeln bleiben vollständig erhalten, außer der
  Änderungswunsch betrifft sie explizit
- Die feste Foliengröße (`.slide` mit `width`, `height`, `overflow: hidden`)
  und das Overflow-Markierungs-Script am Ende des <body> bleiben unverändert
  erhalten, außer der Änderungswunsch betrifft sie explizit
- Bestehende CSS-Variablen, Komponenten-Klassen und Folienstruktur bleiben
  konsistent — keine neuen Ad-hoc-Styles, wo vorhandene Komponenten reichen
- Keine Rückfragen, keine Kommentare außerhalb des Dokuments — nur das
  vollständige, in sich valide HTML-Dokument

[HIER Aktuelles HTML-Deck EINFÜGEN]

[HIER Änderungswunsch EINFÜGEN]
```

## Output

Das vollständige, überarbeitete HTML-Dokument — ersetzt den bisherigen
Stand aus Schritt 3.
