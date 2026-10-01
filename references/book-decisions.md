# Book decisions and feedback

Run Jev across the full local book index:

```bash
python3 scripts/book_learning.py audit
python3 scripts/book_learning.py scores
```

Each passage receives three independent judgments: reusable guidance, actionable
advice, and content that consists only of an example or reference.
The pass includes every indexed passage. It preserves uncertain decisions.
An interrupted pass resumes from missing records when you run `audit` again.

## Scores and prior decisions

The source score combines those judgments into a provisional ranking value.
It measures whether a passage can support writing review. It does not measure
the quality of your writing or certify STE compliance.

The ledger retains previous scores, model decisions, revisions, and feedback.
Book lookup uses those scores to adjust the local shortlist.
Jev receives a candidate's previous decision when judging its relevance.
It must assess the actual source independently because prior judgments can be wrong.

```bash
python3 scripts/book_learning.py history --passage p43_l14
python3 scripts/book_learning.py audit --passage p43_l14 --reconsider
```

Reconsideration supplies the earlier decisions and feedback to Jev.
It records the new decisions and updates the model ranking score.
Explicit reviewer corrections retain priority until the reviewer changes them.
All earlier versions remain in the history.

## Correct a score

Read the cited source before rating it. Use 1 for useful guidance and 0 for
content that cannot support a review. Intermediate values express mixed usefulness.
Include a short evidence note explaining the decision.

```bash
python3 scripts/book_learning.py feedback --passage p43_l14 \
  --rating 1 --note "Explains how verbs can express the main action."
```

Feedback changes the retrieval score immediately and enters later Jev context.
An agent must add `--reviewer agent` when recording its own source review.
Agent reviews do not count as user ratings. The scoring report measures agreement
with user ratings only when such ratings exist.

These changes update decisions and retrieval rankings. The writing agent can
revise a skill instruction when source evidence supports the change and the
user authorizes that edit. Keep STE, facts, safety, and requirement strength.

The ledger lives at `~/.local/share/ste-writing/books/decisions.sqlite3`.
It records source identities, decisions, and feedback without storing book text
or API credentials. Keep private details out of feedback notes.
