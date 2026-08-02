# Deckforge Studio — Technical Design Document

**Version:** 0.1 (Draft)
**Status:** Vor Implementierungsbeginn
**Autor:** Simon Schneider
**Datum:** 2026-08-02

---

## 1. Problem & Zielsetzung

### Problem

Präsentationen im Corporate Design zu erstellen ist zeitaufwändig. KI-Tools
können Inhalte schnell generieren, treffen aber das Corporate Design nicht
zuverlässig — insbesondere, wenn sie Design-Vorgaben aus Screenshots
"interpretieren" statt aus maschinenlesbaren Quellen abzuleiten.

Der bestehende `deckforge`-Workflow (4 Schritte: Design-Guideline-Extraktion →
Folienstruktur → HTML-Generierung → PDF-Export) löst das methodisch, ist aber
als Sammlung von Skripten und Prompt-Dateien in der Anwendung unbequem:
Copy-Paste zwischen Chatbot, Dateisystem und Browser, kein direktes Feedback
auf das gerenderte Ergebnis.

### Ziel

Eine lokal laufende Streamlit-Anwendung, die die Schritte 2–4 des
deckforge-Workflows in einem iterativen UI zusammenführt: Eingabe und
Chat-Iteration links, Live-Vorschau des gerenderten Decks rechts.

### Explizites Nicht-Ziel

Die App ist ein generischer Präsentations-Generator, der mit einer
beliebigen Design-Guideline gefüttert wird. Die Guideline ist Input, nicht
Bestandteil der Anwendung.

---

## 2. Nutzer & Nutzungskontext

| Aspekt | Festlegung |
|---|---|
| Primärnutzer | Einzelner Anwender (Ersteller der App) |
| Nutzeranzahl | 1 (Single-User, kein Mehrbenutzerbetrieb) |
| Technisches Vorwissen | Hoch (Python, CLI, Git) |
| Nutzungsfrequenz | Projektbezogen, unregelmäßig |
| Betriebsmodus | Lokal (`streamlit run`), kein Server-Deployment |
| Netzwerk | Ausgehende Verbindung zum konfigurierten LLM-Endpoint |

**Implikation:** Keine Authentifizierung, keine Mandantentrennung, keine
Nutzerverwaltung, kein horizontales Skalierungskonzept erforderlich. Diese
Entscheidungen sind bewusst und in Abschnitt 10 als Out-of-Scope dokumentiert.

---

## 3. Funktionale Anforderungen

### 3.1 Zwei-Phasen-Modell

Die App führt den Nutzer durch zwei klar getrennte Phasen. Phase 2 wird erst
freigeschaltet, wenn Phase 1 vom Nutzer explizit bestätigt wurde.

```
SETUP → PHASE 1: STRUKTUR → (Bestätigung) → PHASE 2: HTML → EXPORT
```

Begründung der Trennung: Die Folienarchitektur ist eine inhaltlich-konzeptionelle
Entscheidung, die vor der Gestaltung stehen muss. Wird beides in einem Chat
vermischt, führt Feedback zum Layout dazu, dass sich die Struktur unbemerkt
mitverändert.

### 3.2 User Stories

#### Setup

| ID | Story | Priorität |
|---|---|---|
| S-01 | Als Nutzer kann ich eine Design-Guideline als Markdown-Datei hochladen, damit die generierten Folien meinem Corporate Design entsprechen. | MUSS |
| S-02 | Als Nutzer sehe ich nach dem Upload eine Bestätigung, welche Folientypen und CSS-Tokens erkannt wurden, damit ich Fehler in der Guideline früh bemerke. | SOLL |
| S-03 | Als Nutzer gebe ich Thema, Zielgruppe, Ziel und gewünschte Wirkung in strukturierten Formularfeldern ein. | MUSS |
| S-04 | Als Nutzer kann ich vorhandene Rohinhalte (Stichpunkte, Text) in ein Freitextfeld einfügen. | MUSS |

#### Phase 1 — Folienstruktur

| ID | Story | Priorität |
|---|---|---|
| P1-01 | Als Nutzer starte ich die Strukturgenerierung und sehe das Ergebnis (Kernbotschaft, Dramaturgie, Folientabelle) im rechten Bereich. | MUSS |
| P1-02 | Als Nutzer kann ich per Freitext-Chat Änderungen an der Struktur anfordern, ohne von vorne zu beginnen. | MUSS |
| P1-03 | Als Nutzer kann ich die Struktur manuell im Markdown-Editor nachbearbeiten. | KANN |
| P1-04 | Als Nutzer bestätige ich die Struktur per Button und schalte damit Phase 2 frei. | MUSS |
| P1-05 | Als Nutzer kann ich aus Phase 2 zu Phase 1 zurückspringen, wobei mich die App auf den Verlust des HTML-Stands hinweist. | SOLL |

