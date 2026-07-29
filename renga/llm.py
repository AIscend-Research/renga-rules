"""Thin wrapper around the Claude API for the two LLM-side jobs in this pipeline:

1. generate_verse  -- write the next stanza given context + active constraints
2. extract_tags    -- pull out short motif/theme labels and sarikirai
                      categories for a verse, as structured JSON

Everything else (whether a candidate verse actually satisfies a constraint)
is decided by rules.py using embeddings, not by asking the model to grade
its own homework.
"""
from __future__ import annotations

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()  # reads .env in the repo root if present; real env vars still take precedence

DEFAULT_MODEL = os.environ.get("RENGA_MODEL", "claude-sonnet-5")

_client = None


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def generate_verse(system: str, user: str, model: str = DEFAULT_MODEL, max_tokens: int = 300) -> str:
    resp = client().messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
        thinking={"type": "disabled"},  # this task needs neither reasoning nor its token cost
    )
    # resp.content[0] isn't guaranteed to be the text block -- some models emit a
    # ThinkingBlock (or other block types) first, so find the actual text block.
    for block in resp.content:
        if block.type == "text":
            return block.text.strip()
    raise ValueError(f"No text block in response content: {resp.content}")


TAG_SYSTEM = """You are a literary annotator. Given a short poem stanza, extract:
- "motifs": 2-4 short noun-phrase labels for the concrete images/themes present
  (e.g. "falling snow", "a lover's silence", "a distant bell"). Lowercase, no punctuation.
- "categories": 0-3 labels drawn ONLY from this fixed list, whichever apply:
  ["love", "travel", "grief", "dream", "night", "nature", "animals", "weather",
   "season_change", "war", "memory", "solitude", "domestic", "sound", "light",
   "food_drink", "work", "childhood"]

Return ONLY valid JSON: {"motifs": [...], "categories": [...]}. No commentary."""


def extract_tags(verse_text: str, model: str = DEFAULT_MODEL) -> dict:
    raw = generate_verse(TAG_SYSTEM, verse_text, model=model, max_tokens=200)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[-1] if raw.lower().startswith("json") else raw
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        try:
            data = json.loads(raw[start : end + 1]) if start != -1 and end != -1 else {}
        except json.JSONDecodeError:
            # the model occasionally emits slightly malformed JSON (a missing comma,
            # a stray line). Not worth crashing an entire multi-hour run over one bad
            # tag-extraction call -- fall back to empty tags for this verse. This does
            # mean that verse won't be checked for uchikoshi/sarikirai violations or
            # counted in provenance lineages, which is a small, rare source of noise
            # worth disclosing rather than silently absorbing.
            print(f"[llm.extract_tags] WARNING: unparseable tag response, falling back to empty tags. Raw: {raw!r}")
            data = {}
    data.setdefault("motifs", [])
    data.setdefault("categories", [])
    return data
