#!/usr/bin/env python3
"""CLI: run the full ablation battery (or a subset) and write results/<condition>/seq_NNN.json.

Examples:
  python scripts/run_experiment.py --pilot            # 3 sequences x 8 verses, all conditions, cheap sanity check
  python scripts/run_experiment.py                    # default: 20 sequences x 16 verses, all conditions
  python scripts/run_experiment.py --conditions baseline full_shikimoku arbitrary_control --n 30
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from renga.conditions import CONDITIONS
from renga.experiment import run_experiment


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--conditions", nargs="*", default=None, choices=list(CONDITIONS.keys()))
    p.add_argument("--n", type=int, default=20, help="sequences per condition")
    p.add_argument("--length", type=int, default=16, help="verses per sequence")
    p.add_argument("--seeds", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "seeds.json"))
    p.add_argument("--out", default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results"))
    p.add_argument("--model", default=None)
    p.add_argument("--pilot", action="store_true", help="shortcut for --n 3 --length 8, useful for calibrating thresholds cheaply")
    p.add_argument("--seed-rng", type=int, default=0)
    args = p.parse_args()

    n, length = (3, 8) if args.pilot else (args.n, args.length)

    run_experiment(
        conditions=args.conditions,
        n_sequences=n,
        length=length,
        seeds_path=args.seeds,
        out_dir=args.out,
        model=args.model,
        seed_rng=args.seed_rng,
    )


if __name__ == "__main__":
    main()
