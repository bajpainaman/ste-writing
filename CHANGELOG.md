# Changelog

## 1.3.0 (2026-10-01)

- Import Aasim Sani's simplify-writing rules and pinned Vale package selections.
- Install native Harper automatically and combine its grammar findings with Vale.
- Add TypeSafe Jev decisions for ambiguity, filler, and personal writing preferences.
- Capture originals for Jev comparisons of meaning, requirements, omissions, and added claims.
- Keep API keys in existing local files and cache raw decisions without prose.
- Run Vale and Harper in the approved GitHub Actions workflow.
- Index the full local Williams/Bizup book and add a skill for source-based revision.
- Use Jev to select relevant passages and review all twelve lessons and both appendices.
- Retain full-book decisions and use feedback to update source rankings.

## 1.2.0 (2026-09-29)

- Run Vale automatically after prose edits in Claude and Codex.
- Install a verified Vale release automatically when needed.
- Add guided setup for one global personal style alongside the STE rules.
- Ask permission for each repository before adding the GitHub Actions workflow.
- Load the shared Paul Graham, Patrick O'Grady, and Stripe preference profile in CI.

## 1.1.0 (2026-09-29)

- Add Vale linting for technical English, with description, procedure, and safety profiles.
- Map all 53 Issue 9 writing rules. 27 have partial checks. 26 require contextual review.
- Add a private book importer that retains dictionary entries, usage restrictions, source locations, and extraction audits.
- Add a project glossary for technical nouns, technical verbs, proper names, and canonical terminology.
- Integrate Vale into the writing skill while retaining the Python AI-prose checker and semantic preservation requirements.

The imported OCR has 879 approved and 1,319 non-approved headword/POS records,
compared with the book introduction's totals of 875 and 1,274. The count audit
remains unresolved. Git ignores the full source and generated dictionary files.
A clean lint result does not certify STE compliance.

## 1.0.0

Initial writing skill, condensed Issue 9 references, advisory Python checker,
and Claude Code plugin packaging.
