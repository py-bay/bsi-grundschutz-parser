"""Structural cross-artifact consistency checks (stage: validate)."""

from __future__ import annotations

import re
from typing import Any

from bsi_pipeline import config, io, log


_log = log.get_logger("validate")

_REQ_ID_RE = re.compile(r"^SYS(?:\.\d+)+\.A\d+$")
_SENTENCE_ID_RE = re.compile(r"^SYS(?:\.\d+)+\.A\d+\.S\d{2}$")


class ValidationError(Exception):
    """Raised when an invariant fails."""


def _load_required(path):
    if not path.exists():
        raise ValidationError(f"missing artifact: {config.rel(path)}")
    return io.load_json(path)


def check_requirements(requirements: list[dict[str, Any]]) -> None:
    seen_ids: set[str] = set()
    for req in requirements:
        rid = req.get("requirement_id", "")
        if not _REQ_ID_RE.match(rid):
            raise ValidationError(f"invalid requirement_id: {rid!r}")
        if rid in seen_ids:
            raise ValidationError(f"duplicate requirement_id: {rid}")
        seen_ids.add(rid)
        if req.get("level") not in config.LEVEL_ORDER:
            raise ValidationError(f"{rid}: invalid level {req.get('level')!r}")
        for field in ("title", "level_label", "text", "module_id"):
            if not req.get(field):
                raise ValidationError(f"{rid}: empty field {field!r}")


def check_metrics(metrics: dict[str, Any], requirements: list[dict[str, Any]]) -> None:
    if metrics.get("scope") != "SYS":
        raise ValidationError(f"metrics.scope is {metrics.get('scope')!r}, want 'SYS'")

    total = metrics["total_requirements"]
    active = metrics["active_requirements"]
    deprecated = metrics["deprecated_requirements"]["count"]
    if total != len(requirements):
        raise ValidationError(
            f"metrics.total_requirements={total} disagrees with requirements.json ({len(requirements)})"
        )
    if active + deprecated != total:
        raise ValidationError(
            f"active ({active}) + deprecated ({deprecated}) != total ({total})"
        )

    level_sum = sum(metrics["levels"][lvl]["count"] for lvl in config.LEVEL_ORDER)
    if level_sum != total:
        raise ValidationError(
            f"levels B+S+H = {level_sum} disagrees with total ({total})"
        )

    module_total = sum(m["total_requirements"] for m in metrics["modules"].values())
    if module_total != total:
        raise ValidationError(
            f"sum of module totals ({module_total}) disagrees with total ({total})"
        )

    if metrics["total_modules"] != len(metrics["modules"]):
        raise ValidationError(
            f"total_modules={metrics['total_modules']} disagrees with len(modules)={len(metrics['modules'])}"
        )


def check_sentences(sentences: list[dict[str, Any]], requirements: list[dict[str, Any]]) -> None:
    active_ids = {r["requirement_id"] for r in requirements if not r["is_deprecated"]}
    per_req: dict[str, int] = {}
    seen_ids: set[str] = set()

    for s in sentences:
        sid = s["sentence_id"]
        if not _SENTENCE_ID_RE.match(sid):
            raise ValidationError(f"invalid sentence_id: {sid!r}")
        if sid in seen_ids:
            raise ValidationError(f"duplicate sentence_id: {sid}")
        seen_ids.add(sid)
        rid = s["requirement_id"]
        if rid not in active_ids:
            raise ValidationError(f"{sid}: parent {rid} is not an active requirement")
        if not s.get("sentence_text"):
            raise ValidationError(f"{sid}: empty sentence_text")
        per_req[rid] = per_req.get(rid, 0) + 1

    missing = active_ids - per_req.keys()
    if missing:
        raise ValidationError(
            f"{len(missing)} active requirements have zero sentences, "
            f"first: {sorted(missing)[0]}"
        )


def check_parsed_alignment(
    parsed: dict[str, Any], requirements: list[dict[str, Any]]
) -> None:
    sys_modules = [
        m for m in parsed.get("modules", []) if m["module_id"].startswith(config.SCOPE_PREFIX)
    ]
    sys_total = sum(len(m["requirements"]) for m in sys_modules)
    if sys_total != len(requirements):
        raise ValidationError(
            f"parsed SYS requirement count ({sys_total}) "
            f"disagrees with downstream requirements.json ({len(requirements)})"
        )


def run() -> None:
    """Run all structural checks; raises ValidationError on first failure."""
    requirements = _load_required(config.REQUIREMENTS_JSON)
    metrics = _load_required(config.METRICS_JSON)
    sentences = _load_required(config.SENTENCES_JSON)
    parsed = _load_required(config.PARSED_JSON)

    check_requirements(requirements)
    check_metrics(metrics, requirements)
    check_sentences(sentences, requirements)
    check_parsed_alignment(parsed, requirements)

    _log.info(
        "OK: %d requirements / %d modules / %d sentences",
        len(requirements),
        metrics["total_modules"],
        len(sentences),
    )