#### Phase 2 — HTML-Deck

| ID | Story | Priorität |
|---|---|---|
| P2-01 | Als Nutzer starte ich die HTML-Generierung und sehe das gerenderte Deck als scrollbare Vorschau rechts. | MUSS |
| P2-02 | Als Nutzer kann ich per Freitext-Chat Änderungen anfordern ("Abstand unter der Headline zu groß"), die Vorschau aktualisiert sich danach. | MUSS |
| P2-03 | Als Nutzer sehe ich den generierten HTML-Quellcode in einem eigenen Tab. | SOLL |
| P2-04 | Als Nutzer kann ich zu einer vorherigen Iteration zurückspringen, wenn eine Änderung das Ergebnis verschlechtert hat. | SOLL |

#### Export

| ID | Story | Priorität |
|---|---|---|
| E-01 | Als Nutzer kann ich das HTML-Deck als Datei herunterladen. | MUSS |
| E-02 | Als Nutzer kann ich die Folienstruktur als Markdown-Datei herunterladen. | MUSS |
| E-03 | Als Nutzer kann ich die verwendete Design-Guideline erneut herunterladen (Reproduzierbarkeit). | SOLL |
| E-04 | Als Nutzer kann ich ein PDF erzeugen, sofern Playwright lokal installiert ist. Fehlt es, zeigt die App einen klaren Hinweis statt eines Fehlers. | KANN |

---

## 4. Nicht-funktionale Anforderungen

| Kategorie | Anforderung |
|---|---|
| **Portabilität** | Der LLM-Provider ist über Konfiguration austauschbar. Die App muss ohne Codeänderung sowohl gegen Azure OpenAI (Firmenumgebung) als auch gegen einen alternativen Endpoint (private Entwicklungsumgebung) laufen. |
| **Reproduzierbarkeit** | Abhängigkeiten über `pyproject.toml` + `uv.lock`. `uv sync` erzeugt auf jedem Rechner eine identische Umgebung. |
| **Datensparsamkeit** | Keine Persistenz von Guidelines, Inhalten oder generierten Decks auf Platte (MVP). Alles bleibt im Session-State und ist nach Prozessende weg. |
| **Latenz** | Generierungsläufe dauern LLM-bedingt 10–60 s. Die App zeigt während der Verarbeitung einen Fortschrittsindikator und blockiert Eingaben. Streaming ist wünschenswert, aber nicht MVP-kritisch. |
| **Fehlertoleranz** | API-Fehler (Timeout, Rate Limit, Auth) werden abgefangen und als verständliche Meldung angezeigt, ohne den Session-State zu verlieren. |
| **Sicherheit** | Keine Secrets im Code oder Repo. Konfiguration ausschließlich über `.env` (gitignored) oder Umgebungsvariablen. |
| **Wartbarkeit** | Prompts liegen als versionierte Markdown-Dateien im Repo, nicht als String-Literale im Code. |

---

## 5. Architektur

### 5.1 Komponentenübersicht

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit App (lokal)                 │
│                                                          │
│  ┌────────────────────┐      ┌────────────────────────┐ │
│  │  Linke Spalte      │      │  Rechte Spalte         │ │
│  │  - Guideline-Upload│      │  - Phase 1: Struktur   │ │
│  │  - Setup-Formular  │      │    (Markdown-Render)   │ │
│  │  - Chat-Verlauf    │      │  - Phase 2: Deck       │ │
│  │  - Chat-Input      │      │    (HTML im iframe)    │ │
│  │  - Phasen-Steuerung│      │  - Tab: Quellcode      │ │
│  │  - Downloads       │      │                        │ │
│  └────────────────────┘      └────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Session State                                      │ │
│  │  phase | guideline_md | setup{} | structure_md      │ │
│  │  deck_html | history[] | chat_msgs[]                │ │
│  └────────────────────────────────────────────────────┘ │
│                          │                               │
│  ┌───────────────────────┴────────────────────────────┐ │
│  │  llm/client.py  (Provider-Abstraktion)             │ │
│  └───────────────────────┬────────────────────────────┘ │
│  ┌───────────────────────┴────────────────────────────┐ │
│  │  prompts/  (Markdown-Templates aus dem Repo)       │ │
│  └────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────┐ │
│  │  export/pdf.py  (Playwright, optional)             │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────┬───────────────────────────────┘
                           │ HTTPS
              ┌────────────┴─────────────┐
              │  LLM-Endpoint            │
              │  (Azure OpenAI / andere) │
              └──────────────────────────┘
