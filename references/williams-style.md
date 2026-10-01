# Williams and Bizup book review

Use `Style: Lessons in Clarity and Grace`, eleventh edition, as an editorial
review layer. The STE profile and the user's task determine which choices apply.

## Local source and coverage

The importer accepts an OCR directory containing `markdown.md` and
`pages/page-N/markdown.md`, or an original PDF readable by `pdftotext`.
It checks the title's authors, edition, page sequence, and available page metadata.
It indexes every nonblank source line without changing the downloaded files.

```bash
python3 scripts/style_book.py index --source "<book-path>"
python3 scripts/style_book.py status
```

The index lives at `~/.local/share/ste-writing/books/williams.sqlite3`.
The configuration at `~/.config/ste-writing/style-book.json` enables it globally.
The status report records pages, passages, source lines, blank pages, and a hash.

Reindex after replacing the source or correcting OCR. The hash identifies the
imported text. It does not certify OCR accuracy.

The lesson catalog covers all twelve lessons and both appendices.
Its summaries use original wording. The full index also covers the glossary,
suggested answers, acknowledgments, and index. Those sections can help locate
material, but they do not always contain advice suitable for a writing review.

## Relevant passages

```bash
python3 scripts/style_book.py search \
  --query "cohesion old new information paragraph topics" \
  --draft README.md --jev --limit 6
```

SQLite searches the full corpus locally. Jev judges the returned candidates
against the draft. Each result includes an OCR page, exact source line range,
excerpt, probability, and provisional decision.

A probability of at least 0.8 marks a candidate as relevant.
Values greater than 0.2 and less than 0.8 remain uncertain. These thresholds are provisional.

Inspect the actual passage before revising. A shared word alone is insufficient.
Lexical search can miss relevant guidance. Use targeted queries when needed.

## Automatic review

When you enable Jev and the book index, the existing edit hook uses both.
The combined launcher supplies fourteen editorial checks and up to six passages.
Jev reviews each judgment independently in one request. It also checks passage
relevance.

Applicable book findings carry printed lesson pages and available
source excerpts that Jev judged relevant to the draft.

```bash
python3 scripts/writing_check.py --base --jev README.md
python3 scripts/writing_check.py --base --jev --original original.md draft.md
```

Without an original, meaning and requirement comparisons do not run.
The agent reviews findings, chooses justified edits, and makes at most two passes.

STE requirements, safety, facts, and requested updates take priority.
Book advice is advisory and does not automatically change files or fail CI.

The review sends selected excerpts and the draft to TypeSafe.
It also sends an original when you supply one or the edit hook captures one.
The source files and full index remain local. The response cache stores validated
decisions and usage without prose.

Captured originals expire after one day.

Use `--no-jev` to keep checks local. Use `--no-book` to run Jev without book context.
The approved CI workflow runs local Vale and Harper checks.

## Reading a source location

An OCR page counts from the first extracted page, including front matter.
Printed page numbers come from the book's contents and differ from OCR numbers.
Line ranges refer to the cited page's Markdown file.

PDF imports instead cite
line ranges in extracted text. Check OCR against the page image when needed.

The standalone `williams-style` skill explains how to retrieve and apply guidance.

Read [book decisions and feedback](book-decisions.md) to run Jev across every
passage, inspect previous judgments, and update retrieval scores with evidence.

The publisher retains copyright in the source text. The repository distributes
original summaries and tooling. Local book imports retain their original rights.
