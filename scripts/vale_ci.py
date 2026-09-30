#!/usr/bin/env python3
"""Lint changed tracked prose in GitHub Actions; use all prose for a manual run."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vale"))
from ensure import ensure_vale


def main() -> int:
    ensure_vale()
    base = os.environ.get("STE_BASE_SHA", "")
    if re.fullmatch(r"[0-9a-fA-F]{40,64}", base) and set(base) != {"0"}:
        command = ["git", "diff", "--name-only", "--diff-filter=ACMR", "-z", base, "HEAD"]
    else:
        command = ["git", "ls-files", "-z"]
    result = subprocess.run(command, check=True, capture_output=True)
    paths = [Path(os.fsdecode(name)) for name in result.stdout.split(b"\0") if name]
    paths = [p for p in paths if p.suffix.lower() in {".md", ".txt", ".rst", ".adoc", ".html"} and p.is_file()]
    if not paths:
        print("STE English: no changed prose files.")
        return 0
    profile = os.environ.get("STE_VALE_PROFILE", "description")
    code = 0
    for path in paths:
        command = [sys.executable, str(ROOT / "vale/check.py"), "--base", "--strict-exit", "--profile", profile]
        for parent in path.resolve().parents:
            config = parent / ".vale.ini"
            if config.is_file():
                command.extend(["--config", str(config)])
                break
            if (parent / ".git").exists():
                break
        command.append(str(path.resolve()))
        result = subprocess.run(command, check=False)
        code = max(code, result.returncode)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
