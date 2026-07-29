#!/usr/bin/env python3
"""Print raw similarity/lineage numbers on a small pilot batch so you can set
LINK_MIN_SIM / SHIFT_MAX_SIM (renga/rules.py) and LINEAGE_SIM (renga/provenance.py)
from real data instead of guessing.

Run this AFTER a --pilot experiment (see run_experiment.py --pilot), on the
baseline condition specifically, since it has no rules pushing similarities
around -- it shows you the natural distribution to threshold against.

Usage:
  python scripts/run_experiment.py --pilot --conditions baseline
  python scripts/calibrate.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np

from renga.experiment import load_condition
from renga.embeddings import cosine_sim

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def main():
    sequences = load_condition("baseline", RESULTS_DIR)
    if not sequences:
        print("No baseline pilot data found. Run: python scripts/run_experiment.py --pilot --conditions baseline")
        return

    lag1, lag2 = [], []
    for seq in sequences:
        embs = [v.emb() for v in seq.verses]
        for i in range(1, len(embs)):
            lag1.append(cosine_sim(embs[i], embs[i - 1]))
        for i in range(2, len(embs)):
            lag2.append(cosine_sim(embs[i], embs[i - 2]))

    def report(name, vals):
        vals = np.array(vals)
        print(f"{name}: n={len(vals)} mean={vals.mean():.3f} p25={np.percentile(vals,25):.3f} "
              f"median={np.percentile(vals,50):.3f} p75={np.percentile(vals,75):.3f}")

    print("Natural (unconstrained) similarity distribution on baseline pilot data:")
    report("lag-1 (adjacent verses)", lag1)
    report("lag-2 (verse before last)", lag2)
    print("\nSuggested starting points:")
    print(f"  LINK_MIN_SIM  ~= 25th percentile of lag-1  (verse must be at least this connected)")
    print(f"  SHIFT_MAX_SIM ~= 75th percentile of lag-2  (verse must be at most this similar to 2-back)")
    print("Edit renga/rules.py with whatever you land on, re-run the pilot, and sanity-check by eye")
    print("that accepted verses actually read as linked/shifted before committing to the full run.")


if __name__ == "__main__":
    main()
