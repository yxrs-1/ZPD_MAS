# H0 protocol — calibrate over-help before any model

Locked before the scorer is run.

## Question

On a fixed set of decision points, does an error-streak ladder give fewer overly strong scaffolds than a policy that always emits level 2?

## Why this first

The classroom claim needs a ruler: over-help means the chosen level is above the maximum allowed for that moment. Until that ruler distinguishes two non-model policies, there is nothing for a multi-agent system to beat.

## Policies (frozen)

Features available to both policies: `error_streak`, `successes_without_scaffold`, `idle_sec`, `hint_requests`, `events`, `same_error`, `partial_progress`.

**B0 Fixed.** Always level 2.

**B1 Ladder.** Ignore idle, hint counts, whether the error changed, and partial progress.

- If `successes_without_scaffold >= 1` and `error_streak == 0`: level 0
- Else if `error_streak >= 3`: level 4
- Else if `error_streak == 2`: level 3
- Else if `error_streak == 1`: level 2
- Else: level 1

Level text is the template in `code/benchmark.py`. A decision leaks if that text contains `Counter`, `most_common`, or `sorted(`.

## Gold labels

Twelve decisions in `code/traces.json`, written as teaching judgments:

- Independent success allows only level 0.
- A first error allows only a pointer (level 2).
- Two errors with some progress allow a next step, not a fragment (max 3).
- The same error repeated four or more times allows a fragment (level 4).
- No activity, or a long idle with almost no actions, allows no academic prompt (max 0). The teacher would be notified instead. That notification is outside this metric.
- Hint spamming, including hint spamming plus a single error, allows only a metacognitive prompt (max 1).
- Three errors that are not the same error, when the student has already made partial progress, allow at most a next step (max 3).

## Predictions (confirmatory)

1. `overhelp_rate(B1) < overhelp_rate(B0)`.
2. B0 under-helps the repeated-same-error cases, because it cannot rise above 2.
3. B1 still over-helps when the student has stopped, when errors changed but progress exists, and when one error is paired with hint spamming.
4. Leakage is 0 for both, because templates are fixed.

## What this does not show

The labels and the ladder come from the same author. Agreement between B1 and the streak-shaped labels only checks the scorer. The informative gaps are the cases the ladder is forbidden to special-case. No student data, no claim about learning.

## Metric

- Primary: `overhelp_rate` = share of decisions with `level > gold_max`. Lower is better.
- Secondary: `underhelp_rate` (`level < gold_min`), `within_band_rate`.
