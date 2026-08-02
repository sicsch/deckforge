# CLAUDE.md

Kontext für Claude Code in diesem Repository.

## Was dieses Projekt ist

deckforge erzeugt Präsentationen im Corporate Design als HTML statt PowerPoint.
Vier Schritte: Design-Tokens extrahieren → Folienstruktur ableiten → HTML-Deck
generieren → PDF exportieren. Schritt 1 und 4 sind Python-Skripte, Schritt 2
und 3 sind Prompt-Templates. Eine Streamlit-App fasst Schritte 2–4 in einem
iterativen UI zusammen (in Entwicklung, Spezifikation in `docs/tech-spec.md`).

## Sprache

Code, Kommentare, Docstrings und Commit-Messages auf **Englisch**.
README-Dateien, Prompt-Templates und Dokumentation auf **Deutsch** — das ist
die Arbeitssprache des Projekts und die Sprache der generierten Präsentationen.

## Harte Regeln

Diese Regeln haben Vorrang vor Bequemlichkeit. Wenn eine Aufgabe sie verletzen
würde, weise darauf hin, statt sie zu umgehen.

**1. Keine Corporate-Design-Daten im Repository.**
Keine echten Farbpaletten, Schriftnamen, Logos oder Layout-Werte eines
konkreten Unternehmens — auch nicht in Beispielen, Tests, Docstrings oder
Kommentaren. Beispiele verwenden erkennbar generische Platzhalter
(`#1A73E8`, `"Example Sans"`, `company_report.pdf`).

**2. Keine Firmenreferenzen.**
Weder in Code, Doku, Commit-Messages noch in Dateinamen. Dieses Repo ist
öffentlich und designagnostisch. Wenn dir ein Firmenname im Kontext begegnet,
übernimm ihn nicht in Artefakte.

**3. Keine Secrets.**
Zugangsdaten ausschließlich über `.env` (gitignored) und Umgebungsvariablen.
Niemals Keys, Endpoints oder Tenant-IDs in Code, Tests oder Beispiele
schreiben. `.env.example` enthält nur leere Variablennamen.

**4. Extraktionsergebnisse gehören nicht ins Repo.**
`*_tokens.json`, `*.pdf`, `*.pptx`, `*.potx` sind gitignored. Diese Regel nicht
aufweichen, auch nicht für Testdaten. Wenn Testdaten gebraucht werden:
synthetische Dateien erzeugen, die keinerlei realem Design entstammen.

**5. Prompts sind Quellcode.**
Die Prompt-Templates in `02-slide-structure/` und `03-html-generation/` sind
der inhaltliche Kern des Projekts. Änderungen daran wie Codeänderungen
behandeln: bewusst, begründet, in einem eigenen Commit. Keine Prompts als
String-Literale in Python-Code duplizieren — immer aus den Markdown-Dateien
laden.

## Architektur-Entscheidungen

Diese wurden bewusst getroffen. Nicht ohne Rücksprache ändern.

**Chat Completions statt Agent Service.**
Der LLM-Zugriff läuft über die Chat-Completions-API, nicht über serverseitige
Agents. Grund: Prompts bleiben in der Versionskontrolle und die App läuft
gegen beliebige Endpoints, auch außerhalb eines bestimmten Cloud-Tenants.

**Provider-Abstraktion.**
`app/llm/client.py` definiert ein schmales Interface. Die App-Logik kennt nur
`complete()`. Provider-Wechsel erfolgt über `LLM_PROVIDER` in `.env`, niemals
über Codeänderungen. Neue Provider als eigenes Modul in `app/llm/` ergänzen.

**Zwei-Phasen-UI.**
Folienstruktur (Phase 1) und HTML-Generierung (Phase 2) sind getrennt. Phase 2
wird erst nach expliziter Bestätigung freigeschaltet. Diese Trennung nicht
aufheben — sie verhindert, dass Layout-Feedback unbemerkt die inhaltliche
Struktur verändert.

**Session-State only (MVP).**
Keine Datenbank, keine Persistenz auf Platte. Alles in `st.session_state`.
Persistenz ist als Ausbaustufe geplant, nicht Teil des MVP.

## Entwicklung

```bash
uv sync                              # Umgebung herstellen
uv run streamlit run app/main.py     # App starten
uv run 04-pdf-export/export_to_pdf.py deck.html deck.pdf
```

Immer `uv run` statt manueller venv-Aktivierung. Dependencies über `uv add`
ergänzen, nie direkt in `pyproject.toml` editieren. `uv.lock` wird mitcommittet.

## Issue-Workflow

Feature-Arbeit läuft über den persönlichen `tackle-github-issue`-Skill
(Branch-Isolation, Verifikation vor Commit, PR erst auf Bestätigung). Jedes
Issue entspricht einer User Story aus `docs/tech-spec.md` Abschnitt 3. Vor
Arbeitsbeginn: Issue lesen, Akzeptanzkriterium im Kopf behalten, erst danach
branchen.

## Streamlit-Besonderheiten

Jede Nutzerinteraktion löst einen vollständigen Skript-Rerun aus. Nur
`st.session_state` überlebt — lokale Variablen sind nach jedem Rerun weg.

Konsequenzen für Änderungen an `app/`:

- State-Schreibzugriffe **vor** dem Rendern abhängiger Widgets
- Keine Annahmen über Ausführungsreihenfolge zwischen Reruns
- Widget-Keys explizit setzen, wenn der Wert überleben soll
- Teure Operationen (LLM-Calls) niemals im Render-Pfad ohne Guard — sonst
  laufen sie bei jedem Rerun erneut

## Kontextfenster-Disziplin

Guideline + vollständiges HTML-Deck + Chatverlauf summieren sich schnell auf
zehntausende Token. Bei Iterationen **nicht** den kompletten Chatverlauf
mitschicken, sondern nur die Änderungsanweisung plus den aktuellen Stand.
Wenn du Code schreibst, der Kontext an das LLM übergibt: prüfe, ob wirklich
alles gebraucht wird.

## Commits

Konventionelle Präfixe: `feat:`, `fix:`, `docs:`, `refactor:`, `chore:`.
Imperativ, englisch, eine Zeile. Prompt-Änderungen bekommen einen eigenen
Commit mit Begründung im Body — sie ändern das Verhalten des Systems stärker
als die meisten Codeänderungen.

Vor jedem `git add .`: `git status` prüfen. Die `.gitignore` fängt das meiste
ab, aber erzeugte Guidelines und Decks können unter Namen liegen, die keinem
Muster entsprechen.

## Was du proaktiv ansprechen sollst

- Wenn eine Änderung eine der harten Regeln verletzen würde
- Wenn Code an das LLM mehr Kontext schickt als nötig
- Wenn ein Prompt-Template und der Code, der es lädt, auseinanderlaufen
- Wenn ein Feature vorgeschlagen wird, das laut `docs/tech-spec.md`
  explizit Out of Scope ist
