# renga-rules

A testable mechanism, not a metaphor: renga's 14th-century shikimoku
(link-and-shift, uchikoshi non-return, sarikirai recurrence tables, author
rotation, master-scribe arbitration) implemented as constraints on
LLM-generated linked verse, plus instrumentation to measure whether it
actually redistributes thematic control instead of just measuring
instruction compliance.

Thesis: agency in human-LLM co-writing is procedural, not intentional. The
model's thematic gravity, its tendency to have its own motifs outlive and
dominate a collaborator's, is a property of the *governance rules* in
force, not of anyone's stated intentions. Renga is a 700-year-old existence
proof that this can be fixed by constitution rather than willpower.

## What's actually implemented

- `renga/rules.py`: the shikimoku as checkable predicates. `link` (must
  connect to verse n-1), `shift` (must depart from verse n-2, embedding
  level), `uchikoshi` (must not repeat a category from verse n-2, the named
  classical fault), `sarikirai` (per-category minimum recurrence gap),
  `rotation` (no same author twice running). Plus `arbitrary`, an
  equal-instruction-load control rule (a color-word constraint) with no
  thematic-governance function, used to show the effect isn't just "any
  constraint reduces repetition."
- `renga/scribe.py`: the master scribe. Generates a candidate verse, runs
  the active checks for the condition, and on failure hands the model a
  specific rejection reason and asks it to retry (up to 3x, then accepts
  and flags the violation as unresolved).
- `renga/provenance.py`: clusters motif mentions into cross-sequence
  "lineages" (via local sentence-embedding similarity) and computes
  **thematic gravity**, whether one author's motifs systematically outlive
  the other's. This is the metric the project's argument rests on; see
  "Why provenance, not autocorrelation" below.
- `renga/conditions.py`: 8 ablation conditions. `baseline`,
  `rotation_only`, `link_only`, `shift_only`, `uchikoshi_only`,
  `sarikirai_only`, `full_shikimoku`, `arbitrary_control`.
- `renga/metrics.py`: bootstrap CIs, permutation tests, descriptive
  lag-1..5 semantic autocorrelation.
- `scripts/run_experiment.py`: bulk runner. N sequences per condition,
  alternating two model personas (model_A/model_B) so rotation is testable
  without needing a live human for every run.
- `scripts/human_session.py`: interactive real human-LLM co-writing
  session under a chosen condition, producing a transcript for
  qualitative/case-study material.
- `scripts/make_plots.py`: ablation table (CSV), gravity-gap bar chart
  with CIs, autocorrelation curves, permutation-test p-values.
- `scripts/calibrate.py`: prints the natural similarity distribution from
  an unconstrained pilot batch so thresholds get set from data.

## Why provenance, not autocorrelation

Instructing the model "don't return to the verse before last" and then
measuring lag-2 embedding similarity only shows instruction compliance,
not governance. `metrics.semantic_autocorrelation` is kept in the codebase
and the plots for exactly this reason: it is shown explicitly as
**descriptive only**, not the headline result.

The claim that matters is about who steers. `provenance.gravity_gap` tracks
individual motifs across the whole sequence (via embedding-clustered
"lineages") and asks whether one author's introduced material persists and
recurs more than the other's, and whether that gap shrinks under
governance. That is a measurement of control, not of surface variety.

Caveat baked into the code: in bulk automated runs both authors are the
model (two personas, model_A/model_B), so there is no principled "positive
means the model wins" direction. Report the *imbalance magnitude*
(`summarize_condition(..., signed=False)`, the default). The literal
human-vs-model signed gap comes from `human_session.py` transcripts
(`signed=True`, small n, case-study material, not the headline statistic).

## Setup

```bash
pip install -r requirements.txt
export HF_TOKEN=...      # a Read (Read-only) access token from https://huggingface.co/settings/tokens is enough.
                          # This project only calls Inference Providers, it never pushes to the Hub.
```

Generation and motif/category tagging both call
[Qwen2.5-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct) via
HF's hosted Inference Providers by default (`renga/llm.py`), no GPU
needed locally, it is a remote API call billed per request/token like any
other hosted model. Override with `RENGA_MODEL=<hf-repo-id>` to try a
different hosted model, for example to test whether the effect holds
across model pairings.

The first run downloads `all-MiniLM-L6-v2` (sentence-transformers) locally
for constraint-checking embeddings. After that, embedding is offline and
free, so it is safe to call inside the scribe's retry loop.

## Running it

**1. Calibrate thresholds on a cheap pilot before trusting any numbers.**
`LINK_MIN_SIM`, `SHIFT_MAX_SIM` (`renga/rules.py`) and `LINEAGE_SIM`
(`renga/provenance.py`) are cosine-similarity cutoffs chosen as reasonable
starting points, not calibrated against ground truth.

```bash
python scripts/run_experiment.py --pilot --conditions baseline
python scripts/calibrate.py
# Edit renga/rules.py thresholds based on the printed percentiles.
# Re-run the pilot across all conditions, spot-check a few sequences by eye:
# do "link" verses actually read as connected? Do "shift" verses actually
# read as departed? If not, adjust and repeat. This step is what turns
# the mechanism into something defensible; do not skip it.
```

