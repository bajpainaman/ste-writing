---
name: williams-style
description: Review and revise prose with Joseph M. Williams and Joseph Bizup's Style, using a full local book index, exact source locations, and TypeSafe Jev relevance decisions. Use for clarity, sentence structure, coherence, concision, emphasis, and source attribution alongside STE writing.
---

# Williams and Bizup style

Use the local copy of `Style: Lessons in Clarity and Grace`, eleventh edition,
to diagnose a specific reader problem. Apply its guidance alongside STE writing.

## Find the tools

Find the installed `ste-writing` root in `CLAUDE_PLUGIN_ROOT`,
`~/.claude/skills/ste-writing`, `~/.agents/skills/ste-writing`, or
`~/.codex/skills/ste-writing`. Confirm that `scripts/style_book.py` exists.
Use that path as `<ste-root>` in the commands below.

The source remains local. Read the index status before using page citations:

```bash
python3 "<ste-root>/scripts/style_book.py" status
```

If no index exists, ask for the book's OCR folder or PDF. Import it with:

```bash
python3 "<ste-root>/scripts/style_book.py" index --source "<book-path>"
```

## Retrieve guidance

Read `references/williams-principles.json` under the STE root for the lesson
catalog. It contains original summaries of all twelve lessons and both appendices.
The local index also includes the glossary, answers, and remaining book pages.

Search with the diagnosed problem rather than only the draft's subject matter:

```bash
python3 "<ste-root>/scripts/style_book.py" search \
  --query "characters subjects actions verbs nominalization" \
  --draft "<draft-file>" --jev
```

Jev judges whether each retrieved passage contains useful guidance for the draft.
It returns provisional relevance probabilities. Inspect uncertain results.

Read the returned excerpts and cited source lines before applying their advice.
Search other terms when the shortlist misses the problem.

An example can demonstrate bad writing. An exercise or index entry can mention a
topic without teaching its use. Distinguish these cases from the author's guidance.
Check the page image when OCR changes punctuation or makes a passage unclear.

## Feed the writing review

```bash
python3 "<ste-root>/scripts/writing_check.py" \
  --base --jev --original "<original-file>" "<draft-file>"
```

The launcher combines Vale and Harper findings with Jev's semantic review.
When you enable the book index, it sends the lesson catalog and a small passage
shortlist with the draft. Book findings include lesson references and relevant
source excerpts when available. Review the full report before revising.

Record facts, conditions, numbers, uncertainty, and requirement strength first.
Make at most two revision passes. Preserve authorized factual additions.

Keep STE requirements and safety wording ahead of optional editorial choices.
Never invent an actor or remove a qualification to make a sentence shorter.

Concision, rhythm, and voice depend on audience and purpose. A reference table,
procedure, or short answer does not need an essay introduction or literary variety.
Jev selects attention. The writing agent chooses and makes justified edits.

## Full-book decisions and adaptation

Use `scripts/book_learning.py audit` under the STE root to review every passage.
Run `scores` to inspect coverage and provisional source rankings.
Book lookup supplies prior decisions to Jev and uses their scores in retrieval.
Use `audit --passage <id> --reconsider` to reassess a decision with its history.

Read the source before changing a score. Record evidence with `feedback` and
mark an agent's own review with `--reviewer agent`. Explicit corrections take
priority over later model guesses. Preserve prior versions and user intent.

Read `references/book-decisions.md` under the STE root for commands and limits.

## Source and limits

Report OCR page numbers and page-local line ranges exactly as returned.
Printed page numbers in the catalog apply to this edition. These locations differ.

Full indexing covers the source text. Lexical retrieval does not guarantee that
every relevant passage reaches Jev. Model probabilities remain advisory.

The source, SQLite index, and API credentials remain outside the repository.
Hosted reviews send the draft, optional original, summaries, and selected excerpts
to TypeSafe. Use `--no-jev` for local checks or `--no-book` to omit book context.
Read `references/williams-style.md` under the STE root for setup details.
