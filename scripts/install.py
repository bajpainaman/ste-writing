#!/usr/bin/env python3
"""Install Vale, Harper, automatic hooks, and one global personal style over STE."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = Path.home() / ".config/ste-writing"
sys.path.insert(0, str(ROOT / "vale"))
from ensure import ensure_vale
from ensure_harper import ensure_harper
from style_config import ensure_packages, profile_config


def json_rule(path: Path, rule: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rule, indent=2, ensure_ascii=False) + "\n")


def style_revision() -> str:
    files = [Path(__file__), ROOT / "vale/style_config.py"]
    for namespace in ("STE100", "STE100Description", "STE100Procedure", "STE100Safety", "SimplifyWriting", "config"):
        files += sorted(path for path in (ROOT / "vale/styles" / namespace).rglob("*")
                        if path.is_file() and not path.name.startswith("Dictionary"))
    return hashlib.sha256(b"".join(path.read_bytes() for path in files)).hexdigest()


def validate(profile: dict) -> None:
    if profile.get("language") not in {"en-US", "en-GB"}:
        raise ValueError("language must be en-US or en-GB.")
    for field in ("references", "likes", "dislikes", "avoid_terms"):
        if not isinstance(profile.get(field), list) or any(not isinstance(x, str) for x in profile[field]):
            raise ValueError(f"{field} must be a list of strings.")
    terms = profile.get("preferred_terms")
    if not isinstance(terms, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in terms.items()):
        raise ValueError("preferred_terms must map strings to strings.")
    for field, maximum in (("max_sentence_words", 25), ("max_paragraph_sentences", 6)):
        if type(profile.get(field)) is not int or not 1 <= profile[field] <= maximum:
            raise ValueError(f"{field} must be an integer from 1 to {maximum}.")


def save_style(profile: dict) -> None:
    validate(profile)
    GLOBAL.mkdir(parents=True, exist_ok=True)
    GLOBAL.chmod(0o700)
    styles = GLOBAL / "styles"
    styles.mkdir(exist_ok=True)
    for namespace in ("STE100", "STE100Description", "STE100Procedure", "STE100Safety", "SimplifyWriting", "config"):
        shutil.copytree(ROOT / "vale/styles" / namespace, styles / namespace, dirs_exist_ok=True)
    personal = styles / "UserStyle"
    personal.mkdir(exist_ok=True)
    for filename in ("AvoidTerms.yml", "PreferredTerms.yml", "BritishSpelling.yml"):
        (personal / filename).unlink(missing_ok=True)
    if profile["avoid_terms"]:
        json_rule(personal / "AvoidTerms.yml", {
            "extends": "existence", "level": "warning", "scope": "text", "ignorecase": True,
            "message": "Personal style: review '%s'. Prefer direct, concrete wording.",
            "tokens": [re.escape(term) for term in profile["avoid_terms"] if term.strip()],
        })
    if profile["preferred_terms"]:
        json_rule(personal / "PreferredTerms.yml", {
            "extends": "substitution", "level": "suggestion", "scope": "text", "ignorecase": True,
            "message": "Personal style: consider '%s' for '%s' if the meaning stays the same.",
            "swap": {re.escape(k): v for k, v in profile["preferred_terms"].items()},
        })
    maximum = profile["max_sentence_words"]
    counter = (ROOT / "vale/styles/config/scripts/DescriptionLength.tengo").read_text()
    counter = counter.replace("> 25", f"> {maximum}")
    (styles / "config/scripts/UserSentenceLength.tengo").write_text(counter)
    json_rule(personal / "SentenceLength.yml", {
        "extends": "script", "level": "warning", "scope": "sentence",
        "message": f"Personal style: keep this sentence at {maximum} words or fewer.",
        "script": "UserSentenceLength.tengo",
    })
    maximum = profile["max_paragraph_sentences"]
    (styles / "config/scripts/UserParagraphLength.tengo").write_text(
        'text := import("text")\nmatches := []\n'
        'sentences := text.re_find("[^.!?]+[.!?](?:\\\\s|$)", scope, -1)\n'
        f'if sentences != undefined && len(sentences) > {maximum} {{\n'
        '    matches = append(matches, {begin: 0, end: len(scope)})\n}\n'
    )
    json_rule(personal / "ParagraphLength.yml", {
        "extends": "script", "level": "warning", "scope": "paragraph",
        "message": f"Personal style: keep this paragraph at {maximum} sentences or fewer.",
        "script": "UserParagraphLength.tengo",
    })
    spelling = ""
    if profile["language"] == "en-GB":
        source = (ROOT / "vale/styles/STE100/AmericanSpelling.yml").read_text()
        pairs = re.findall(r'^  ([a-z]+): "([a-z]+)"$', source, re.M)
        json_rule(personal / "BritishSpelling.yml", {
            "extends": "substitution", "level": "warning", "scope": "text", "ignorecase": True,
            "message": "Personal spelling: use '%s' for '%s'.",
            "swap": {us: uk for uk, us in pairs},
        })
        spelling = "STE100.AmericanSpelling = NO\n"
    dictionary_source = next((path for path in (
        ROOT / "vale", Path.home() / ".claude/skills/ste-writing/vale",
        Path.home() / ".agents/skills/ste-writing/vale",
    ) if (path / "styles/STE100Dictionary").is_dir()), None)
    dictionary = dictionary_source is not None
    if dictionary:
        shutil.copytree(dictionary_source / "styles/STE100Dictionary", styles / "STE100Dictionary", dirs_exist_ok=True)
        for script in (dictionary_source / "styles/config/scripts").glob("Dictionary*.tengo"):
            shutil.copy2(script, styles / "config/scripts" / script.name)
    review_terms = [p.stem for p in (styles / "STE100").glob("WordReview_*.yml")]
    for name, namespaces in {
        "description": ["STE100", "STE100Description"],
        "procedure": ["STE100", "STE100Procedure"],
        "safety": ["STE100", "STE100Procedure", "STE100Safety"],
    }.items():
        config = profile_config(styles, namespaces, personal=True, spelling=spelling)
        (GLOBAL / f"{name}.ini").write_text(config)
        strict = profile_config(
            styles, namespaces, personal=True, dictionary=dictionary,
            spelling=spelling, review_terms=review_terms,
        )
        (GLOBAL / f"strict-{name}.ini").write_text(strict)
    (GLOBAL / ".vale.ini").write_text((GLOBAL / "description.ini").read_text())
    (GLOBAL / "style.json").write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
    (GLOBAL / ".engine-revision").write_text(style_revision() + "\n")


def install_hook(client: str) -> None:
    path = Path.home() / (".codex/hooks.json" if client == "codex" else ".claude/settings.json")
    data = json.loads(path.read_text()) if path.is_file() else {}
    # The Claude plugin supplies the same hooks; avoid registering duplicates.
    if client == "claude" and data.get("enabledPlugins", {}).get("ste-writing@naman-plugins"):
        print("Claude: enabled plugin supplies the automatic hooks.")
        return
    command = "python3 " + shlex.quote(str(ROOT / "scripts/vale_hook.py"))
    hooks = data.setdefault("hooks", {})
    for event in ("SessionStart", "PreToolUse", "PostToolUse"):
        entries = hooks.setdefault(event, [])
        existing = [hook for item in entries for hook in item.get("hooks", []) if "vale_hook.py" in hook.get("command", "")]
        if existing:
            for hook in existing:
                hook["timeout"] = 180
            continue
        entry = {"hooks": [{"type": "command", "command": command, "timeout": 180}]}
        if event in {"PreToolUse", "PostToolUse"}:
            entry["matcher"] = "Write|Edit|MultiEdit|apply_patch"
        entries.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"{client}: automatic writing hooks installed.")


def guided_profile() -> dict:
    profile = json.loads((ROOT / "profiles/default.json").read_text())
    print("One global writing style, applied over the STE rules.")
    profile["likes"] = [x.strip() for x in input("What writing do you like? Separate traits with commas: ").split(",") if x.strip()]
    profile["dislikes"] = [x.strip() for x in input("What should the writing avoid? Separate traits with commas: ").split(",") if x.strip()]
    language = input("English spelling: US or UK [US]: ").strip().lower()
    profile["language"] = "en-GB" if language in {"uk", "gb", "british"} else "en-US"
    profile["references"] = [x.strip() for x in input("People or publications whose traits you want [none]: ").split(",") if x.strip() and x.strip().lower() != "none"]
    extra = input("Exact words or phrases to flag, separated by commas [keep defaults]: ").strip()
    if extra:
        profile["avoid_terms"] = [x.strip() for x in extra.split(",") if x.strip()]
    profile["inferred_traits"] = False
    return profile


def install_book_skill() -> None:
    source = ROOT / "skills/williams-style"
    for directory in (".claude/skills", ".agents/skills", ".codex/skills"):
        target = Path.home() / directory / "williams-style"
        if source.resolve() != target.resolve():
            shutil.copytree(source, target, dirs_exist_ok=True)
    print("Williams/Bizup skill installed for Claude and Codex.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preferences", type=Path, help="Use a reviewed preference JSON file instead of the guided interview")
    parser.add_argument("--style-only", action="store_true", help="Configure the style without installing client hooks")
    parser.add_argument("--enable-jev", action="store_true", help="Enable hosted Jev reviews when TypeSafe credentials are available")
    parser.add_argument("--jev-key-file", type=Path, help="Reference an existing local dotenv file without copying the key")
    parser.add_argument("--jev-key-name", default="TYPESAFE_API_KEY", help="Variable name in the existing dotenv file")
    parser.add_argument("--style-book-source", type=Path, help="Index a local Williams/Bizup OCR directory or PDF")
    args = parser.parse_args()
    profile = json.loads(args.preferences.read_text()) if args.preferences else guided_profile()
    validate(profile)
    print(f"Vale ready: {ensure_vale()}")
    print(f"Harper ready: {ensure_harper()}")
    save_style(profile)
    ensure_packages(ensure_vale(), ROOT / "vale/description.ini")
    ensure_packages(ensure_vale(), GLOBAL / "description.ini")
    if args.enable_jev:
        path = GLOBAL / "jev.json"
        config = json.loads(path.read_text()) if path.is_file() else {}
        config.update({"enabled": True, "model": "jev-latest", "threshold": 0.8})
        if args.jev_key_file:
            config.update({"key_file": str(args.jev_key_file.expanduser().resolve()), "key_name": args.jev_key_name})
        path.write_text(json.dumps(config, indent=2) + "\n")
    if not args.style_only:
        install_book_skill()
        for client in ("claude", "codex"):
            install_hook(client)
    if args.style_book_source:
        from style_book import index
        report = index(args.style_book_source, Path.home() / ".local/share/ste-writing/books/williams.sqlite3")
        print(f"Williams/Bizup book indexed: {report['pages']} pages, {report['passages']} passages.")
    print(f"Global style: {GLOBAL / '.vale.ini'}")
    print("Restart your clients once to load newly installed hooks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
