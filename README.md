# bsi-grundschutz-parser

Datenpipeline für das BSI IT-Grundschutz-Kompendium (Edition 2023): lädt die
offiziellen Baustein-PDFs vom BSI herunter, parst die Anforderungen der
SYS-Schicht, zerlegt sie in Satz-Einheiten und schreibt strukturierte
JSON-/CSV-Dateien samt Kennzahlen in den `output/`-Ordner.

Entstanden im Rahmen meiner Bachelorarbeit.

## Quickstart

Benötigt wird nur [uv](https://docs.astral.sh/uv/) (Python 3.13 wird automatisch verwaltet):

```bash
git clone https://github.com/py-bay/bsi-grundschutz-parser.git
cd bsi-grundschutz-parser
uv run bsi-pipeline run
```

Das ist der „1-Click“-Weg: Der Befehl lädt das Einzel-PDF-ZIP vom BSI
(~16 MB), entpackt es nach `data/pdfs/` und schreibt alle Ergebnisse nach
`output/`.

## Stages

`run` führt standardmäßig `download → parse → sentences → metrics` aus.

| Stage       | Eingabe                                    | Ausgabe                                              |
|-------------|--------------------------------------------|------------------------------------------------------|
| `download`  | BSI-Website (ZIP, Edition 2023)            | `data/pdfs/*.pdf` (111 Baustein-PDFs)                |
| `parse`     | `data/pdfs/SYS.*.pdf` (25 PDFs)            | `output/bsi_requirements.json` (verschachtelt), `output/requirements.{json,csv}` (flach) |
| `sentences` | `output/requirements.json`                 | `output/sentences.{json,csv}` (Satz-Ebene, ID `SYS.x.x.Ay.Snn`) |
| `metrics`   | `requirements.json`, `sentences.json`      | `output/metrics.{json,csv}`                          |
| `validate`  | alle obigen Artefakte                      | Exit-Code 0/1 (strukturelle Konsistenzchecks)        |

## Verwendung

```bash
uv run bsi-pipeline run                          # komplette Pipeline
uv run bsi-pipeline run --from sentences --to metrics
uv run bsi-pipeline run --stages parse,sentences
uv run bsi-pipeline download --force             # PDFs neu herunterladen
uv run bsi-pipeline validate
uv run bsi-pipeline -vv run                      # Debug-Logging
```

Tests:

```bash
uv run python -m unittest discover tests
```

## Aufbau

```
src/bsi_pipeline/
├── cli.py               # argparse-Subcommands
├── config.py            # Pfade, Schutzbedarfs-Labels, BSI-URL
├── io.py                # JSON-/CSV-Helfer
├── log.py               # Logging-Setup
├── sentence_splitter.py # deutscher Satz-Splitter (separat getestet)
└── stages/
    ├── download.py      # ZIP vom BSI laden und entpacken
    ├── parse.py         # SYS-PDFs -> strukturierte Anforderungen
    ├── sentences.py     # Anforderungen -> Satz-Einheiten
    ├── metrics.py       # Metriken über Anforderungen + Satz-Einheiten
    └── validate.py      # Konsistenzchecks
```

Der SYS-Fokus liegt in `config.SCOPE_PREFIX` — wer z. B. APP- oder
NET-Anforderungen braucht, ändert dort eine Zeile (die `validate`-Stage prüft
allerdings SYS-spezifische IDs).

## Datenquelle

Die PDFs stammen aus dem
[IT-Grundschutz-Kompendium, Edition 2023](https://www.bsi.bund.de/DE/Themen/Unternehmen-und-Organisationen/Standards-und-Zertifizierung/IT-Grundschutz/IT-Grundschutz-Kompendium/it-grundschutz-kompendium_node.html)
des Bundesamts für Sicherheit in der Informationstechnik (BSI). Sie werden
nicht in diesem Repository verteilt, sondern bei jedem Lauf direkt vom BSI
heruntergeladen. Die Inhalte der PDFs unterliegen den Nutzungsbedingungen des
BSI.

## Credits

Andere Projekte, die das IT-Grundschutz-Kompendium maschinenlesbar gemacht
haben und als Inspiration bzw. Vergleich dienten:

- [gockelhahn/grundschmutz-tools](https://github.com/gockelhahn/grundschmutz-tools) — Download + Parsing des Kompendiums nach JSON (via pdftohtml)
- [Vulnona/BSI-Grundschutz](https://github.com/Vulnona/BSI-Grundschutz) — Extraktion der Anforderungen aus den Einzel-PDFs 2023 nach Excel, inkl. C5-Mapping
- [nfelger/it-grundschutz-bausteine](https://github.com/nfelger/it-grundschutz-bausteine) — Anforderungstexte aller Bausteine als Textdateien
- [BSI-Bund/Stand-der-Technik-Bibliothek](https://github.com/BSI-Bund/Stand-der-Technik-Bibliothek) — offizielle maschinenlesbare BSI-Inhalte im OSCAL-Format

## Lizenz

MIT (nur der Code — nicht die BSI-Inhalte, siehe Datenquelle).
