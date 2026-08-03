# Skill: Deck-CSS-Iteration per Chat

Nimmt **nur den CSS-Block** eines bestehenden HTML-Decks und einen
Änderungswunsch entgegen und liefert den überarbeiteten CSS-Block zurück. Das
Folien-Markup geht gar nicht erst an das Modell — es bleibt dadurch
byte-identisch, und pro Runde wandern statt ~60 KB Deck nur wenige KB CSS
durch den Kontext (Kontextfenster-Disziplin, siehe CLAUDE.md).

Dieser Prompt gilt ausschließlich für reine Stiländerungen (Farben, Abstände,
Schriftgrößen, Typografie). Änderungen an Inhalten, Folienreihenfolge,
Layoutwahl oder Slot-Struktur laufen weiter über
`html_deck_chat_prompt.md` — dort ist das Markup Teil des Prompts.

## Inputs (von der App bereitgestellt)

- **Aktuelles Deck-CSS**: der Inhalt des `<style>`-Blocks, den das Modell in
  Schritt 3 selbst geschrieben hat. Der aus dem Folienmaster erzeugte
  `<style>`-Block ist nicht enthalten und wird nie mitgeschickt
  (`app/layout_css.py`, `deck_css`/`replace_deck_css`).
- **Änderungswunsch**: die Freitext-Nachricht des Nutzers aus dem Chat

## Prompt

```
Du bist HTML-Präsentations-Entwickler. Du bekommst den CSS-Block eines
bestehenden HTML-Decks und einen Änderungswunsch dazu.

Wende den Änderungswunsch gezielt an und gib den vollständigen,
überarbeiteten CSS-Block zurück.

Regeln:
- Gib ausschließlich CSS zurück: kein HTML, keine <style>-Tags, keine
  Markdown-Codefences, keine Erklärungen, keine Rückfragen
- Das Folien-Markup siehst du nicht und kannst es nicht ändern. Verlangt der
  Änderungswunsch eine Markup-Änderung (andere Inhalte, andere Folien,
  anderes Layout), setze sie nicht um, sondern gib das CSS unverändert
  zurück und ergänze am Ende die Zeile:
  /* HINWEIS: Änderung braucht das Markup, bitte ohne "Nur Styles" erneut */
- Ändere nur, was der Änderungswunsch verlangt — jede andere Regel bleibt
  unverändert erhalten, inklusive Reihenfolge und Kommentaren
- Die @media-print-Regeln bleiben vollständig erhalten, außer der
  Änderungswunsch betrifft sie explizit
- Kein Positionierungs-CSS für `.slide` und `.ph`: keine `position`, `top`,
  `left`, `right`, `bottom`, `width`, `height`, `transform` oder `float`.
  Diese Geometrie kommt aus dem Folienmaster. Verlangt der Änderungswunsch
  eine andere Platzhaltergeometrie, setze sie nicht um und schreibe
  stattdessen einen /* HINWEIS: ... */-Kommentar an das Ende des Blocks.
- Der Folienmaster-Block ist nicht Teil dieses CSS. Baue seine Regeln nicht
  nach und definiere seine Variablen nicht neu — nutze die vorhandenen
  CSS-Variablen und Komponenten-Klassen.

[HIER Aktuelles Deck-CSS EINFÜGEN]

[HIER Änderungswunsch EINFÜGEN]
```

## Output

Der vollständige, überarbeitete CSS-Block. Die App setzt ihn an derselben
Stelle in das Deck zurück; alles außerhalb des `<style>`-Blocks bleibt
unverändert.
