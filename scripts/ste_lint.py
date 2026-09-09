#!/usr/bin/env python3
"""Advisory ASD-STE100 and AI-prose linter.

This tool checks mechanical rules and common prose smells. It does not implement
the complete ASD-STE100 dictionary and cannot certify compliance.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


SEVERITY_WEIGHT = {"high": 20, "medium": 8, "low": 2, "advisory": 0}
PROFILE_LIMIT = {
    "procedure": 20,
    "description": 25,
    "safety": 20,
    "interface": 20,
}

CONTRACTIONS = re.compile(
    r"\b(?:"
    r"aren't|can't|couldn't|didn't|doesn't|don't|hadn't|hasn't|haven't|"
    r"he's|here's|how's|isn't|it's|let's|mustn't|shan't|she's|shouldn't|"
    r"that's|there's|they're|they've|wasn't|we're|we've|weren't|what's|"
    r"where's|who's|won't|wouldn't|you're|you've"
    r")\b",
    re.IGNORECASE,
)

PASSIVE = re.compile(
    r"\b(?:am|is|are|was|were|be|been|being)\s+"
    r"(?:\w+\s+){0,2}"
    r"(?:\w+(?:ed|en)|built|done|found|given|held|known|made|put|read|"
    r"sent|set|shown|told|used|written)\b",
    re.IGNORECASE,
)

STACKED_AUXILIARY = re.compile(
    r"\b(?:have|has|had)\s+(?:been\s+)?\w+(?:ed|en)\b|"
    r"\b(?:would|could|should|might)\s+(?:have\s+)?(?:been\s+)?\w+\b",
    re.IGNORECASE,
)

PROGRESSIVE = re.compile(
    r"\b(?:am|is|are|was|were|be|been)\s+\w+ing\b",
    re.IGNORECASE,
)

LATIN_ABBREVIATION = re.compile(r"\b(?:e\.g\.|i\.e\.|etc\.)", re.IGNORECASE)
AMBIGUOUS_THIS = re.compile(
    r"\bthis\s+(?:is|was|can|could|will|would|may|might|must|should|"
    r"has|had|does|did)\b",
    re.IGNORECASE,
)
GENDERED = re.compile(
    r"\b(?:he|she|him|her|his|hers|himself|herself|man|woman|men|women)\b",
    re.IGNORECASE,
)

PHRASAL_VERBS = (
    "back up",
    "break down",
    "bring up",
    "carry out",
    "check out",
    "come up with",
    "figure out",
    "fill out",
    "find out",
    "follow up",
    "kick off",
    "lay out",
    "look into",
    "pick up",
    "roll out",
    "set up",
    "shut down",
    "spin up",
    "start up",
    "take down",
    "turn off",
    "turn on",
)

REVIEW_TERMS = {
    "acceptable": "Review PERMITTED.",
    "alternate": "Review ALTERNATIVE.",
    "avoid": "Review PREVENT or reconstruct the sentence.",
    "both": "Review THE TWO when exactly two known items exist.",
    "ensure": "Review MAKE SURE.",
    "fit": "Review INSTALL only when installation is the action.",
    "follow": "Review OBEY only for instructions.",
    "further": "Review MORE and preserve the intended dimension.",
    "however": "Review BUT.",
    "insert": "Review PUT, but preserve code-domain terms.",
    "main": "Review PRIMARY.",
    "may": "Review CAN, but preserve legal permission and uncertainty.",
    "now": "Review AT THIS TIME or delete if time is irrelevant.",
    "perform": "Use the primary action verb.",
    "portion": "Review PART.",
    "press": "Review PUSH, but preserve labels and hardware names.",
    "repeat": "Review DO ... AGAIN.",
    "shall": "Review MUST only when requirement force is equal.",
    "should": "Do not strengthen advice into a requirement without authority.",
    "since": "Review BECAUSE when the meaning is causal.",
    "therefore": "Review THUS or AS A RESULT.",
    "using": "Prefer the primary action verb or WITH.",
}

AI_PHRASES = {
    "it is important to note": "State the fact directly.",
    "it is worth mentioning": "State the fact directly.",
    "in today's rapidly evolving": "Delete the time-setting filler.",
    "when it comes to": "Name the topic directly.",
    "at its core": "State the core fact.",
    "as we have seen": "Delete the recap lead-in.",
    "in conclusion": "Delete unless a distinct conclusion follows.",
    "in order to": "Use TO.",
    "at the end of the day": "State the decision or result.",
}

AI_WORDS = {
    "comprehensive",
    "crucial",
    "cutting-edge",
    "delve",
    "effortless",
    "ecosystem",
    "empower",
    "facilitate",
    "foster",
    "fundamental",
    "game-changing",
    "innovative",
    "intricate",
    "journey",
    "landscape",
    "leverage",
    "multifaceted",
    "nuanced",
    "pivotal",
    "powerful",
    "realm",
    "revolutionary",
    "robust",
    "scalable",
    "seamless",
    "showcase",
    "significant",
    "tapestry",
    "transformative",
    "underscore",
    "unlock",
    "utilize",
    "vibrant",
    "world-class",
}

IMPERATIVE_VERBS = {
    "add",
    "apply",
    "attach",
    "check",
    "clean",
    "click",
    "close",
    "connect",
    "copy",
    "create",
    "delete",
    "disconnect",
    "do",
    "download",
    "enter",
    "install",
    "make",
    "move",
    "open",
    "push",
    "read",
    "remove",
    "replace",
    "restart",
    "run",
    "save",
    "select",
    "set",
    "start",
    "stop",
    "turn",
    "type",
    "upload",
    "use",
    "verify",
    "wait",
    "write",
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    line: int
    message: str
    excerpt: str
    suggestion: str


@dataclass(frozen=True)
class TextBlock:
    line: int
    text: str
    kind: str


def clean_markdown_text(line: str) -> str:
    """Remove Markdown syntax while preserving visible prose."""
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", line)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`[^`]*`", " CODE ", text)
    text = re.sub(r"<https?://[^>]+>", " URL ", text)
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+", "", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text)
    text = re.sub(r"[*_~]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def text_blocks(text: str) -> list[TextBlock]:
    """Return prose blocks and skip fenced code, tables, and separators."""
    blocks: list[TextBlock] = []
    paragraph: list[str] = []
    paragraph_line = 1
    in_fence = False

    def flush() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append(TextBlock(paragraph_line, " ".join(paragraph), "paragraph"))
            paragraph = []

    for line_number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            flush()
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not stripped:
            flush()
            continue
        if re.match(r"^\s*\|.*\|\s*$", raw):
            flush()
            continue
        if re.match(r"^\s*(?:---+|===+)\s*$", raw):
            flush()
            continue

        is_list = bool(re.match(r"^\s{0,3}(?:[-*+]|\d+[.)])\s+", raw))
        is_heading = bool(re.match(r"^\s{0,3}#{1,6}\s+", raw))
        cleaned = clean_markdown_text(raw)
        if not cleaned:
            continue

        if is_list or is_heading:
            flush()
            blocks.append(
                TextBlock(line_number, cleaned, "list" if is_list else "heading")
            )
            continue

        if not paragraph:
            paragraph_line = line_number
        paragraph.append(cleaned)

    flush()
    return blocks


def split_sentences(text: str) -> list[str]:
    """Split prose into approximate sentences without external packages."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])", text.strip())
    return [part.strip() for part in parts if part.strip()]


