# renga-rules

This project tries to answer a weird question: can a 700 year old Japanese
poetry rulebook fix a modern AI writing problem?

The problem: when a human and an LLM write something together, the model's
ideas slowly take over the piece. Even if nobody means for that to happen.
My guess is that this isn't about the model's "intentions" at all, it's
about whether there are actual rules stopping it. So I went looking for a
historical example of people solving exactly this problem and found renga
(Japanese linked verse poetry), which had a whole rulebook (shikimoku) for
keeping group-written poems from getting hijacked by one voice: verses had
to connect to the one right before them, but weren't allowed to circle back
to the theme from two verses ago, certain topics could only come back after
enough verses had passed, nobody could write two verses in a row, and a
head poet enforced all of it.

This repo turns that rulebook into actual code that constrains an LLM
while it writes linked verse with another author (another model persona,
or a real human), and measures whether it actually stops one side from
dominating the poem, instead of just whether the poem "looks" more varied
on the surface.

## The idea, basically

If you tell a model "don't repeat the topic from two verses ago" and then
just check if it repeated the topic, all you've shown is that it followed
an instruction. That's not the interesting claim. The interesting claim is
about who ends up controlling the poem: do the model's own ideas keep
coming back and sticking around longer than the other author's ideas do?
That's what I'm calling "thematic gravity," and it's the actual thing this
project measures.

## What's in here

- `renga/rules.py` — the shikimoku rules as actual code checks: `link`
  (has to connect to the verse right before it), `shift` (has to move away
  from the verse two back), `uchikoshi` (can't repeat a topic category from
  two verses back, this was a named foul in real renga), `sarikirai`
  (certain topics need a minimum gap before they can come back),
  `rotation` (same author can't go twice in a row). There's also
  `arbitrary`, a fake rule (has to use exactly one color word) that's just
  as complicated to follow but has nothing to do with themes. That's the
  control group.
- `renga/scribe.py` — this is the "head poet." It generates a verse, checks
  it against whatever rules are turned on, and if it breaks one, tells the
  model why and makes it try again (up to 3 times).
- `renga/provenance.py` — tracks individual ideas/motifs across the whole
  poem and figures out which author started each one and how long it kept
  showing up. This is where the thematic gravity number comes from.
- `renga/conditions.py` — the 8 test setups: no rules at all, each rule by
  itself, all the rules together, and the fake control rule.
- `renga/metrics.py` — stats stuff: confidence intervals, significance
  tests, plus a similarity-over-distance chart that's just there to show
  the shape of things. It doesn't prove anything by itself.
- `scripts/run_experiment.py` — runs a bunch of poems automatically, using
  two model personas so you don't need an actual human sitting there for
  every single run.
- `scripts/human_session.py` — lets you actually sit down and write verses
  back and forth with the model yourself. Good for getting a real example
  to put in the paper.
- `scripts/make_plots.py` — turns all the saved poems into a results table
  and some charts.
- `scripts/calibrate.py` — helps you figure out reasonable similarity
  thresholds instead of guessing.

## Why I'm not just measuring "did it repeat itself less"

Worth spelling out because it's the easiest way this project could go
wrong. If I tell the model "don't return to two verses ago" and then
measure whether it returned to two verses ago, I've basically just checked
that it obeyed me. That's not a finding, that's a compliance test.

So instead of only measuring repetition, `provenance.py` follows individual
motifs across the entire poem (using sentence embeddings to cluster
"snow falling" and "the snow kept falling" as the same idea) and tracks
which author started each idea and how long it stuck around. If the
model's ideas consistently outlive the other author's ideas, that's
thematic gravity. If the rules actually work, that gap should shrink.

One thing to be upfront about: in the automated bulk runs, both "authors"
are the same model wearing two different personas, so there's no real
human to compare against. That version measures which persona ends up
dominating, whichever one it happens to be. It isn't really "model vs
human." The actual human vs. model comparison only comes from real
sessions run through `human_session.py`, and there won't be a ton of
those, so treat them as a small supporting example instead of the main
result.

## Setup

```bash
pip install -r requirements.txt
```

You'll need an Anthropic API key in your `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get one from https://console.anthropic.com. This is a paid API, billed
per token, there's no ongoing free tier beyond whatever trial credit a
new account gets.

By default it uses `claude-sonnet-5`, no GPU needed on your end, it's just
an API call. You can swap models with `RENGA_MODEL=<other-claude-model>` if
you want to use something cheaper (like a Haiku model) for cheap bulk
testing before spending more on the final run.

The first time you run anything, it'll also download a small local
embedding model (`all-MiniLM-L6-v2`) for comparing verses to each other.
That one's free and runs offline after the first download.

## How to actually run this

**Step 1: cheap test run first.** Don't run the whole thing blind, the
similarity thresholds in `renga/rules.py` are just guesses right now.

```bash
python scripts/run_experiment.py --pilot --conditions baseline
python scripts/calibrate.py
```

Look at what it prints, adjust `LINK_MIN_SIM` / `SHIFT_MAX_SIM` in
`renga/rules.py` if the numbers look off, and maybe read a couple of the
generated poems yourself to make sure "linked" verses actually read as
linked and "shifted" verses actually read as different. Skipping this step
is how you end up with numbers that don't mean anything.

**Step 2: run everything.**

```bash
python scripts/run_experiment.py --n 20 --length 16
```

This calls the API a lot (roughly 8 setups x 20 poems x 16 verses, times 2
calls per verse, plus retries), so maybe start smaller (`--n 8`) if you're
worried about cost or time.

**Step 3: do at least one real human session.**

```bash
python scripts/human_session.py --condition baseline --length 12
python scripts/human_session.py --condition full_shikimoku --length 12
```

**Step 4: make the charts and table.**

```bash
python scripts/make_plots.py
```

This spits out `results/ablation_table.csv`, `results/gravity_gap.png`,
`results/autocorrelation.png`, and prints p-values comparing
`full_shikimoku` against `baseline` and against the fake `arbitrary_control`
rule.

## Turning this into an actual paper

This fits the kind of track where you submit a short (2-6 page) poster
paper about how constraints and rules shape creative work with AI. Here's
roughly how I'd lay it out:

**Abstract.** Open with the historical hook, renga's rulebook is basically
a 650-year-old set of decoding constraints (uchikoshi = don't repeat what
happened 2 steps ago, sarikirai = topics need cooldowns before they can
come back). Then say the actual claim: agency in human-AI collaboration comes down to
the rules in place more than anyone's intentions. Then give the one
headline number: how much the thematic gravity gap shrinks under the full
rule set vs. no rules, with the p-value.

**Intro.** Explain the problem (models slowly taking over collaborative
writing), bring in renga as an existing solution to basically the same
problem, and state the prediction clearly: the gap should shrink under the
full rules, and specifically because of these rules rather than because
any random constraint would do the same thing (that's what the fake
`arbitrary_control` condition is for).

**Method section.**
- Be upfront that this is a simplified version of the real rules rather
  than an exact historical recreation. The real sarikirai tables are way more
  detailed than the 10 categories used here.
- Explain the retry loop and report how often verses got rejected per
  condition, that's an interesting number on its own (how much friction
  each rule set actually creates).
