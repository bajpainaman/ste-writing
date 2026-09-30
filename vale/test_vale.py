"""Integration tests exercise the compiled rules through the actual Vale CLI."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from build import ROOT, catalog, render
from check import resolve_vale
from dictionary import parse_book


@unittest.skipUnless(resolve_vale(), "Vale is required for integration checks")
class ValeIntegration(unittest.TestCase):
    def lint(self, content: str, profile: str = "procedure", base: bool = False) -> list[dict]:
        config = ROOT / ("." if base else "private") / f"{profile}.ini"
        if not config.is_file():
            config = ROOT / f"{profile}.ini"
        result = subprocess.run(
            [resolve_vale(), "--no-global", "--no-exit", "--output=JSON",
             f"--config={config}", "--ext=.md"],
            input=content, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        try:
            alerts = json.loads(result.stdout)
        except json.JSONDecodeError:
            self.fail(result.stdout + result.stderr)
        self.assertIsInstance(alerts, dict, alerts)
        self.assertNotIn("Code", alerts, alerts)
        return [alert for group in alerts.values() for alert in group]

    def checks(self, content: str, profile: str = "procedure", base: bool = False) -> list[str]:
        return [alert["Check"] for alert in self.lint(content, profile, base)]

    def test_profiles_use_twenty_and_twenty_five_words(self):
        sentence = "Check " + "the " * 19 + "valve."
        self.assertIn("STE100Procedure.ProcedureLength", self.checks(sentence))
        self.assertNotIn("STE100Description.DescriptionLength", self.checks(sentence, "description"))
        sentence = "Check " + "the " * 24 + "valve."
        self.assertIn("STE100Description.DescriptionLength", self.checks(sentence, "description"))

    def test_notes_have_the_books_twenty_five_word_exception(self):
        sentence = "NOTE: The " + "the " * 22 + "valve."
        checks = self.checks(sentence)
        self.assertNotIn("STE100Procedure.ProcedureLength", checks)
        self.assertNotIn("STE100Procedure.NoteLength", checks)
        sentence = "NOTE: The " + "the " * 25 + "valve."
        self.assertIn("STE100Procedure.NoteLength", self.checks(sentence))

    def test_literal_quotations_and_code_are_preserved(self):
        text = 'The label says "Don\'t; ensure colour". Don\'t use the label.'
        checks = self.checks(text)
        self.assertEqual(checks.count("STE100.Contractions"), 1)
        self.assertNotIn("STE100.Semicolons", checks)
        mark = chr(96)
        fence = mark * 3
        text = "Use the cable.\n\n" + fence + "sh\nensure don't; colour\n" + fence + "\n\nUse " + mark + "ensure don't; colour" + mark + ".\n"
        self.assertFalse(any(c.endswith(("Contractions", "Semicolons", "DictionaryWords")) for c in self.checks(text)))

    def test_known_book_word_count_constructs(self):
        # The book counts parenthetical references and number-plus-unit as one.
        sentence = "Remove " + "the " * 15 + "cover (refer to paragraphs 2 thru 5) at 10 degrees Celsius."
        self.assertNotIn("STE100Procedure.ProcedureLength", self.checks(sentence))
        sentence = "Remove the cover (" + "the " * 22 + "valve)."
        self.assertIn("STE100Procedure.ProcedureLength", self.checks(sentence))

    def test_paragraphs_have_at_most_six_sentences(self):
        self.assertNotIn("STE100Description.ParagraphSentences", self.checks("The valve is open. " * 6, "description"))
        self.assertIn("STE100Description.ParagraphSentences", self.checks("The valve is open. " * 7, "description"))

    def test_dictionary_gives_advice_without_automatic_replacement(self):
        if not (ROOT / "private/procedure.ini").is_file():
            self.skipTest("Full-book dictionary not installed")
        alerts = self.lint("Ensure the cover is closed.")
        matches = [a for a in alerts if a["Check"] == "STE100Dictionary.DictionaryWords"]
        self.assertTrue(matches, alerts)
        self.assertIn("MAKE SURE", matches[0]["Message"])
        self.assertNotEqual(matches[0].get("Action", {}).get("Name"), "replace")
        # TEST is approved as a noun; lexical rules cannot decide its verb use.
        self.assertNotIn("STE100Dictionary.DictionaryWords", self.checks("Do a test."))

    def test_dictionary_does_not_match_don_inside_dont(self):
        messages = [a["Message"] for a in self.lint("Don't remove the cover.")
                    if a["Check"] == "STE100Dictionary.DictionaryWords"]
        self.assertFalse(any("review 'Don'." in message for message in messages))


class BookImport(unittest.TestCase):
    def test_all_fifty_three_rules_are_cataloged(self):
        self.assertEqual(len(catalog()), 53)
        self.assertIn("5.1", catalog())
        self.assertIn("9.4", catalog())

    def test_pos_ambiguity_help_and_qualified_headwords_are_retained(self):
        table = """| Word (part of speech) | Approved meaning/ALTERNATIVES | STE EXAMPLE | Non-STE example |
