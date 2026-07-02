"""BSI ZIP download -> module PDFs (stage: download)."""

from __future__ import annotations

import tempfile
import urllib.request
import zipfile
from pathlib import Path

from bsi_pipeline import config, log


_log = log.get_logger("download")

# The BSI web server rejects requests without a browser-like User-Agent.
_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) bsi-grundschutz-parser"


def download_zip(url: str, target: Path) -> None:
    """Download `url` to `target` (streamed, ~16 MB)."""
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(request) as response, target.open("wb") as file:
        while chunk := response.read(1 << 16):
            file.write(chunk)


def extract_pdfs(zip_path: Path, pdf_dir: Path) -> int:
    """Unpack all PDFs from the ZIP flat into `pdf_dir`; returns the count."""
    pdf_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path) as archive:
        for info in archive.infolist():
            name = Path(info.filename).name
            if info.is_dir() or not name.lower().endswith(".pdf"):
                continue
            (pdf_dir / name).write_bytes(archive.read(info))
            count += 1
    return count


def run(force: bool = False) -> None:
    """Fetch the BSI Einzel-PDFs ZIP and unpack it into the PDF directory."""
    existing = sorted(config.PDF_DIR.glob("*.pdf")) if config.PDF_DIR.is_dir() else []
    if existing and not force:
        _log.info(
            "Found %d PDFs in %s, skipping download (use --force to re-download).",
            len(existing),
            config.rel(config.PDF_DIR),
        )
        return

    _log.info("Downloading BSI Kompendium ZIP (Edition 2023) ...")
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        zip_path = Path(tmp.name)
        download_zip(config.BSI_ZIP_URL, zip_path)
        count = extract_pdfs(zip_path, config.PDF_DIR)

    if not count:
        raise SystemExit("Downloaded ZIP contained no PDFs — has the BSI URL changed?")
    _log.info("Unpacked %d PDFs -> %s", count, config.rel(config.PDF_DIR))