- Explain how the motif tracking works and mention the two-model-persona
  caveat from above.
- Table listing all 8 conditions with a one-line description each (you can
  basically copy these from `renga/conditions.py`).

**Results.**
- The main table from `results/ablation_table.csv`.
- The gravity gap bar chart as your main figure, with the p-values in the
  caption.
- The autocorrelation chart as a secondary, clearly-labeled-as-descriptive
  figure. It isn't a proof of anything on its own.
- A paragraph on which individual rule (link, shift, uchikoshi, sarikirai,
  rotation) seems to matter most on its own vs. needing all of them
  together.

**Discussion.** This is where the historical angle actually earns its
place: renga didn't rely on poets being polite or well-intentioned, it
made domination structurally hard to do. The important comparison here is
`full_shikimoku` vs. `arbitrary_control`. If both reduce the imbalance
about the same amount, all you've shown is "constraints help," which isn't
really the point. If `full_shikimoku` clearly beats the fake rule, that's
evidence it's specifically link-and-shift-style governance doing the work,
not just friction in general.

**Limitations.** Say plainly: simplified topic categories, thresholds that
were tuned by hand rather than from ground truth, the two-persona proxy
standing in for a real human in most of the data, and that motif matching
can occasionally group things together that aren't really the same idea
(worth spot-checking a handful by hand and reporting how many held up).

**Before submitting.** It's a short, non-archival, poster-style
submission, so preliminary results are completely fine, just don't
overstate how confident the numbers are (report your actual sample sizes
and confidence intervals, don't round anything away). Also throw in one or
two real verse excerpts as a figure, like a baseline poem where one voice
clearly took over sitting next to a full-rules poem where it didn't. That
kind of concrete example will land better with readers than the bar chart
alone.
