#!/usr/bin/env python3
"""Run the repository's Vale package with a specific STE writing profile."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from ensure import ensure_vale, resolve_vale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("description", "procedure", "safety"), default="description")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--base", action="store_true", help="Use the condensed package without a private full-book dictionary")
    parser.add_argument("--config", type=Path, help="Use a project's Vale configuration")
    parser.add_argument("--no-personal-style", action="store_true", help="Use the package without the global personal style")
    parser.add_argument("--strict-exit", action="store_true", help="Exit 1 for warning or error findings")
    parser.add_argument("paths", nargs="+", help="Files or directories to lint")
    args = parser.parse_args()
    try:
        vale = ensure_vale()
    except (OSError, RuntimeError) as error:
        parser.error(f"Automatic Vale installation failed: {error}")
    root = Path(__file__).resolve().parent
    private = root / "private" / f"{args.profile}.ini"
    full_book = (root / "styles/STE100Dictionary/DictionaryWords.yml").is_file()
    config = private if private.is_file() and full_book and not args.base else root / f"{args.profile}.ini"
    global_style = Path.home() / ".config/ste-writing" / f"{'strict-' if not args.base else ''}{args.profile}.ini"
    if global_style.is_file() and not args.no_personal_style:
        config = global_style
    configs = [config]
    if args.config:
        project = args.config.resolve()
        if not project.is_file():
            parser.error(f"Vale configuration does not exist: {project}")
        if project != config:
            configs.append(project)
    findings = {}
    exit_code = 0
    for selected in configs:
        command = [vale, "--no-global", "--no-color", "--output=JSON", f"--config={selected}"]
        # Resolve paths so filenames cannot be interpreted as Vale options.
        command.extend(str(Path(p).resolve()) for p in args.paths)
        result = subprocess.run(command, check=False, capture_output=True, text=True)
        exit_code = max(exit_code, result.returncode)
        try:
            data = json.loads(result.stdout)
            if not isinstance(data, dict) or any(not isinstance(alerts, list) for alerts in data.values()):
                raise ValueError("Invalid Vale report")
        except ValueError:
            print(result.stderr or result.stdout or "Vale returned no report.", file=sys.stderr)
            return result.returncode or 2
        for path, alerts in data.items():
            combined = findings.setdefault(path, [])
            for alert in alerts:
                if alert not in combined:
                    combined.append(alert)
    if args.format == "json":
        print(json.dumps(findings, indent=2, ensure_ascii=False))
    else:
        for path, alerts in findings.items():
            for alert in alerts:
                print(f"{path}:{alert['Line']}: {alert['Severity']} {alert['Check']}: {alert['Message']}")
        print(f"Vale: {sum(map(len, findings.values()))} findings.")
    if args.strict_exit and any(alert.get("Severity") in {"warning", "error"} for alerts in findings.values() for alert in alerts):
        exit_code = max(exit_code, 1)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