def ste_word_count(sentence: str) -> int:
    """Approximate ASD-STE100 word-count rules."""
    masked = re.sub(r"\([^()]*\)", " TOKEN ", sentence)
    masked = re.sub(r'"[^"]*"|“[^”]*”', " TOKEN ", masked)
    masked = re.sub(r"https?://\S+|\bURL\b|\bCODE\b", " TOKEN ", masked)
    masked = re.sub(
        r"\b\d+(?:\.\d+)?\s*(?:%|°[CF]?|[kmc]?m|kg|g|ms|s|min|h|Hz|kHz|"
        r"MHz|GHz|V|A|W|kW|Pa|kPa|MPa|L|mL)\b",
        " TOKEN ",
        masked,
        flags=re.IGNORECASE,
    )
    return len(
        re.findall(
            r"\b(?:TOKEN|[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*)\b",
            masked,
        )
    )


def excerpt(text: str, limit: int = 160) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact if len(compact) <= limit else compact[: limit - 1] + "…"


def add(
    findings: list[Finding],
    code: str,
    severity: str,
    line: int,
    message: str,
    source: str,
    suggestion: str,
) -> None:
    findings.append(
        Finding(code, severity, line, message, excerpt(source), suggestion)
    )


def lint_text(
    text: str,
    *,
    mode: str,
    profile: str,
) -> dict[str, object]:
    if profile == "auto":
        profile = infer_profile(text)

    findings: list[Finding] = []
    blocks = text_blocks(text)
    sentence_count = 0
    max_sentence_words = 0
    total_words = 0
    limit = PROFILE_LIMIT[profile]

    for block in blocks:
        sentences = split_sentences(block.text)
        if block.kind == "paragraph" and len(sentences) > 6:
            add(
                findings,
                "STR-001",
                "medium",
                block.line,
                f"Paragraph has {len(sentences)} sentences; maximum is 6.",
                block.text,
                "Split the paragraph by topic.",
            )

        for sentence in sentences:
            sentence_count += 1
            count = ste_word_count(sentence)
            total_words += count
            max_sentence_words = max(max_sentence_words, count)

            if count > limit:
                add(
                    findings,
                    "SEN-001",
                    "medium",
                    block.line,
                    f"Sentence has {count} words; {profile} limit is {limit}.",
                    sentence,
                    "Split the sentence without losing conditions or sequence.",
                )

            if ";" in sentence:
                add(
                    findings,
                    "PUN-001",
                    "medium",
                    block.line,
                    "Semicolon is not permitted.",
                    sentence,
                    "Use a period or reconstruct the sentence.",
                )

            if "—" in sentence:
                add(
                    findings,
                    "AIP-001",
                    "low",
                    block.line,
                    "Em dash violates the AI-prose overlay.",
                    sentence,
                    "Use a period, comma, colon, or clear parenthetical phrase.",
                )

            match = CONTRACTIONS.search(sentence)
            if match:
                add(
                    findings,
                    "SEN-002",
                    "medium" if mode == "strict" else "low",
                    block.line,
                    f"Contraction found: {match.group(0)}.",
                    sentence,
                    "Write the complete words.",
                )

            match = PASSIVE.search(sentence)
            if match:
                add(
                    findings,
                    "VRB-001",
                    "advisory",
                    block.line,
                    f"Possible passive voice: {match.group(0)}.",
                    sentence,
                    "Use active voice when the actor is known.",
                )

            match = STACKED_AUXILIARY.search(sentence)
            if match:
                add(
                    findings,
                    "VRB-002",
                    "medium" if mode == "strict" else "advisory",
                    block.line,
                    f"Possible complex verb construction: {match.group(0)}.",
                    sentence,
                    "Use a simple tense if it preserves time and modality.",
                )

            match = PROGRESSIVE.search(sentence)
            if match:
                add(
                    findings,
                    "VRB-003",
                    "advisory",
                    block.line,
                    f"Possible progressive verb form: {match.group(0)}.",
                    sentence,
                    "Use a simple tense when it states the same time and action.",
                )

            match = LATIN_ABBREVIATION.search(sentence)
            if match:
                add(
                    findings,
                    "WRD-001",
                    "low",
                    block.line,
                    f"Latin abbreviation found: {match.group(0)}.",
                    sentence,
                    "Use English words such as FOR EXAMPLE or THAT IS.",
                )

            match = AMBIGUOUS_THIS.search(sentence)
            if match:
                add(
                    findings,
                    "PRO-001",
                    "advisory",
                    block.line,
                    "The pronoun 'this' can have an unclear referent.",
                    sentence,
                    "Name the event, state, or object that 'this' refers to.",
                )

            match = GENDERED.search(sentence)
            if match:
                add(
                    findings,
                    "WRD-002",
                    "advisory",
                    block.line,
                    f"Review gender-specific word: {match.group(0)}.",
                    sentence,
                    "Use neutral wording unless the context requires the distinction.",
                )

            lower = sentence.lower()
            for phrase in PHRASAL_VERBS:
                if re.search(rf"\b{re.escape(phrase)}\b", lower):
                    add(
                        findings,
                        "VRB-004",
                        "advisory",
                        block.line,
                        f"Possible phrasal verb: {phrase}.",
                        sentence,
                        "Select a direct verb after you confirm the exact meaning.",
                    )

            for term, guidance in REVIEW_TERMS.items():
                if re.search(rf"\b{re.escape(term)}\b", lower):
                    add(
                        findings,
                        "WRD-003",
                        "advisory" if mode == "flavored" else "low",
                        block.line,
                        f"Review term: {term}.",
                        sentence,
                        guidance,
                    )

            for phrase, guidance in AI_PHRASES.items():
                if phrase in lower:
                    add(
                        findings,
                        "AIP-002",
                        "low",
                        block.line,
                        f"AI-style lead-in or filler: {phrase}.",
                        sentence,
                        guidance,
                    )

            seen_ai_words = sorted(
                word
                for word in AI_WORDS
                if re.search(rf"\b{re.escape(word)}\b", lower)
            )
            if seen_ai_words:
                add(
                    findings,
                    "AIP-003",
                    "low",
                    block.line,
                    "Vague, promotional, or model-favored word found: "
                    + ", ".join(seen_ai_words)
                    + ".",
                    sentence,
                    "Replace with a concrete action, mechanism, limit, or measurement.",
                )

            if profile == "procedure":
                check_procedure_sentence(findings, block, sentence)

        if re.match(r"^NOTE\s*:", block.text, re.IGNORECASE):
            note_body = re.sub(r"^NOTE\s*:\s*", "", block.text, flags=re.IGNORECASE)
            first = first_word(note_body)
            if first in IMPERATIVE_VERBS or note_body.lower().startswith("do not "):
                add(
                    findings,
                    "SEN-003",
                    "medium",
                    block.line,
                    "A note appears to contain an instruction.",
                    block.text,
                    "Move the instruction into a procedure step.",
                )

        if profile == "safety":
            check_safety_block(findings, block)

    counts = Counter(finding.severity for finding in findings)
    score = max(
        0,
        100
        - sum(SEVERITY_WEIGHT[finding.severity] for finding in findings),
    )
    return {
        "mode": mode,
        "profile": profile,
        "certification": "not assessed",
        "stats": {
            "blocks": len(blocks),
            "sentences": sentence_count,
            "words": total_words,
            "max_sentence_words": max_sentence_words,
            "sentence_limit": limit,
        },
        "counts": {
            severity: counts.get(severity, 0)
            for severity in ("high", "medium", "low", "advisory")
        },
        "readiness_score": score,
        "findings": [asdict(finding) for finding in findings],
    }


