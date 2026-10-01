# Harper grammar checks

The writing launcher runs native `harper-cli` alongside Vale. Harper checks
grammar, repeated words, and confused words. The installer verifies a Harper
release's SHA-256 checksum when no supported command-line tool exists.

[Aasim Sani's simplify-writing fork](https://github.com/bajpainaman/simplify-writing)
supplies the rule selections in [ignore.csv](ignore.csv).

The ignored rules fall into three groups:

1. Spelling checks that flag product names and identifiers.
2. Length, heading, and punctuation checks that repeat Vale rules.
3. Expansion and compound checks that conflict with technical terms.

Harper uses the spelling convention from the global writing profile. HTML
checks use extracted prose and skip scripts, styles, and code. HTML findings
refer to the document rather than an exact source line.

Harper skips Markdown code and link destinations. The launcher marks filename
link labels as code and maps findings back to the original source positions.

Run the combined checks from the skill root:

```bash
python3 scripts/writing_check.py --base --no-jev README.md
```

Harper findings are suggestions for review. They do not fail CI by themselves.
An installation, parsing, or execution failure returns exit code 2.
