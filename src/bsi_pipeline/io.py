"""Shared file I/O for JSON and CSV artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence


def load_json(path: Path) -> Any:
    """Read a UTF-8 JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Write a UTF-8 JSON file with stable indentation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv(path: Path) -> list[dict[str, Any]]:
    """Read a CSV file into a list of dicts."""
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_csv_dicts(
    path: Path,
    rows: Iterable[dict[str, Any]],
    fieldnames: Sequence[str],
) -> None:
    """Write rows of dicts to CSV with a fixed column order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def write_csv_rows(
    path: Path,
    header: Sequence[str],
    rows: Iterable[Sequence[Any]],
) -> None:
    """Write a header row and tuple/list rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(list(header))
        writer.writerows(rows)