```

### 5.2 Provider-Abstraktion

Kernstück für die Portabilität zwischen privater und Firmenumgebung. Ein
schmales Interface, zwei Implementierungen:

```python
# llm/client.py
class LLMClient(Protocol):
    def complete(self, system: str, messages: list[dict]) -> str: ...

def get_client() -> LLMClient:
    provider = os.getenv("LLM_PROVIDER", "azure")
    if provider == "azure":
        return AzureOpenAIClient(...)
    elif provider == "anthropic":
        return AnthropicClient(...)
    raise ValueError(f"Unbekannter Provider: {provider}")
```

Die App-Logik kennt nur `complete()`. Der Wechsel zwischen Umgebungen erfolgt
über `LLM_PROVIDER` in der `.env`, ohne Codeänderung.

**Entscheidung: Chat Completions API statt Azure AI Foundry Agent Service.**

| Kriterium | Chat Completions | Agent Service |
|---|---|---|
| Läuft auf Privatrechner | ja (anderer Provider) | nein (tenant-gebunden) |
| Prompts versionierbar in Git | ja | nein (Azure-seitige Config) |
| State-Verwaltung | in der App | serverseitige Threads |
| Zusatznutzen für diesen Fall | — | Tools/RAG (nicht benötigt) |

Die Prompts sind der eigentliche Wert dieses Projekts. Sie gehören in die
Versionskontrolle, nicht in eine Cloud-Konfiguration.

### 5.3 Datenfluss

**Phase 1:**
```
guideline_md + setup{} → Template slide_architect_prompt.md
                       → LLMClient.complete()
                       → structure_md → Markdown-Render rechts
```

**Phase 1 Iteration:**
```
structure_md + chat_msgs[] + neue Nutzeranfrage
                       → LLMClient.complete()
                       → structure_md (ersetzt) → Re-Render
```

**Phase 2:**
```
guideline_md + structure_md → Template html_deck_prompt.md
                            → LLMClient.complete()
                            → deck_html → iframe-Render rechts
                            → history.append(deck_html)
