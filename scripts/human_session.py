#!/usr/bin/env python3
"""Interactive real human-LLM co-writing session under a chosen condition.
This is the qualitative/demo condition for the paper (a transcript you can
quote) -- the automated model_A/model_B runs (run_experiment.py) are what
give you statistical power for the ablation table.

Usage:
  python scripts/human_session.py --condition full_shikimoku --length 12
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from renga.conditions import CONDITIONS
from renga.scribe import generate_next_verse
from renga.sequence import Sequence, Verse
from renga.embeddings import embed
from renga.llm import extract_tags


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--condition", required=True, choices=list(CONDITIONS.keys()))
    p.add_argument("--length", type=int, default=12)
    p.add_argument("--out", default=None)
    p.add_argument("--model", default=None)
    args = p.parse_args()

    print(f"Human-LLM renga session. Condition: {args.condition}")
    seed_text = input("Write the opening verse (hokku): ").strip()
    tags = extract_tags(seed_text, **({"model": args.model} if args.model else {}))
    verses = [Verse(index=0, author="human", text=seed_text, motifs=tags["motifs"], categories=tags["categories"], embedding=embed(seed_text).tolist())]

    for i in range(1, args.length):
        if i % 2 == 1:
            verse = generate_next_verse(verses, args.condition, "model_A", model=args.model)
            print(f"\n[model] {verse.text}")
            if verse.rejections:
                print(f"  (rejected {len(verse.rejections)}x before acceptance)")
            if verse.unresolved_violation:
                print("  (WARNING: accepted with an unresolved rule violation after max retries)")
        else:
            text = input("\nYour verse: ").strip()
            tags = extract_tags(text, **({"model": args.model} if args.model else {}))
            verse = Verse(index=i, author="human", text=text, motifs=tags["motifs"], categories=tags["categories"], embedding=embed(text).tolist())
        verses.append(verse)

    seq = Sequence(condition=args.condition, seed_id="human_session", verses=verses)
    out_dir = args.out or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "human_sessions")
    os.makedirs(out_dir, exist_ok=True)
    idx = len([f for f in os.listdir(out_dir) if f.endswith(".json")])
    out_path = os.path.join(out_dir, f"session_{idx:03d}.json")
    with open(out_path, "w") as f:
        json.dump(seq.to_dict(), f, indent=2)
    print(f"\nSaved transcript to {out_path}")


if __name__ == "__main__":
    main()
