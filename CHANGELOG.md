# Changelog

Chronological record of every change made while building this project,
with the reasoning behind each one. Useful for writing the paper's Method
and Limitations sections honestly, since a lot of the real work here was
tuning things after seeing them fail, not getting it right on the first try.

## 1. Initial build

Wrote the full project from scratch: the shikimoku rule checks
(`renga/rules.py`), the master scribe retry loop (`renga/scribe.py`), the
8 ablation conditions (`renga/conditions.py`), the motif-lineage /
thematic-gravity tracker (`renga/provenance.py`), stats helpers
(`renga/metrics.py`), the bulk experiment runner and CLI scripts, seed
poems, and a README.

## 2. Fixed a real bug in `gravity_gap` before it ever ran

`provenance.gravity_gap` was originally hardcoded to compare "model"
authors against "human" authors. But the bulk automated runner alternates
two model personas (model_A/model_B) with no human turn at all, so that
comparison would have silently returned nothing (`None`) for every bulk
run. Changed it to compare two configurable groups and, by default, report
the *unsigned* dominance imbalance between the two personas (there's no
principled "model wins" direction when both authors are the model). The
signed, literal human-vs-model version is reserved for `human_session.py`
transcripts specifically.

## 3. Switched the backend from Anthropic to Hugging Face, then back

At the user's request, swapped `renga/llm.py` from the Anthropic SDK to
`huggingface_hub.InferenceClient` targeting `Qwen/Qwen2.5-7B-Instruct` via
HF's hosted Inference Providers (no self-hosting, no GPU needed). Updated
`requirements.txt`, comments in `renga/embeddings.py`, and the README to
match.

Then, per a later request, switched back to the Anthropic SDK
(`claude-sonnet-5`), reverting all of the above.

## 4. Added `.env` support

Created a `.env` file (with a placeholder key) and a `.gitignore` entry
for it, and wired `python-dotenv`'s `load_dotenv()` into `renga/llm.py` so
the API key doesn't need to be exported manually in every shell session.

## 5. README rewrites

The README went through several tone passes based on direct feedback:
removed em dashes throughout, removed the ", not X" rhetorical pattern
(reworded as separate sentences or "instead of" / "rather than"), removed
meta-commentary addressed to "the reviewer" (e.g. "say this before a
reviewer does") in favor of stating things directly, and finally rewritten
in a more casual, first-person voice instead of a polished/formal
register.

## 6. Fixed a crash: `ThinkingBlock` has no `.text`

First real run crashed on `resp.content[0].text`. `claude-sonnet-5` can
return a `ThinkingBlock` as the first content block, not a text block, so
indexing `[0]` directly isn't safe. Fixed `generate_verse` in
`renga/llm.py` to scan `resp.content` for the actual `type == "text"`
block instead of assuming position 0.

## 7. Fixed a second crash: thinking ate the whole token budget

Under `full_shikimoku`, `extract_tags` crashed with "No text block in
response content" (a `ThinkingBlock` with empty thinking and nothing
else). The model was spending its `max_tokens` budget on thinking before
it ever got to emit the JSON tags. Fixed by explicitly passing
`thinking={"type": "disabled"}` on every call (this task needs neither
reasoning nor the extra cost) and raising `max_tokens` a bit for both
`generate_verse` (200 → 300) and `extract_tags` (150 → 200) as headroom.

## 8. Calibrated `LINK_MIN_SIM` and `SHIFT_MAX_SIM` from real pilot data

Ran `scripts/calibrate.py` against a baseline (unconstrained) pilot and
found the initial guesses were badly off:

- Natural lag-1 (adjacent-verse) similarity: mean 0.247, p25 0.149, p75
  0.338. `LINK_MIN_SIM` had been set to 0.35, stricter than even the 75th
  percentile of how connected natural, unconstrained writing ever gets.
  This alone was likely the single biggest cause of rejections.