```

**Export:**
```
deck_html → st.download_button (HTML)
structure_md → st.download_button (MD)
deck_html → playwright → PDF → st.download_button (optional)
```

---

## 6. Tech-Stack

| Komponente | Wahl | Begründung |
|---|---|---|
| UI-Framework | Streamlit | Schnellster Weg zu einem funktionalen Zwei-Spalten-UI mit Datei-Upload, Chat und HTML-Embed. Kein Frontend-Build nötig. Bekannt aus Vorprojekt. |
| Sprache | Python 3.12 | Konsistent mit den bestehenden Extraktionsskripten. |
| Paketmanagement | uv | Lockfile-basierte Reproduzierbarkeit, deutlich schneller als pip/venv, ein Tool statt zwei. |
| LLM-Zugang (Firma) | Azure OpenAI via `openai`-SDK (`AzureOpenAI`-Client) | Vorhandenes Deployment im Firmen-Tenant. |
| LLM-Zugang (privat) | Konfigurierbarer Alternativ-Provider | Ermöglicht Entwicklung ohne Firmen-Tenant. |
| HTML-Vorschau | `st.components.v1.html` | Rendert das Deck im iframe, isoliert vom Streamlit-CSS. |
| PDF-Export | Playwright (Chromium) | Wendet `@media print`-Regeln korrekt an, konsistenter als manueller Browser-Druck. Optional installierbar. |
| Konfiguration | `python-dotenv` | Secrets über `.env`, nie im Repo. |

---

## 7. UI/UX-Grobkonzept

### Layout

Zweispaltig über `st.columns([1, 2])` — Steuerung schmal links, Vorschau breit
rechts. Die Vorschau ist der Arbeitsgegenstand und bekommt den Platz.

### Linke Spalte (Steuerung)

**Immer sichtbar:** Phasen-Indikator (Setup / Struktur / Deck), Statusanzeige
des LLM-Providers.

**Phase SETUP:**
- File-Uploader für Design-Guideline (`.md`)
- Formularfelder: Thema, Zielgruppe, Ziel, gewünschte Wirkung
- Textarea: vorhandene Rohinhalte
- Button "Struktur generieren"

**Phase STRUKTUR:**
- Chat-Verlauf (nur Iterationen dieser Phase)
- `st.chat_input` für Änderungswünsche
- Button "Struktur bestätigen → Deck bauen" (primär)
- Download: Struktur als `.md`

**Phase DECK:**
- Chat-Verlauf (Iterationen dieser Phase)
- `st.chat_input` für Änderungswünsche
- Iterations-Auswahl (Zurückspringen auf frühere Version)
- Downloads: HTML, Struktur, Guideline, PDF (falls verfügbar)
- Button "Zurück zur Struktur" (sekundär, mit Warnhinweis)

### Rechte Spalte (Vorschau)

- **Phase SETUP:** Platzhalter mit Kurzanleitung
- **Phase STRUKTUR:** Struktur als gerendertes Markdown
- **Phase DECK:** Tabs
  - *Vorschau* — Deck im iframe, scrollbar, feste Höhe
  - *Quellcode* — HTML in `st.code`, kopierbar

### Interaktionsverhalten

- Während eines LLM-Laufs: `st.spinner`, Eingaben deaktiviert
- Nach erfolgreicher Generierung: Vorschau aktualisiert sich automatisch
- Bei Fehler: `st.error` mit Klartextmeldung, bisheriger Stand bleibt erhalten

---

## 8. Datenmodell & State-Management

Alles liegt in `st.session_state`. Keine Datenbank, keine Dateien auf Platte.

```python
{
  "phase": "setup" | "structure" | "deck",

  "guideline_md": str | None,        # hochgeladene Design-Guideline
  "guideline_name": str | None,      # Originaldateiname

  "setup": {
      "thema": str,
      "zielgruppe": str,
      "ziel": str,
      "wirkung": str,
      "rohinhalte": str,
  },

  "structure_md": str | None,        # aktueller Strukturstand
  "structure_chat": [                # Iterationsverlauf Phase 1
      {"role": "user" | "assistant", "content": str}
  ],

  "deck_html": str | None,           # aktueller HTML-Stand
  "deck_chat": [ ... ],              # Iterationsverlauf Phase 2
  "deck_history": [                  # frühere Versionen zum Zurückspringen
      {"label": str, "html": str, "timestamp": str}
  ],

  "error": str | None,
}
```

**Wichtig bei Streamlit:** Jede Nutzerinteraktion löst einen vollständigen
Skript-Rerun aus. Nur `st.session_state` überlebt. Jeder Schreibzugriff auf
den State muss daher vor dem Rendern der abhängigen Widgets erfolgen.

**Kontextfenster:** Bei jeder Iteration wird der bisherige Stand (Guideline +
aktuelle Struktur bzw. HTML + Chatverlauf) mitgeschickt. Bei langen Decks
kann das gegen Token-Limits laufen. Mitigation siehe Abschnitt 11.

---

## 9. Sicherheit & Compliance

| Punkt | Festlegung |
|---|---|
| Datenübertragung | Guideline und Inhalte werden bei jedem Prompt an den konfigurierten LLM-Endpoint gesendet. |
| Umgebung | Azure-Tenant mit bestehendem Deployment. Datenverarbeitung erfolgt innerhalb des Tenants. |
| Private Umgebung | **Es dürfen ausschließlich generische Testdaten verwendet werden.** Keine Corporate-Guidelines, keine realen Präsentationsinhalte. |
| Secrets | Ausschließlich in `.env`, die per `.gitignore` ausgeschlossen ist. Eine `.env.example` ohne Werte dokumentiert die benötigten Variablen. |
| Repo-Inhalt | Nur generischer Code und generische Prompt-Templates. Keine Design-Guidelines, keine Firmenreferenzen, keine Beispieldateien mit realem Corporate Design. |
| Trennung der Repositories | Öffentliches Repo (Code) und internes Repo (erzeugte Guidelines) sind **getrennte Repositories**, nicht zwei Remotes desselben Repos. Damit ist ein versehentlicher Push interner Daten strukturell ausgeschlossen. |

### Entwicklungs-Workflow über zwei Rechner

```
Privatrechner                      Firmenlaptop
─────────────                      ────────────
Code entwickeln                    Repo clonen (read-only nutzen)
Generische Testdaten               Schritt 1 ausführen (PDF/PPTX → Tokens)
LLM_PROVIDER=<alternativ>          Guideline erzeugen
        │                          LLM_PROVIDER=azure
        │ git push                 App mit echter Guideline nutzen
        ▼                                  │
   GitHub (öffentlich)                     │ Guideline separat ablegen
                                           ▼
                                   Azure DevOps (intern)
