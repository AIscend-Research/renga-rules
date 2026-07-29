#!/usr/bin/env python3
"""Load results/<condition>/*.json, compute the ablation table, and render:
  - results/ablation_table.csv     (one row per condition: gravity gap + CI, rejection rate, autocorrelation)
  - results/gravity_gap.png        (bar chart with bootstrap CIs -- the headline figure)
  - results/autocorrelation.png    (descriptive line chart, lag 1-5, one line per condition)

Also runs a permutation test comparing full_shikimoku vs baseline and
full_shikimoku vs arbitrary_control on gravity gap, and prints the p-values --
that comparison is what turns the headline figure into a claim.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from renga.conditions import CONDITIONS
from renga.experiment import load_condition
from renga.metrics import summarize_condition, permutation_test_diff

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def main():
    summaries = {}
    for condition in CONDITIONS:
        sequences = load_condition(condition, RESULTS_DIR)
        if not sequences:
            continue
        summaries[condition] = summarize_condition(sequences)

    if not summaries:
        print("No results found under results/. Run scripts/run_experiment.py first.")
        return

    # --- table ---
    table_path = os.path.join(RESULTS_DIR, "ablation_table.csv")
    with open(table_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["condition", "n_sequences", "gravity_gap_mean", "gravity_gap_ci_lo", "gravity_gap_ci_hi", "rejection_rate_mean", "unresolved_violation_rate_mean"])
        for cond, s in summaries.items():
            lo, hi = s["gravity_gap_ci"]
            writer.writerow([cond, s["n_sequences"], s["gravity_gap_mean"], lo, hi, s["rejection_rate_mean"], s["unresolved_violation_rate_mean"]])
    print(f"Wrote {table_path}")

    # --- gravity gap bar chart ---
    conds = list(summaries.keys())
    means = [summaries[c]["gravity_gap_mean"] or 0 for c in conds]
    los = [summaries[c]["gravity_gap_ci"][0] or 0 for c in conds]
    his = [summaries[c]["gravity_gap_ci"][1] or 0 for c in conds]
    err_low = [m - l for m, l in zip(means, los)]
    err_high = [h - m for h, m in zip(his, means)]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(conds, means, yerr=[err_low, err_high], capsize=4)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Thematic gravity imbalance\n(|mean survival(persona A) − mean survival(persona B)|, in verses)")
    ax.set_title("Thematic gravity imbalance by governance condition")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    fig.savefig(os.path.join(RESULTS_DIR, "gravity_gap.png"), dpi=150)
    print(f"Wrote {os.path.join(RESULTS_DIR, 'gravity_gap.png')}")

    # --- autocorrelation curves (descriptive) ---
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    for cond, s in summaries.items():
        lags = sorted(s["autocorrelation_by_lag"].keys())
        vals = [s["autocorrelation_by_lag"][l] for l in lags]
        ax2.plot(lags, vals, marker="o", label=cond)
    ax2.set_xlabel("Lag (verses)")
    ax2.set_ylabel("Mean cosine similarity")
    ax2.set_title("Semantic autocorrelation by lag (descriptive only)")
    ax2.legend(fontsize=8)
    plt.tight_layout()
    fig2.savefig(os.path.join(RESULTS_DIR, "autocorrelation.png"), dpi=150)
    print(f"Wrote {os.path.join(RESULTS_DIR, 'autocorrelation.png')}")

    # --- significance checks on the headline comparison ---
    if "full_shikimoku" in summaries:
        for other in ("baseline", "arbitrary_control"):
            if other in summaries:
                a = summaries["full_shikimoku"]["gravity_gap_raw"]
                b = summaries[other]["gravity_gap_raw"]
                if a and b:
                    p = permutation_test_diff(a, b)
                    print(f"permutation test full_shikimoku vs {other}: p = {p:.4f} (n_a={len(a)}, n_b={len(b)})")


if __name__ == "__main__":
    main()