| --- | --- | --- | --- |
| TEST (n) | An examination | Do a test. | |
| test (v) | EXAMINE (v) | Examine the valve. | Test the valve. |
| HELP: | Use for examination only. | | |
| case (in case of) (conj) | IF (conj) | If there is a fire, stop. | In case of fire, stop. |
| MATT (or MATTE) (adj) | Not shiny | The surface is matt. | |
| FOR EXAMPLE | Introduces an example | For example, use a mallet. | |
| such as | FOR EXAMPLE | For example, use a mallet. | Use tools such as a mallet. |
| CAN (v), CAN, COULD No other verb forms. | Auxiliary modal | The door can open. | |
| HELP (n) | Aid | Get help. | |
"""
        with tempfile.TemporaryDirectory() as temporary:
            book = Path(temporary) / "book.md"
            book.write_text(table, encoding="utf-8")
            parsed = parse_book(book, require_complete=False)
            self.assertFalse(parsed["unparsed"])
            self.assertEqual(parsed["entries"][1]["help"][0]["text"].strip(),
                             "HELP: Use for examination only.")
            self.assertEqual(parsed["entries"][2]["headword"], "in case of")
            self.assertEqual(parsed["entries"][3]["aliases"], ["matte"])
            self.assertEqual(parsed["entries"][4]["part_of_speech"], "unspecified")
            self.assertEqual(parsed["entries"][5]["headword"], "such as")
            self.assertEqual(parsed["entries"][6]["headword"], "can")
            self.assertIn("No other verb forms.", parsed["entries"][6]["forms_source"])
            self.assertEqual(parsed["entries"][7]["headword"], "help")
            with self.assertRaisesRegex(ValueError, "extraction incomplete"):
                parse_book(book)

    def test_source_bytes_and_count_discrepancy_are_audited(self):
        book = ROOT / "private/ASD-STE100_ISSUE9.md"
        archive = ROOT / "private/ASD-STE100_ISSUE9.zip"
        if not book.is_file() or not archive.is_file():
            self.skipTest("Original book not installed")
        original = ZipFile(archive).read("ASD-STE100_ISSUE9/ASD-STE100_ISSUE9.md")
        self.assertEqual(book.read_bytes(), original)
        parsed = parse_book(book, require_complete=False)
        self.assertTrue(parsed["all_headwords_parsed"])
        self.assertEqual(parsed["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(parsed["counts_match_expected"], parsed["counts"] == parsed["expected_counts"])
        files = render(book, allow_count_mismatch=True)
        metadata = json.loads(files["coverage.json"])
        self.assertTrue(all(r.get("book_source_line") for r in metadata["rules"]))
        self.assertEqual(metadata["dictionary"]["complete"], parsed["complete"])


if __name__ == "__main__":
    unittest.main()
