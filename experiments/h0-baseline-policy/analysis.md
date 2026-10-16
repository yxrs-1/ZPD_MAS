# H0 analysis

Confirmatory on the locked protocol. Twelve authored decision points, not students.

| Policy | Over-help | Under-help | Within band | Leak |
|---|---:|---:|---:|---:|
| B0 always level 2 | 0.583 | 0.167 | 0.250 | 0 |
| B1 error-streak ladder | 0.333 | 0.000 | 0.667 | 0 |

Predictions:

1. B1 over-help is lower than B0. Held (0.333 < 0.583).
2. B0 under-helps repeated identical errors. Held: `frustrated_same_4` and `frustrated_same_5` stay at level 2 while the rubric requires level 4.
3. B1 still over-helps on the cases it was forbidden to special-case. Held:
   - `disengaged_no_events`, `disengaged_idle`: no academic prompt allowed, ladder emits level 1.
   - `zpd_changed_errors_progress`: errors changed and there is partial progress, max level 3, ladder emits 4 because the streak is 3.
   - `gaming_one_error`: hint spam plus one error, max level 1, ladder emits 2 because it only sees the streak.
4. Leakage is 0. Held. Templates do not contain a full solution.

## What this rules out

A fixed mid-level hint is not a neutral baseline. On this rubric it both talks over students who are already succeeding or have stopped, and stays too weak when the same error repeats.

An error count is also not a student model. It cannot tell “stopped” from “thinking”, or “the error changed and the draft moved forward” from “the same error again”.

## What this does not show

Labels and the ladder were written by the same author. Where the rubric is itself a streak rule, B1 matching it only shows the scorer runs. No classroom, no learning gain. Do not refit a new rule on these same twelve rows and treat the drop in over-help as a new finding.
