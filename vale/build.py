#!/usr/bin/env python3
"""Compile the skill's STE rule map and optional Issue 9 book into Vale styles."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from dictionary import parse_book

ROOT = Path(__file__).resolve().parent
SKILL = ROOT.parent
sys.path.insert(0, str(SKILL / "scripts"))
import ste_lint as seed  # noqa: E402


def quoted(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def outside_quotes(pattern: str) -> str:
    """Protect literal labels and quotations from mechanical punctuation edits."""
    return "(?:" + pattern + r')(?![^"\n]*"(?:[^"\n]*"[^"\n]*")*[^"\n]*$)(?![^“”\n]*”)'


def tengo_map(name: str, values: dict) -> str:
    # A large map literal pushes every key/value onto Tengo's fixed operand
    # stack. Incremental assignments keep stack usage constant.
    return f"{name} := {{}}\n" + "".join(
        f"{name}[{quoted(key)}] = {quoted(value) if isinstance(value, str) else json.dumps(value)}\n"
        for key, value in values.items()
    )


def yaml_map(values: dict, indent: int = 0) -> str:
    lines = []
    for key, value in values.items():
        label = key if re.fullmatch(r"[A-Za-z_]\w*", key) else quoted(key)
        prefix = " " * indent + label + ":"
        if isinstance(value, dict):
            lines.append(prefix)
            lines.append(yaml_map(value, indent + 2).rstrip())
        elif isinstance(value, list):
            if not value:
                lines.append(prefix + " []")
            else:
                lines.append(prefix)
                lines.extend(" " * (indent + 2) + "- " + quoted(item) for item in value)
        else:
            scalar = quoted(value) if isinstance(value, str) else json.dumps(value)
            lines.append(prefix + " " + scalar)
    return "\n".join(lines) + "\n"


def catalog() -> dict:
    source = (SKILL / "references/rules.md").read_text(encoding="utf-8")
    records = {}
    for match in re.finditer(r"(?m)^\d+\.\s+\*\*(\d+\.\d+)\*\*\s+(.+?(?=\n\d+\.|\n##|\Z))", source, re.S):
        rule_id, summary = match.groups()
        records[rule_id] = {
            "id": rule_id, "summary": re.sub(r"\s+", " ", summary).strip(),
            "status": "review", "checks": [],
            "limits": ["Requires review of meaning, grammar, terminology, or document structure."],
        }
    if len(records) != 53:
        raise ValueError(f"Expected 53 STE writing rules, found {len(records)}.")
    return records


def word_counter(proper_names: list[str]) -> str:
    names = "|".join(re.escape(n) for n in sorted(proper_names, key=len, reverse=True))
    name_mask = (
        f'value = text.re_replace({quoted("(?i)"+r"\b(?:"+names+r")\b")}, value, " TOKEN ")\n'
        if names else ""
    )
    return r'''text := import("text")
count_words := func(value) {
    value = text.re_replace("([\\p{L}])\\(s\\)", value, "$1s")
    // Collapse nested parenthetical groups from the innermost group outward.
    for depth := 0; depth < 32; depth++ {
        next := text.re_replace("\\([^()]*\\)", value, " TOKEN ")
        if next == value { break }
        value = next
    }
    value = text.re_replace("\"[^\"]*\"|“[^”]*”", value, " TOKEN ")
    value = text.re_replace("https?://\\S+", value, " TOKEN ")
''' + name_mask + r'''
    value = text.re_replace("(?i)\\b[0-9]+(?:[.,][0-9]+)*\\s*(?:(?:degrees?\\s+(?:Celsius|Fahrenheit)|kilograms?|grams?|liters?|litres?|meters?|metres?|millimeters?|centimeters?|ohms?|knots?|seconds?|minutes?|hours?|feet|inches|pounds?|psi|kg|mg|g|km|cm|mm|m|ms|s|min|h|kHz|MHz|GHz|Hz|mV|V|mA|A|kW|W|MPa|kPa|Pa|mL|L)\\b|%|°[CF]|Ω)", value, " TOKEN ")
    value = text.re_replace("\\b[0-9]+(?:[.,][0-9]+)*\\b", value, " TOKEN ")
    words := text.re_find("[\\p{L}\\p{N}]+(?:[-'’_.][\\p{L}\\p{N}]+)*", value, -1)
    if words == undefined { return 0 }
    return len(words)
}
'''


def render(book: Path | None = None, allow_partial: bool = False, glossary_path: Path | None = None, allow_count_mismatch: bool = False) -> dict[str, str]:
    glossary = json.loads((glossary_path or ROOT / "glossary.json").read_text(encoding="utf-8"))
    for key in ("proper_names", "technical_nouns", "technical_verbs"):
        if not isinstance(glossary.get(key), list) or any(not isinstance(x, str) or not x.strip() for x in glossary[key]):
            raise ValueError(f"glossary.{key} must be a list of non-empty strings.")
    if not isinstance(glossary.get("aliases"), dict) or any(
        not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip()
        for k, v in glossary["aliases"].items()
    ):
        raise ValueError("glossary.aliases must map non-empty strings to canonical terms.")
    dictionary = parse_book(book, require_complete=not (allow_partial or allow_count_mismatch)) if book else None
    if dictionary and allow_count_mismatch and dictionary["unparsed"]:
        raise ValueError("--allow-count-mismatch still requires every headword row to parse.")
    rules = catalog()
    if book:
        source_lines = book.read_text(encoding="utf-8").splitlines()
        locations = {}
        for index, line in enumerate(source_lines, 1):
            if line.strip() == "Page 2-0-1":
                break
            heading = line.lstrip("#* -")
            match = re.match(r"Rule\s+(\d+\.\d+)\b", heading)
            if match:
                locations[match[1]] = index
        for rule_id, record in rules.items():
            if rule_id not in locations:
                raise ValueError(f"Writing rule {rule_id} was not found in the full book.")
            record["book_source_line"] = locations[rule_id]
    files: dict[str, str] = {}

    def rule(style: str, name: str, ids: tuple[str, ...], values: dict, limits: str, status: str = "partial") -> None:
        check = f"{style}.{name}"
        files[f"styles/{style}/{name}.yml"] = (
            "# Generated by vale/build.py. Edit the compiler or glossary, then rebuild.\n"
            + yaml_map({"extends": "existence", "level": "warning", "scope": "text", **values})
        )
        for rule_id in ids:
            record = rules[rule_id]
            if not record["checks"]:
                record["limits"] = []
            record["checks"].append(check)
            record["status"] = status
            if limits not in record["limits"]:
                record["limits"].append(limits)

    def script(style: str, name: str, ids: tuple[str, ...], scope: str, code: str, message: str, limits: str, status: str = "partial", level: str = "warning") -> None:
        files[f"styles/config/scripts/{name}.tengo"] = code
        rule(style, name, ids, {
            "extends": "script", "scope": scope, "script": f"{name}.tengo",
            "level": level, "message": message,
        }, limits, status)

    rule("STE100", "Contractions", ("4.2",), {
        "message": "STE 4.2: expand '%s' and preserve its meaning.",
        "level": "error", "ignorecase": True, "vocab": False,
        "tokens": [outside_quotes(seed.CONTRACTIONS.pattern.replace("'", "['’]"))],
    }, "Detects the listed contractions; omission of necessary words requires review.")
    rule("STE100", "Semicolons", ("8.1",), {
        "message": "STE 8.1: replace the semicolon with suitable sentence structure.",
        "level": "error", "nonword": True, "vocab": False, "tokens": [outside_quotes(";")],
    }, "Enforces the semicolon prohibition. Other punctuation still needs review.")
    rule("STE100", "ComplexTense", ("3.2", "3.4", "3.5"), {
        "message": "STE 3.2/3.4/3.5: review '%s' for an approved verb construction. Preserve time and requirement strength.",
        "ignorecase": True, "vocab": False,
        "tokens": [
            r"\b(?:have|has|had)\s+(?:been\s+)?(?:\w+(?:ed|en)|done|gone|made|seen|taken|written)\b",
            seed.PROGRESSIVE.pattern,
            r"\b(?:would|could|should|might|must|will)\s+have\s+(?:been\s+)?\w+\b",
        ],
    }, "Patterns detect some perfect/progressive constructions; approved adjective and technical-noun uses need review.")
    rule("STE100", "PassiveVoice", ("3.6",), {
        "message": "STE 3.6: review '%s' for passive voice. Descriptions permit it when the actor is unknown.",
        "ignorecase": True, "vocab": False,
        "tokens": [r"\b(?:am|is|are|was|were|be|been|being)\s+(?:not\s+)?(?:\w{3,}ed|\w{3,}en|built|done|found|given|held|known|made|sent|set|shown|taken|told|written)\b"],
        "exceptions": [r"(?i)(?:am|is|are|was|were|be|been|being)\s+(?:not\s+)?green"],
    }, "A past participle can be an adjective; the rule cannot identify the actor or decide whether it is unknown.")
    rule("STE100", "PhrasalVerbs", ("9.3",), {
        "message": "STE 9.3: review '%s' for a phrasal verb. A technical noun can contain the same words.",
        "ignorecase": True, "level": "suggestion",
        "tokens": [re.escape(term).replace(r"\ ", r"\s+") for term in seed.PHRASAL_VERBS],
    }, "Uses the existing skill's curated phrase list; part of speech and unlisted phrases need review.")
    spelling = {
        "colour": "color", "colours": "colors", "centre": "center", "centres": "centers",
        "organisation": "organization", "organisations": "organizations",
        "organise": "organize", "organised": "organized", "analyse": "analyze",
        "analysed": "analyzed", "behaviour": "behavior", "behaviours": "behaviors",
        "metre": "meter", "metres": "meters", "litre": "liter", "litres": "liters",
        "catalogue": "catalog", "catalogues": "catalogs", "labelled": "labeled",
    }
    rule("STE100", "AmericanSpelling", ("1.14",), {
        "extends": "substitution", "ignorecase": True,
        "message": "STE 1.14: use '%s' for '%s' unless an official directive requires another spelling.",
        "swap": spelling,
    }, "Curated spelling pairs; directives, official names, and other spelling differences need review.")
    for term, advice in seed.REVIEW_TERMS.items():
        rule("STE100", "WordReview_" + term, ("1.1", "9.1"), {
            "message": f"STE 1.1/9.1: review '%s'. {advice}",
            "level": "suggestion", "ignorecase": True, "tokens": [re.escape(term)],
        }, "Uses the skill's curated review map. Alternatives depend on meaning; this is not the full dictionary.")

    verbs = "(?:" + "|".join(sorted(seed.IMPERATIVE_VERBS)) + ")"
    rule("STE100Procedure", "MultipleInstructions", ("5.2",), {
        "scope": "sentence & ~heading", "ignorecase": True, "level": "suggestion",
        "message": "STE 5.2: review '%s' for multiple instructions. Actions that occur at the same time may stay together.",
        "tokens": [rf"\b{verbs}\b[^.!?]{{0,160}}\b(?:and|then)\s+{verbs}\b"],
    }, "Matches some pairs of known action verbs; simultaneous actions and other verbs need review.")
    rule("STE100Procedure", "Imperative", ("5.3",), {
        "scope": "sentence & ~heading", "ignorecase": True, "level": "suggestion",
        "message": "STE 5.3: review '%s' and use a clear command where appropriate. Preserve requirement strength.",
        "raw": [r"^\s*(?:You\s+(?:must|should|need\s+to|have\s+to|can)\b|Please\s+)"],
    }, "Flags some indirect instruction openings; deciding whether a sentence is an instruction needs review.")
    rule("STE100Procedure", "ConditionFirst", ("5.4",), {
        "scope": "sentence & ~heading", "ignorecase": True, "level": "suggestion",
        "message": "STE 5.4: review '%s'; put a necessary condition before the command and separate it with a comma.",
        "raw": [rf"^\s*{verbs}\b[^.!?]+\b(?:if|when|unless)\b"],
    }, "Finds some trailing conditions. Condition scope and comma placement need review.")
    rule("STE100Procedure", "NoteInstructions", ("5.5",), {
        "ignorecase": True,
        "message": "STE 5.5: review '%s'; notes give information and must not contain instructions.",
        "raw": [rf"^\s*NOTE\s*:\s*(?:{verbs}\b|Do\s+not\b|You\s+must\b|Please\b)"],
    }, "Detects some commands after NOTE:. Other note formats and unlisted verbs need review.")
    counter = word_counter(glossary["proper_names"])
    for profile, limit, rule_id in (("Procedure", 20, "5.1"), ("Description", 25, "6.3")):
        code = counter + f'''
matches := []
if count_words(scope) > {limit} {{
    matches = append(matches, {{begin: 0, end: len(scope)}})
}}
// Parenthetical prose is also subject to its own sentence-length limit (8.5).
starts := []
for index := 0; index < len(scope); index++ {{
    char := scope[index:index+1]
    if char == "(" {{
        starts = append(starts, index)
    }} else if char == ")" && len(starts) > 0 {{
        begin := starts[len(starts)-1]
        starts = starts[:len(starts)-1]
        value := scope[begin+1:index]
        sentences := text.re_find("[^.!?]+(?:[.!?]|$)", value, -1)
        if sentences != undefined {{
            for sentence in sentences {{
                if count_words(sentence[0].text) > {limit} {{
                    matches = append(matches, {{begin: begin, end: index+1}})
                    break
                }}
            }}
        }}
    }}
}}
'''
        scope = "sentence & ~heading"
        if profile == "Procedure":
            scope += ' & ~doc(p:contains("NOTE:")) & ~doc(p:contains("Note:")) & ~doc(p:contains("note:"))'
        script("STE100" + profile, profile + "Length", (rule_id, "4.1", "8.4", "8.5", "8.6", "8.7"),
               scope, code,
               f"STE {rule_id}: this sentence exceeds {limit} STE words. Split it without changing meaning.",
               "Counts parentheses, double quotations, common units, hyphens, and configured proper names. Other names, labels, unusual units, and abbreviations need review.")
    script("STE100Procedure", "NoteLength", ("5.1", "8.5"), "paragraph", counter + r'''
matches := []
if text.re_match("(?i)^\\s*note\\s*:", scope) {
    value := text.re_replace("(?i)^\\s*note\\s*:\\s*", scope, "")
    value = text.re_replace("\\b[0-9]+\\.[0-9]+\\b", value, "NUMBER")
    sentences := text.re_find("[^.!?]+(?:[.!?]|$)", value, -1)
    if sentences != undefined {
        for sentence in sentences {
            if count_words(sentence[0].text) > 25 {
                matches = append(matches, {begin: 0, end: len(scope)})
                break
            }
        }
    }
}
''', "STE 5.1: this NOTE appears to exceed 25 words in a sentence. Notes have the descriptive limit.",
           "The full book permits 25 words in NOTE sentences. Recognizes NOTE: paragraphs; other note markup and sentence boundaries need review.")
    script("STE100Description", "ParagraphSentences", ("6.6",), "paragraph", r'''text := import("text")
matches := []
value := text.re_replace("\\b[0-9]+\\.[0-9]+\\b", scope, "NUMBER")
value = text.re_replace("(?i)\\b(?:Mr|Mrs|Dr|Ms|No|Fig)\\.", value, "ABBR")
ends := text.re_find("[.!?]+(?:[\"”')]+)?(?:\\s+|$)", value, -1)
count := 0
if ends != undefined { count = len(ends) }
if !text.re_match("[.!?][\"”')]*\\s*$", value) && text.trim_space(value) != "" { count += 1 }
if count > 6 { matches = append(matches, {begin: 0, end: len(scope)}) }
''', "STE 6.6: this paragraph appears to exceed six sentences; split it by topic.",
           "Sentence boundaries are approximate; punctuation in abbreviations and quotations can need review.")

    risk = r"(?:death|injur(?:y|ies)|burns?|electric\s+shock|blindness)"
    rule("STE100Safety", "RiskLevel", ("7.1",), {
        "ignorecase": True, "nonword": True,
        "message": "STE 7.1: review '%s'; WARNING identifies a risk of injury or death.",
        "tokens": [rf"\bCAUTION\b[^.!?]{{0,250}}\b{risk}\b"],
    }, "Finds some CAUTION labels associated with human harm; symbols, missing labels, and other hazards need review.")
    rule("STE100Safety", "CommandFirst", ("7.2",), {
        "ignorecase": True, "level": "suggestion",
        "message": "STE 7.2: review '%s'; start the safety instruction with a clear command or condition.",
        "raw": [r"^\s*(?:WARNING|CAUTION)\s*:?\s+(?:The|There|This|It|You)\b"],
    }, "Reviews some descriptive openings; determining the necessary command or condition requires context.")
    script("STE100Safety", "Consequence", ("7.3",), "paragraph", r'''text := import("text")
matches := []
if text.re_match("(?i)^\\s*(?:WARNING|CAUTION)\\b", scope) &&
   !text.re_match("(?i)\\b(?:risk|injury|injuries|death|damage|burn|burns|shock|fire|explosion|can|could|may|because|result|cause|prevent)\\b", scope) {
    matches = append(matches, {begin: 0, end: len(scope)})
}
''', "STE 7.3: review this safety instruction for an explanation of the risk or possible result.",
           "Absence of a risk keyword is a review prompt. Keywords cannot establish that the risk is explained correctly.", level="suggestion")

    terms = glossary["proper_names"] + glossary["technical_nouns"] + glossary["technical_verbs"]
    files["styles/config/vocabularies/STE100Project/accept.txt"] = (
        "# Generated project terms. Edit vale/glossary.json and rebuild.\n"
        + "".join(re.escape(term) + "\n" for term in terms)
    )
    files["styles/config/vocabularies/STE100Project/reject.txt"] = "# No global rejected terms.\n"
    if glossary["aliases"]:
        rule("STE100", "Terminology", ("1.11", "9.4"), {
            "extends": "substitution", "ignorecase": True,
            "message": "STE 1.11/9.4: review '%s' as the canonical term for '%s'.",
            "swap": {re.escape(k): v for k, v in glossary["aliases"].items()},
        }, "Enforces configured aliases. Establishing which terms denote the same item requires review.")
    for term in glossary["technical_nouns"]:
        if len(term.split()) > 3:
            rule("STE100", "LongNoun_" + hashlib.sha256(term.encode()).hexdigest()[:10], ("2.1", "2.2"), {
                "message": "STE 2.1/2.2: review '%s'; define a clear short form for this technical noun.",
                "level": "suggestion", "ignorecase": True, "vocab": False,
                "tokens": [re.escape(term)],
            }, "Only configured technical nouns are checked. Definitions and permitted hyphenation require review.")

    if dictionary:
        approved = {e["headword"] for e in dictionary["entries"] if e["approved"]}
        grouped: dict[str, list[dict]] = {}
        for entry in dictionary["entries"]:
            if not entry["approved"]:
                grouped.setdefault(entry["headword"], []).append(entry)
        dictionary["context_review"] = sorted(approved.intersection(grouped))
        advice_by_word = {}
        for headword, entries in sorted(grouped.items()):
            # A token can be approved as a noun and non-approved as a verb.
            if headword in approved or any(e["contextual"] for e in entries):
                continue
            advice_by_word[headword] = " / ".join(dict.fromkeys(e["meaning_or_alternatives"] for e in entries))
        patterns = "|".join(re.escape(w).replace(r"\ ", r"\s+") for w in sorted(advice_by_word, key=len, reverse=True))
        allowed_pattern = "|".join(re.escape(term).replace(r"\ ", r"\s+") for term in sorted(terms, key=len, reverse=True))
        protection = r'''
protected := []
literal := text.re_find("\"[^\"]*\"|“[^”]*”", scope, -1)
if literal != undefined {
    for item in literal { protected = append(protected, item[0]) }
}
'''
        if allowed_pattern:
            protection += f'''
known := text.re_find({quoted("(?i)"+r"\b(?:"+allowed_pattern+r")\b")}, scope, -1)
if known != undefined {{
    for item in known {{ protected = append(protected, item[0]) }}
}}
'''
        protection += '''
is_protected := func(word) {
    for item in protected {
        if word.begin >= item.begin && word.end <= item.end { return true }
    }
    return false
}
'''
        # Tengo string literals use Go escaping; serialize each key and value.
        code = 'text := import("text")\nmatches := []\n' + tengo_map("advice", advice_by_word) + protection + f'''
found := text.re_find({quoted("(?i)"+r"\b(?:"+patterns+r")\b")}, scope, -1)
if found != undefined {{
    for item in found {{
        word := item[0]
        key := text.re_replace("\\\\s+", text.to_lower(word.text), " ")
        is_token := !text.re_match("^['’_-]", scope[word.end:]) &&
                    !text.re_match("['’_-]$", scope[:word.begin])
        if is_token && !is_protected(word) && advice[key] != undefined {{
            message := "STE 1.1/9.1: review '" + word.text + "'. Alternatives: " + advice[key] + ". Confirm meaning, part of speech, and technical-term status."
            matches = append(matches, {{begin: word.begin, end: word.end, message: message}})
        }}
    }}
}}
'''
        script("STE100Dictionary", "DictionaryWords", ("1.1", "9.1"), "text", code,
               "STE 1.1: review this non-approved dictionary word.",
               "All extracted non-approved entries are retained. Ambiguous POS, contextual constructions, meanings, and technical-term status require review.")
        accepted = set()
        for entry in dictionary["entries"]:
            if not entry["approved"]:
                continue
            accepted.update(re.findall(r"[a-z]+(?:[-'][a-z]+)*", entry["headword"]))
            accepted.update(entry["aliases"])
            accepted.update(word.lower() for word in re.findall(r"\b[A-Z][A-Z'-]*\b", entry["forms_source"]))
            if entry["part_of_speech"] == "n" and " " not in entry["headword"]:
                word = entry["headword"]
                plural = (word[:-1] + "ies" if re.search(r"[^aeiou]y$", word)
                          else word + "es" if re.search(r"(?:s|x|z|ch|sh)$", word) else word + "s")
                accepted.add(plural)
        accepted.update(term.lower() for term in terms if " " not in term)
        code = 'text := import("text")\nmatches := []\n' + tengo_map("accepted", {w: True for w in sorted(accepted)}) + protection + r'''
found := text.re_find("[\\p{L}][\\p{L}\\p{N}'’_-]*", scope, -1)
if found != undefined {
    for item in found {
        word := item[0]
        if accepted[text.to_lower(word.text)] == undefined && !is_protected(word) &&
           !text.re_match("[0-9]", word.text) {
            matches = append(matches, {begin: word.begin, end: word.end})
        }
    }
}
'''
        script("STE100Dictionary", "DictionaryVocabulary", ("1.1", "1.4", "3.1"), "text", code,
               "STE 1.1/1.4/3.1: review '%s' against approved forms or the project technical-term glossary.",
               "Checks approved headwords and listed verb/adjective forms, with approximate noun plurals. This lexical check cannot determine POS, meaning, irregular noun forms, or whether an unknown technical term is valid.", level="suggestion")
        dictionary["lexical_checks"] = {
            "nonapproved_patterns": len(advice_by_word), "approved_forms": len(accepted),
            "contextual_entries": [e["source_headword"] for e in dictionary["entries"] if e["contextual"]],
        }
        files["private/dictionary.json"] = json.dumps(dictionary, indent=2, ensure_ascii=False) + "\n"

    for profile in ("description", "procedure", "safety"):
        styles = ["STE100", "STE100Description" if profile == "description" else "STE100Procedure"]
        if profile == "safety":
            styles.append("STE100Safety")
        files[f"{profile}.ini"] = (
            "StylesPath = styles\nMinAlertLevel = suggestion\nVocab = STE100Project\n\n"
            "[*.{md,txt,rst,adoc,html}]\nBasedOnStyles = " + ", ".join(styles) + "\n"
        )
        if dictionary:
            files[f"private/{profile}.ini"] = (
                files[f"{profile}.ini"].replace("StylesPath = styles", "StylesPath = ../styles").rstrip()
                + ", STE100Dictionary\n"
                + "\n".join(f"STE100.WordReview_{term} = NO" for term in seed.REVIEW_TERMS) + "\n"
            )
    files[".vale.ini"] = files["description.ini"]
    for record in rules.values():
        record["limits"] = [
            re.sub(r";\s+([a-z])", lambda match: ". " + match[1].upper(), limit)
            .replace("All extracted non-approved entries are retained.", "The importer retains all extracted non-approved entries.")
            .replace("Keywords cannot establish that the risk is explained correctly.", "Keywords cannot establish whether the explanation describes the risk correctly.")
            for limit in record["limits"]
        ]
    metadata = {
        "standard": "ASD-STE100", "issue": 9, "writing_rules": len(rules),
        "source": "references/rules.md (condensed summaries)",
        "dictionary": {
            "complete": dictionary["complete"] if dictionary else False,
            "counts": dictionary["counts"] if dictionary else {"approved": 0, "nonapproved": 0},
            "curated_review_terms": len(seed.REVIEW_TERMS),
            **({"all_headwords_parsed": dictionary["all_headwords_parsed"],
                "counts_match_expected": dictionary["counts_match_expected"],
                "expected_counts": dictionary["expected_counts"],
                "lexical_checks": dictionary["lexical_checks"]} if dictionary else {}),
            **({"source_sha256": dictionary["sha256"]} if dictionary else {}),
        },
        "rules": list(rules.values()),
    }
    files["coverage.json"] = json.dumps(metadata, indent=2) + "\n"
    rows = ["# STE rule coverage", "", "Generated from the condensed Issue 9 rule map. Partial checks do not establish compliance.", "",
            "| Rule | Status | Vale checks | Remaining review |", "| --- | --- | --- | --- |"]
    for record in rules.values():
        rows.append("| " + " | ".join((
            record["id"], record["status"], ", ".join(record["checks"]) or "—",
            " ".join(record["limits"]).replace("|", r"\|"),
        )) + " |")
    files["coverage.md"] = "\n".join(rows) + "\n"
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=Path, help="The original Issue 9 OCR Markdown")
    parser.add_argument("--allow-partial-dictionary", action="store_true", help="Permit an explicitly incomplete import for review")
    parser.add_argument("--allow-count-mismatch", action="store_true", help="Compile every source headword despite a mismatch with the book's claimed totals")
    parser.add_argument("--glossary", type=Path, help="Project terms and proper names")
    parser.add_argument("--emit-json", action="store_true", help="Return generated files without writing them")
    parser.add_argument("--check", action="store_true", help="Fail if generated files differ")
    args = parser.parse_args()
    try:
        files = render(args.book, args.allow_partial_dictionary, args.glossary, args.allow_count_mismatch)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"{exc}\n")
    if args.emit_json:
        print(json.dumps(files))
        return 0
    if args.check:
        changed = [name for name, content in files.items()
                   if not (ROOT / name).is_file() or (ROOT / name).read_text(encoding="utf-8") != content]
        if changed:
            print("Generated files differ: " + ", ".join(changed), file=sys.stderr)
            return 1
        print(f"{len(files)} generated files match.")
        return 0
    # Remove stale dictionary checks only from this compiler's own namespace.
    wanted = {ROOT / name for name in files}
    for style in ("STE100", "STE100Procedure", "STE100Description", "STE100Safety", "STE100Dictionary"):
        for old in (ROOT / "styles" / style).glob("*.yml"):
            if old not in wanted and old.read_text(encoding="utf-8").startswith("# Generated by vale/build.py."):
                old.unlink()
    for name, content in files.items():
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    print(f"Generated {len(files)} files; 53 writing rules cataloged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
