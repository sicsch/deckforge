# Skill: Struktur-Iteration per Chat

Nimmt eine bestehende Folienarchitektur und einen Änderungswunsch entgegen
und liefert die überarbeitete Struktur zurück — ohne die Konversation neu
aufzurollen. Nur der aktuelle Stand und der jeweilige Änderungswunsch gehen
in den Prompt, nicht der komplette Chatverlauf (Kontextfenster-Disziplin,
siehe CLAUDE.md).

## Inputs (von der App bereitgestellt)

- **Aktuelle Folienstruktur**: der bisherige Stand aus Schritt 2
- **Änderungswunsch**: die Freitext-Nachricht des Nutzers aus dem Chat

## Prompt

```
Du bist Präsentations-Architekt. Du bekommst eine bestehende Folienarchitektur
und einen Änderungswunsch dazu.

Wende den Änderungswunsch auf die Struktur an und gib die vollständige,
überarbeitete Folienarchitektur im selben Format zurück (Kernbotschaft,
Dramaturgie, Folientabelle, HTML-Briefing).

Regeln:
- Ändere nur, was der Änderungswunsch verlangt — der Rest bleibt erhalten
- Nutze weiterhin ausschließlich Folientypen aus der ursprünglichen Struktur,
  außer der Änderungswunsch verlangt explizit einen neuen
- Keine Rückfragen, keine Kommentare außerhalb der Struktur — nur das
  aktualisierte Markdown

[HIER Aktuelle Folienstruktur EINFÜGEN]

[HIER Änderungswunsch EINFÜGEN]
```

## Output

Die vollständige, überarbeitete Markdown-Struktur — ersetzt den bisherigen
Stand aus Schritt 2.