```

Die App erfährt nie, für welches Unternehmen sie eingesetzt wird — die
Guideline ist zur Laufzeit hochgeladener Input.

---

## 10. Out of Scope (MVP)

Bewusst nicht enthalten, um Scope Creep zu vermeiden:

- Authentifizierung und Nutzerverwaltung
- Mehrbenutzerbetrieb, Server-Deployment, Containerisierung
- Persistenz von Projekten über Sitzungen hinweg (siehe Ausbaustufe 2)
- Schritt 1 (Guideline-Extraktion) im UI — bleibt CLI-Skript
- Folien-Navigation, Thumbnails, Präsentationsmodus in der Vorschau
- Direkter PowerPoint-Export (.pptx)
- Bild-/Diagrammgenerierung
- Automatisches Einlesen von Quelldokumenten (Word, Excel) als Inhaltsbasis
- Kostenkontrolle/Token-Budgetierung im UI

---

## 11. Risiken & Annahmen

### Risiken

| Risiko | Auswirkung | Mitigation |
|---|---|---|
| Kontextfenster wird bei langen Decks überschritten | Generierung schlägt fehl | Bei Iterationen nur Diff-Anweisung + aktuellen HTML-Stand senden, nicht den vollen Chatverlauf. Falls nicht ausreichend: folienweise Regeneration. |
| LLM hält sich nicht an CSS-Tokens der Guideline | Deck weicht vom Corporate Design ab | QC-Checkliste als Teil des Prompts; optional automatisierte Prüfung, ob im HTML nur Farben aus der Token-Liste vorkommen (Ausbaustufe). |
| HTML-Vorschau im iframe verhält sich anders als der PDF-Export | Nutzer sieht Layoutfehler erst im PDF | Print-CSS von Anfang an im Prompt verankert (bereits in `html_deck_prompt.md`). PDF-Export früh testen, nicht erst am Ende. |
| Playwright auf dem Firmenlaptop nicht installierbar | Kein PDF-Export in der App | Export ist optional; manueller Browser-Druckweg ist dokumentiert (`04-pdf-export/README.md`). |
| Guideline-Markdown ist unstrukturiert oder unvollständig | Schlechte Generierungsergebnisse | Validierung beim Upload (S-02): Prüfen, ob CSS-Tokens und Folientypen erkennbar sind, sonst Warnhinweis. |
| Streamlit-Rerun-Verhalten führt zu State-Verlust | Nutzer verliert Arbeitsstand | State-Zugriffe konsequent über `st.session_state`, keine lokalen Variablen über Reruns hinweg. Frühe Tests mit Iterationen. |

### Annahmen

- Das Azure-Deployment im Firmen-Tenant ist erreichbar und hat ausreichendes
  Kontingent für Prompts dieser Größenordnung (Guideline + Struktur + HTML
  können mehrere zehntausend Token umfassen).
- Der Firmenlaptop erlaubt lokale Python-Umgebungen und das Starten eines
  lokalen Webservers auf `localhost`.
- Die Design-Guideline aus Schritt 1 ist qualitativ ausreichend, um daraus
  konsistente Folien abzuleiten. Falls nicht, liegt der Fehler in Schritt 1
  und muss dort behoben werden — nicht durch Nachbessern in der App.

---

## 12. Implementierungsplan

### Vorbereitung

- [ ] `uv init`, Dependencies ergänzen, `.env.example` anlegen
- [ ] Repo-Struktur um `app/` erweitern
- [ ] `.gitignore` um `.env`, `.venv/` prüfen

### Meilenstein 1 — Skelett (lauffähig, ohne LLM)

- [ ] Streamlit-Grundgerüst mit Zwei-Spalten-Layout
- [ ] Session-State-Struktur implementiert
- [ ] Phasenwechsel funktioniert (mit Dummy-Inhalten)
- [ ] Guideline-Upload und Anzeige
- [ ] Setup-Formular

**Akzeptanz:** App startet, Phasen lassen sich durchklicken, State bleibt über
Reruns erhalten.

### Meilenstein 2 — LLM-Anbindung

- [ ] `llm/client.py` mit Provider-Abstraktion
- [ ] Prompt-Templates aus `prompts/` laden und befüllen
- [ ] Phase 1: Strukturgenerierung end-to-end
- [ ] Fehlerbehandlung (Timeout, Auth, Rate Limit)

**Akzeptanz:** Aus Guideline + Setup entsteht eine sinnvolle Folienstruktur.

### Meilenstein 3 — Iteration & Phase 2

- [ ] Chat-Iteration Phase 1
- [ ] Phasenübergang mit Bestätigung
- [ ] Phase 2: HTML-Generierung
- [ ] iframe-Vorschau
- [ ] Chat-Iteration Phase 2 mit Versionshistorie

**Akzeptanz:** Ein vollständiges Deck entsteht und lässt sich per Chat
verändern; die Vorschau spiegelt Änderungen wider.

### Meilenstein 4 — Export & Abschluss

- [ ] Download-Buttons (HTML, Struktur, Guideline)
- [ ] PDF-Export mit Graceful Degradation
- [ ] Quellcode-Tab
- [ ] README für die App

**Akzeptanz:** Kompletter Durchlauf von Guideline-Upload bis PDF ohne
manuelle Zwischenschritte.

### Ausbaustufen (nach MVP)

1. Persistenz: Projekte lokal speichern und laden
2. Automatisierte Token-Compliance-Prüfung des generierten HTML
3. Streaming der LLM-Antworten
4. Schritt 1 (Guideline-Extraktion) im UI statt CLI
5. Folien-Navigation in der Vorschau

---

## 13. Akzeptanzkriterien (MVP)

Das MVP gilt als fertig, wenn:

1. Die App lokal per `uv run streamlit run app/main.py` startet.
2. Eine beliebige Design-Guideline im Markdown-Format hochgeladen werden kann.
3. Aus Setup-Eingaben eine Folienstruktur generiert wird, die ausschließlich
   Folientypen aus der hochgeladenen Guideline verwendet.
4. Die Struktur per Freitext-Chat mindestens dreimal iterativ verändert werden
   kann, ohne dass der Kontext verloren geht.
5. Nach Bestätigung ein HTML-Deck entsteht, das in der Vorschau korrekt
   gerendert wird.
6. Das Deck per Freitext-Chat verändert werden kann und die Vorschau sich
   aktualisiert.
7. HTML und Struktur als Dateien heruntergeladen werden können.
8. Ein Providerwechsel ausschließlich über `.env` funktioniert, ohne
   Codeänderung.
9. Das Repository enthält keine Secrets, keine Design-Guidelines und keine
   Firmenreferenzen.

---

## Anhang A — Zielstruktur des Repositories

```
deckforge/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── pyproject.toml
├── uv.lock
│
├── app/
│   ├── main.py                 # Streamlit-Entry-Point
│   ├── state.py                # Session-State-Initialisierung/Helper
│   ├── ui/
│   │   ├── sidebar.py          # linke Spalte
│   │   ├── preview.py          # rechte Spalte
│   │   └── phases.py           # Phasenlogik
│   ├── llm/
│   │   ├── client.py           # Provider-Abstraktion
│   │   ├── azure.py
│   │   └── anthropic.py
│   ├── prompts/
│   │   └── loader.py           # lädt Templates aus 02-/03-
│   └── export/
│       └── pdf.py              # Playwright-Wrapper
│
├── 01-design-guideline/        # CLI, unverändert
├── 02-slide-structure/         # Prompt-Template
├── 03-html-generation/         # Prompt-Template
└── 04-pdf-export/              # CLI, unverändert
```

## Anhang B — Konfigurationsvariablen

```bash
# .env.example

# Provider-Auswahl: azure | anthropic
LLM_PROVIDER=azure

# --- Azure OpenAI (Firmenumgebung) ---
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
AZURE_OPENAI_API_VERSION=

# --- Alternativ-Provider (private Entwicklung) ---
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=
```

---

## Offene Punkte

Vor Implementierungsbeginn zu klären:

- [ ] Konkretes Azure-Deployment (Modellname, API-Version, Kontextfenster)
- [ ] Token-Limit des Deployments vs. erwartete Prompt-Größe
- [ ] Playwright-Installierbarkeit auf dem Firmenlaptop
- [ ] Ablageort und Struktur des internen Guideline-Repositories
