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

Install [Vale](https://docs.vale.sh/topics/installation) first. The launcher
requires Python 3 and accepts files or directories. The compiler requires
Python 3.12 or later. With no `--profile` argument, it uses `description`.

The launcher selects the private full-book dictionary when it is installed.
Use `--base` to select the condensed package. With a Snap installation, the
launcher uses the installed Vale binary directly so it can read the hidden
skill directory.

## What is implemented

[coverage.md](coverage.md) and [coverage.json](coverage.json) map all 53 writing
rules to their checks and remaining review requirements.

- 27 rules have partial automated checks.
- 26 rules require contextual review.
- The full-book dictionary provides 1,185 non-approved word/phrase patterns and
  1,502 approved lexical forms, including approximate noun plurals.
- Procedure sentences have a 20-word limit; descriptions and NOTE sentences have
  a 25-word limit. Paragraphs have a six-sentence limit.

The package implements [Vale YAML checks](https://docs.vale.sh/checks/existence)
and [Tengo scripts](https://docs.vale.sh/checks/script). It protects fenced code,
inline code, and literal quotations from the contraction, semicolon, and
dictionary checks. Dictionary advice has no automatic replacement action.
These checks provide technical English style feedback; they do not establish
that a sentence is grammatically correct.

A lexical checker cannot establish meaning or part of speech. For example,
`test` is approved as a noun and non-approved as a verb. A whitelist cannot
decide which use appears in a sentence. The coverage map retains those review
requirements; a clean Vale result does not certify STE compliance.

## The original book

The received Markdown is stored at:

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

Every headword row is parsed. The parsed headword/POS totals are **879 approved
and 1,319 non-approved records**; the introduction states **875 and 1,274**.
These totals use different possible counting conventions or contain OCR/source
discrepancies. That discrepancy remains unresolved. The audit records
`complete: false` and the original source SHA-256. The count override preserves
all source entries; it does not certify the extraction against an official PDF.
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
technical-term categories still require review. The word counter approximates
unregistered titles, unusual units, and other context-dependent constructs.

## Verification

```bash
python3 vale/test_vale.py
python3 vale/build.py \
  --book vale/private/ASD-STE100_ISSUE9.md \
  --allow-count-mismatch --check
```

Ten integration and import tests cover profile limits, the NOTE exception,
parenthetical text, units, quotations, code, paragraph limits, dictionary
advice, POS conflicts, help restrictions, qualified headwords, source byte
integrity, and the count audit. Tested with the installed Vale 3.23.0. The
compiler requires Python 3.12 or later.

To rebuild only the distributable condensed rules, run `python3 vale/build.py`.
The public configuration files load that package; private profiles add the full
dictionary. Custom rules should use a separate style namespace.
