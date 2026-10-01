"""Render the shared STE and simplify-writing profiles; prepare pinned packages."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

PACKAGES = {
    "Google": "https://github.com/vale-cli/Google/releases/download/v0.7.1/Google.zip",
    "Readability": "https://github.com/vale-cli/readability/releases/download/v0.1.1/Readability.zip",
    "Microsoft": "https://github.com/errata-ai/Microsoft/releases/download/v0.15.1/Microsoft.zip",
    "proselint": "https://github.com/errata-ai/proselint/releases/download/v0.3.4/proselint.zip",
    "ai-tells": "https://github.com/tbhb/vale-ai-tells/releases/download/v1.37.0/ai-tells.zip",
}

# Aasim Sani's selections from simplify-writing, commit c4d96746.
# Avoid the Google rules that duplicate or conflict with the STE rules.
RULES = """Google.Contractions = NO
Google.Passive = NO
Google.Semicolons = NO
Google.Spelling = NO
Google.EmDash = NO
Google.We = suggestion
Readability.FleschKincaid = suggestion
Readability.FleschReadingEase = suggestion
Microsoft.Accessibility = warning
proselint.Uncomparables = warning
proselint.Oxymorons = warning
proselint.Hyperbole = warning
proselint.Needless = warning
proselint.Nonwords = warning
proselint.Malapropisms = warning
proselint.RASSyndrome = warning
proselint.CorporateSpeak = warning
proselint.Skunked = warning
proselint.Cliches = warning
proselint.Jargon = warning
proselint.Archaisms = warning
ai-tells.NounString = suggestion
ai-tells.LabelAndExplain = warning
ai-tells.MicDrop = warning
ai-tells.ParticipialPadding = warning
ai-tells.AbstractionSubject = warning
ai-tells.ShellNounCopula = warning
ai-tells.PseudoCleft = warning
ai-tells.IncompleteComparison = warning
ai-tells.VagueAttributions = warning
ai-tells.StackedHedges = warning
ai-tells.DefensiveHedges = warning
ai-tells.HollowAcknowledgment = warning
ai-tells.UrgencyInflation = warning
ai-tells.StrategyBuzzwords = warning
ai-tells.PromotionalPuffery = warning
ai-tells.DespiteChallenges = warning
ai-tells.SummativeAppositive = warning
ai-tells.RestatementMarkers = warning
ai-tells.FalseExclusivity = warning
ai-tells.RedundantPrecaution = warning
ai-tells.NominalizedScopeChange = warning
ai-tells.OrganicConsequence = warning
ai-tells.ScopePartition = warning
ai-tells.ListIntroductions = warning
ai-tells.ClosingPleasantries = warning
ai-tells.SycophancyMarkers = warning
"""


def profile_config(styles_path: str | Path, namespaces: list[str], *, personal: bool = False,
                   dictionary: bool = False, spelling: str = "", review_terms: list[str] = ()) -> str:
    styles = list(namespaces) + ["SimplifyWriting", "Google"]
    if personal:
        styles.append("UserStyle")
    if dictionary:
        styles.append("STE100Dictionary")
    config = (
        f"StylesPath = {styles_path}\nMinAlertLevel = suggestion\nVocab = STE100Project, Writing\n"
        "Packages = " + ", ".join(PACKAGES.values()) + "\n\n"
        "[*.{md,txt,rst,adoc,html}]\nBasedOnStyles = " + ", ".join(styles) + "\n"
        + RULES + spelling
    )
    if dictionary:
        config += "".join(f"STE100.{term} = NO\n" for term in review_terms)
    return config


def ensure_packages(vale: str, config: Path) -> None:
    """Sync only our pinned package configurations; leave project packages alone."""
    text = config.read_text()
    if not all(url in text for url in PACKAGES.values()):
        return
    match = re.search(r"(?m)^StylesPath\s*=\s*(.+)$", text)
    if not match:
        raise RuntimeError(f"StylesPath is missing in {config}.")
    path = Path(match[1].strip())
    if not path.is_absolute():
        path = config.parent / path
    path = path.resolve()
    fingerprint = hashlib.sha256(json.dumps(PACKAGES, sort_keys=True).encode()).hexdigest()
    marker = path / ".ste-writing-packages.json"
    if marker.is_file() and marker.read_text().strip() == fingerprint and all(
        (path / name).is_dir() and any((path / name).glob("*.yml")) for name in PACKAGES
    ):
        return
    result = subprocess.run(
        [vale, "--no-global", f"--config={config.resolve()}", "sync"],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode or not all((path / name).is_dir() for name in PACKAGES):
        raise RuntimeError("Vale package sync did not complete: " + (result.stderr or result.stdout)[-1800:])
    marker.write_text(fingerprint + "\n")
