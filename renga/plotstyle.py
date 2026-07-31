"""Shared styling for the project's static paper figures (not the runtime
scribe/rules logic). Colors are the dataviz skill's validated default
categorical palette -- fixed hue order, not cycled, and the specific
highlight/context/foil pairing here was run through the skill's CVD
validator (blue vs red: worst adjacent normal-vision dE 32.3, CVD dE 21.6,
both well clear of the pass floors) before use.

Only three roles are used, on purpose: most of these charts compare 8
conditions, but the story is about 2-3 of them (the headline condition, the
control/foil, and everything else as supporting ablation detail). Giving
all 8 conditions distinct saturated hues would be a rainbow chart with no
story; muting the context conditions to gray and reserving color for what
the finding is actually about is the point.
"""
from __future__ import annotations

import textwrap

import matplotlib.pyplot as plt

SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS = "#c3c2b7"

COLOR_HERO = "#2a78d6"      # blue -- the condition the finding is about
COLOR_FOIL = "#e34948"      # red -- the adversarial/equal-complexity control
COLOR_CONTEXT = "#c3c2b7"   # muted gray -- supporting ablation detail, not the headline

# Author-identity colors for per-sequence figures (thread timeline, etc.) --
# distinct role from the condition-level hero/foil/context above. Validated
# adjacent pair (worst-case normal-vision dE 33.6, CVD dE 24.7).
COLOR_MODEL_A = "#2a78d6"   # blue
COLOR_MODEL_B = "#eb6834"   # orange
COLOR_HUMAN = "#1baf7a"     # aqua -- for human_session.py transcripts (three authors: model_A/model_B/human never co-occur, but human sessions only ever have model_A + human)

# Sequential single-hue ramp (blue, light -> dark) for similarity heatmaps /
# other continuous-magnitude encodings. From the dataviz skill's validated
# palette.md sequential row.
SEQUENTIAL_BLUE = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
    "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]

DEFAULT_ROLES = {
    "baseline": "context",
    "rotation_only": "context",
    "link_only": "context",
    "shift_only": "context",
    "uchikoshi_only": "context",
    "sarikirai_only": "context",
    "full_shikimoku": "hero",
    "arbitrary_control": "foil",
}


def styled_bar_chart(conds, means, err_low, err_high, ylabel, title, out_path, roles=None, value_fmt="{:.2f}"):
    """roles: dict condition -> "hero" | "foil" | "context" (defaults to
    DEFAULT_ROLES, the project's fixed 8-condition story)."""
    roles = roles or DEFAULT_ROLES
    color_map = {"hero": COLOR_HERO, "foil": COLOR_FOIL, "context": COLOR_CONTEXT}
    colors = [color_map[roles.get(c, "context")] for c in conds]

    fig, ax = plt.subplots(figsize=(9, 5), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    bars = ax.bar(
        conds, means, yerr=[err_low, err_high], capsize=3, width=0.6,
        color=colors, edgecolor="none",
        error_kw={"ecolor": INK_SECONDARY, "elinewidth": 1, "capthick": 1},
    )

    tops = [m + e for m, e in zip(means, err_high)]
    for bar, mean, top in zip(bars, means, tops):
        ax.text(
            bar.get_x() + bar.get_width() / 2, top + 0.015 * max(tops), value_fmt.format(mean),
            ha="center", va="bottom", fontsize=9, color=INK_PRIMARY,
        )

    # Long y-labels get clipped at the figure edge under tight_layout otherwise --
    # wrap to multiple lines rather than letting the first character vanish off-canvas.
    wrapped_ylabel = "\n".join(textwrap.wrap(ylabel, width=45))
    ax.set_ylabel(wrapped_ylabel, color=INK_SECONDARY, fontsize=10)
    ax.set_title(title, color=INK_PRIMARY, fontsize=12, loc="left", pad=14)

    ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(AXIS)
        ax.spines[spine].set_linewidth(0.8)

    ax.tick_params(colors=INK_SECONDARY, labelsize=9)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", color=INK_SECONDARY)

    fig.savefig(out_path, dpi=200, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
