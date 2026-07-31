#!/usr/bin/env python3
"""Deeper re-analysis of already-generated experiment data. No new API calls,
this only re-processes the 160 sequences already saved under results/.

Covers six things scripts/make_plots.py doesn't:

1. Fixes a real confound: the seed verse (pre-written, not model-generated)
   was hardcoded as authored by "model_A" in every sequence, so any motif
   originating in the seed and persisting later inflated model_A's apparent
   thematic gravity in every single condition. Recomputes gravity_gap with
   the seed excluded from both authorship groups.
2. Synergy test: is full_shikimoku's effect on the corrected gap bigger than
   the sum of each individual rule's own marginal effect (interaction), or
   just additive (or less)?
3. Dose-response: within full_shikimoku, does a sequence's rejection count
   (how much friction it took to write) predict its corrected gravity gap?
4. Category-usage entropy as a second, more direct outcome measure than
   gravity gap -- does full governance actually spread topics more evenly?
5. Paired-by-seed permutation tests, blocking on the 8 recurring seed poems,
   to control for seed-level variance (e.g. "letter" behaving worse than
   other seeds every round during calibration).
6. Programmatically picks the most illustrative excerpt pair (most-imbalanced
   baseline sequence, most-balanced full_shikimoku sequence) for the paper's
   qualitative figure, instead of an arbitrarily hand-picked one.

Run after scripts/run_experiment.py and scripts/make_plots.py, once the full
8-condition, n=20 experiment is done.
"""
import copy
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from renga.conditions import CONDITIONS
from renga.experiment import load_condition
from renga.provenance import build_lineages, gravity_gap
from renga.metrics import bootstrap_ci, permutation_test_diff, paired_permutation_test, category_entropy
from renga.plotstyle import styled_bar_chart

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
OUT_DIR = os.path.join(RESULTS_DIR, "deep_analysis")

SINGLE_RULE_CONDITIONS = ["link_only", "shift_only", "uchikoshi_only", "sarikirai_only", "rotation_only"]


def corrected_gravity_gap(sequence):
    """Same computation as provenance.gravity_gap, but on a patched in-memory
    copy where the seed verse (index 0) is relabeled author="seed" instead of
    "model_A", so it's excluded from both authorship groups. Does not touch
    the saved JSON files."""
    patched = copy.deepcopy(sequence)
    patched.verses[0].author = "seed"
    lineages = build_lineages(patched)
    gap, _, _ = gravity_gap(lineages, group_a=("model_A",), group_b=("model_B",))
    return gap, lineages


def per_sequence_stats(sequences):
    rows = []
    for seq in sequences:
        gap, _ = corrected_gravity_gap(seq)
        rows.append({
            "seed_id": seq.seed_id,
            "gap": abs(gap) if gap is not None else None,
            "rejections": sum(len(v.rejections) for v in seq.verses),
            "entropy": category_entropy(seq),
        })
    return rows


def load_all():
    data = {}
    for cond in CONDITIONS:
        seqs = load_condition(cond, RESULTS_DIR)
        if seqs:
            data[cond] = seqs
    return data


