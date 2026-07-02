"""SYS metrics over requirements + sentence units (stage: metrics)."""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from bsi_pipeline import config, io, log


_log = log.get_logger("metrics")


def _percent(count: int, total: int) -> float:
    return round(count / total * 100, 1) if total else 0.0


def compute_levels_by_module(
    requirements: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, int]]]:
    """Cross-tabulate requirements by module × level (total and active)."""
    table: dict[str, dict[str, dict[str, int]]] = {}
    for req in requirements:
        module_id = req["module_id"]
        level = req["level"]
        cell = table.setdefault(
            module_id,
            {lvl: {"count": 0, "active_count": 0} for lvl in config.LEVEL_ORDER},
        )
        if level in cell:
            cell[level]["count"] += 1
            if not req["is_deprecated"]:
                cell[level]["active_count"] += 1
    return {module_id: table[module_id] for module_id in sorted(table)}


def compute_sentence_metrics(sentences: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate sentence counts."""
    per_req: Counter[str] = Counter()
    per_level: Counter[str] = Counter()
    per_module: Counter[str] = Counter()
    for s in sentences:
        per_req[s["requirement_id"]] += 1
        per_level[s["level"]] += 1
        per_module[s["module_id"]] += 1

    distribution = sorted(per_req.values())
    return {
        "total": len(sentences),
        "active_requirements_with_sentences": len(per_req),
        "mean_per_active_requirement": (
            round(statistics.mean(distribution), 2) if distribution else 0.0
        ),
        "median_per_active_requirement": (
            int(statistics.median(distribution)) if distribution else 0
        ),
        "max_per_active_requirement": max(distribution) if distribution else 0,
        "by_level": {lvl: per_level.get(lvl, 0) for lvl in config.LEVEL_ORDER},
        "by_module": {mid: per_module[mid] for mid in sorted(per_module)},
    }


def compute_metrics(
    requirements: list[dict[str, Any]], sentences: list[dict[str, Any]]
) -> dict[str, Any]:
    """Compute the canonical SYS metrics dict."""
    total = len(requirements)
    active = [req for req in requirements if not req["is_deprecated"]]
    deprecated_count = total - len(active)

    level_counts = Counter(req["level"] for req in requirements)
    active_level_counts = Counter(req["level"] for req in active)
    module_counts = Counter(req["module_id"] for req in requirements)
    role_counts: Counter[str] = Counter()
    for req in requirements:
        for role in str(req["roles"]).split("; "):
            if role:
                role_counts[role] += 1

    metrics: dict[str, Any] = {
        "scope": "SYS",
        "total_modules": len(module_counts),
        "total_requirements": total,
        "active_requirements": len(active),
        "deprecated_requirements": {
            "count": deprecated_count,
            "percent": _percent(deprecated_count, total),
        },
        "levels": {
            lvl: {
                "count": level_counts[lvl],
                "percent": _percent(level_counts[lvl], total),
                "active_count": active_level_counts[lvl],
                "active_percent": _percent(active_level_counts[lvl], len(active)),
            }
            for lvl in config.LEVEL_ORDER
        },
        "modules": {
            module_id: {
                "total_requirements": count,
                "active_requirements": sum(
                    1 for req in active if req["module_id"] == module_id
                ),
            }
            for module_id, count in sorted(module_counts.items())
        },
        "levels_by_module": compute_levels_by_module(requirements),
        "roles": {
            role: count
            for role, count in sorted(role_counts.items(), key=lambda item: (-item[1], item[0]))
        },
    }

    metrics["sentences"] = compute_sentence_metrics(sentences)
    return metrics


def _write_metrics_csv(metrics: dict[str, Any]) -> None:
    rows: list[tuple[str, Any]] = [
        ("total_modules", metrics["total_modules"]),
        ("total_requirements", metrics["total_requirements"]),
        ("active_requirements", metrics["active_requirements"]),
        ("deprecated_requirements", metrics["deprecated_requirements"]["count"]),
        ("deprecated_requirements_percent", metrics["deprecated_requirements"]["percent"]),
    ]
    for level, values in metrics["levels"].items():
        rows.extend(
            [
                (f"level_{level}_count", values["count"]),
                (f"level_{level}_percent", values["percent"]),
                (f"level_{level}_active_count", values["active_count"]),
                (f"level_{level}_active_percent", values["active_percent"]),
            ]
        )

    sents = metrics.get("sentences")
    if isinstance(sents, dict) and "total" in sents:
        rows.extend(
            [
                ("sentences_total", sents["total"]),
                ("sentences_active_requirements", sents["active_requirements_with_sentences"]),
                ("sentences_mean_per_requirement", sents["mean_per_active_requirement"]),
                ("sentences_median_per_requirement", sents["median_per_active_requirement"]),
                ("sentences_max_per_requirement", sents["max_per_active_requirement"]),
            ]
        )
        for level, count in sents["by_level"].items():
            rows.append((f"sentences_level_{level}", count))

    io.write_csv_rows(config.METRICS_CSV, ["metric", "value"], rows)


def run() -> None:
    """Write the SYS metrics artifacts."""
    if not config.REQUIREMENTS_JSON.exists():
        raise SystemExit(
            f"Missing {config.rel(config.REQUIREMENTS_JSON)} — run the `parse` stage first."
        )
    if not config.SENTENCES_JSON.exists():
        raise SystemExit(
            f"Missing {config.rel(config.SENTENCES_JSON)} — run the `sentences` stage first."
        )

    requirements = io.load_json(config.REQUIREMENTS_JSON)
    sentences = io.load_json(config.SENTENCES_JSON)
    metrics = compute_metrics(requirements, sentences)

    io.write_json(config.METRICS_JSON, metrics)
    _write_metrics_csv(metrics)

    _log.info(
        "Wrote metrics for %d SYS requirements across %d modules -> %s",
        len(requirements),
        metrics["total_modules"],
        config.rel(config.METRICS_JSON),
    )
