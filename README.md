# ste-writing

Write clearer technical prose. Lint the English.

This skill applies [ASD-STE100](https://www.asd-ste100.org/) (Simplified Technical English, Issue 9) principles to docs, READMEs, PR descriptions, error messages, release notes, and comments. It rewrites, authors, audits, and lints prose while preserving facts, requirements, code, identifiers, command syntax, and exact literals.

## Lint English

Install [Vale](https://docs.vale.sh/topics/installation), then run these commands from the repository root:

```bash
# General technical English: condensed STE style checks.
python3 vale/check.py --base README.md docs/

# Procedures: 20-word sentences and instruction checks.
python3 vale/check.py --profile procedure runbook.md

# JSON findings for editors and automation.
python3 vale/check.py --base --format json README.md
```

The [Vale package](vale/README.md) includes description, procedure, and safety profiles. It checks sentence and paragraph length, contractions, punctuation, voice, word choice, and configured terminology. The description profile is the default. The `--base` option selects the public rules. Without it, the launcher adds the private full-book dictionary when available.

All **53 writing rules** have a [coverage entry](vale/coverage.md). **27 have partial automated checks. 26 require contextual review.** The compiler can import the original book's dictionary, usage restrictions, and source locations. The full book and generated dictionary data stay local and Git-ignored.

These are English style checks. Meaning, grammatical use, technical terms, and safety decisions still require review. A clean result does not certify STE compliance.

## Install

Install it as a plugin:

```shell
/plugin marketplace add bajpainaman/ste-writing
/plugin install ste-writing@naman-plugins
```

Start it with `/ste-writing:ste-writing`, or ask Claude to "lint English in docs/", "de-slopify this", or "audit this prose".

Or install it as a standalone skill:

```bash
git clone https://github.com/bajpainaman/ste-writing.git ~/.claude/skills/ste-writing
```

Start it with `/ste-writing`.

## Python checker

`scripts/ste_lint.py` is an advisory linter with no dependencies. It checks mechanical STE rules and common signs of AI prose:

```bash
python3 scripts/ste_lint.py --mode flavored --profile auto README.md
python3 scripts/ste_lint.py --mode strict --format json --strict-exit docs/*.md
```

With `--strict-exit`, the checker returns exit code 1 when a non-advisory finding exists. It provides the AI-prose overlay and works when Vale is unavailable. Its vocabulary map is smaller than the optional full-book Vale dictionary.

## Contents

- `SKILL.md`: the skill entry point
- `chapters/`: 11 chapters that distill ASD-STE100 Issue 9
- `references/`: rules, word choice, rewrite workflow, finding taxonomy, AI-prose overlay
- `cheatsheet.md`, `glossary.md`, `patterns.md`: quick references
- `scripts/`: the linter and its tests
- `vale/`: profiles, compiler, glossary, rules, and coverage audit
- `evals/cases.json`: eval cases

## Tests

```bash
python3 scripts/test_ste_lint.py
python3 scripts/test_package.py
python3 vale/test_vale.py
```

See [the Vale instructions](vale/README.md) for private-source rebuilds and the unresolved dictionary count audit. See [CHANGELOG.md](CHANGELOG.md) for release changes.

## License

The code uses the MIT license. The ASD-STE100 standard remains the property of its publisher. This repository excludes the full standard.
