#!/usr/bin/env python3
"""Analyze the real human-LLM session transcripts under results/human_sessions/.

Computes, per session:
- signed gravity gap (model - human) -- unlike the bulk two-persona runs,
  this comparison has a real, meaningful sign: positive means the model's
  motifs outlived the human's, negative means the human's outlived the
  model's. See renga/provenance.py's gravity_gap docstring.
- category-usage entropy (topic diversity), same metric as the bulk analysis
- rejection/unresolved counts, for comparison against the bulk experiment's
  averages

This is n=1-per-condition case-study material, NOT a statistical sample --
there is no p-value here and none should be computed. Report these numbers
as concrete qualitative evidence alongside the bulk ablation results, not as
if they were independently powered findings.

Writes results/human_sessions/analysis.txt (plain text, safe to paste into
the paper) in addition to printing to stdout.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from renga.sequence import Sequence
from renga.provenance import build_lineages, gravity_gap
from renga.metrics import category_entropy
import json

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "human_sessions")


def analyze_session(path):
    d = json.load(open(path))
    seq = Sequence.from_dict(d)
    lineages = build_lineages(seq)
    gap, model_s, human_s = gravity_gap(lineages, group_a=("model_A",), group_b=("human",))
    entropy = category_entropy(seq)
    total_rej = sum(len(v.rejections) for v in seq.verses)
    total_unres = sum(1 for v in seq.verses if v.unresolved_violation)
    model_verses = sum(1 for v in seq.verses if v.author == "model_A")

    surviving_model = [l for l in lineages if l.origin_author == "model_A" and l.survival > 0]
    surviving_human = [l for l in lineages if l.origin_author == "human" and l.survival > 0]

    return {
        "path": path,
        "condition": d["condition"],
        "n_verses": len(seq.verses),
        "signed_gravity_gap": gap,
        "model_survivals": model_s,
        "human_survivals": human_s,
        "surviving_model_lineages": [(l.example_phrases, l.survival) for l in surviving_model],
        "surviving_human_lineages": [(l.example_phrases, l.survival) for l in surviving_human],
        "category_entropy_bits": entropy,
        "total_rejections": total_rej,
        "rejections_per_model_verse": total_rej / max(model_verses, 1),
        "unresolved_count": total_unres,
        "unresolved_rate": total_unres / max(model_verses, 1),
    }


def format_report(results):
    lines = []
    lines.append("Human-LLM session analysis")
    lines.append("=" * 70)
    lines.append("")
    lines.append("n=1 per condition -- case-study evidence, not a statistical sample.")
    lines.append("No significance test applies here; report these numbers as concrete")
    lines.append("qualitative illustrations alongside the bulk (n=20) ablation results.")
    lines.append("")
    for r in results:
        lines.append(f"--- {os.path.basename(r['path'])} (condition: {r['condition']}) ---")
        gap_str = f"{r['signed_gravity_gap']:+.3f}" if r["signed_gravity_gap"] is not None else "N/A"
        lines.append(f"  signed gravity gap (model - human): {gap_str}")
        lines.append(f"    positive = model's motifs outlived the human's; negative = the reverse")
        if r["surviving_model_lineages"]:
            lines.append(f"  model-originated motifs that recurred:")
            for phrases, survival in r["surviving_model_lineages"]:
                lines.append(f"    - {phrases} (survived {survival} verses)")
        if r["surviving_human_lineages"]:
            lines.append(f"  human-originated motifs that recurred:")
            for phrases, survival in r["surviving_human_lineages"]:
                lines.append(f"    - {phrases} (survived {survival} verses)")
        lines.append(f"  category-usage entropy: {r['category_entropy_bits']:.3f} bits" if r["category_entropy_bits"] is not None else "  entropy: N/A")
        lines.append(f"  rejections: {r['total_rejections']} total, {r['rejections_per_model_verse']:.2f} per model-written verse")
        lines.append(f"  unresolved violations: {r['unresolved_count']} ({r['unresolved_rate']*100:.0f}% of model verses)")
        lines.append("")

    if len(results) >= 2:
        conds = {r["condition"]: r for r in results}
        if "baseline" in conds and "full_shikimoku" in conds:
            b, f = conds["baseline"], conds["full_shikimoku"]
            lines.append("--- baseline vs full_shikimoku, same human, same opening hokku ---")
            if b["signed_gravity_gap"] is not None and f["signed_gravity_gap"] is not None:
                lines.append(f"  gravity gap: {b['signed_gravity_gap']:+.3f} (baseline) -> {f['signed_gravity_gap']:+.3f} (full_shikimoku)")
                if (b["signed_gravity_gap"] > 0) != (f["signed_gravity_gap"] > 0):
                    lines.append("  -> SIGN FLIP: whichever side dominated under baseline reversed under full governance")
            lines.append(f"  entropy: {b['category_entropy_bits']:.3f} -> {f['category_entropy_bits']:.3f} bits")
            lines.append(f"  rejections/verse: {b['rejections_per_model_verse']:.2f} -> {f['rejections_per_model_verse']:.2f}")
            lines.append("")
            lines.append("  Caveat: same human author wrote both sessions, with the baseline session")
            lines.append("  written first. The human's choices in the second session may have been")
            lines.append("  subtly informed by having just written the first -- a limitation of n=1")
            lines.append("  qualitative comparison, worth disclosing rather than ignoring.")

    return "\n".join(lines)


def main():
    paths = sorted(glob.glob(os.path.join(SESSIONS_DIR, "session_*.json")))
    if not paths:
        print("No human sessions found. Run scripts/human_session.py first.")
        return

    results = [analyze_session(p) for p in paths]
    report = format_report(results)
    print(report)

    out_path = os.path.join(SESSIONS_DIR, "analysis.txt")
    with open(out_path, "w") as f:
        f.write(report)
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()