def first_word(text: str) -> str:
    match = re.match(r"^[\"'([]*([A-Za-z]+)", text.strip())
    return match.group(1).lower() if match else ""


def check_procedure_sentence(
    findings: list[Finding], block: TextBlock, sentence: str
) -> None:
    lower = sentence.lower()
    first = first_word(sentence)
    if block.kind == "list" and first and first not in IMPERATIVE_VERBS:
        if first in {"you", "the", "a", "an", "this", "these", "it", "they"}:
            add(
                findings,
                "SEN-004",
                "advisory",
                block.line,
                "Procedure item may not use the imperative form.",
                sentence,
                "Start the step with the primary action verb.",
            )

    imperative_pattern = "|".join(sorted(IMPERATIVE_VERBS))
    if re.match(rf"^(?:do not\s+)?(?:{imperative_pattern})\b", lower):
        if re.search(rf"\band\s+(?:then\s+)?(?:{imperative_pattern})\b", lower):
            add(
                findings,
                "SEN-005",
                "advisory",
                block.line,
                "Procedure sentence may contain more than one instruction.",
                sentence,
                "Split the actions unless they must occur at the same time.",
            )


def check_safety_block(findings: list[Finding], block: TextBlock) -> None:
    upper = block.text.upper()
    if "CAUTION:" in upper and re.search(r"\b(?:INJURY|DEATH|KILL|FATAL)\b", upper):
        add(
            findings,
            "SAF-001",
            "high",
            block.line,
            "CAUTION text mentions an injury or death risk.",
            block.text,
            "Confirm the risk analysis. A combined or personal risk uses WARNING.",
        )
    if "WARNING:" in upper or "CAUTION:" in upper:
        if not re.search(
            r"\b(?:CAN|COULD|RISK|INJURY|DEATH|DAMAGE|BREAK|CORROSION|"
            r"FIRE|EXPLOSION|FAIL)\b",
            upper,
        ):
            add(
                findings,
                "SAF-002",
                "medium",
                block.line,
                "Safety instruction may not state the risk or possible result.",
                block.text,
                "State the supported consequence after the command or condition.",
            )


