"""Default paths and shared constants for the pipeline."""

from __future__ import annotations

from pathlib import Path


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from `start` (or this file) until a `pyproject.toml` is found."""
    here = (start or Path(__file__)).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


ROOT = find_project_root()

# BSI IT-Grundschutz-Kompendium Edition 2023, individual module PDFs as ZIP.
BSI_ZIP_URL = (
    "https://www.bsi.bund.de/SharedDocs/Downloads/DE/BSI/Grundschutz/"
    "IT-GS-Kompendium_Einzel_PDFs_2023/Zip_Datei_Edition_2023.zip"
    "?__blob=publicationFile"
)

PDF_DIR = ROOT / "data" / "pdfs"

OUTPUT_DIR = ROOT / "output"
PARSED_JSON = OUTPUT_DIR / "bsi_requirements.json"
REQUIREMENTS_JSON = OUTPUT_DIR / "requirements.json"
REQUIREMENTS_CSV = OUTPUT_DIR / "requirements.csv"
METRICS_JSON = OUTPUT_DIR / "metrics.json"
METRICS_CSV = OUTPUT_DIR / "metrics.csv"
SENTENCES_JSON = OUTPUT_DIR / "sentences.json"
SENTENCES_CSV = OUTPUT_DIR / "sentences.csv"

LEVEL_ORDER: tuple[str, ...] = ("B", "S", "H")
LEVEL_LABELS: dict[str, str] = {
    "B": "Basis",
    "S": "Standard",
    "H": "Erhöhter Schutzbedarf",
}

SCOPE_PREFIX = "SYS."


def rel(path: Path) -> str:
    """Path relative to the project root for log messages, if possible."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
