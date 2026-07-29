"""The shikimoku, operationalized as checkable predicates.

This is a *simplified* operationalization of a real 14th-century renga
rulebook, not a literal reproduction -- the classical sarikirai tables
specify exact interval counts per word-category across a 100-verse kasen
sequence, keyed to a much larger taxonomy than the 10 categories below.
Say so explicitly in the paper's method section; the claim is about the
*mechanism* (link, shift, non-return, rotation), not about philological
fidelity.

Every check returns (passed: bool, reason: str). `reason` is fed back to
the model verbatim as the master scribe's rejection note, which is also
the thing that makes rotation/link/shift *rules* rather than just
*measurements* -- the model is told why it was bounced and asked to try
again.

Thresholds (LINK_MIN_SIM, SHIFT_MAX_SIM, LINEAGE_SIM) are cosine-similarity
cutoffs over all-MiniLM-L6-v2 embeddings and are NOT calibrated against any
ground truth -- they're a starting point. Run scripts/calibrate.py against
a small hand-labeled pilot batch before trusting numbers derived from them
in a paper. See README "Calibration" section.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .embeddings import cosine_sim

LINK_MIN_SIM = 0.15   # verse n must be at least this close to verse n-1
                       # calibrated from a baseline pilot: natural lag-1 similarity was
                       # mean=0.247, p25=0.149, so 0.35 was stricter than natural writing
                       # ever gets, causing near-constant link rejections
SHIFT_MAX_SIM = 0.33  # verse n must be at most this close to verse n-2 (embedding-level departure)
                       # the naive calibration (0.26, the natural lag-2 p75) turned out too
                       # strict in practice: enforcing LINK pulls verse n toward n-1, which
                       # transitively pulls it toward n-2 as well, so satisfying both link and
                       # shift together is harder than either marginal distribution suggests.
                       # loosened after a full_shikimoku pilot showed most SHIFT failures were
                       # only marginally over 0.26 (0.27-0.35), not wildly off.

# sarikirai table: category -> minimum number of *other* verses that must
# intervene before the category may recur. Loosely modeled on the real
# renga convention that heavier/rarer topics (love, grief) demand longer
# absence than lighter recurring ones (night, nature).
SARIKIRAI_MIN_GAP: Dict[str, int] = {
    # loosened by one step across the board after a full_shikimoku pilot showed
    # night/solitude/memory (common, ordinary categories for short verse) were
    # triggering repeated rejections just from running out of room to avoid them.
    "love": 4,
    "grief": 3,
    "travel": 3,
    "war": 3,
    "dream": 2,
    "memory": 2,
    "solitude": 2,
    "night": 1,
    "season_change": 1,
    "nature": 1,
    "animals": 1,
    "weather": 1,
    "domestic": 1,
    "sound": 1,
    "light": 1,
    "food_drink": 1,
    "work": 1,
    "childhood": 2,
}

ARBITRARY_COLORS = ["crimson", "silver", "amber", "violet", "ash", "gold", "jade"]


def check_link(verses, candidate_emb) -> Tuple[bool, str]:
    if len(verses) == 0:
        return True, ""
    prev = verses[-1].emb()
    sim = cosine_sim(prev, candidate_emb)
    if sim < LINK_MIN_SIM:
        return False, (
            f"LINK violation: your verse must connect to the immediately preceding verse "
            f"(similarity {sim:.2f} < required {LINK_MIN_SIM}). Pick up an image, mood, or "
            f"implication from the previous verse and continue it."
        )
    return True, ""


def check_shift(verses, candidate_emb) -> Tuple[bool, str]:
    if len(verses) < 2:
        return True, ""
    two_back = verses[-2].emb()
    sim = cosine_sim(two_back, candidate_emb)
    if sim > SHIFT_MAX_SIM:
        return False, (
            f"SHIFT violation: your verse must depart from the verse before last, not just "
            f"the immediately preceding one (similarity {sim:.2f} > allowed {SHIFT_MAX_SIM}). "
            f"Move the poem's world elsewhere while still linking to the last verse."
        )
    return True, ""


def check_uchikoshi(verses, candidate_categories: List[str]) -> Tuple[bool, str]:
    """The named fault of returning to the world of two verses back, at the
    category level (stricter and more literal than the embedding-based shift check)."""
    if len(verses) < 2:
        return True, ""
    prev_categories = set(verses[-2].categories)
    overlap = prev_categories.intersection(candidate_categories)
    if overlap:
        return False, (
            f"UCHIKOSHI violation: category/categories {sorted(overlap)} reappear from the verse "
            f"before last. This is the named fault of 'returning' -- choose different ground."
        )
    return True, ""


def check_sarikirai(verses, candidate_categories: List[str]) -> Tuple[bool, str]:
    for cat in candidate_categories:
        min_gap = SARIKIRAI_MIN_GAP.get(cat)
        if min_gap is None:
            continue
        last_idx = None
        for v in reversed(verses):
            if cat in v.categories:
                last_idx = v.index
                break
        if last_idx is not None:
            gap = len(verses) - 1 - last_idx  # verses elapsed since last use (verses[-1].index == len(verses)-1)
            if gap < min_gap:
                return False, (
                    f"SARIKIRAI violation: category '{cat}' was used {gap} verse(s) ago; "
                    f"it may not recur for {min_gap} verses. Choose a different topic."
                )
    return True, ""


def check_rotation(verses, candidate_author: str) -> Tuple[bool, str]:
    if len(verses) == 0:
        return True, ""
    if verses[-1].author == candidate_author:
        return False, "ROTATION violation: the same author may not write two verses in a row."
    return True, ""


def check_arbitrary(verses, candidate_text: str) -> Tuple[bool, str]:
    """Control condition: equivalent instruction load, no thematic-governance function.
    Rule: the verse must contain exactly one color word from a fixed list, and that
    color must not be the one used in either of the previous two verses."""
    lower = candidate_text.lower()
    used = [c for c in ARBITRARY_COLORS if c in lower]
    if len(used) != 1:
        return False, (
            f"ARBITRARY-RULE violation: verse must contain exactly one color word from "
            f"{ARBITRARY_COLORS}; found {used or 'none'}."
        )
    color = used[0]
    recent = verses[-2:]
    for v in recent:
        prior_used = [c for c in ARBITRARY_COLORS if c in v.text.lower()]
        if color in prior_used:
            return False, (
                f"ARBITRARY-RULE violation: color '{color}' was used within the last 2 verses; "
                f"pick a different color from {ARBITRARY_COLORS}."
            )
    return True, ""
