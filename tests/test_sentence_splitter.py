"""Unit tests for the German sentence splitter.

Run from repo root:

    uv run --project code/bsi_pipeline python -m unittest discover code/bsi_pipeline/tests
"""

from __future__ import annotations

import unittest

from bsi_pipeline.sentence_splitter import split_sentences


class SplitSentencesTests(unittest.TestCase):
    def test_single_sentence(self) -> None:
        self.assertEqual(
            split_sentences("Der Server MUSS gehärtet werden."),
            ["Der Server MUSS gehärtet werden."],
        )

    def test_two_sentences(self) -> None:
        text = "Der Server MUSS gehärtet werden. Updates MÜSSEN installiert werden."
        self.assertEqual(
            split_sentences(text),
            [
                "Der Server MUSS gehärtet werden.",
                "Updates MÜSSEN installiert werden.",
            ],
        )

    def test_abbreviations_do_not_split(self) -> None:
        text = "Dienste z.B. SSH MÜSSEN konfiguriert werden. Logs SOLLTEN bzw. KÖNNEN ausgewertet werden."
        parts = split_sentences(text)
        self.assertEqual(len(parts), 2)
        self.assertIn("z.B.", parts[0])
        self.assertIn("bzw.", parts[1])

    def test_question_and_exclamation_split(self) -> None:
        text = "Ist der Dienst aktiv? Dann MUSS er gehärtet werden!"
        self.assertEqual(len(split_sentences(text)), 2)

    def test_empty_input(self) -> None:
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   \n\t  "), [])

    def test_ellipsis_should_not_split(self) -> None:
        text = "Der Server ... MUSS gehärtet werden."
        self.assertEqual(len(split_sentences(text)), 1)

    def test_numbered_step_should_not_split(self) -> None:
        text = "Schritt 1. Den Dienst aktivieren. Schritt 2. Das Log prüfen."
        self.assertEqual(len(split_sentences(text)), 2)


if __name__ == "__main__":
    unittest.main()
