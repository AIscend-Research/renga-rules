#!/usr/bin/env python3
"""Two structural figures that show the mechanism directly, instead of
summarizing it as a single number:

1. thread_timeline.png -- a Gantt-style chart, one horizontal bar per
   recurring motif lineage, spanning from the verse it first appears in to
   the verse it last recurs in, colored by which persona introduced it.
   Baseline vs. full_shikimoku, same two sequences already selected as the
   "most imbalanced" / "most balanced" excerpts in deep_analysis.py, for
   consistency with the text figure.

2. similarity_heatmap.png -- a 16x16 verse-to-verse cosine-similarity
   matrix ("self-similarity matrix", a technique borrowed from music/motion
   analysis for visualizing repetition structure). A blocky, banded pattern
   means long runs of similar consecutive verses; a mottled, patchy pattern
   means more topic movement.

Both use data already generated -- no new API calls. Run after
scripts/deep_analysis.py (reuses its sequence-selection logic).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

import deep_analysis as da
from renga.embeddings import cosine_sim
from renga.plotstyle import (
    SURFACE, INK_PRIMARY, INK_SECONDARY, GRIDLINE, AXIS,
    COLOR_MODEL_A, COLOR_MODEL_B, SEQUENTIAL_BLUE,
)

RESULTS_DIR = da.RESULTS_DIR
OUT_DIR = da.OUT_DIR

AUTHOR_COLOR = {"model_A": COLOR_MODEL_A, "model_B": COLOR_MODEL_B}
AUTHOR_LABEL = {"model_A": "persona A", "model_B": "persona B"}


def select_illustrative_sequences():
    """Same selection as deep_analysis.py's excerpt pair: the most-imbalanced
    baseline sequence and the most-balanced full_shikimoku sequence, so the
    thread timeline / heatmap match the text excerpt already quoted."""
    data = da.load_all()
    corrected = {}
    for cond, seqs in data.items():
        rows = da.per_sequence_stats(seqs)
        gaps = [r["gap"] for r in rows if r["gap"] is not None]
        if gaps:
            corrected[cond] = {"rows": rows, "seqs": seqs}

    worst_baseline = None
    if "baseline" in corrected:
        rows, seqs = corrected["baseline"]["rows"], corrected["baseline"]["seqs"]
        valid = [i for i, r in enumerate(rows) if r["gap"] is not None]
        idx = max(valid, key=lambda i: rows[i]["gap"])
        worst_baseline = seqs[idx]

    best_full = None
    if "full_shikimoku" in corrected:
        rows, seqs = corrected["full_shikimoku"]["rows"], corrected["full_shikimoku"]["seqs"]
        valid = [i for i, r in enumerate(rows) if r["gap"] is not None]
        idx = min(valid, key=lambda i: rows[i]["gap"])
        best_full = seqs[idx]

    return worst_baseline, best_full


def plot_thread_timeline(sequences_with_titles, out_path):
    n = len(sequences_with_titles)
    fig, axes = plt.subplots(n, 1, figsize=(9, 3.2 * n), facecolor=SURFACE)
    if n == 1:
        axes = [axes]

    for ax, (seq, title) in zip(axes, sequences_with_titles):
        ax.set_facecolor(SURFACE)
        _, lineages = da.corrected_gravity_gap(seq)
        recurring = sorted([l for l in lineages if l.survival > 0], key=lambda l: l.origin_idx)

        for row_i, lin in enumerate(recurring):
            color = AUTHOR_COLOR.get(lin.origin_author, INK_SECONDARY)
            ax.barh(row_i, lin.last_seen_idx - lin.origin_idx, left=lin.origin_idx,
                    height=0.55, color=color, edgecolor="none")
            label = lin.example_phrases[0] if lin.example_phrases else ""
            ax.text(lin.last_seen_idx + 0.3, row_i, label, va="center", ha="left",
                    fontsize=8, color=INK_PRIMARY)

        n_verses = len(seq.verses)
        ax.set_xlim(0, n_verses + 3.5)
        ax.set_ylim(-0.7, max(len(recurring) - 0.3, 0.3))
        ax.invert_yaxis()
        ax.set_yticks([])
        ax.set_xlabel("Verse index", color=INK_SECONDARY, fontsize=9)
        ax.set_title(title, color=INK_PRIMARY, fontsize=11, loc="left", pad=10)
        ax.xaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
        ax.set_axisbelow(True)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.spines["bottom"].set_color(AXIS)
        ax.tick_params(colors=INK_SECONDARY, labelsize=8)

        handles = [
            plt.Rectangle((0, 0), 1, 1, color=COLOR_MODEL_A, label="persona A"),
            plt.Rectangle((0, 0), 1, 1, color=COLOR_MODEL_B, label="persona B"),
        ]
        ax.legend(handles=handles, loc="lower right", fontsize=8, frameon=False)

    fig.suptitle("Motif persistence: who introduced each recurring idea, and how long it lasted",
                 color=INK_PRIMARY, fontsize=12, x=0.01, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def plot_similarity_heatmap(sequences_with_titles, out_path):
    n = len(sequences_with_titles)
    fig, axes = plt.subplots(1, n, figsize=(6 * n, 5.5), facecolor=SURFACE)
    if n == 1:
        axes = [axes]
    cmap = LinearSegmentedColormap.from_list("seq_blue", SEQUENTIAL_BLUE)

    im = None
    for ax, (seq, title) in zip(axes, sequences_with_titles):
        ax.set_facecolor(SURFACE)
        embs = [v.emb() for v in seq.verses]
        n_v = len(embs)
        mat = np.zeros((n_v, n_v))
        for i in range(n_v):
            for j in range(n_v):
                mat[i, j] = cosine_sim(embs[i], embs[j])
        im = ax.imshow(mat, cmap=cmap, vmin=0, vmax=1, origin="upper")
        ax.set_title(title, color=INK_PRIMARY, fontsize=11, loc="left", pad=10)
        ax.set_xlabel("Verse index", color=INK_SECONDARY, fontsize=9)
        ax.set_ylabel("Verse index", color=INK_SECONDARY, fontsize=9)
        ax.tick_params(colors=INK_SECONDARY, labelsize=8)
        for spine in ax.spines.values():
            spine.set_color(AXIS)

    fig.suptitle("Verse-to-verse similarity structure (self-similarity matrix)",
                 color=INK_PRIMARY, fontsize=12, x=0.01, ha="left")
    cbar = fig.colorbar(im, ax=axes, shrink=0.8, pad=0.02)
    cbar.set_label("cosine similarity", color=INK_SECONDARY, fontsize=9)
    cbar.ax.tick_params(colors=INK_SECONDARY, labelsize=8)
    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    worst_baseline, best_full = select_illustrative_sequences()
    if worst_baseline is None or best_full is None:
        print("Need both baseline and full_shikimoku data. Run the full experiment first.")
        return

    pairs = [
        (worst_baseline, f"baseline (seed={worst_baseline.seed_id}) -- most imbalanced"),
        (best_full, f"full_shikimoku (seed={best_full.seed_id}) -- most balanced"),
    ]

    timeline_path = os.path.join(OUT_DIR, "thread_timeline.png")
    plot_thread_timeline(pairs, timeline_path)
    print(f"wrote {timeline_path}")

    heatmap_path = os.path.join(OUT_DIR, "similarity_heatmap.png")
    plot_similarity_heatmap(pairs, heatmap_path)
    print(f"wrote {heatmap_path}")


if __name__ == "__main__":
    main()
