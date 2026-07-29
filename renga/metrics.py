"""Descriptive + inferential stats layer.

semantic_autocorrelation is DESCRIPTIVE ONLY -- it shows the shape of
topical drift across lags but, per the critique this project is built on,
must not be reported as the headline finding (that would be measuring
instruction compliance, not governance). The headline metric is
provenance.gravity_gap; this module's bootstrap/permutation helpers are
what make that gap a claim rather than an anecdote.
"""
from __future__ import annotations

import numpy as np

from .embeddings import cosine_sim


def semantic_autocorrelation(sequence, max_lag: int = 5):
    embs = [v.emb() for v in sequence.verses]
    out = {}
    for lag in range(1, max_lag + 1):
        sims = [cosine_sim(embs[i], embs[i - lag]) for i in range(lag, len(embs))]
        out[lag] = float(np.mean(sims)) if sims else None
    return out


def bootstrap_ci(values, n_boot: int = 2000, alpha: float = 0.05, rng=None):
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return None, None, None
    rng = rng or np.random.default_rng(0)
    boots = np.array([rng.choice(values, size=len(values), replace=True).mean() for _ in range(n_boot)])
    lo, hi = np.percentile(boots, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(values.mean()), float(lo), float(hi)


def permutation_test_diff(a, b, n_perm: int = 5000, rng=None) -> float:
    """Two-sided permutation test on difference of means; returns p-value."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    rng = rng or np.random.default_rng(0)
    observed = a.mean() - b.mean()
    pooled = np.concatenate([a, b])
    n_a = len(a)
    count = 0
    for _ in range(n_perm):
        rng.shuffle(pooled)
        diff = pooled[:n_a].mean() - pooled[n_a:].mean()
        if abs(diff) >= abs(observed):
            count += 1
    return count / n_perm


def summarize_condition(sequences, group_a=("model_A",), group_b=("model_B", "human"), signed=False):
    """sequences: list[Sequence] for ONE condition. Returns dict of aggregate stats
    used directly as one row of the ablation table.

    signed=False (default, for bulk two-persona runs): gravity_gap_raw stores
    |gap| per sequence, since there's no principled sign when both authors
    are the model (see provenance.gravity_gap docstring) -- the ablation
    table and its bootstrap CI are over *dominance imbalance magnitude*.

    signed=True: use for human_session.py transcripts with
    group_a=("model_A",), group_b=("human",), where the sign IS meaningful
    (positive = model dominates the human)."""
    from .provenance import build_lineages, gravity_gap

    gaps, rejection_rates, unresolved_rates, autocorrs = [], [], [], []
    for seq in sequences:
        lineages = build_lineages(seq)
        gap, _, _ = gravity_gap(lineages, group_a, group_b)
        if gap is not None:
            gaps.append(gap if signed else abs(gap))
        n_verses = len(seq.verses)
        n_rejections = sum(len(v.rejections) for v in seq.verses)
        n_unresolved = sum(1 for v in seq.verses if v.unresolved_violation)
        rejection_rates.append(n_rejections / max(n_verses, 1))
        unresolved_rates.append(n_unresolved / max(n_verses, 1))
        autocorrs.append(semantic_autocorrelation(seq))

    mean_gap, lo, hi = bootstrap_ci(gaps)
    lag_means = {}
    if autocorrs:
        for lag in autocorrs[0]:
            vals = [a[lag] for a in autocorrs if a.get(lag) is not None]
            lag_means[lag] = float(np.mean(vals)) if vals else None

    return {
        "n_sequences": len(sequences),
        "gravity_gap_mean": mean_gap,
        "gravity_gap_ci": (lo, hi),
        "gravity_gap_raw": gaps,
        "rejection_rate_mean": float(np.mean(rejection_rates)) if rejection_rates else None,
        "unresolved_violation_rate_mean": float(np.mean(unresolved_rates)) if unresolved_rates else None,
        "autocorrelation_by_lag": lag_means,
    }
