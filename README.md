# ste-writing

This Claude Code skill applies [ASD-STE100](https://www.asd-ste100.org/) (Simplified Technical English, Issue 9) principles to technical prose.

It rewrites, authors, audits, and lints docs, READMEs, PR descriptions, error messages, release notes, and comments. It does not change code, identifiers, command syntax, or exact literals.

## Install

Install it as a plugin:

```shell
/plugin marketplace add bajpainaman/ste-writing
/plugin install ste-writing@naman-plugins
```

Start it with `/ste-writing:ste-writing`, or ask Claude to "de-slopify this" or "audit this prose".

Or install it as a standalone skill:

```bash
git clone https://github.com/bajpainaman/ste-writing.git ~/.claude/skills/ste-writing
```

Start it with `/ste-writing`.

## Linter

`scripts/ste_lint.py` is an advisory linter with no dependencies. It checks mechanical STE rules and common signs of AI prose:

```bash
python3 scripts/ste_lint.py --mode flavored --profile auto README.md
python3 scripts/ste_lint.py --mode strict --format json --strict-exit docs/*.md
```

With `--strict-exit`, the linter returns exit code 1 when a non-advisory finding exists. The linter does not contain the complete ASD-STE100 dictionary and cannot certify compliance.

## Contents

- `SKILL.md`: the skill entry point
- `chapters/`: 11 chapters that distill ASD-STE100 Issue 9
- `references/`: rules, word choice, rewrite workflow, finding taxonomy, AI-prose overlay
- `cheatsheet.md`, `glossary.md`, `patterns.md`: quick references
- `scripts/`: the linter and its tests
- `evals/cases.json`: eval cases

## Tests

```bash
python3 scripts/test_ste_lint.py
python3 scripts/test_package.py
```

## License

MIT