def infer_profile(text: str) -> str:
    upper = text.upper()
    if "WARNING:" in upper or "CAUTION:" in upper:
        return "safety"
    blocks = text_blocks(text)
    list_blocks = [block for block in blocks if block.kind == "list"]
    imperative = sum(first_word(block.text) in IMPERATIVE_VERBS for block in list_blocks)
    if list_blocks and imperative >= max(1, len(list_blocks) // 2):
        return "procedure"
    numbered_starts = [
        clean_markdown_text(line)
        for line in text.splitlines()
        if re.match(r"^\s{0,3}\d+[.)]\s+", line)
    ]
    if any(
        first_word(item) in IMPERATIVE_VERBS
        or first_word(item) in {"you", "if", "when", "before", "after"}
        for item in numbered_starts
    ):
        return "procedure"
    return "description"


def format_text_report(source: str, result: dict[str, object]) -> str:
    counts = result["counts"]
    stats = result["stats"]
    findings = result["findings"]
    lines = [
        "STE100-STYLE AUDIT",
        f"Source: {source}",
        f"Mode: {result['mode']}",
        f"Profile: {result['profile']}",
        f"Readiness: {result['readiness_score']}/100 (not certification)",
        (
            "Findings: "
            f"{counts['high']} high, {counts['medium']} medium, "
            f"{counts['low']} low, {counts['advisory']} advisory"
        ),
        (
            "Text: "
            f"{stats['sentences']} sentences, {stats['words']} words, "
            f"longest sentence {stats['max_sentence_words']} words"
        ),
    ]
    if not findings:
        lines.append("\nNo mechanical findings.")
        return "\n".join(lines)

    lines.append("")
    for index, finding in enumerate(findings, start=1):
        lines.extend(
            [
                (
                    f"{index}. {finding['code']} line {finding['line']} "
                    f"[{finding['severity']}] - {finding['message']}"
                ),
                f"   Text: {finding['excerpt']}",
                f"   Fix: {finding['suggestion']}",
            ]
        )
    return "\n".join(lines)


def read_sources(paths: Sequence[str]) -> list[tuple[str, str]]:
    if paths:
        sources: list[tuple[str, str]] = []
        for raw in paths:
            path = Path(raw)
            if not path.is_file():
                raise OSError(f"input file not found: {path}")
            sources.append((str(path), path.read_text(encoding="utf-8")))
        return sources
    if sys.stdin.isatty():
        raise OSError("provide a file or pipe text on stdin")
    return [("<stdin>", sys.stdin.read())]


def self_check() -> None:
    assert ste_word_count("Restart the API.") == 3
    assert ste_word_count("Wait 10 ms.") == 2
    assert ste_word_count("Check the red-green status.") == 4
    assert ste_word_count("Use the key (ID 44 and label A).") == 4
    assert infer_profile("1. Restart the service.\n2. Check the log.") == "procedure"
    result = lint_text(
        "It is important to note that the file is processed by the worker;",
        mode="strict",
        profile="description",
    )
    codes = {finding["code"] for finding in result["findings"]}
    assert {"PUN-001", "AIP-002", "VRB-001"} <= codes


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", help="UTF-8 text or Markdown files")
    parser.add_argument(
        "--mode",
        choices=("strict", "flavored"),
        default="flavored",
        help="strict STE mechanics or STE-flavored technical prose",
    )
    parser.add_argument(
        "--profile",
        choices=("auto", "procedure", "description", "safety", "interface"),
        default="auto",
        help="content profile and sentence limit",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        dest="output_format",
    )
    parser.add_argument(
        "--strict-exit",
        action="store_true",
        help="return exit code 1 when a non-advisory finding exists",
    )
    parser.add_argument(
        "--self-check",
        action="store_true",
        help="run built-in checks and exit",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_check:
        self_check()
        print("SELF_CHECK_OK")
        return 0

    try:
        sources = read_sources(args.paths)
    except (OSError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    reports = []
    has_non_advisory = False
    for source, text in sources:
        result = lint_text(text, mode=args.mode, profile=args.profile)
        reports.append({"source": source, **result})
        has_non_advisory = has_non_advisory or any(
            finding["severity"] != "advisory" for finding in result["findings"]
        )

    if args.output_format == "json":
        payload: object = reports[0] if len(reports) == 1 else reports
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(
            "\n\n".join(
                format_text_report(report["source"], report) for report in reports
            )
        )

    return 1 if args.strict_exit and has_non_advisory else 0


if __name__ == "__main__":
    raise SystemExit(main())
