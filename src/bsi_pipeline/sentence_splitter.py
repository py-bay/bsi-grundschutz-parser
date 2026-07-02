"""German sentence splitter for BSI requirement texts."""

from __future__ import annotations

import re


ABBREVIATIONS: tuple[str, ...] = (
    "bzw",
    "ca",
    "d.h",
    "d. h",
    "etc",
    "ggf",
    "i.d.R",
    "u.a",
    "u. a",
    "vgl",
    "z.B",
    "z. B",
)


def protect_abbreviations(text: str) -> str:
    """Replace dots in abbreviations, ellipses, and numbered items with a sentinel."""
    protected = text.replace("...", "<DOT><DOT><DOT>")
    protected = re.sub(r"\b(\d+)\.", r"\1<DOT>", protected)
    for abbreviation in ABBREVIATIONS:
        protected_abbreviation = abbreviation.replace(".", "<DOT>")
        protected = re.sub(
            re.escape(abbreviation) + r"\.",
            protected_abbreviation + "<DOT>",
            protected,
            flags=re.IGNORECASE,
        )
    return protected


def restore_abbreviations(text: str) -> str:
    """Reverse `protect_abbreviations` after splitting."""
    return text.replace("<DOT>", ".")


def split_sentences(text: str) -> list[str]:
    """Split a requirement text into sentence-like classification units."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    protected = protect_abbreviations(normalized)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9])", protected)
    return [restore_abbreviations(part).strip() for part in parts if part.strip()]
