# H5 protocol — does the H0 ladder transfer to project 2?

Locked before the scorer runs. Decision points are new. The twelve programming-style rows from H0 are not reused.

## Question

If the H0 error-streak ladder is applied unchanged to authored moments from 活动 2.2 and 活动 2.3, does it give a stronger scaffold than the textbook moment allows?

## Policies (frozen)

Features: `activity` (2.2 or 2.3), `unassisted_pass`, `same_check_fails`, `missing_categories`, `copied_recharge_example`, `idle_sec`, `hint_requests`, `events`, `partial_progress`.

**B0 Fixed.** Always level 2.

**B1 Transplanted ladder.** Same rule as H0. It ignores activity, which category is missing, whether the recharge example was copied, idle time, and hint counts.

- If `unassisted_pass` and `same_check_fails == 0`: level 0
- Else if `same_check_fails >= 3`: level 4
- Else if `same_check_fails == 2`: level 3
- Else if `same_check_fails == 1`: level 2
- Else: level 1

Level 4 text may mention one element of 新卡充值. It must not name 网络购票 or 购票平台. Leak if the emitted text contains either of those strings.

## Gold labels

Written as teaching judgments for this book, in `code/traces.json`:

- A passed table with no scaffold allows only level 0, on 2.2 and on 2.3.
- One wrong bin (余额 placed under 硬件) allows only a pointer (level 2).
- Two failures with only 网络 still missing allow a pointer or a next step (max 3), not a worked example.
- The same cell failing four times while the other categories are already filled allows only a pointer (max 2). A worked recharge example is too strong.
- Four failures with nothing filled correctly allow a next step or one worked element (max 4).
- No activity, or a long idle with almost no edits, allows no academic prompt (max 0).
- Hint spamming, including hint spamming plus one failure, allows only a metacognitive prompt (max 1).
- On 活动 2.3, three failures of “this is still the recharge example” allow only a metacognitive prompt (max 1). Another recharge fragment would feed the copy.
- A student who has edited a little and is not yet failing a check allows only level 1.

## Predictions (confirmatory)

1. B1 over-helps when one category is still wrong but the others are filled, because three failures force level 4.
2. B1 over-helps on 活动 2.3 when the copied-recharge check has failed repeatedly, because it answers with another recharge fragment.
3. B1 over-helps when the student has stopped, and when one failure is paired with hint spamming.
4. B0 over-helps finished tables and stopped students, and under-helps the case where nothing is filled and the same check has failed many times.
5. Leakage is 0 for both. Templates do not name the student’s own system.

## What this does not show

Labels are authored. This does not measure learning. It asks whether the previous ladder, left unchanged, respects the project 2 rubric.
