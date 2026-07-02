"""Split requirements into individual sentences (stage: sentences)."""

from __future__ import annotations

from typing import Any

from bsi_pipeline import config, io, log
from bsi_pipeline.sentence_splitter import split_sentences


_log = log.get_logger("sentences")

_SENTENCE_FIELDS = (
    "sentence_id",
    "requirement_id",
    "sentence_index",
    "module_id",
    "module_name",
    "title",
    "level",
    "level_label",
    "roles",
    "is_deprecated",
    "sentence_text",
    "requirement_text",
)


def build_sentences(
    requirements: list[dict[str, Any]],
    include_deprecated: bool = False,
) -> list[dict[str, Any]]:
    """Flatten requirements into per-sentence rows."""
    rows: list[dict[str, Any]] = []

    for req in requirements:
        if req.get("is_deprecated") and not include_deprecated:
            continue

        sentences = split_sentences(str(req.get("text", "")))
        for index, sentence in enumerate(sentences, start=1):
            rows.append(
                {
                    "sentence_id": f"{req['requirement_id']}.S{index:02d}",
                    "requirement_id": req.get("requirement_id", ""),
                    "sentence_index": index,
                    "module_id": req.get("module_id", ""),
                    "module_name": req.get("module_name", ""),
                    "title": req.get("title", ""),
                    "level": req.get("level", ""),
                    "level_label": req.get("level_label", ""),
                    "roles": req.get("roles", ""),
                    "is_deprecated": req.get("is_deprecated", False),
                    "sentence_text": sentence,
                    "requirement_text": req.get("text", ""),
                }
            )

    return rows


def run(include_deprecated: bool = False) -> None:
    """Write per-sentence rows derived from parsed requirements."""
    if not config.REQUIREMENTS_JSON.exists():
        raise SystemExit(
            f"Missing {config.rel(config.REQUIREMENTS_JSON)} — run the `parse` stage first."
        )

    requirements = io.load_json(config.REQUIREMENTS_JSON)
    rows = build_sentences(requirements, include_deprecated=include_deprecated)

    io.write_csv_dicts(config.SENTENCES_CSV, rows, _SENTENCE_FIELDS)
    io.write_json(config.SENTENCES_JSON, rows)

    _log.info(
        "Wrote %d sentences from %d requirements -> %s",
        len(rows),
        len({r["requirement_id"] for r in rows}),
        config.rel(config.SENTENCES_CSV),
    )
