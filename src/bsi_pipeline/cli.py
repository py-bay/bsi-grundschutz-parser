"""Command-line interface for the BSI SYS data pipeline.

    uv run bsi-pipeline run                     # download -> parse -> sentences -> metrics
    uv run bsi-pipeline run --from sentences --to metrics
    uv run bsi-pipeline run --stages parse,sentences
    uv run bsi-pipeline download [--force]
    uv run bsi-pipeline parse
    uv run bsi-pipeline sentences [--include-deprecated]
    uv run bsi-pipeline metrics
    uv run bsi-pipeline validate
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from bsi_pipeline import log


_DEFAULT_RUN_ORDER: tuple[str, ...] = ("download", "parse", "sentences", "metrics")
_KNOWN_STAGES: tuple[str, ...] = ("download", "parse", "sentences", "metrics", "validate")


def _import_stage(name: str) -> Callable[..., None]:
    """Lazy-import a stage module to keep CLI startup fast."""
    if name == "download":
        from bsi_pipeline.stages import download
        return download.run
    if name == "parse":
        from bsi_pipeline.stages import parse
        return parse.run
    if name == "sentences":
        from bsi_pipeline.stages import sentences
        return sentences.run
    if name == "metrics":
        from bsi_pipeline.stages import metrics
        return metrics.run
    if name == "validate":
        from bsi_pipeline.stages import validate
        return validate.run
    raise SystemExit(f"unknown stage: {name}")


def _parse_stage_list(value: str) -> list[str]:
    stages = [stage.strip() for stage in value.split(",") if stage.strip()]
    for stage in stages:
        if stage not in _KNOWN_STAGES:
            raise SystemExit(
                f"unknown stage {stage!r}; known: {', '.join(_KNOWN_STAGES)}"
            )
    return stages


def _resolve_run_order(
    stages: list[str] | None,
    from_stage: str | None,
    to_stage: str | None,
) -> list[str]:
    """Determine which stages to execute for the `run` command."""
    if stages and (from_stage or to_stage):
        raise SystemExit("--stages cannot be combined with --from/--to")

    if stages:
        return stages

    order = list(_DEFAULT_RUN_ORDER)
    start = order.index(from_stage) if from_stage else 0
    stop = order.index(to_stage) + 1 if to_stage else len(order)
    if start >= stop:
        raise SystemExit(f"--from {from_stage!r} is at or after --to {to_stage!r}")
    return order[start:stop]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bsi-pipeline",
        description="BSI IT-Grundschutz SYS data pipeline.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=1,
        help="-v = INFO (default), -vv = DEBUG, no -v = WARNING.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_const",
        const=0,
        dest="verbose",
        help="Suppress informational logging (WARNING and above only).",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Run multiple stages in order.")
    run_p.add_argument(
        "--stages",
        type=_parse_stage_list,
        help=f"Comma-separated stage names. Default: {','.join(_DEFAULT_RUN_ORDER)}.",
    )
    run_p.add_argument(
        "--from",
        dest="from_stage",
        choices=_DEFAULT_RUN_ORDER,
        help="Start of the default-order slice (inclusive).",
    )
    run_p.add_argument(
        "--to",
        dest="to_stage",
        choices=_DEFAULT_RUN_ORDER,
        help="End of the default-order slice (inclusive).",
    )

    download_p = sub.add_parser(
        "download", help="Fetch the BSI Einzel-PDFs ZIP and unpack it into data/pdfs."
    )
    download_p.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if PDFs already exist.",
    )

    parse_p = sub.add_parser(
        "parse", help="Parse BSI PDFs into nested + flat requirement artifacts."
    )
    parse_p.add_argument(
        "pdfs",
        nargs="*",
        type=Path,
        help="Optional explicit PDF paths; defaults to all SYS PDFs under data/pdfs.",
    )

    sentences_p = sub.add_parser("sentences", help="Split active requirements into sentences.")
    sentences_p.add_argument(
        "--include-deprecated",
        action="store_true",
        help="Also emit sentences for deprecated (ENTFALLEN) requirements.",
    )

    sub.add_parser("metrics", help="Compute SYS metrics over requirements + sentences.")
    sub.add_parser("validate", help="Run structural cross-artifact checks.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    log.configure(verbosity=args.verbose)
    pipeline_log = log.get_logger("cli")

    if args.command == "run":
        order = _resolve_run_order(args.stages, args.from_stage, args.to_stage)
        pipeline_log.info("Pipeline order: %s", " -> ".join(order))
        for stage in order:
            pipeline_log.info("=== stage: %s ===", stage)
            _import_stage(stage)()
        pipeline_log.info("Pipeline complete.")
        return 0

    if args.command == "download":
        _import_stage("download")(force=args.force)
        return 0

    if args.command == "parse":
        _import_stage("parse")(pdf_paths=list(args.pdfs) or None)
        return 0

    if args.command == "sentences":
        _import_stage("sentences")(include_deprecated=args.include_deprecated)
        return 0

    if args.command in {"metrics", "validate"}:
        _import_stage(args.command)()
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
