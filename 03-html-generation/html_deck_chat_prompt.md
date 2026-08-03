# Skill: HTML-Deck-Iteration per Chat

Nimmt ein bestehendes HTML-Deck und einen Änderungswunsch entgegen und
liefert das überarbeitete Deck zurück — ohne die Konversation neu
aufzurollen. Nur der aktuelle Stand und der jeweilige Änderungswunsch gehen
in den Prompt, nicht der komplette Chatverlauf (Kontextfenster-Disziplin,
siehe CLAUDE.md).

## Inputs (von der App bereitgestellt)

- **Aktuelles HTML-Deck**: der bisherige Stand aus Schritt 3, ohne den aus dem
  Folienmaster erzeugten `<style>`-Block. Die App schneidet ihn heraus und setzt
  dafür den Kommentar `<!-- FOLIENMASTER-CSS: unverändert übernehmen -->` ein;
  nach dem Lauf fügt sie den Block an derselben Stelle wieder ein
  (`app/layout_css.py`, `split_master_css`/`restore_master_css`). Das spart
  Kontext und verhindert Drift über mehrere Runden.
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
- Der Kommentar `<!-- FOLIENMASTER-CSS: unverändert übernehmen -->` steht
  stellvertretend für den aus dem Folienmaster erzeugten <style>-Block. Er ist
  absichtlich nicht mitgeschickt. Gib den Kommentar unverändert und an
  derselben Stelle wieder aus. Schreibe an seiner Stelle kein CSS und
  rekonstruiere den Block nicht.
- Du änderst ausschließlich Slot-Inhalte und die Layout-Klasse einer Folie.
  Kein Positionierungs-CSS: keine `position`, `top`, `left`, `right`,
  `bottom`, `width`, `height`, `transform` oder `float` für `.slide` und
  `.ph`, weder im <style>-Block noch als `style`-Attribut.
  Verlangt der Änderungswunsch eine andere Platzhaltergeometrie, setze sie
  nicht um, sondern weise auf den Konflikt mit dem Folienmaster hin.
  Passt der Inhalt nicht in den Platzhalter, kürze ihn oder wähle ein anderes
  Layout aus der Layout-Liste — verschiebe nie die Box.
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
