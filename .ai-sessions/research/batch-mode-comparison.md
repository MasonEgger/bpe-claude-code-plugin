# Batch-Mode Comparison: Phase 2 Against the 0.7.2 Baseline

Measured 2026-11-13 for the 0.7.3 release (#51 acceptance).
Plan: `plan.md`, Sections 4 and 5 run as batches `sweep` and `checkpoint`; Section 6 is this note and the version bump.
Models as the script reported them: Phase 2 ran `claude-sonnet-5-5` for every executor dispatch and `claude-opus-5-5` for every validator dispatch.
The 0.7.2 baseline ran `claude-opus-4-8` and `claude-fable-5` (see `.ai-sessions/research/baseline-0.7.2-goal-run.md`).
The profiles differ, so minutes and token counts are not model-for-model comparable.

Script: `bpe/scripts/goal-run-report.py <phase-2 transcript> --since 2026-11-11T17:32:31Z --until 2026-11-13T21:30:00Z`.
The `--until` bound is the moment the note was first measured (after the release implement dispatch, before its finalize), so the later final-sweep dispatches in the same transcript stay out.
That start is the Section 3 commit `e4c07ef` (2026-11-11T11:32:31-06:00).
Goal dispatches began at 12:38:35 CST (18:38:35Z).
The dispatch tables are identical for both starts: 17 subagent dispatches, 19.3 minutes, 22.9M subagent cache-read tokens.
Only the orchestrator row moves: 358 turns and 63.9M cache-read from the commit, 312 turns and 60.8M cache-read from 12:38:35.
That is a 5 percent difference in cache-read, so the plan's git-derived start is used below.

## What The Span Contains

Phase 2 did not run as one clean loop, so the span total overstates the batch loops.

- Loop 1, batch `sweep` (Section 4, 2 steps): ran from 18:38:35Z (12:38 CST) and hit the 3-iteration validator cap at about 12:45 CST.
  It was finished by hand and committed as `d1afbc9`.
- Loop 2, batch `checkpoint` (Section 5, 3 steps): ran 13:18:35 to 13:32:01 CST, also hit the cap, and got a fourth fix pass outside the loop (`44d06c8`).
- Hand-run work in the same session, not loop cost: the validator-loop redesign (`3827949`) with two hand-dispatched `bpe:validator` passes, and this Section 6 implement dispatch.
  This dispatch also runs inside the span it measures, so its own cost is partly counted (0.8 minutes of subagent time, and none of its finalize).

The script separates the two loop windows with `--since` and `--until`.
Rows in "Loop Windows" below are those two windows added together.
The checkpoint tail (fix pass 3 and the finalize at about 13:58 CST) falls outside the window and is not in that column.

## Comparison

Per-step values divide by 12 for the baseline and by 5 for Phase 2 (Section 4 has 2 steps and Section 5 has 3; both Section 6 steps were unchecked when this ran).

| Measure | 0.7.2 baseline | Phase 2 whole span | Phase 2 loop windows | Baseline per step | Phase 2 span per step | Phase 2 loops per step |
|---|---|---|---|---|---|---|
| Dispatches | 42 | 17 | 12 | 3.5 | 3.4 | 2.4 |
| Subagent minutes | 88.8 | 19.3 | 15.2 | 7.4 | 3.9 | 3.0 |
| Subagent cache-read tokens | 76.8M | 22.9M | 17.9M | 6.4M | 4.6M | 3.6M |
| Orchestrator turns | 283 | 358 | 83 | 23.6 | 71.6 | 16.6 |
| Orchestrator cache-read tokens | 108.7M | 63.9M | 14.0M | 9.1M | 12.8M | 2.8M |

Phase 2 whole-span subagent minutes split as 3.4 implement, 13.1 validator, 2.0 fix, and 0.8 finalize.
The baseline split was 30.6 implement, 30.2 validator, 4.2 fix, 23.7 finalize.

### Warn Rate Per First-Pass Validation

| Run | First-pass validations | Warn verdicts | Block verdicts | Clean |
|---|---|---|---|---|
| 0.7.2 baseline | 10 | 4 | 0 | 6 |
| Phase 2 batch run | 2 | 0 | 2 | 0 |

Phase 2 first passes, from the two session summaries:

- `sweep` pass 1: 1 block (the sweep diff source compared commits only, so an uncommitted fix was invisible to the re-check).
  Later passes: 1 warn and 1 info, then 1 block and 1 warn at the cap.
- `checkpoint` pass 1: 4 block and 3 warn.
  Later passes: 2 warn, then 1 block (`contract.reset-safety`) at the cap.

## Cap Trips

Both batches hit the 3-iteration cap with findings still open.
The diagnosis and the loop change (exhaustive passes, re-check passes with a fix delta, and a convergence-aware cap) are in `.ai-sessions/session-20261113-1523-validator-loop-convergence.md`.
The convergence-aware cap has not yet run in a real goal loop, so no number here reflects it.

## What The Numbers Show

Batch mode cut the dispatch count per step slightly (3.4 against 3.5 over the whole span, 2.4 in the loop windows) and cut subagent cache-read per step by 28 percent over the whole span (4.6M against 6.4M) and 44 percent in the loop windows (3.6M), mostly because finalize and fix were warm continuations.
The orchestrator figures for the loop windows are far lower per step (2.8M against 9.1M cache-read) than the baseline, but the whole-span figure is higher because it includes the hand-run redesign and unrelated session turns, so neither orchestrator column is a clean measure of the loop.
Quality did not hold up in this run: both first passes returned block verdicts, against 0 blocks in 10 baseline first passes, and both batches hit the cap.

What the numbers cannot show:

- Recomputed 2026-11-22 with the fixed `goal-run-report.py`, which attributes SendMessage continuation usage to the turns inside each continuation's own window; the 2026-11-13 figures left the 5 fix rows and the finalize row at 0 minutes and 0 tokens.
- The plan content differs: Phase 2 steps edited protocol and agent prose and Python scripts, the baseline steps were 12 Task-shape fixes.
- The models differ between runs, as noted in the header.
- Dispatch minutes are first to last timestamp inside the dispatch's own window, so idle time between a dispatch and its next continuation is not counted; the checkpoint implement dispatch now reads 1.7 minutes (the 2026-11-13 table read 41.7 because its file also held the later continuations).
- No final sweep ran in this loop, because the Phase 2 goal.md was rendered before Section 4 landed.
- Only 2 first-pass validations exist, so the warn and block rates carry far less weight than the baseline's 10.
- Dispatch start times in the script table are HH:MM UTC with no date, which is why the last three rows (2026-11-13) look out of order.
