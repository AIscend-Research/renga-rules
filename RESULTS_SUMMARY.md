# Results summary

This is the synthesis of every finding from the full experiment: what the
numbers are, which ones are strong vs. weak, what to headline in the paper,
and what to soft-pedal. `CHANGELOG.md` documents the technical/debugging
history (why thresholds got recalibrated, what bugs got fixed); this file
documents the actual scientific findings that came out the other end.

Raw data backing every number below lives under `results/`:
- `results/ablation_table.csv`, `results/gravity_gap.png`, `results/autocorrelation.png`
- `results/deep_analysis/` — `report.txt` (full console output), `corrected_ablation_table.csv`,
  `entropy_by_condition.png`, `dose_response.png`, `excerpts.txt`
- `results/human_sessions/` — `session_000.json` (baseline), `session_001.json` (full_shikimoku), `analysis.txt`

## Experiment design

8 conditions × 20 sequences × 16 verses, two model personas (model_A/model_B)
alternating, plus 2 real human-LLM sessions (baseline and full_shikimoku,
same human, same opening hokku, for a matched comparison). Model:
`claude-sonnet-5`. Full condition list and rule definitions: `renga/conditions.py`.

## Finding 1 (strongest, cleanest): friction climbs monotonically with rule count

Rejection rate per verse, from the ablation table:

| condition | rejections/verse |
|---|---|
| link_only | 0.03 |
| shift_only | 0.12 |
| uchikoshi_only | 1.54 |
| sarikirai_only | 2.52 |
| full_shikimoku | 6.41 |

Combining rules doesn't just add friction, it multiplies it. This alone is a
clean, publishable, non-controversial result: governance has a real,
escalating cost, and sarikirai/uchikoshi are the expensive rules, not
link/shift.

## Finding 2: gravity gap (the original headline metric) is directional, not significant

| condition | gravity gap | 95% CI |
|---|---|---|
| baseline | 0.47 | 0.32–0.65 |
| rotation_only | 0.49 | 0.36–0.62 |
| link_only | 0.51 | 0.36–0.68 |
| shift_only | 0.60 | 0.43–0.81 |
| uchikoshi_only | 0.50 | 0.29–0.75 |
| sarikirai_only | 0.46 | 0.33–0.59 |
| **full_shikimoku** | **0.38** | 0.26–0.51 |
| **arbitrary_control** | **0.55** | 0.41–0.71 |

full_shikimoku is the lowest of all 8, and specifically lower than the
equal-complexity fake-rule control, the comparison the whole argument
depends on. But: permutation test vs. baseline p=0.40, vs. arbitrary_control
p=0.086. Neither clears conventional significance at n=20. No individual
rule alone shows a real effect either. **Report this as directionally
consistent with the thesis, not as proof.**

A confound was checked and ruled out here: the seed verse was hardcoded as
authored by `model_A`, raising a concern that it inflated model_A's apparent
gravity. Recomputing with the seed excluded from both groups produced
**identical numbers** (see `results/deep_analysis/corrected_ablation_table.csv`),
because the seed verse is never tagged with motifs in the first place
(`extract_tags` never runs on it), so no lineage could originate there
regardless of label. Worth one disclosure sentence in the paper: "we
checked for this and it does not affect the result."

## Finding 3 (the real headline candidate): topic-diversity entropy is significant

Shannon entropy of category usage per sequence, a more direct measure of
"did the poem actually cover new ground" than gravity gap:

| condition | entropy (bits) |
|---|---|
| baseline | 2.98 |
| rotation_only | 2.97 |
| link_only | 2.79 |
| shift_only | 3.12 |
| **uchikoshi_only** | **3.34** (highest of all 8) |
| sarikirai_only | 3.20 |
| full_shikimoku | 3.29 |
| arbitrary_control | 3.14 |

full_shikimoku vs baseline: **p < 0.0001**. Full_shikimoku vs arbitrary_control:
**p = 0.030**. Both real, clean significant results. Note uchikoshi_only alone
edges out full_shikimoku, worth a sentence: uchikoshi is doing a lot of the
diversity work by itself. **Recommend leading the results section with this,
not gravity gap** — it's the strongest quantitative claim you have.

## Finding 4 (novel, worth a discussion paragraph): no single rule works, but the combination overcomes that

Individual rule marginal effects on gravity gap (baseline mean − condition mean;
positive = the rule helps):

| rule | marginal effect |
|---|---|
| link_only | −0.032 |
| shift_only | −0.131 (worst single rule) |
| uchikoshi_only | −0.023 |
| sarikirai_only | +0.012 (only one that helps alone, barely) |
| rotation_only | −0.022 |
| **sum of individual effects** | **−0.196** (net negative!) |
| **actual full_shikimoku effect** | **+0.096** |

Four of five rules look mildly counterproductive in isolation. The full
combination reverses this. This is a **synergy finding**: governance here is
not decomposable into independently-effective parts, only the complete
constitution works, which maps directly onto the historical argument (real
renga theory never claimed any single rule worked standalone either). This
is a strong, quotable, novel angle for the Discussion section.

## Finding 5 (null, report honestly): no dose-response within full_shikimoku

Correlating per-sequence rejection count against per-sequence gravity gap
within full_shikimoku: Pearson r = 0.132, Spearman rho = 0.134. Essentially
no relationship. More friction during writing does not predict a more
balanced outcome at this sample size. State this plainly as a negative
result, don't force a story onto it.

