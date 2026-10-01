# Jev writing review

Jev returns decisions and probabilities. The writing agent uses those decisions
to guide revisions.

Vale checks the STE, personal, and developer style rules.
Harper checks grammar. Jev reviews ambiguity, filler, and conflict with the
global writing preferences.

When an original is available, Jev also compares facts, requirement strength,
omissions, and added claims. Without an original, those comparison checks do
not run. Jev judges the supplied evidence rather than external factual truth.

## Set up

Run these commands from the skill root. Install TypeSafe using one method:

```bash
npx skills add typesafe-ai/skills --skill typesafe-ai --agent codex --global --yes
```

For Claude Code, use its plugin installation instead:

```text
claude plugin marketplace add typesafe-ai/skills
claude plugin install typesafe@typesafe-ai
```

Use the TypeSafe skill when changing the Jev integration. Read its live
[API contract](https://docs.typesafe.ai/api) and
[Noul guidance](https://docs.typesafe.ai/primitives/noul).

Set `TYPESAFE_API_KEY` in the agent's environment. Or reference an existing
dotenv file without copying its key:

```bash
python3 scripts/install.py \
  --preferences /path/to/style.json \
  --enable-jev --jev-key-file /path/to/.env --jev-key-name KEY
```

The global `~/.config/ste-writing/jev.json` records the path and variable
name. It does not contain the key. The parser reads dotenv values without
executing shell commands. Enabled reviews send prose to TypeSafe's API.

## Review a revision

```bash
python3 scripts/writing_check.py --base --jev \
  --original original.md revision.md
```

Edit hooks capture a local original before editing. Snapshots expire after
one day. A review consumes the snapshot. Shell edits require an explicit
`--original` file to compare meaning and requirements.

All independent questions run in one request per document. Each question
asks for a Noul, the probability that a specific problem exists. Responses
must contain every requested answer with a valid probability.

The local policy flags probabilities of 0.8 or higher for review. Values
between 0.2 and 0.8 require contextual review. These initial thresholds need
evaluation on representative writing before they can support automatic
acceptance. Jev does not change files or authorize an edit.

The cache retains decisions, model IDs, and token usage for one day. It stores
no source prose or API keys. Its request hash changes when the evidence or
questions change. Threshold changes reuse the same raw judgments.

Review the semantic invariants after any revision. Fix clear problems, record
intentional exceptions, and rerun the checks. Stop after two revision passes
if findings remain uncertain. Ask for missing facts when they affect meaning.

Requested factual updates can cause comparison findings. Check them against
the user's task and supporting facts. Record authorized additions as intentional.

## Controls and limits

1. Use `--no-jev` or `STE_JEV_AUTO=0` to run local checks.
2. Use `STE_JEV_MODEL` to select a documented Jev model ID.
3. Review smaller complete sections when the request exceeds 120 KB.
4. Report service failures. Local findings remain available when Jev fails.
5. GitHub Actions runs local checks without uploading prose to Jev.

A low problem probability does not prove accuracy or STE compliance.