def per_seed_means(rows):
    by_seed = {}
    for r in rows:
        if r["gap"] is not None:
            by_seed.setdefault(r["seed_id"], []).append(r["gap"])
    return {seed: float(np.mean(vals)) for seed, vals in by_seed.items()}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    report_lines = []

    def log(msg=""):
        print(msg)
        report_lines.append(msg)

    data = load_all()
    if "baseline" not in data or "full_shikimoku" not in data:
        log("Need at least baseline and full_shikimoku data. Run the full experiment first.")
        return

    log("=" * 72)
    log("1. CORRECTED GRAVITY GAP (seed-authorship confound removed)")
    log("=" * 72)
    corrected = {}
    for cond, seqs in data.items():
        rows = per_sequence_stats(seqs)
        gaps = [r["gap"] for r in rows if r["gap"] is not None]
        if not gaps:
            log(f"{cond:20s} no valid gaps, skipping")
            continue
        mean, lo, hi = bootstrap_ci(gaps)
        corrected[cond] = {"rows": rows, "gaps": gaps, "mean": mean, "lo": lo, "hi": hi}
        log(f"{cond:20s} n={len(gaps):2d}  corrected_gap={mean:.3f} (CI {lo:.3f}-{hi:.3f})")

    if "full_shikimoku" in corrected and "baseline" in corrected:
        p = permutation_test_diff(corrected["full_shikimoku"]["gaps"], corrected["baseline"]["gaps"])
        log(f"\npermutation test (corrected) full_shikimoku vs baseline: p = {p:.4f}")
    if "full_shikimoku" in corrected and "arbitrary_control" in corrected:
        p = permutation_test_diff(corrected["full_shikimoku"]["gaps"], corrected["arbitrary_control"]["gaps"])
        log(f"permutation test (corrected) full_shikimoku vs arbitrary_control: p = {p:.4f}")

    log()
    log("=" * 72)
    log("2. SYNERGY: is full_shikimoku's effect bigger than the sum of its parts?")
    log("=" * 72)
    if "baseline" in corrected:
        baseline_mean = corrected["baseline"]["mean"]
        individual_effects = {}
        for cond in SINGLE_RULE_CONDITIONS:
            if cond in corrected:
                effect = baseline_mean - corrected[cond]["mean"]
                individual_effects[cond] = effect
                log(f"  {cond:20s} marginal effect (baseline - condition) = {effect:+.3f}")
        if individual_effects and "full_shikimoku" in corrected:
            sum_of_parts = sum(individual_effects.values())
            actual_full_effect = baseline_mean - corrected["full_shikimoku"]["mean"]
            log(f"\n  sum of individual marginal effects   = {sum_of_parts:+.3f}")
            log(f"  actual full_shikimoku effect         = {actual_full_effect:+.3f}")
            if actual_full_effect > sum_of_parts:
                log("  -> SYNERGY: combined rules outperform the sum of their individual effects")
            else:
                log("  -> NO SYNERGY: combined effect is <= the sum of individual effects")

    log()
    log("=" * 72)
    log("3. DOSE-RESPONSE within full_shikimoku: rejections vs corrected gap")
    log("=" * 72)
    if "full_shikimoku" in corrected:
        rows = [r for r in corrected["full_shikimoku"]["rows"] if r["gap"] is not None]
        rejections = np.array([r["rejections"] for r in rows], dtype=float)
        gaps = np.array([r["gap"] for r in rows], dtype=float)
        if len(rejections) > 2:
            pearson_r = float(np.corrcoef(rejections, gaps)[0, 1])
            rank_rej = np.argsort(np.argsort(rejections))
            rank_gap = np.argsort(np.argsort(gaps))
            spearman_r = float(np.corrcoef(rank_rej, rank_gap)[0, 1])
            log(f"  Pearson r  = {pearson_r:.3f}  (n={len(rejections)})")
            log(f"  Spearman rho = {spearman_r:.3f}")

            fig, ax = plt.subplots(figsize=(6, 5))
            ax.scatter(rejections, gaps, alpha=0.7)
            z = np.polyfit(rejections, gaps, 1)
            xs = np.linspace(rejections.min(), rejections.max(), 50)
            ax.plot(xs, np.polyval(z, xs), color="black", linewidth=1, linestyle="--")
            ax.set_xlabel("Rejections during generation (friction)")
            ax.set_ylabel("Corrected thematic gravity gap")
            ax.set_title(f"full_shikimoku: friction vs balance (Pearson r={pearson_r:.2f})")
            plt.tight_layout()
            fig.savefig(os.path.join(OUT_DIR, "dose_response.png"), dpi=150)
            log(f"  wrote {os.path.join(OUT_DIR, 'dose_response.png')}")
        else:
            log("  not enough sequences with valid gaps to correlate")

    log()
    log("=" * 72)
    log("4. CATEGORY-DIVERSITY (Shannon entropy) as a second outcome measure")
    log("=" * 72)
    entropy_summary = {}
    for cond, info in corrected.items():
        ents = [r["entropy"] for r in info["rows"] if r["entropy"] is not None]
        if not ents:
            continue
        mean, lo, hi = bootstrap_ci(ents)
        entropy_summary[cond] = {"ents": ents, "mean": mean, "lo": lo, "hi": hi}
        log(f"{cond:20s} n={len(ents):2d}  entropy={mean:.3f} bits (CI {lo:.3f}-{hi:.3f})")

    if "full_shikimoku" in entropy_summary and "baseline" in entropy_summary:
        p = permutation_test_diff(entropy_summary["full_shikimoku"]["ents"], entropy_summary["baseline"]["ents"])
        log(f"\npermutation test (entropy) full_shikimoku vs baseline: p = {p:.4f}")
    if "full_shikimoku" in entropy_summary and "arbitrary_control" in entropy_summary:
        p = permutation_test_diff(entropy_summary["full_shikimoku"]["ents"], entropy_summary["arbitrary_control"]["ents"])
        log(f"permutation test (entropy) full_shikimoku vs arbitrary_control: p = {p:.4f}")

    if entropy_summary:
        conds = list(entropy_summary.keys())
        means = [entropy_summary[c]["mean"] for c in conds]
        los = [entropy_summary[c]["lo"] for c in conds]
        his = [entropy_summary[c]["hi"] for c in conds]
        err_low = [m - l for m, l in zip(means, los)]
        err_high = [h - m for h, m in zip(his, means)]
        entropy_path = os.path.join(OUT_DIR, "entropy_by_condition.png")
        styled_bar_chart(
            conds, means, err_low, err_high,
            ylabel="Category-usage entropy (bits)",
            title="Topic diversity by governance condition",
            out_path=entropy_path,
        )
        log(f"wrote {entropy_path}")

    table_path = os.path.join(OUT_DIR, "corrected_ablation_table.csv")
    with open(table_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["condition", "n", "corrected_gap_mean", "corrected_gap_ci_lo", "corrected_gap_ci_hi",
                          "entropy_mean", "entropy_ci_lo", "entropy_ci_hi"])
        for cond in corrected:
            g = corrected[cond]
            e = entropy_summary.get(cond, {"mean": None, "lo": None, "hi": None})
            writer.writerow([cond, len(g["gaps"]), g["mean"], g["lo"], g["hi"], e["mean"], e["lo"], e["hi"]])
    log(f"wrote {table_path}")

    log()
    log("=" * 72)
    log("5. PAIRED-BY-SEED tests (blocking on the 8 recurring seed poems)")
    log("=" * 72)
    if "full_shikimoku" in corrected and "baseline" in corrected:
        a = per_seed_means(corrected["full_shikimoku"]["rows"])
        b = per_seed_means(corrected["baseline"]["rows"])
        shared = sorted(set(a) & set(b))
        diffs = [a[s] - b[s] for s in shared]
        p = paired_permutation_test(diffs)
        log(f"  full_shikimoku vs baseline: n_seeds={len(diffs)}  mean_diff={np.mean(diffs):+.3f}  p={p:.4f}")

    if "full_shikimoku" in corrected and "arbitrary_control" in corrected:
        a = per_seed_means(corrected["full_shikimoku"]["rows"])
        b = per_seed_means(corrected["arbitrary_control"]["rows"])
        shared = sorted(set(a) & set(b))
        diffs = [a[s] - b[s] for s in shared]
        p = paired_permutation_test(diffs)
        log(f"  full_shikimoku vs arbitrary_control: n_seeds={len(diffs)}  mean_diff={np.mean(diffs):+.3f}  p={p:.4f}")

    log()
    log("=" * 72)
    log("6. EXCERPT SELECTION: most-imbalanced baseline vs most-balanced full_shikimoku")
    log("=" * 72)
    excerpt_lines = []
    if "baseline" in corrected:
        rows = corrected["baseline"]["rows"]
        seqs = data["baseline"]
        valid = [i for i, r in enumerate(rows) if r["gap"] is not None]
        idx_max = max(valid, key=lambda i: rows[i]["gap"])
        worst_seq = seqs[idx_max]
        excerpt_lines.append(f"MOST IMBALANCED baseline sequence (seed={worst_seq.seed_id}, corrected_gap={rows[idx_max]['gap']:.3f}):")
        excerpt_lines.append("")
        for v in worst_seq.verses:
            excerpt_lines.append(f"[{v.index}] ({v.author}): {v.text}")
        excerpt_lines.append("")
    if "full_shikimoku" in corrected:
        rows = corrected["full_shikimoku"]["rows"]
        seqs = data["full_shikimoku"]
        valid = [i for i, r in enumerate(rows) if r["gap"] is not None]
        idx_min = min(valid, key=lambda i: rows[i]["gap"])
        best_seq = seqs[idx_min]
        excerpt_lines.append(f"MOST BALANCED full_shikimoku sequence (seed={best_seq.seed_id}, corrected_gap={rows[idx_min]['gap']:.3f}):")
        excerpt_lines.append("")
        for v in best_seq.verses:
            excerpt_lines.append(f"[{v.index}] ({v.author}): {v.text}")

    excerpt_path = os.path.join(OUT_DIR, "excerpts.txt")
    with open(excerpt_path, "w") as f:
        f.write("\n".join(excerpt_lines))
    log(f"wrote {excerpt_path}\n")
    log("\n".join(excerpt_lines))

    report_path = os.path.join(OUT_DIR, "report.txt")
    with open(report_path, "w") as f:
        f.write("\n".join(report_lines))
    print(f"\nwrote {report_path}")


if __name__ == "__main__":
    main()