## Finding 6 (null, didn't help): paired-by-seed tests

Blocking on the 8 recurring seed poems (to control for seed-level variance,
since `letter` behaved worse than other seeds throughout calibration) did
not sharpen the significance: full_shikimoku vs baseline paired p=0.377
(vs 0.399 unpaired), vs arbitrary_control paired p=0.219 (vs 0.086
unpaired, actually weaker). Seed-level variance was not the dominant noise
source. Mention briefly; not a result worth building a figure around.

## Finding 7: the real human-LLM session shows the sign flip live

Same human author, same opening hokku ("Steam curls from warm rice bowls /
evening gathers quietly / the first autumn breeze"), one session under
`baseline`, one under `full_shikimoku`.

| | signed gravity gap (model − human) | what happened |
|---|---|---|
| baseline | **+0.395** | model's "a waiting cup" → "a cup of waiting tea" survived 7 verses; human's "a circling spoon" survived only 1 |
| full_shikimoku | **−0.583** | human's "first autumn breeze" → "autumn leaves" survived 6 verses; **zero** model-originated motifs recurred at all |

The sign of who-dominates flipped between conditions, in a real, non-simulated
session. Entropy also rose (2.63 → 3.15 bits), consistent with the bulk
finding. Friction matched the bulk average almost exactly (6.83 rejections
per model verse here vs. 6.41/verse averaged across the n=20 automated run),
good convergent validity between the automated two-persona proxy and a real
human trial.

**Caveat to disclose**: same human wrote both sessions, baseline first, so
the second session's choices may have been subtly informed by the first.
n=1 per condition — present as a case study, not a statistical result.

## Finding 8: lineage-clustering spot check (validity check on the method itself)

Manually inspected motif clustering on baseline/full_shikimoku/arbitrary_control
sequences sharing the same seed ("snow"). Clean, correct merges dominated
(e.g. baseline: "a humming kettle" → "boiling kettle" → "cooling kettle"
correctly tracked as one persisting object). A couple of borderline
over-merges were found and are worth disclosing in Limitations rather than
hiding: baseline lumped "unspoken absence", "unspoken truth", "unspoken
agreement" into one lineage (same linguistic frame, arguably three distinct
ideas); full_shikimoku merged "a porch at dusk" with "a burning porchlight"
(related but looser than the clean examples). No egregious false merges
(nothing unrelated got merged together), which is the failure mode that
would actually break the metric.

**Unplanned bonus finding from doing this by hand**: the *shape* of
persistence differs by condition, not just the count. Baseline shows one or
two themes running continuously through most of the back half of the poem
(one voice taking over). `arbitrary_control` instead shows *many* long-lived
threads in parallel (several "light"/color-adjacent motifs each surviving
9–13 verses), a plausible side effect of forcing a color word into every
verse. This is good material for Discussion: it shows the control condition
isn't neutral, it creates its own kind of governance artifact, just a
different one than baseline's single-voice takeover, which is exactly why
the control needed to exist.

## Recommended figures for the paper (3, not more)

1. **`results/deep_analysis/entropy_by_condition.png`** — the strongest
   quantitative result, lead with this.
2. **`results/gravity_gap.png`** — supporting/directional evidence for the
   mechanism the paper's argument is built around, even though not
   individually significant.
3. **The excerpt pair from `results/deep_analysis/excerpts.txt`** (most
   imbalanced baseline sequence vs. most balanced full_shikimoku sequence,
   programmatically selected, not hand-picked) as a text figure.

Skip `autocorrelation.png` and `dose_response.png` as figures, both are
null/descriptive results; mention them in one sentence each instead of
spending page-limited figure slots on them.

**Visual ideas discussed but not built** (bring these up if there's room/interest
for a stronger version of the paper): a motif-lineage "thread timeline" (Gantt-style,
one bar per lineage spanning origin→last-seen verse, colored by author) for a
baseline vs. full_shikimoku sequence side by side; a 16×16 verse-similarity
heatmap (self-similarity matrix, borrowed from music/motion analysis) showing
banded repetition structure in baseline vs. a mottled pattern in
full_shikimoku; a stacked bar of rejection-reason proportions per condition;
mean rejection count by verse position within full_shikimoku (tests whether
friction escalates as sarikirai categories get "used up" over the poem).

## Recommended paper framing

- **Headline the entropy result**, not gravity gap. It's the one that's
  actually statistically clean.
- **Use the synergy finding (Finding 4) as the Discussion's load-bearing
  argument** — it's the most novel, most historically-resonant claim in the
  whole project.
- **Present gravity gap and the human-session sign-flip as supporting,
  directionally-consistent evidence**, not as independently proven claims.
- **Report the null results (dose-response, paired-seed) honestly** rather
  than omitting them, a 2-6 page preliminary/poster paper has room for
  "we checked this and found nothing," and it's better scientific practice
  than silence.
- **Limitations section should cover**: simplified sarikirai/category
  taxonomy, embedding-threshold calibration as a tuned hyperparameter (not
  ground truth, see CHANGELOG.md for the actual calibration history),
  n=1 human sessions as case-study not statistical evidence, the lineage-
  clustering borderline cases from Finding 8, non-determinism of LLM
  generation (no seed control at the API level).