- Natural lag-2 (verse-before-last) similarity: mean 0.209, p75 0.258.
  `SHIFT_MAX_SIM` had been set to 0.55, far looser than natural, so it was
  barely doing anything.

Updated `LINK_MIN_SIM` to 0.15 and `SHIFT_MAX_SIM` to 0.26 (the naive
25th/75th-percentile picks) in `renga/rules.py`.

## 9. Loosened thresholds again after seeing the calibrated version still fail

Ran a `full_shikimoku` pilot with the step-8 thresholds. Checked all three
generated sequences (not just one, to rule out a single bad seed) and
found the same pattern in every one: 40-46 total rejections per sequence,
and 5-6 of the 7 generated verses (71-86%) landing as
`unresolved_violation: true`, meaning most "accepted" verses had actually
exhausted their retries and were accepted despite still failing a check.

Two causes, both visible directly in the logged rejection reasons:

- **LINK and SHIFT were fighting each other.** Forcing verse n close to
  verse n-1 transitively pulls it closer to verse n-2 as well, so
  satisfying "close to n-1" and "far from n-2" simultaneously is harder
  than the marginal single-lag distributions from step 8 suggested. Most
  SHIFT failures were only marginally over the 0.26 line (0.27-0.35), not
  wildly off. Loosened `SHIFT_MAX_SIM` from 0.26 to 0.33.
- **Sarikirai gaps were too tight for the vocabulary the model actually
  uses.** `solitude` showed up in nearly every verse across all three
  pilot poems regardless of seed (snow, harbor, letter) — it's the
  model's default register for short reflective verse, not something it
  can easily avoid. A 3-verse gap requirement on a category that common
  guarantees frequent rejection. Loosened every entry in
  `SARIKIRAI_MIN_GAP` by one step (e.g. `solitude` 3 → 2, `night` 2 → 1,
  `love` 5 → 4), keeping the same relative ordering (rarer topics like
  love/grief/travel/war still require longer gaps than common ones like
  nature/night).

This is still being verified: the next pilot run will show whether the
loosened thresholds bring the unresolved-violation rate down to something
trustworthy, or whether `MAX_RETRIES` (currently 3, in `renga/scribe.py`)
needs to go up instead of loosening the rules further.

## 10. Found the real bottleneck: too few sarikirai categories, not thresholds

Re-ran the step-9 pilot and checked rejection reasons by type, not just
totals, across all three sequences:

| seed | rejections | unresolved | breakdown |
|---|---|---|---|
| snow | 17 (was 41) | 2/7 (was 5/7) | mostly SARIKIRAI |
| harbor | 48 (was 46) | 6/7 (was 6/7) | SARIKIRAI 24, UCHIKOSHI 20 |
| letter | 51 (was 40) | 6/7 (was 5/7) | SARIKIRAI 24, UCHIKOSHI 20, SHIFT 7 |

The step-9 changes worked exactly as intended: LINK and SHIFT nearly
stopped appearing as failure reasons. But two of three sequences got
*worse* overall, and SARIKIRAI + UCHIKOSHI now account for almost every
rejection. This ruled out "thresholds still too strict" as the
explanation, since the failing checks are categorical (does category X
overlap / has category X recurred too soon), not similarity-based.

Root cause: the fixed category vocabulary only had 10 labels
(`renga/llm.py:TAG_SYSTEM`), and short reflective verse keeps landing on
the same handful of them (`solitude` alone showed up in nearly every verse
across all three step-9 pilots, regardless of seed). With that few
buckets, `uchikoshi` (reject on *any* category overlap two verses back)
and `sarikirai` (minimum gap before reuse) stack on top of each other and
become close to jointly unsatisfiable a few verses into any poem, no
matter how good the writing is. This isn't a tuning problem, it's that
the taxonomy itself is too coarse, something the code already flagged as
a known simplification versus the real (much larger) historical sarikirai
tables.

Two changes:

