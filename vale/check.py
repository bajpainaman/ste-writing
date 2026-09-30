#!/usr/bin/env python3
"""Run the repository's Vale package with a specific STE writing profile."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def resolve_vale() -> str | None:
    executable = shutil.which("vale")
    # Snap's wrapper cannot open the hidden skill directory. Its installed Go
    # binary can run directly, with the same version and without another install.
    direct = Path("/snap/vale/current/bin/vale")
    if executable and Path(executable).parent == Path("/snap/bin") and direct.is_file():
        return str(direct)
    return executable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("description", "procedure", "safety"), default="description")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--base", action="store_true", help="Use the condensed package without a private full-book dictionary")
    parser.add_argument("paths", nargs="+", help="Files or directories to lint")
    args = parser.parse_args()
    vale = resolve_vale()
    if not vale:
        parser.error("Vale is required: https://docs.vale.sh/topics/installation")
    root = Path(__file__).resolve().parent
    private = root / "private" / f"{args.profile}.ini"
    full_book = (root / "styles/STE100Dictionary/DictionaryWords.yml").is_file()
    config = private if private.is_file() and full_book and not args.base else root / f"{args.profile}.ini"
    command = [vale, "--no-global", "--no-color", f"--config={config}"]
    if args.format == "json":
        command.append("--output=JSON")
    # Resolve paths so filenames cannot be interpreted as Vale options.
    command.extend(str(Path(p).resolve()) for p in args.paths)
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
