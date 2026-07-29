"""Experiment runner: generates N sequences per condition, alternating two
model personas (model_A/model_B) as authors so `rotation` is testable even
in fully-automated bulk runs (no live human needed for statistical power).

For a real human-in-the-loop co-writing study, use scripts/human_session.py
instead -- that's the qualitative/demo condition for the paper, this is the
quantitative one.
"""
from __future__ import annotations

import json
import os
import random
import time

import anthropic

from .conditions import CONDITIONS
from .scribe import generate_next_verse
from .sequence import Sequence, Verse
from .embeddings import embed


def _seed_verse(seed_text: str) -> Verse:
    return Verse(index=0, author="model_A", text=seed_text, motifs=[], categories=[], embedding=embed(seed_text).tolist())


def run_sequence(condition: str, seed_id: str, seed_text: str, length: int, model: str = None) -> Sequence:
    verses = [_seed_verse(seed_text)]
    for i in range(1, length):
        author = "model_A" if i % 2 == 0 else "model_B"
        verse = generate_next_verse(verses, condition, author, model=model)
        verses.append(verse)
    return Sequence(condition=condition, seed_id=seed_id, verses=verses)


def run_experiment(
    conditions=None,
    n_sequences: int = 20,
    length: int = 16,
    seeds_path: str = "data/seeds.json",
    out_dir: str = "results",
    model: str = None,
    seed_rng: int = 0,
):
    conditions = conditions or list(CONDITIONS.keys())
    with open(seeds_path) as f:
        seeds = json.load(f)

    rng = random.Random(seed_rng)
    consecutive_failures = 0
    # If several sequences in a row fail even after the client's own retry budget
    # (llm.client's max_retries=8) is exhausted, that's not a one-off blip anymore,
    # it means Anthropic's API is having a sustained outage. Grinding through the
    # rest of n_sequences one at a time, each waiting out 8 retries before giving
    # up, just wastes time proving the same thing over and over. Stop the whole
    # run instead of the caller having to notice and Ctrl+C.
    CONSECUTIVE_FAILURE_LIMIT = 3

    for condition in conditions:
        cond_dir = os.path.join(out_dir, condition)
        os.makedirs(cond_dir, exist_ok=True)
        for i in range(n_sequences):
            out_path = os.path.join(cond_dir, f"seq_{i:03d}.json")
            if os.path.exists(out_path):
                # Resuming after a crash (e.g. a transient API 5xx/529) shouldn't re-pay for
                # and regenerate sequences that already completed successfully. Delete the
                # file first if you actually want to regenerate a specific sequence.
                print(f"[{condition}] skipping {out_path} (already exists)")
                continue
            seed = seeds[i % len(seeds)]
            try:
                seq = run_sequence(condition, seed_id=seed["id"], seed_text=seed["text"], length=length, model=model)
            except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
                print(f"[{condition}] FAILED seq_{i:03d} after retries ({e}); skipping, re-run this command later to fill it in")
                consecutive_failures += 1
                if consecutive_failures >= CONSECUTIVE_FAILURE_LIMIT:
                    print(
                        f"\n{consecutive_failures} sequences in a row failed even after the client's own "
                        "retry budget was exhausted. This almost certainly means Anthropic's API is "
                        "having a sustained outage right now, not a transient blip. Stopping here instead "
                        "of grinding through the rest -- check https://status.anthropic.com, wait, and "
                        "re-run this exact same command later; it will skip everything already completed."
                    )
                    return
                time.sleep(10)
                continue
            consecutive_failures = 0
            with open(out_path, "w") as f:
                json.dump(seq.to_dict(), f, indent=2)
            print(f"[{condition}] wrote {out_path} (rejections={sum(len(v.rejections) for v in seq.verses)})")


def load_condition(condition: str, out_dir: str = "results"):
    cond_dir = os.path.join(out_dir, condition)
    sequences = []
    if not os.path.isdir(cond_dir):
        return sequences
    for fname in sorted(os.listdir(cond_dir)):
        if fname.endswith(".json"):
            with open(os.path.join(cond_dir, fname)) as f:
                sequences.append(Sequence.from_dict(json.load(f)))
    return sequences
