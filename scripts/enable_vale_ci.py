#!/usr/bin/env python3
"""Prepare or install STE CI in one repository after explicit user approval."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = Path(".github/workflows/ste-english.yml")
STATE = Path.home() / ".local/state/ste-writing/ci-consent.json"


def repository(path: Path) -> Path | None:
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=5)
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else None


def read_state() -> dict:
    try:
        data = json.loads(STATE.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=STATE.parent, delete=False) as stream:
        json.dump(data, stream, indent=2)
        temporary = Path(stream.name)
    os.replace(temporary, STATE)


def key(repo: Path) -> str:
    return hashlib.sha256(os.fsencode(repo)).hexdigest()


def permission_prompt(repo: Path, session: str) -> str:
    if (repo / WORKFLOW).is_file():
        return ""
    data = read_state()
    entry = data.get(key(repo), {})
    if entry.get("decision") == "declined" or entry.get("prompted_session") == session:
        return ""
    data[key(repo)] = {"decision": "pending", "prompted_session": session}
    save_state(data)
    return (
        f"STE CI is missing in {repo}. Before adding it, ask the user for permission for this repository. "
        f"Show {ROOT / 'automation/ste-english.yml'} as the proposed workflow. "
        "Explain that it adds .github/workflows/ste-english.yml, installs Vale in GitHub Actions, "
        "and lints changed tracked prose on pushes and pull requests. "
        f"After an explicit yes, run python3 {shlex.quote(str(ROOT / 'scripts/enable_vale_ci.py'))} --repo {shlex.quote(str(repo))} --approve. "
        "After an explicit no, run the same command with --decline. "
        "Do not infer approval from silence, a prior approval for another repository, or a style preference."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    decision = parser.add_mutually_exclusive_group()
    decision.add_argument("--approve", action="store_true")
    decision.add_argument("--decline", action="store_true")
    args = parser.parse_args()
    repo = repository(args.repo)
    if not repo:
        parser.error("The target is not a Git repository.")
    if not args.approve and not args.decline:
        print((ROOT / "automation/ste-english.yml").read_text())
        print(f"Proposed destination: {repo / WORKFLOW}\nExplicit approval is required.")
        return 0
    data = read_state()
    if args.decline:
        data[key(repo)] = {"decision": "declined"}
        save_state(data)
        print(f"STE CI declined for {repo}.")
        return 0
    target = repo / WORKFLOW
    content = (ROOT / "automation/ste-english.yml").read_text()
    if target.exists():
        if target.read_text() != content:
            parser.error(f"Existing workflow differs. Review it before changing {target}.")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("x") as stream:
            stream.write(content)
    data[key(repo)] = {"decision": "approved"}
    save_state(data)
    print(f"Added STE CI: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
