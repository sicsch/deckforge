# deckforge App

Streamlit-UI für die Schritte 2–4 des deckforge-Workflows (Folienstruktur,
HTML-Generierung, PDF-Export) in einem iterativen Chat-Interface. Details zum
Gesamtworkflow stehen im [Haupt-README](../README.md), zur Architektur in
[docs/tech-spec.md](../docs/tech-spec.md).

## Setup

```bash
uv sync
cp .env.example .env
```

`.env` danach mit den eigenen Werten befüllen (siehe unten). Die Datei ist
gitignored und wird beim Start automatisch geladen.

## Starten

```bash
uv run streamlit run app/main.py
```

Die App läuft anschließend unter `http://localhost:8501`.

## Layout aus dem Folienmaster

Im Setup lässt sich neben der Guideline die Token-JSON eines Folienmasters
hochladen (Output von `01-design-guideline/extract_pptx_theme.py`). Daraus
erzeugt `app/layout_css.py` deterministisch:

- einen fertigen `<style>`-Block: `:root`-Variablen, feste Foliengröße und je
  Layout eine Regel pro Platzhalter — Position und Größe in Prozent der
  Foliengröße, nicht in cm
- ein Komponenten-Set (`cards`, `kpis`, `data-table`, `quote`), das
  ausschließlich innerhalb eines Platzhalters (`.ph`) wirkt
- eine Layout-Liste, die Schritt 2 und Schritt 3 im Prompt bekommen

Der Block geht unverändert ins Deck; das Modell füllt nur die Slots. Welche
Layouts überhaupt verwendet werden dürfen, wird im Setup angehakt —
Folienmaster enthalten regelmäßig ungenutzte Karteileichen. Ohne Token-JSON
bleibt das Verhalten wie bisher: das Modell baut das Layout-CSS selbst aus
der Guideline.

Bei Deck-Iterationen wird der Block gar nicht erst mitgeschickt:
`split_master_css()` schneidet ihn heraus und hinterlässt den Kommentar
`<!-- FOLIENMASTER-CSS: unverändert übernehmen -->`, `restore_master_css()`
setzt ihn danach an derselben Stelle wieder ein. Das spart Kontext pro Runde
und macht Drift am Layout-CSS über mehrere Runden unmöglich.

## Provider-Wechsel

Der LLM-Zugriff läuft über eine schmale Provider-Abstraktion
(`app/llm/client.py`). Welcher Provider verwendet wird, bestimmt einzig die
Umgebungsvariable `LLM_PROVIDER` in `.env` — kein Codeänderung nötig.

- **`azure`** (Standard, Firmenumgebung): Authentifizierung über
  `DefaultAzureCredential`, kein API-Key in `.env`. Benötigt
  `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`.
- **`openrouter`** (Alternative, z. B. private Entwicklung): benötigt
  `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`.

Der aktive Provider wird in der App-Kopfzeile angezeigt.

## Bekannte Einschränkungen (MVP)

- **Keine Persistenz.** Alles liegt in `st.session_state`. Nach Prozessende
  (Neustart, Absturz, Browser-Reload mit neuer Session) sind Guideline,
  Struktur und generiertes Deck verloren. Persistenz ist als Ausbaustufe
  geplant, nicht Teil des MVP.
- Schritt 1 (Guideline-Extraktion) läuft nicht in der App, sondern separat als
  CLI-Skript.
- Kein Mehrbenutzerbetrieb, keine Authentifizierung, kein Server-Deployment
  vorgesehen.

Vollständige Out-of-Scope-Liste: `docs/tech-spec.md`, Abschnitt 10.
