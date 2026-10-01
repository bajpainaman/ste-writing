#!/usr/bin/env python3
"""Combine STE, simplify-writing, personal Vale rules, Harper, and optional Jev."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vale"))
from ensure_harper import ensure_harper
from jev_review import automatic_enabled, review

PROSE = {".md", ".txt", ".rst", ".adoc", ".html"}


def machine_vocabulary(path: Path) -> bool:
    return any(path.parts[i:i + 3] == ("styles", "config", "vocabularies") for i in range(len(path.parts) - 2))


class HTMLProse(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skipped = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "pre", "code"}:
            self.skipped.append(tag)
        if tag in {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "h5", "h6"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.skipped and self.skipped[-1] == tag:
            self.skipped.pop()
        if tag in {"p", "div", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skipped:
            self.parts.append(data)


def protected_markdown(text: str) -> tuple[str, list[int]]:
    """Mark filename link labels as code and map positions back to the source."""
    # Native Harper already skips Markdown code and link destinations. A label
    # such as [style_config.py] needs explicit code markup to avoid suffix lints.
    parts = []
    positions = []
    cursor = 0
    for match in re.finditer(r"\[([\w./-]+\.[A-Za-z0-9]+)\]\(", text):
        start, end = match.span(1)
        parts.extend([text[cursor:start], "`", text[start:end], "`"])
        positions.extend(range(cursor, start))
        positions.append(start)
        positions.extend(range(start, end))
        positions.append(end - 1)
        cursor = end
    parts.append(text[cursor:])
    positions.extend(range(cursor, len(text)))
    return "".join(parts), positions


def prose_files(paths: list[str]) -> list[Path]:
    files = []
    for name in paths:
        path = Path(name).resolve()
        candidates = path.rglob("*") if path.is_dir() else [path]
        for candidate in candidates:
            if candidate.is_file() and candidate.suffix.lower() in PROSE and not machine_vocabulary(candidate) and not any(
                p in {".git", "node_modules", "__pycache__"} for p in candidate.parts
            ) and not any(a == "vale" and b == "private" for a, b in zip(candidate.parts, candidate.parts[1:])):
                if candidate not in files:
                    files.append(candidate)
    return sorted(files)


def snapshot_key(path: Path, session: str) -> Path:
    digest = hashlib.sha256((session + "\0" + str(path.resolve())).encode()).hexdigest()
    return Path.home() / ".cache/ste-writing/originals" / f"{digest}.json"


def remember_original(path: Path, session: str) -> None:
    if not automatic_enabled() or path.stat().st_size > 60_000:
        return
    cache = snapshot_key(path, session)
    cache.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    cache.parent.chmod(0o700)
    # Expire unused snapshots after a day; overwritten snapshots are consumed after edits.
    import time
    for old in cache.parent.glob("*.json"):
        if old.stat().st_mtime < time.time() - 86400:
            old.unlink(missing_ok=True)
    cache.write_text(json.dumps({"original": path.read_text()}))
    cache.chmod(0o600)


def load_original(path: Path) -> str | None:
    session = os.environ.get("STE_WRITING_SESSION")
    if not session:
        return None
    cache = snapshot_key(path, session)
    if not cache.is_file():
        return None
    import time
    if time.time() - cache.stat().st_mtime > 86400:
        cache.unlink(missing_ok=True)
        return None
    return json.loads(cache.read_text())["original"]


def forget_original(path: Path) -> None:
    session = os.environ.get("STE_WRITING_SESSION")
    if session:
        snapshot_key(path, session).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("description", "procedure", "safety"), default="description")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--base", action="store_true")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--no-personal-style", action="store_true")
    parser.add_argument("--strict-exit", action="store_true")
    parser.add_argument("--jev", action="store_true", help="Request hosted Jev decisions; requires TypeSafe credentials")
    parser.add_argument("--no-jev", action="store_true", help="Run only local checks")
    parser.add_argument("--no-book", action="store_true", help="Skip the optional Williams/Bizup context")
    parser.add_argument("--original", type=Path, help="Original for a single file's Jev comparison")
    parser.add_argument("--vale-launcher", type=Path, default=ROOT / "vale/check.py", help=argparse.SUPPRESS)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    files = prose_files(args.paths)
    if not files:
        parser.error("No supported prose files were found.")
    if args.original and len(files) != 1:
        parser.error("--original requires exactly one draft file.")
    if args.jev and args.no_jev:
        parser.error("Choose --jev or --no-jev.")
    command = [sys.executable, str(args.vale_launcher), "--profile", args.profile, "--format", "json"]
    for flag in ("base", "no_personal_style", "strict_exit"):
        if getattr(args, flag):
            command.append("--" + flag.replace("_", "-"))
    if args.config:
        command.extend(["--config", str(args.config)])
    command.extend(map(str, files))
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode not in (0, 1):
        print(result.stderr or result.stdout, file=sys.stderr)
        return 2
    try:
        findings = json.loads(result.stdout)
        if not isinstance(findings, dict) or any(not isinstance(v, list) for v in findings.values()):
            raise ValueError("Vale returned an invalid report.")
        harper = ensure_harper()
        ignored = (ROOT / "harper/ignore.csv").read_text().strip()
        style = Path.home() / ".config/ste-writing/style.json"
        prefs = json.loads(style.read_text()) if style.is_file() else {}
        dialect = "uk" if prefs.get("language") == "en-GB" and not args.no_personal_style else "us"
        use_jev = not args.no_jev and (args.jev or automatic_enabled())
    except (OSError, ValueError, RuntimeError) as error:
        print(f"Writing setup did not complete: {error}", file=sys.stderr)
        return 2
    errors = []
    for path in files:
        alerts = findings.setdefault(str(path), [])
        try:
            with tempfile.TemporaryDirectory(prefix="ste-harper-") as temporary:
                target = Path(temporary) / path.name
                html_prose = path.suffix.lower() == ".html"
                source = path.read_text()
                positions = []
                if path.suffix.lower() == ".html":
                    html = HTMLProse()
                    html.feed(source)
                    target = Path(temporary) / "prose.txt"
                    target.write_text("".join(html.parts))
                else:
                    prepared, positions = protected_markdown(source)
                    target.write_text(prepared)
                result = subprocess.run(
                    [harper, "lint", "--no-color", "--format", "json", "--quiet", "--dialect", dialect,
                     "--ignore", ignored, str(target)], capture_output=True, text=True, timeout=12, check=False,
                )
                reports = json.loads(result.stdout)
                if result.returncode not in (0, 1) or not isinstance(reports, list) or len(reports) != 1:
                    raise ValueError("Harper returned an invalid report.")
                report = reports[0]
                if report.get("error") or not isinstance(report.get("lints"), list):
                    raise ValueError("Harper could not read the document.")
                for lint in report["lints"]:
                    if html_prose:
                        line, column = 1, 1
                    else:
                        offset = lint["span"]["char_start"]
                        if not isinstance(offset, int) or not 0 <= offset < len(positions):
                            raise ValueError("Harper returned an invalid source span.")
                        offset = positions[offset]
                        line = source.count("\n", 0, offset) + 1
                        column = offset - source.rfind("\n", 0, offset)
                    suffix = " Review the extracted HTML prose; this location is document-wide." if html_prose else ""
                    alerts.append({
                        "Check": "Harper." + lint["rule"], "Severity": "suggestion", "Line": line,
                        "Span": [column, column], "Message": lint["message"] + suffix,
                    })
        except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
            errors.append(f"{path}: Harper check did not complete: {error}")
        if use_jev:
            try:
                original = args.original.read_text() if args.original else load_original(path)
                alerts.extend(review(path.read_text(), original, profile=args.profile, book=not args.no_book))
                if not args.original:
                    forget_original(path)
                if original is None:
                    print(f"{path}: Jev had no original; meaning and requirements were not compared.", file=sys.stderr)
            except (OSError, ValueError, RuntimeError, KeyError, sqlite3.Error) as error:
                errors.append(f"{path}: Jev check did not complete: {error}")
    for error in errors:
        print(error, file=sys.stderr)
    if args.format == "json":
        print(json.dumps(findings, indent=2, ensure_ascii=False))
    else:
        for path, alerts in findings.items():
            for alert in alerts:
                print(f"{path}:{alert['Line']}: {alert['Severity']} {alert['Check']}: {alert['Message']}")
        print(f"Writing: {sum(map(len, findings.values()))} findings.")
    if errors:
        return 2
    if args.strict_exit and any(a.get("Severity") in {"error", "warning"} for v in findings.values() for a in v):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