- Expanded the category list from 10 to 18 (`renga/llm.py:TAG_SYSTEM`):
  added `animals`, `weather`, `domestic`, `sound`, `light`, `food_drink`,
  `work`, `childhood` alongside the original 10. This gives short,
  mundane verse more places to land without repeatedly re-triggering the
  same category. Added matching entries to `SARIKIRAI_MIN_GAP` in
  `renga/rules.py`, at gap=1 (common/light topics) except `childhood`
  (gap=2, treated as a heavier/rarer topic like `dream`/`memory`).
- Bumped `MAX_RETRIES` in `renga/scribe.py` from 3 to 5, as a cheap safety
  net independent of the taxonomy fix, since several verses across the
  pilots needed more than 3 attempts to satisfy every active check
  simultaneously.

Not yet re-verified with a pilot run. If the category expansion doesn't
bring SARIKIRAI/UCHIKOSHI rejections down enough on its own, the next
lever is loosening `uchikoshi` itself (e.g. only fail on a *primary*
category match rather than any overlap) rather than expanding the
taxonomy further, since taxonomy size has diminishing returns and
`uchikoshi` may just be a stricter rule than `sarikirai` by construction.

## 11. Fixed a crash: malformed JSON from the tagging call had no real fallback

Re-running the step-10 pilot crashed the whole run on a `JSONDecodeError`
in `extract_tags`. The model occasionally emits slightly malformed JSON (a
missing comma in this case), and the existing fallback path (re-extracting
the substring between the first `{` and last `}`) still ran `json.loads`
on that same malformed text and raised the identical error unhandled, it
wasn't actually a fallback, just a second attempt that failed the same
way.

Fixed `extract_tags` in `renga/llm.py` to catch the second failure too and
fall back to empty `{"motifs": [], "categories": []}` for that one verse,
with a printed warning so the failure is visible during a run rather than
silently swallowed. This means an occasional verse won't be checked for
uchikoshi/sarikirai violations or counted in a provenance lineage. Worth
tracking how often this fires across the real experiment (grep the run
output for `[llm.extract_tags] WARNING`) and reporting the rate in the
paper rather than assuming it never happens.

## 12. Fixed real data loss: self-corrected tag responses were being discarded

Re-running the step-11 pilot did drop rejection counts significantly (17-28
per sequence, down from 40-51), confirming the taxonomy expansion worked.
But it also printed the new WARNING from step 11 on a case worth looking at
closely: the model second-guessed itself mid-response ("categories":
["nature", "water"], then "Wait, 'water' is not in the fixed list, let me
correct that", then a second, correct JSON object). That's not malformed
JSON, it's two valid objects concatenated, and the model's second object
is exactly the corrected answer we want. The old fallback (grab everything
between the first `{` and the last `}`) spanned both objects and failed to
parse, so the entire verse's tags were being thrown away even though a
perfectly good answer was sitting right there in the response.

Since the tag schema is flat (`{"motifs": [...], "categories": [...]}`,
no nested braces), fixed `extract_tags` in `renga/llm.py` to find every
non-nested `{...}` object in the response with a regex and try parsing
them last-to-first, since a self-correction is always the intended final
answer. Verified against the exact raw text from the warning: it now
correctly extracts `{"motifs": [...], "categories": ["nature"]}` instead
of discarding the verse's tags entirely. The empty-tags fallback and its
warning print are still there for genuinely malformed JSON (e.g. an actual
missing comma), just no longer triggered by this case.

## Why this belongs in the paper

All of section 8-9 is exactly the kind of calibration transparency a
reviewer wants: the thresholds were tuned against data from pilot runs,
not picked to make the headline result come out favorably, and the
specific failure mode (LINK/SHIFT tension, common-category sarikirai
gaps) is itself a small finding about what a short reflective linked-verse
poem's natural vocabulary looks like. Worth a paragraph in Method
("thresholds were calibrated iteratively against pilot data; see appendix
for before/after numbers") and a line in Limitations about the sarikirai
category vocabulary being simplified and skewed toward a few common
labels.
