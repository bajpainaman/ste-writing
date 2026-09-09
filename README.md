# ste-writing

A Claude Code skill that rewrites, authors, audits, and lints technical prose using [ASD-STE100](https://www.asd-ste100.org/) (Simplified Technical English, Issue 9) principles — adapted for software docs, READMEs, PR descriptions, error messages, release notes, and comments.

Use it to de-slopify AI-sounding prose, simplify jargon, tighten procedures and safety instructions, and check word choice, voice, sentence length, and structure. It never rewrites code, identifiers, command syntax, or exact literals.

## Install

Clone into your Claude Code skills directory:

```bash
git clone https://github.com/bajpainaman/ste-writing.git ~/.claude/skills/ste-writing
```

Then invoke it in Claude Code with `/ste-writing`, or just ask things like "de-slopify this", "make this not sound like AI", or "audit this prose".

Works from `~/.codex/skills/ste-writing` too — the skill preamble checks both locations.

## What's inside

| Path | Contents |
|---|---|
| `SKILL.md` | The skill entry point: workflow, modes, and guardrails |
| `chapters/` | 11 chapters distilling ASD-STE100 Issue 9 (words, verbs, sentences, procedures, descriptions, safety, punctuation, practices, dictionary) |
| `references/` | Rules, word-choice tables, rewrite workflow, finding taxonomy, AI-prose overlay, source notes |
| `cheatsheet.md` | One-page quick reference |
| `glossary.md` / `patterns.md` | Terminology and common rewrite patterns |
| `scripts/ste_lint.py` | Standalone advisory linter (no dependencies, Python 3) |
| `evals/cases.json` | Eval cases for the skill's behavior |

## The linter

`scripts/ste_lint.py` is a standalone, dependency-free advisory linter for STE mechanics and AI-prose smells:

```bash
python3 scripts/ste_lint.py --mode flavored --profile auto README.md
python3 scripts/ste_lint.py --mode strict --format json --strict-exit docs/*.md
python3 scripts/ste_lint.py --self-check
```

- `--mode strict` enforces STE mechanics; `--mode flavored` targets STE-flavored technical prose.
- `--profile` sets the content type and sentence-length limit (`procedure`, `description`, `safety`, `interface`, or `auto`).
- `--strict-exit` returns exit code 1 when a non-advisory finding exists, for CI use.

It checks mechanical rules and common prose smells; it does not implement the complete ASD-STE100 dictionary and cannot certify compliance.

## Tests

```bash
python3 scripts/test_ste_lint.py
python3 scripts/test_package.py
```

## License

MIT
