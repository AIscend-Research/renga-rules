"""Measure who steers, not just how much surface variety exists.

The critique that motivated this file: instructing "don't return to the verse
before last" and then measuring lag-2 embedding similarity only shows the
model complied with an instruction. The claim this paper actually needs is
about *thematic gravity* -- whether motifs the MODEL introduces persist
longer / dominate more than motifs the HUMAN (or the other persona)
introduces. That requires tracking individual motifs across the whole
sequence, not just adjacent-verse similarity.

Approach: cluster same-topic motif mentions into "lineages" using embedding
similarity of the short motif phrases (e.g. "falling snow" in verse 3 and
"the snow keeps falling" in verse 7 should cluster). Each lineage records
its origin verse/author and the last verse it was seen in. Thematic gravity
gap = mean survival length of model-originated lineages minus mean survival
length of human/other-persona-originated lineages, within a sequence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import numpy as np

from .embeddings import embed, cosine_sim

LINEAGE_SIM = 0.62  # cosine-sim cutoff for "same motif" clustering; calibrate on pilot data


@dataclass
class Lineage:
    id: int
    centroid: np.ndarray
    origin_idx: int
    origin_author: str
    last_seen_idx: int
    n_mentions: int = 1
    example_phrases: List[str] = field(default_factory=list)

    @property
    def survival(self) -> int:
        return self.last_seen_idx - self.origin_idx


def build_lineages(sequence) -> List[Lineage]:
    lineages: List[Lineage] = []
    next_id = 0
    for verse in sequence.verses:
        if not verse.motifs:
            continue
        phrase_embs = embed(verse.motifs)
        for phrase, emb in zip(verse.motifs, phrase_embs):
            best, best_sim = None, -1.0
            for lin in lineages:
                sim = cosine_sim(lin.centroid, emb)
                if sim > best_sim:
                    best, best_sim = lin, sim
            if best is not None and best_sim >= LINEAGE_SIM:
                best.centroid = (best.centroid * best.n_mentions + emb) / (best.n_mentions + 1)
                best.n_mentions += 1
                best.last_seen_idx = verse.index
                best.example_phrases.append(phrase)
            else:
                lineages.append(
                    Lineage(
                        id=next_id,
                        centroid=emb,
                        origin_idx=verse.index,
                        origin_author=verse.author,
                        last_seen_idx=verse.index,
                        example_phrases=[phrase],
                    )
                )
                next_id += 1
    return lineages


def gravity_gap(lineages: List[Lineage], group_a=("model_A",), group_b=("model_B", "human")):
    """Returns (gap, a_survivals, b_survivals). gap = mean(group_a) - mean(group_b).

    In bulk automated runs (two model personas, no human turn) this is an
    *inter-author dominance imbalance*: whichever persona's motifs happen to
    outlive the other's, regardless of identity. Report it as |gap| (or the
    absolute-value summary in metrics.summarize_condition) -- there is no
    principled "positive means model wins" direction when both authors are
    the model. Under baseline, whichever persona seeds a sticky theme should
    dominate; under full_shikimoku the imbalance should shrink toward 0.

    For the human_session.py transcripts, pass group_a=("model_A",),
    group_b=("human",) to get the literal human-vs-model gap the paper's
    framing is actually about; that's a qualitative/case-study number (small
    n), not the bulk-run statistic.
    """
    a_s = [l.survival for l in lineages if l.origin_author in group_a]
    b_s = [l.survival for l in lineages if l.origin_author in group_b]
    if not a_s or not b_s:
        return None, a_s, b_s
    gap = float(np.mean(a_s) - np.mean(b_s))
    return gap, a_s, b_s
