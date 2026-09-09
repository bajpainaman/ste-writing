#!/usr/bin/env python3
"""Static package checks for the STE Writing skill."""

from __future__ import annotations

import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


class PackageTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        required = [
            "SKILL.md",
            "cheatsheet.md",
            "patterns.md",
            "glossary.md",
            "references/rules.md",
            "references/rewrite-workflow.md",
            "references/ai-prose-overlay.md",
            "scripts/ste_lint.py",
            "evals/cases.json",
        ]
        for relative in required:
            with self.subTest(relative=relative):
                self.assertTrue((ROOT / relative).is_file())
        self.assertTrue(
            (ROOT / "agents" / "openai.yaml").is_file()
            or "preamble-tier:" in (ROOT / "SKILL.md").read_text(encoding="utf-8")
        )

    def test_chapter_count(self) -> None:
        self.assertEqual(len(list((ROOT / "chapters").glob("ch*.md"))), 11)

    def test_no_template_markers(self) -> None:
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".yaml", ".json", ".py"}:
                with self.subTest(path=path.relative_to(ROOT)):
                    text = path.read_text(encoding="utf-8")
                    self.assertNotIn("[" + "TODO", text)
                    self.assertNotIn("{{" + "PREAMBLE" + "}}", text)

    def test_relative_markdown_links_resolve(self) -> None:
        for path in ROOT.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for raw_target in LINK.findall(text):
                target = raw_target.strip()
                if (
                    not target
                    or target.startswith(("#", "http://", "https://", "/"))
                ):
                    continue
                target_path = (path.parent / target.split("#", 1)[0]).resolve()
                with self.subTest(path=path.relative_to(ROOT), target=target):
                    self.assertTrue(target_path.exists())

    def test_codex_frontmatter_is_minimal(self) -> None:
        if not (ROOT / "agents" / "openai.yaml").is_file():
            self.skipTest("Claude package")
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        keys = {
            match.group(1)
            for line in frontmatter.splitlines()
            if (match := re.match(r"^([a-zA-Z0-9_-]+):", line))
        }
        self.assertEqual(keys, {"name", "description"})

    def test_claude_frontmatter_has_gstack_fields(self) -> None:
        source = ROOT / "SKILL.claude.md"
        if not source.is_file():
            source = ROOT / "SKILL.md"
        text = source.read_text(encoding="utf-8")
        if "preamble-tier:" not in text.split("---", 2)[1]:
            self.skipTest("Codex package")
        frontmatter = text.split("---", 2)[1]
        for key in (
            "name:",
            "preamble-tier:",
            "version:",
            "description:",
            "triggers:",
            "allowed-tools:",
        ):
            self.assertIn(key, frontmatter)

    def test_linter_self_check(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "ste_lint.py"), "--self-check"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("SELF_CHECK_OK", completed.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
