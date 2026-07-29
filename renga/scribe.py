"""The master scribe: generates a candidate verse, checks it against the
condition's active rules, and either accepts it or hands the model a
specific rejection reason and asks it to try again.

This loop is the actual mechanism under test. Everything else in the repo
is instrumentation around it.
"""
from __future__ import annotations

from typing import List

from . import llm
from .embeddings import embed
from .conditions import CONDITIONS, rule_preamble
from .rules import check_link, check_shift, check_uchikoshi, check_sarikirai, check_rotation, check_arbitrary
from .sequence import Verse

MAX_RETRIES = 3

PERSONA_SYSTEM = {
    "model_A": "You are a poet in a renga (linked-verse) sequence. Write ONE short stanza (2-4 lines), "
    "plain contemporary English, no titles or explanations -- just the verse.",
    "model_B": "You are a second poet in the same renga (linked-verse) sequence, with your own voice and "
    "concerns, distinct from the other contributor. Write ONE short stanza (2-4 lines), plain "
    "contemporary English, no titles or explanations -- just the verse.",
}


def _context_block(verses: List[Verse], n: int = 4) -> str:
    recent = verses[-n:]
    if not recent:
        return "(This is the opening verse -- the hokku. Set a scene.)"
    lines = "\n".join(f"{i+1}. {v.text}" for i, v in enumerate(recent))
    return f"The most recent verses of the sequence so far:\n{lines}\n\nWrite the next verse."


def _run_checks(condition: str, verses: List[Verse], candidate_text: str, candidate_author: str, candidate_emb, candidate_tags: dict):
    cfg = CONDITIONS[condition]
    failures = []
    if cfg["link"]:
        ok, reason = check_link(verses, candidate_emb)
        if not ok:
            failures.append(reason)
    if cfg["shift"]:
        ok, reason = check_shift(verses, candidate_emb)
        if not ok:
            failures.append(reason)
    if cfg["uchikoshi"]:
        ok, reason = check_uchikoshi(verses, candidate_tags["categories"])
        if not ok:
            failures.append(reason)
    if cfg["sarikirai"]:
        ok, reason = check_sarikirai(verses, candidate_tags["categories"])
        if not ok:
            failures.append(reason)
    if cfg["rotation"]:
        ok, reason = check_rotation(verses, candidate_author)
        if not ok:
            failures.append(reason)
    if cfg["arbitrary"]:
        ok, reason = check_arbitrary(verses, candidate_text)
        if not ok:
            failures.append(reason)
    return failures


def generate_next_verse(seq_verses: List[Verse], condition: str, author: str, model: str = None, max_retries: int = MAX_RETRIES) -> Verse:
    """author: which persona/human writes this turn ("model_A", "model_B", or "human" if
    supplying a pre-written verse -- see scripts/human_session.py for the human path)."""
    system = PERSONA_SYSTEM.get(author, PERSONA_SYSTEM["model_A"])
    preamble = rule_preamble(condition)

    rejections = []
    candidate_text = None
    feedback = ""
    kwargs = {"model": model} if model else {}

    for attempt in range(max_retries + 1):
        user_msg = _context_block(seq_verses) + ("\n\n" + preamble if preamble else "")
        if feedback:
            user_msg += f"\n\nYour previous attempt was rejected:\n{feedback}\nWrite a new verse that fixes this."
        candidate_text = llm.generate_verse(system, user_msg, **kwargs)
        candidate_emb = embed(candidate_text)
        candidate_tags = llm.extract_tags(candidate_text, **kwargs)

        failures = _run_checks(condition, seq_verses, candidate_text, author, candidate_emb, candidate_tags)
        if not failures:
            return Verse(
                index=len(seq_verses),
                author=author,
                text=candidate_text,
                motifs=candidate_tags["motifs"],
                categories=candidate_tags["categories"],
                rejections=rejections,
                unresolved_violation=False,
                embedding=candidate_emb.tolist(),
            )
        rejections.extend(failures)
        feedback = " ".join(failures)

    # Exhausted retries: accept the last candidate anyway, flagged as unresolved.
    return Verse(
        index=len(seq_verses),
        author=author,
        text=candidate_text,
        motifs=candidate_tags["motifs"],
        categories=candidate_tags["categories"],
        rejections=rejections,
        unresolved_violation=True,
        embedding=candidate_emb.tolist(),
    )
