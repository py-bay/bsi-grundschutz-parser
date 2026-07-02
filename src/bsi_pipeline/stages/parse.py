"""PDF -> structured requirements (stage: parse)."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pdfplumber

from bsi_pipeline import config, io, log


_log = log.get_logger("parse")

_REQUIREMENT_FIELDS = (
    "requirement_id",
    "module_id",
    "module_name",
    "title",
    "level",
    "level_label",
    "roles",
    "is_deprecated",
    "text",
)

REQ_ID_PATTERN = re.compile(r"^([A-Z]+(?:\.\d+)+\.A\d+)\s+")
LEVEL_MARKER = re.compile(r"\(([BSH])\)")
ROLES_PATTERN = re.compile(r"^\[([^\]]+)\]")
PAGE_FOOTER = re.compile(r"^Seite \d+ von \d+$")

_MODULE_FIRST_LINE = re.compile(r"^([A-Z]+(?:\.\d+)+)\s+(.+)$")
_CHUNK_SPLIT = re.compile(r"\n(?=[A-Z]+(?:\.\d+)+\.A\d+\s|\d+(?:\.\d+)*\.?\s+[A-ZÄÖÜ])")


def extract_text(pdf_path: Path) -> str:
    """Extract and concatenate text from all pages of a PDF."""
    with pdfplumber.open(pdf_path) as pdf:
        pages = [page.extract_text() for page in pdf.pages if page.extract_text()]
    return "\n".join(pages)


def parse_module_info(text: str) -> tuple[str, str]:
    """Return (module_id, module_name) from the first line of the document."""
    first_line = text.strip().split("\n")[0].strip()
    match = _MODULE_FIRST_LINE.match(first_line)
    if match:
        return match.group(1), match.group(2)
    return "UNKNOWN", first_line


def clean_text(raw_text: str, module_id: str) -> str:
    """Remove repeated page headers and footers from extracted text."""
    cleaned: list[str] = []
    for line in raw_text.split("\n"):
        stripped = line.strip()
        if PAGE_FOOTER.match(stripped):
            continue
        if stripped.startswith(module_id + " ") and not REQ_ID_PATTERN.match(stripped):
            continue
        cleaned.append(stripped)
    return "\n".join(cleaned)


def split_into_chunks(text: str) -> list[str]:
    """Split text at requirement starts or section headers."""
    return _CHUNK_SPLIT.split(text)


def parse_requirement(chunk: str) -> dict[str, Any] | None:
    """Parse a chunk into a structured requirement; return None for non-requirements."""
    id_match = REQ_ID_PATTERN.match(chunk)
    if not id_match:
        return None

    req_id = id_match.group(1)
    rest = chunk[id_match.end():]

    level_match = LEVEL_MARKER.search(rest)
    if not level_match:
        _log.warning("No level marker found for %s, skipping", req_id)
        return None

    title = re.sub(r"\s+", " ", rest[: level_match.start()].strip())
    level = level_match.group(1)
    after_level = rest[level_match.end():].strip()

    roles: list[str] = []
    roles_match = ROLES_PATTERN.match(after_level)
    if roles_match:
        roles = [r.strip() for r in roles_match.group(1).split(",")]
        body = after_level[roles_match.end():].strip()
    else:
        body = after_level

    body = re.sub(r"\s+", " ", body).strip()
    is_deprecated = "ENTFALLEN" in title

    return {
        "requirement_id": req_id,
        "title": title,
        "level": level,
        "level_label": config.LEVEL_LABELS[level],
        "roles": roles,
        "is_deprecated": is_deprecated,
        "text": body,
    }



def parse_pdf(pdf_path: Path) -> dict[str, Any]:
    """Parse a single BSI PDF into structured module data."""
    _log.debug("Processing %s", pdf_path.name)

    raw_text = extract_text(pdf_path)
    module_id, module_name = parse_module_info(raw_text)
    text = clean_text(raw_text, module_id)

    chunks = split_into_chunks(text)
    requirements = [
        req for chunk in chunks if (req := parse_requirement(chunk)) is not None
    ]

    active = sum(1 for r in requirements if not r["is_deprecated"])
    _log.debug(
        "  %s: %d requirements (%d active, %d deprecated)",
        module_id,
        len(requirements),
        active,
        len(requirements) - active,
    )

    return {
        "module_id": module_id,
        "module_name": module_name,
        "source_file": pdf_path.name,
        "requirements": requirements,
    }


def flatten_requirements(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten parsed modules into per-requirement rows for downstream stages."""
    rows: list[dict[str, Any]] = []
    for module in modules:
        module_id = module.get("module_id", "")
        if not module_id.startswith(config.SCOPE_PREFIX):
            continue
        for req in module.get("requirements", []):
            rows.append(
                {
                    "requirement_id": req.get("requirement_id", ""),
                    "module_id": module_id,
                    "module_name": module.get("module_name", ""),
                    "title": req.get("title", ""),
                    "level": req.get("level", ""),
                    "level_label": req.get("level_label", ""),
                    "roles": "; ".join(req.get("roles", [])),
                    "is_deprecated": req.get("is_deprecated", False),
                    "text": req.get("text", ""),
                }
            )
    return sorted(rows, key=lambda row: row["requirement_id"])


def run(pdf_paths: list[Path] | None = None) -> None:
    """Parse in-scope BSI PDFs and write nested + flat requirement artifacts."""
    if pdf_paths is None:
        pdf_paths = sorted(
            path
            for path in config.PDF_DIR.glob("*.pdf")
            if path.name.startswith(config.SCOPE_PREFIX)
        )

    if not pdf_paths:
        raise SystemExit(
            f"No {config.SCOPE_PREFIX}* PDFs found in {config.PDF_DIR} — "
            "run the `download` stage first."
        )

    _log.info("Processing %d PDF(s) from %s", len(pdf_paths), config.PDF_DIR)

    modules: list[dict[str, Any]] = []
    for index, path in enumerate(pdf_paths, start=1):
        try:
            modules.append(parse_pdf(path))
        except Exception:
            _log.exception("Failed to process %s", path.name)
        if index % 25 == 0 or index == len(pdf_paths):
            _log.info("  parsed %d / %d PDFs", index, len(pdf_paths))

    total_reqs = sum(len(m["requirements"]) for m in modules)
    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_directory": config.rel(config.PDF_DIR),
            "scope_prefix": config.SCOPE_PREFIX,
            "total_modules": len(modules),
            "total_requirements": total_reqs,
        },
        "modules": modules,
    }

    io.write_json(config.PARSED_JSON, output)

    requirements = flatten_requirements(modules)
    io.write_json(config.REQUIREMENTS_JSON, requirements)
    io.write_csv_dicts(config.REQUIREMENTS_CSV, requirements, _REQUIREMENT_FIELDS)

    _log.info(
        "Wrote %d requirements from %d modules -> %s, %s",
        total_reqs,
        len(modules),
        config.rel(config.PARSED_JSON),
        config.rel(config.REQUIREMENTS_JSON),
    )
