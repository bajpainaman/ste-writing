# STE writing

Write clearer technical prose. Lint the English.

This skill applies [ASD-STE100](https://www.asd-ste100.org/) (Simplified Technical English, Issue 9) principles to docs, READMEs, PR descriptions, error messages, release notes, and comments. It rewrites, authors, audits, and lints prose while preserving facts, requirements, code, identifiers, command syntax, and exact literals.

## Automatic English linting

The Claude plugin runs Vale and Harper after prose edits. The guided installer also sets up Codex hooks:

```bash
python3 scripts/install.py
```

The installer asks what writing you like, which wording to exclude, which English spelling to use, and whose traits to draw from. It saves one global style at `~/.config/ste-writing/style.json` and generates the Vale configuration alongside the STE rules.

Vale and Harper install automatically when needed. Restart your clients once after installing hooks. New sessions load your preferences. Prose edits through `Write`, `Edit`, `MultiEdit`, and `apply_patch` trigger checks and return findings to the agent.

The shared profile draws on Paul Graham, Patrick O'Grady, and Stripe. It favors ordinary words, concrete reasoning, precise terms, and paragraphs of four sentences or fewer. We inferred these traits from the references you selected.

Voice preferences guide the writer. Measurable rules check spelling, sentence limits, paragraph limits, and configured wording.

## Additional writing checks

[Aasim Sani's simplify-writing fork](https://github.com/bajpainaman/simplify-writing)
adds Vale checks for AI filler, vague wording, em dashes, and ambiguous pronouns.
The combined profiles load pinned Google, Readability, Microsoft, proselint,
and ai-tells packages. Conflicting or duplicate Google rules stay off.

[Harper](harper/README.md) adds native grammar checks. Optional
[Jev review](references/jev-review.md) uses TypeSafe's decision model to assess
ambiguity, filler, and fit with the global writing preferences.
Jev uses originals to compare meaning and requirement strength. The writing agent reviews
these judgments and makes revisions.

Enable Jev with `TYPESAFE_API_KEY` and `scripts/install.py --enable-jev`.
The installer can reference an existing dotenv file. It stores the key's location.

Enabled Jev reviews send prose to TypeSafe. Use `--no-jev` for local checks.

## GitHub Actions

For each repository, the hook asks permission before adding `.github/workflows/ste-english.yml`. Review [the template](automation/ste-english.yml). After approval:

```bash
python3 scripts/enable_vale_ci.py --repo /path/to/repo --approve
```

The workflow installs Vale and Harper. It checks changed tracked prose on pushes and pull requests. A manual run checks all tracked prose. Every workflow loads the shared profile from this repository, so personal style files stay centralized.

CI runs local checks without sending prose to Jev. An existing different workflow requires review before changing it.

## Run a check directly

Run these commands from the repository root. The launcher installs Vale and Harper automatically:

```bash
# General technical English: condensed STE style checks.
python3 scripts/writing_check.py --base README.md docs/

# Procedures: 20-word sentences and instruction checks.
python3 scripts/writing_check.py --profile procedure runbook.md

# JSON findings for editors and automation.
python3 scripts/writing_check.py --base --format json README.md
```

The [Vale package](vale/README.md) includes description, procedure, and safety profiles. It checks sentence and paragraph length, contractions, punctuation, voice, word choice, and configured terminology. The description profile is the default.

The `--base` option selects the public rules. Without it, the launcher adds the private full-book dictionary when available.

Use `vale/check.py` for Vale alone. The combined launcher also runs Harper and
Jev when configured. Edit hooks capture originals for Jev comparisons. For shell
edits, pass `--original original.md` with a single revised file.

All **53 writing rules** have a [coverage entry](vale/coverage.md). **27 have partial automated checks. 26 require contextual review.**

The compiler can import the original book's dictionary, usage restrictions, and source locations. The full book and generated dictionary data stay local and Git-ignored.

These are English style checks. Grammatical use, meaning, technical terms, and safety decisions still require review. A clean result does not certify STE compliance.

## Install

Install it as a plugin:

```shell
/plugin marketplace add bajpainaman/ste-writing
/plugin install ste-writing@naman-plugins
```

Start it with `/ste-writing:ste-writing`, or ask Claude to `lint English in docs/`, `de-slopify this`, or `audit this prose`.

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

With `--strict-exit`, the checker returns exit code 1 when a non-advisory finding exists. It works when Vale is unavailable. The combined launcher provides the AI-prose checks through Vale. The Python checker's vocabulary map is smaller than the optional full-book Vale dictionary.

## Williams and Bizup style

Index your local copy of `Style: Lessons in Clarity and Grace`, eleventh edition:

```bash
python3 scripts/style_book.py index --source "<book-path>"
python3 scripts/style_book.py search --query "actions verbs nominalization" --jev
python3 scripts/writing_check.py --base --jev README.md
```

The complete source becomes searchable locally. Jev selects relevant passages
and reviews fourteen editorial principles alongside STE and grammar findings.
The `williams-style` skill uses exact source locations for contextual revision.
Read [the book setup](references/williams-style.md) for coverage and review limits.

## Contents

- `SKILL.md`: the skill entry point
- `chapters/`: 11 chapters that distill ASD-STE100 Issue 9
- `references/`: rules, word choice, rewrite workflow, finding taxonomy, AI-prose overlay
- `cheatsheet.md`, `glossary.md`, `patterns.md`: quick references
- `scripts/`: the linter and its tests
- `vale/`: profiles, compiler, glossary, rules, and coverage audit
- `profiles/`: the shared style used by CI and the installer's initial settings
- `automation/` and `hooks/`: CI template and automatic lint hooks
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
