"""Ablation conditions. Each is a dict of which checks in rules.py are active.

`baseline` is a free continuation (no rule text given to the model at all,
beyond "continue the poem") -- this is the human-LLM co-writing failure mode
we're trying to measure, not a strawman.

`full_shikimoku` turns on every governance rule at once and is the condition
the paper's headline claim is about.

`arbitrary_control` matches full_shikimoku's instruction length/complexity
but enforces a rule with no thematic-governance function (a color-word
constraint). Without this condition the finding is deniable as "any
constraint reduces repetition" rather than specifically "link-and-shift
governance redistributes thematic control."
"""
from __future__ import annotations

CONDITIONS = {
    "baseline": {"link": False, "shift": False, "uchikoshi": False, "sarikirai": False, "rotation": False, "arbitrary": False},
    "rotation_only": {"link": False, "shift": False, "uchikoshi": False, "sarikirai": False, "rotation": True, "arbitrary": False},
    "link_only": {"link": True, "shift": False, "uchikoshi": False, "sarikirai": False, "rotation": False, "arbitrary": False},
    "shift_only": {"link": False, "shift": True, "uchikoshi": False, "sarikirai": False, "rotation": False, "arbitrary": False},
    "uchikoshi_only": {"link": False, "shift": False, "uchikoshi": True, "sarikirai": False, "rotation": False, "arbitrary": False},
    "sarikirai_only": {"link": False, "shift": False, "uchikoshi": False, "sarikirai": True, "rotation": False, "arbitrary": False},
    "full_shikimoku": {"link": True, "shift": True, "uchikoshi": True, "sarikirai": True, "rotation": True, "arbitrary": False},
    "arbitrary_control": {"link": False, "shift": False, "uchikoshi": False, "sarikirai": False, "rotation": False, "arbitrary": True},
}

RULE_EXPLANATIONS = {
    "link": "Each new verse must clearly connect to (pick up an image, mood, or implication from) the immediately preceding verse.",
    "shift": "Each new verse must move away from the verse before last -- do not simply continue that verse's world.",
    "uchikoshi": "A verse may not return to the same topic-category as the verse before last (the classical 'uchikoshi' fault).",
    "sarikirai": "Certain topics (love, grief, travel, war, dream, memory, solitude, night, season changes) may only recur after a minimum number of intervening verses.",
    "rotation": "The same author may not write two verses in a row.",
    "arbitrary": "Each verse must contain exactly one color word (from a fixed list), never repeating a color used in the previous two verses.",
}


def rule_preamble(condition: str) -> str:
    cfg = CONDITIONS[condition]
    active = [RULE_EXPLANATIONS[k] for k, v in cfg.items() if v]
    if not active:
        return ""
    bullets = "\n".join(f"- {r}" for r in active)
    return f"You must follow these constraints:\n{bullets}\n"
