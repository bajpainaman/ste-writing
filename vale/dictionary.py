"""Read Issue 9 dictionary tables without discarding their usage restrictions."""

from __future__ import annotations

import hashlib
import html
import re
from pathlib import Path

EXPECTED = {"approved": 875, "nonapproved": 1274}
POS = r"n|v|adj|adv|pre|prep|conj|pron|art|num|int|interj|prefix"
ENTRY = re.compile(
    rf"^(.+?)\s*\(\s*({POS})\.?\s*\)(.*)$",
    re.IGNORECASE,
)


def plain(value: str) -> str:
    value = re.sub(r"<br\s*/?>", " ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", value)
    return re.sub(r"\s+", " ", html.unescape(value).replace("**", "").replace("`", "")).strip()


def parse_book(path: Path, require_complete: bool = True) -> dict:
    """Import table headwords; retain POS, meanings, examples, and line provenance.

    Uppercase headwords denote approved words. Lowercase headwords denote
    non-approved entries. Mixed-case or unfamiliar POS rows require review.
    Exact Issue 9 counts gate the full dictionary build. Count parity is an
    extraction check, not a semantic certification.
    """
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()
    # The introduction reproduces dictionary entries as teaching examples.
    # Import the actual alphabetic dictionary after its last introductory page.
    intro_pages = [i for i, line in enumerate(lines) if re.fullmatch(r"Page 2-0-\d+", line.strip())]
    first_line = max(intro_pages) + 1 if intro_pages else 0
    entries: list[dict] = []
    unparsed: list[dict] = []
    seen: set[tuple] = set()
    in_dictionary = False
    last_entry: dict | None = None
    for line_no, line in enumerate(lines, 1):
        if line_no <= first_line:
            continue
        if not line.strip().startswith("|"):
            continue
        cells = [plain(c) for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) < 3 or all(re.fullmatch(r"[:\s-]*", c) for c in cells):
            continue
        heading = cells[0].lower()
        if ("word" in heading and ("part of speech" in heading or "key" in heading)
                and any("meaning" in c.lower() or "alternative" in c.lower() for c in cells[1:])):
            in_dictionary = True
            continue
        if not in_dictionary:
            continue
        if last_entry is not None and (
            cells[0].startswith(("🔑", "🕒"))
            or (not ENTRY.match(cells[0]) and (
                cells[0].upper().startswith("HELP")
                or re.search(r"no other verb forms", cells[0], re.IGNORECASE)
            ))
        ):
            last_entry["help"].append({"source_line": line_no, "text": " ".join(cells)})
            continue
        if not cells[0] and last_entry is not None:
            for name, cell in zip(("meaning_or_alternatives", "approved_example", "unapproved_example"), cells[1:]):
                last_entry[name] = (last_entry[name] + " " + cell).strip()
            continue
        match = ENTRY.match(cells[0])
        if match:
            source_headword, pos, forms = match.groups()
        elif re.fullmatch(r"[A-Za-z]+(?:[ -][A-Za-z]+)+", cells[0]):
            # FOR EXAMPLE and such as have no POS label in the source table.
            # Retain the phrase without inventing a grammatical classification.
            source_headword, pos, forms = cells[0], "unspecified", ""
        else:
            if cells[0]:
                unparsed.append({"line": line_no, "row": cells})
            continue
        source_headword = source_headword.strip()
        qualified = re.fullmatch(r"([A-Za-z][A-Za-z /'’.-]*?)\s*(?:\((.*)\))?", source_headword)
        if not qualified:
            unparsed.append({"line": line_no, "row": cells})
            continue
        headword, qualifier = qualified.groups()
        headword = headword.strip()
        if not (headword.isupper() or headword.islower()):
            unparsed.append({"line": line_no, "row": cells})
            continue
        approved = headword.isupper()
        contextual = pos.lower() == "prefix" or qualifier == "from"
        aliases = []
        if qualifier:
            qualifier = qualifier.strip()
            if approved and qualifier.lower().startswith("or "):
                aliases.append(qualifier[3:].strip().lower())
            elif not approved and not contextual:
                headword = qualifier if " " in qualifier or headword.lower() in qualifier.lower().split() else headword + " " + qualifier
        key = (headword.lower(), pos.lower(), approved, tuple(cells[1:]))
        if key in seen:
            unparsed.append({"line": line_no, "reason": "duplicate dictionary entry", "row": cells})
            continue
        seen.add(key)
        last_entry = {
            "headword": headword.lower(), "source_headword": source_headword,
            "approved": approved, "aliases": aliases, "contextual": contextual,
            "part_of_speech": pos.lower(), "forms_source": forms.strip(),
            "meaning_or_alternatives": cells[1],
            "approved_example": cells[2],
            "unapproved_example": cells[3] if len(cells) > 3 else "",
            "source_line": line_no, "help": [],
        }
        entries.append(last_entry)
    counts = {
        "approved": sum(e["approved"] for e in entries),
        "nonapproved": sum(not e["approved"] for e in entries),
    }
    for index, entry in enumerate(entries):
        stop = entries[index + 1]["source_line"] - 1 if index + 1 < len(entries) else len(lines)
        entry["source_excerpt"] = "\n".join(lines[entry["source_line"] - 1:stop])
    complete = counts == EXPECTED and not unparsed
    if require_complete and not complete:
        raise ValueError(
            f"Dictionary extraction incomplete: {counts}; expected {EXPECTED}; "
            f"{len(unparsed)} ambiguous/duplicate rows. No full dictionary rules generated. "
            "Use --allow-partial-dictionary to inspect a partial import."
        )
    return {
        "issue": 9, "source": str(path.resolve()),
        "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "counts": counts, "complete": complete,
        "unique_headwords": {
            "approved": len({e["headword"] for e in entries if e["approved"]}),
            "nonapproved": len({e["headword"] for e in entries if not e["approved"]}),
        },
        "expected_counts": EXPECTED, "counts_match_expected": counts == EXPECTED,
        "all_headwords_parsed": not unparsed,
        "entries": entries, "unparsed": unparsed,
    }
