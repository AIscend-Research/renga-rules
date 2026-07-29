"""Local sentence embeddings used for constraint-checking and provenance tracking.

Kept separate from the HF Inference API calls in llm.py on purpose: rule
*enforcement* (link/shift/uchikoshi thresholds) needs to run many times per
verse during the scribe's retry loop, and doing that with cheap local
embeddings keeps the API cost and latency in generation only. Motif
*labels* still come from the hosted model (see llm.extract_tags) because
free-text theme extraction is not something a small embedding model can
do; but once we have the labels we embed them locally for lineage
clustering (see provenance.py).
"""
from __future__ import annotations

import numpy as np

_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def embed(texts):
    """texts: str or list[str] -> np.ndarray of shape (n, d), L2-normalized."""
    single = isinstance(texts, str)
    if single:
        texts = [texts]
    vecs = _model().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    vecs = np.asarray(vecs)
    return vecs[0] if single else vecs


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    a = a / (np.linalg.norm(a) + 1e-8)
    b = b / (np.linalg.norm(b) + 1e-8)
    return float(np.dot(a, b))
