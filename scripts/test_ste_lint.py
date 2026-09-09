#!/usr/bin/env python3
"""Unit tests for ste_lint.py."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).with_name("ste_lint.py")
SPEC = importlib.util.spec_from_file_location("ste_lint", SCRIPT_PATH)
assert SPEC and SPEC.loader
STE_LINT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = STE_LINT
SPEC.loader.exec_module(STE_LINT)


class WordCountTests(unittest.TestCase):
    def test_number_and_unit_count_as_one(self) -> None:
        self.assertEqual(STE_LINT.ste_word_count("Wait 10 ms."), 2)

    def test_parenthetical_text_counts_as_one(self) -> None:
        self.assertEqual(
            STE_LINT.ste_word_count("Use the key (ID 44 and label A)."),
            4,
        )

    def test_hyphenated_term_counts_as_one(self) -> None:
        self.assertEqual(
            STE_LINT.ste_word_count("Check the red-green status."),
            4,
        )


class ExtractionTests(unittest.TestCase):
    def test_fenced_code_is_not_linted(self) -> None:
        text = "Clear text.\n\n```python\nvalue = 'robust;'\n```\n"
        result = STE_LINT.lint_text(
            text,
            mode="flavored",
            profile="description",
        )
        self.assertEqual(result["findings"], [])

    def test_markdown_link_url_is_not_counted(self) -> None:
        blocks = STE_LINT.text_blocks(
            "Read the [setup guide](https://example.com/a/very/long/path)."
        )
        self.assertEqual(blocks[0].text, "Read the setup guide.")


class RuleTests(unittest.TestCase):
    def codes(self, text: str, *, mode: str = "strict", profile: str = "description"):
        result = STE_LINT.lint_text(text, mode=mode, profile=profile)
        return {finding["code"] for finding in result["findings"]}

    def test_semicolon(self) -> None:
        self.assertIn("PUN-001", self.codes("The check failed; restart the worker."))

    def test_em_dash_overlay(self) -> None:
        self.assertIn("AIP-001", self.codes("The check failed — restart the worker."))

    def test_contraction(self) -> None:
        self.assertIn("SEN-002", self.codes("Do not continue because it isn't safe."))

    def test_passive_voice(self) -> None:
        self.assertIn("VRB-001", self.codes("The file is read by the parser."))

    def test_ai_lead_in_and_word(self) -> None:
        codes = self.codes(
            "It is important to note that this robust system can scale."
        )
        self.assertIn("AIP-002", codes)
        self.assertIn("AIP-003", codes)

    def test_long_procedure_sentence(self) -> None:
        text = (
            "Restart the service after you update all configuration files and "
            "confirm that every dependent worker has completed its current job "
            "without an error."
        )
        self.assertIn(
            "SEN-001",
            self.codes(text, profile="procedure"),
        )

    def test_safety_label_mismatch(self) -> None:
        self.assertIn(
            "SAF-001",
            self.codes(
                "CAUTION: Disconnect the cable. The voltage can cause injury.",
                profile="safety",
            ),
        )

    def test_note_instruction(self) -> None:
        self.assertIn(
            "SEN-003",
            self.codes("NOTE: Restart the service.", profile="procedure"),
        )

    def test_procedure_profile_inference(self) -> None:
        self.assertEqual(
            STE_LINT.infer_profile("1. Restart the service.\n2. Check the log."),
            "procedure",
        )

    def test_numbered_nonimperative_step_is_procedure(self) -> None:
        text = "1. You should restart the service and check the log."
        self.assertEqual(STE_LINT.infer_profile(text), "procedure")
        self.assertIn("SEN-004", self.codes(text, profile="auto"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