**2. Run the full ablation battery.**

```bash
python scripts/run_experiment.py --n 20 --length 16
# ~8 conditions x 20 sequences x 16 verses x (1 generation + 1 tag-extraction
# call per accepted verse, more per rejection/retry). Budget API calls
# accordingly; start smaller (--n 8) for a cheaper first look.
```

**3. Run at least one real human-LLM session** for case-study material and
to sanity-check that the automated two-persona proxy is not measuring
something degenerate:

```bash
python scripts/human_session.py --condition baseline --length 12
python scripts/human_session.py --condition full_shikimoku --length 12
```

**4. Analyze.**

```bash
python scripts/make_plots.py
# -> results/ablation_table.csv
# -> results/gravity_gap.png
# -> results/autocorrelation.png
# -> prints permutation-test p-values: full_shikimoku vs baseline,
#    full_shikimoku vs arbitrary_control
```

## Writing the paper

Target: the non-archival, 2-6 page, poster-format track whose CFP asks how
friction, slowness, refusal, repetition, and constraint preserve or
transform creative agency. This section is a checklist for turning the
`results/` output into that submission.

**Abstract (150 words).** Lead with the reframe, not the poetry: renga's
shikimoku is a hand-specified decoding constraint from 1372. Uchikoshi is
a lag-2 anti-repetition rule; sarikirai tables are distance-scoped
repetition penalties. State the thesis (agency in collaboration is
procedural, not intentional) and the headline number (thematic gravity
imbalance under `full_shikimoku` vs `baseline`, with the p-value).

**Introduction.** One paragraph on the failure mode (a model's thematic
gravity swallowing human-LLM co-written work), one paragraph on renga as a
700-year-old governance system built for exactly this, one paragraph
stating the mechanism (link-and-shift plus uchikoshi, sarikirai, rotation,
and arbitration) and the falsifiable prediction: imbalance shrinks under
full governance, specifically because of *this* rule set and not any
equal-complexity constraint. That is what `arbitrary_control` is for.

**Method.**
- State plainly that this is a simplified operationalization, not a
  philological reproduction: real sarikirai tables specify exact intervals
  across a 100-verse kasen against a much larger word taxonomy than the 10
  categories used here.
- Describe the master-scribe retry loop and report the rejection rate and
  unresolved-violation rate per condition from the ablation table. This is
  itself a result (how much friction each rule set actually imposes) and
  answers the CFP's framing directly.
- Describe the provenance/lineage method and disclose the
  same-model-both-authors caveat above.
- List all 8 conditions in a table with one-line descriptions, pulled
  straight from `renga/conditions.py:RULE_EXPLANATIONS`.

**Results.**
- Table: `results/ablation_table.csv` (condition x gravity-gap mean and CI
  x rejection rate x unresolved-violation rate).
- Figure 1: `gravity_gap.png`, the headline claim. State the permutation
  p-values from `make_plots.py`'s stdout for `full_shikimoku` vs
  `baseline` and vs `arbitrary_control` explicitly in the caption.
- Figure 2: `autocorrelation.png`, labeled explicitly as descriptive, not
  the causal claim.
- A short paragraph on the individual-rule ablations (`link_only`,
  `shift_only`, `uchikoshi_only`, `sarikirai_only`, `rotation_only`):
  which single rule contributes most of the effect versus which
  combinations require the full rule set.

**Discussion.** This is where the historical argument does its work: 700
years of renga theory (uchikoshi as a *named fault*, not a soft
preference; rotation as structural, not a request; the master scribe as an
enforcement role, not a suggestion) argue that what stopped one voice from
dominating collaborative work was never poets' good intentions. It was
that the form made domination mechanically difficult. Frame the
`arbitrary_control` result as the load-bearing piece of that argument. If
`full_shikimoku` and `arbitrary_control` reduce imbalance equally, the
result is "constraints help," which is not the claim. If `full_shikimoku`
clearly outperforms `arbitrary_control`, the specific link-and-shift
mechanism, not general friction, is doing the work.

**Limitations.** Simplified sarikirai taxonomy; embedding-threshold
calibration is a hyperparameter, not ground truth (cite the calibration
numbers); the bulk condition uses two model personas rather than real
human turns (state the human-session case study as complementary, not
equivalent, evidence); motif-lineage clustering can conflate
distinct-but-lexically-similar themes (spot-check a sample of lineages by
hand and report how many held up).

**Submission checklist.** 2-6 pages, poster format, non-archival: this
means preliminary numbers are fine and expected. Do not over-claim
statistical power that is not there (report exact n_sequences and CIs, do
not round them away). Include 1-2 verse excerpts as figures, a `baseline`
sequence where thematic gravity is visible by eye next to a
`full_shikimoku` sequence where it isn't. A legible textual example next
to the number will do more work than the bar chart alone.
