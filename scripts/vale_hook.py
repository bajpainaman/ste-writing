#!/usr/bin/env python3
"""Lint prose files after Claude or Codex write/edit tools succeed."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vale"))
from ensure import ensure_vale
from ensure_harper import ensure_harper
from style_config import ensure_packages
from enable_vale_ci import permission_prompt, repository
from writing_check import machine_vocabulary, remember_original
from install import GLOBAL, save_style, style_revision
from jev_review import automatic_enabled
from style_book import settings as book_settings
PROSE = {".md", ".txt", ".rst", ".adoc", ".html"}
PROFILES = {"description", "procedure", "safety"}


def edited_files(payload: dict) -> list[Path]:
    cwd = Path(payload.get("cwd") or os.getcwd())
    raw = payload.get("tool_input", payload.get("toolInput", {}))
    inputs = raw if isinstance(raw, dict) else {}
    names = []
    for key in ("file_path", "path"):
        if isinstance(inputs.get(key), str):
            names.append(inputs[key])
    patch = raw if isinstance(raw, str) else inputs.get("patch") or inputs.get("input") or ""
    if isinstance(patch, str):
        names.extend(re.findall(r"(?m)^\*\*\* (?:Add File|Update File|Move to): (.+)$", patch))
    paths = []
    for name in names:
        path = Path(name)
        if not path.is_absolute():
            path = cwd / path
        path = path.resolve()
        if (
            path.suffix.lower() in PROSE
            and not machine_vocabulary(path)
            and path.is_file()
            and not any(part in {".git", "node_modules", "__pycache__"} for part in path.parts)
            and not any(a == "vale" and b == "private" for a, b in zip(path.parts, path.parts[1:]))
            and path not in paths
        ):
            paths.append(path)
    return paths


def project_config(path: Path) -> Path | None:
    for parent in path.parents:
        config = parent / ".vale.ini"
        if config.is_file():
            return config
        if (parent / ".git").exists() or parent == Path.home():
            break
    return None


def launcher(strict: bool) -> Path:
    candidates = [
        ROOT / "vale",
        Path.home() / ".claude/skills/ste-writing/vale",
        Path.home() / ".agents/skills/ste-writing/vale",
        Path.home() / ".codex/skills/ste-writing/vale",
    ]
    if strict:
        for candidate in candidates:
            if (candidate / "check.py").is_file() and (candidate / "private/description.ini").is_file():
                return candidate / "check.py"
    return ROOT / "vale/check.py"


def feedback(message: str, event: str = "PostToolUse") -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": message,
        },
    }))


def main() -> int:
    if os.environ.get("STE_VALE_AUTO", "1") == "0":
        return 0
    try:
        payload = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if not isinstance(payload, dict):
        return 0
    event = payload.get("hook_event_name", "PostToolUse")
    startup = event == "SessionStart"
    paths = edited_files(payload)
    session = str(payload.get("session_id") or "unknown")
    if event == "PreToolUse":
        for path in paths:
            try:
                remember_original(path, session)
            except (OSError, ValueError) as error:
                feedback(f"Jev original capture did not complete: {error}.", event)
        return 0
    if not paths and not startup:
        return 0
    messages = []
    try:
        revision = GLOBAL / ".engine-revision"
        preferences = GLOBAL / "style.json"
        if preferences.is_file() and (not revision.is_file() or revision.read_text().strip() != style_revision()):
            save_style(json.loads(preferences.read_text()))
        executable = ensure_vale()
        harper = ensure_harper()
        config = Path.home() / ".config/ste-writing/description.ini"
        ensure_packages(executable, config if config.is_file() else ROOT / "vale/description.ini")
        if startup:
            messages.append(f"STE English: Vale is ready at {executable}; Harper is ready at {harper}. Lint prose automatically after edits.")
            if automatic_enabled():
                messages.append("TypeSafe Jev review is enabled. Compare revisions with captured originals and review model decisions in context.")
                if book_settings().get("enabled"):
                    messages.append("Williams/Bizup book review is enabled. Use the williams-style skill for relevant passages and exact source locations. Editorial advice does not override STE, safety, or intended meaning.")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        feedback(f"Automatic writing setup did not complete: {error}. Report this limitation.", event)
        return 0
    roots = set()
    for path in [Path(payload.get("cwd") or os.getcwd())] if startup else [p.parent for p in paths]:
        try:
            repo = repository(path)
            if repo:
                roots.add(repo)
        except (OSError, subprocess.TimeoutExpired):
            pass
    for repo in sorted(roots):
        prompt = permission_prompt(repo, session)
        if prompt:
            messages.append(prompt)
    style = Path.home() / ".config/ste-writing/style.json"
    if style.is_file():
        messages.append("Apply the user's global writing preferences: " + style.read_text()[:4000])
    elif startup:
        messages.append(
            "Global writing style is not configured. Offer the guided STE installation: "
            "ask what writing the user likes, what to avoid, US or UK spelling, and any writer's traits to draw from. "
            "Save one global preference profile with scripts/install.py; keep STE facts and requirements intact."
        )
    profile = os.environ.get("STE_VALE_PROFILE", "description")
    if profile not in PROFILES:
        feedback("Automatic Vale check could not run: invalid STE_VALE_PROFILE.")
        return 0
    strict = os.environ.get("STE_VALE_STRICT", "0") == "1"
    for path in paths:
        if path.stat().st_size > 2 * 1024 * 1024:
            messages.append(f"{path}: automatic Vale skipped this file because it exceeds 2 MiB.")
            continue
        command = [sys.executable, str(ROOT / "scripts/writing_check.py"), "--vale-launcher", str(launcher(strict)),
                   "--profile", profile, "--format", "json"]
        config = project_config(path)
        if config:
            command.extend(["--config", str(config)])
        elif not strict:
            command.append("--base")
        command.append(str(path))
        result = None
        try:
            environment = dict(os.environ, STE_WRITING_SESSION=session)
            result = subprocess.run(command, capture_output=True, text=True, timeout=45, check=False, env=environment)
            data = json.loads(result.stdout)
            if not isinstance(data, dict) or any(not isinstance(alerts, list) for alerts in data.values()):
                raise ValueError("Vale returned an error instead of file findings.")
            findings = [alert for alerts in data.values() for alert in alerts]
            if any(not isinstance(alert, dict) for alert in findings):
                raise ValueError("Vale returned invalid findings.")
            if result.returncode not in (0, 1, 2):
                raise ValueError(f"Vale exited with code {result.returncode}.")
            if result.stderr.strip():
                messages.append(result.stderr.strip()[:1800])
            if result.returncode == 2:
                messages.append(f"{path}: writing checks did not all complete. Review the available findings and report this limitation.")
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            detail = (result.stderr.strip()[:1000] if result else "") or str(error)
            messages.append(f"{path}: automatic Vale check did not complete. {detail}")
            continue
        messages.append(f"Writing checks returned {len(findings)} findings for {path}.")
        for finding in findings[:12]:
            messages.append(
                f"  line {finding.get('Line', '?')}: {finding.get('Check', 'Vale')}: "
                f"{finding.get('Message', 'Review this finding.')}"
            )
        if len(findings) > 12:
            messages.append(f"  {len(findings) - 12} additional findings. Run scripts/writing_check.py for the full report.")
    messages.append(
        "Review these English style findings before finishing. Fix true findings and report intentional exceptions. "
        "Preserve facts, requirement strength, code, identifiers, URLs, and exact literals. "
        "If a check did not complete, report the limitation. A clean result does not certify STE compliance."
        " Jev comparison findings may reflect requested factual updates. Check them against the task; preserve authorized additions."
        " Revise at most twice. Preserve the original when meaning remains uncertain and ask for missing facts."
    )
    feedback("\n".join(messages), event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
