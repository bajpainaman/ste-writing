# STE100 for Vale

Run from the repository root:

```bash
# General technical English without the private dictionary.
python3 vale/check.py --base README.md docs/

# Strict STE profiles; use the private dictionary when available.
python3 vale/check.py --profile procedure YOUR_FILE.md
python3 vale/check.py --profile description --format json YOUR_FILE.md
python3 vale/check.py --profile safety YOUR_FILE.md
```

The launcher installs a SHA-256-verified [Vale release](https://github.com/vale-cli/vale/releases/tag/v3.23.0)
when no supported binary exists. It requires Python 3 and accepts files or directories. The compiler requires
Python 3.12 or later. With no `--profile` argument, it uses `description`.

The guided installer saves one global personal style at
`~/.config/ste-writing/.vale.ini`. Checks load that style alongside the STE
rules. Use `--no-personal-style` to inspect only the package rules. A project
`.vale.ini` passed with `--config` adds its checks to the global profile.

Session hooks prepare Vale, load personal preferences, and ask permission
before adding CI to a repository. Edit hooks lint Markdown, text,
reStructuredText, AsciiDoc, and HTML files. Shell edits require the agent
to run the launcher before finishing.

The launcher selects the private full-book dictionary when available.
Use `--base` to select the condensed package. With a Snap installation, the
launcher uses the installed Vale binary directly so it can read the hidden
skill directory.

## Implemented checks

[coverage.md](coverage.md) and [coverage.json](coverage.json) map all 53 writing
rules to their checks and remaining review requirements.

- 27 rules have partial automated checks.
- 26 rules require contextual review.
- The full-book dictionary provides 1,185 non-approved word/phrase patterns and
  1,502 approved lexical forms, including approximate noun plurals.
- Procedure sentences have a 20-word limit. Descriptions and NOTE sentences have
  a 25-word limit. Paragraphs have a six-sentence limit.

The package implements [Vale YAML checks](https://docs.vale.sh/checks/existence)
and [Tengo scripts](https://docs.vale.sh/checks/script). It protects fenced code,
inline code, and literal quotations from the contraction, semicolon, and
dictionary checks. Dictionary advice has no automatic replacement action.

These checks provide technical English style feedback. They do not establish
that a sentence is grammatically correct.

A lexical checker cannot establish meaning or part of speech. For example,
the dictionary approves `test` as a noun and rejects it as a verb. A whitelist cannot
decide which use appears in a sentence. The coverage map retains those review
requirements.

A clean Vale result does not certify STE compliance.

## The original book

The received Markdown resides at:

```text
vale/private/ASD-STE100_ISSUE9.md
```

It matches the original ZIP member byte for byte. The source, extracted
dictionary, private profiles, and generated dictionary scripts are Git-ignored.
The ZIP also retains the original OCR JSON.

Rebuild the local full-book checks:

```bash
python3 vale/build.py \
  --book vale/private/ASD-STE100_ISSUE9.md \
  --allow-count-mismatch
```

The importer retains headwords, parts of speech, permitted form text, meanings
or alternatives, examples, help restrictions, source excerpts, and source line
numbers. It recognizes parenthesized expressions and the two phrases whose
source rows have no POS label. It does not invent a POS for those phrases.

The importer parses every headword row. The parsed headword/POS totals are **879 approved
and 1,319 non-approved records**. The introduction states **875 and 1,274**.

These totals use different possible counting conventions or contain OCR/source
discrepancies. That discrepancy remains unresolved.

The audit records
`complete: false` and the original source SHA-256. The count override preserves
all source entries. It does not certify the extraction against an official PDF.
Unknown headword rows still fail the build with this override.

`private/dictionary.json` contains the extraction audit and all retained usage
restrictions. Approved/non-approved POS conflicts and constructions such as
`prevent … from` remain context review items.

## Project terminology

Edit [glossary.json](glossary.json) to register proper names, technical nouns,
technical verbs, and canonical terminology. For example:

```json
{
  "proper_names": ["World Health Organization"],
  "technical_nouns": ["cable", "cover", "valve"],
  "technical_verbs": ["upload"],
  "aliases": {"controller unit": "control unit"}
}
```

Rebuild after changing the glossary. Multi-word proper names count as one word.
Registered terms suppress lexical alerts. Their grammatical use and approved
technical-term categories still require review.

The word counter approximates
unregistered titles, unusual units, and other context-dependent constructs.

## Verification

```bash
python3 vale/test_vale.py
python3 vale/build.py \
  --book vale/private/ASD-STE100_ISSUE9.md \
  --allow-count-mismatch --check
```

Ten integration and import tests cover profile limits, the NOTE exception,
parenthetical text, units, quotations, code, and paragraph limits.
They also cover dictionary advice, POS conflicts, help restrictions, qualified
headwords, source byte integrity, and the count audit. Tested with the installed Vale 3.23.0. The
compiler requires Python 3.12 or later.

To rebuild only the distributable condensed rules, run `python3 vale/build.py`.
The public configuration files load that package. Private profiles add the full
dictionary. Use a separate style namespace for custom rules.
