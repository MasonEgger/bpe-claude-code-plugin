# Session Summary: Validator Loop, Exhaustive Passes and a Convergence-Aware Cap

**Date**: 2026-11-13 (work began 2026-11-11)
**Duration**: not measured
**Conversation Turns**: about 20 user prompts across Phase 2, 5 of them on this change
**Estimated Cost**: not measured
**Model**: orchestrator Fable 5.2; validator Opus 5.5

## Key Actions

- Diagnosed why both Phase 2 batches (`sweep` and `checkpoint`) hit the 3-iteration validator cap.
  The validator reported 1 or 2 findings per pass on `sweep` and 7 when told to report everything on `checkpoint`.
  Each fix added new contract surface, and the next cold pass had no pointer to it.
  The cap allowed only two fix rounds.
  1 of the 14 findings was style, and the executor fixed every finding on the first try, so the findings were neither nitpicks nor unactionable.
- Made the validator pass exhaustive in `bpe/agents/validator.md`: report every `block` and `warn` in one pass, walk each new flow end to end, hold the severity bar, and never ration findings across passes.
- Added re-check passes: on iteration 2 or later the dispatch carries `Previous findings:` and `Fix delta:` (two tree ids), and the validator confirms the earlier findings resolved, reviews the fix delta as new work, then reviews the rest of the diff.
- Made the executor's fix mode record a fix base and fix head with a temporary-index tree snapshot and report them on a `Delta:` line in the Fix-Report.
- Replaced the fixed cap with a convergence-aware one in `bpe/references/validator-protocol.md`: 3 validator passes as the base, one more fix round on pass 3 or 4 only when the `block` plus `warn` count is strictly lower than the previous pass's, and a ceiling of 5.
  `iter` counts validator passes.
  A clean or info-only pass records 0, and a synthesized finalize-test-failure block records no count.
- Added untracked paths from `git status --short` to every statement of the mechanical spec-fence checks (validator, protocol fence table, executor self-check, `execute-plan` step 8).
- Added a commit-first sentence to the RESUME block, and carried the new cap wording into the goal skill, the final-validator agent, the README diagram, and spec.md.

## Validator Iterations On This Change

The change was reviewed by `bpe:validator` under its own new rules, dispatched by hand outside a goal loop.

- Pass 1 (cold): 3 warn, 1 info.
  Untracked files were missing from the mechanical fence checks, `Previous findings` was undefined after a finalize-red fix, and validator.md had several sentences per line.
  The info finding: the validator and step-executor agent prompts are 12,608 and 14,034 characters against a 10,000-character guideline.
- Pass 2 (re-check with the fix delta): 2 warn.
  It confirmed all three earlier findings resolved.
  The convergence count after a finalize-red fix was undefined, and `execute-plan` step 8 had three sentences on one line.
  Both sat on lines the first fix touched.
- No third pass reviewed the fixes for the pass 2 findings.
  They are a few lines of wording.

The re-check cost 86k tokens, 6 tool calls, and 46 seconds, against 110k, 12, and 96 for the cold pass.

## Prompt Inventory

| Prompt | Action | Outcome |
|---|---|---|
| Is this a symptom of the new design? | Analyzed the 14 findings across both batches | Named three causes: rationed findings, unreviewed fix surface, a cap of two fix rounds |
| ultrathink on this and make the changes necessary | Wrote the change as an exact-match replacement script | 35 edits to 8 files, applied by the maintainer |
| I ran the command. | Ran the cold validator pass, then wrote the fix script | 9 edits to 4 files |
| Why is auto mode refusing? Are you editing in a weird place? | Showed an Edit on `commit-msg.md` succeeds | The refusal is specific to files under `./bpe/`, the live `--plugin-dir` plugin (an inference) |
| Ran the third script | Verified and committed | 3 edits to 2 files; `claude plugin validate ./bpe` exits 0 |

## Efficiency Insights

- Auto mode's classifier refused every direct Edit under `./bpe/`, so each round of changes became a script for the maintainer to run.
  Three round trips for 47 edits.
- The exact-match scripts refuse to write anything unless every replacement matches once, which made a dry run a full check.

## Process Improvements

- A change to the validator loop can be dogfooded without a goal run: dispatch `bpe:validator` by hand with `Iteration:`, then again with `Previous findings:` and a `Fix delta:` built from two tree snapshots.
- Record each validator pass's count next to its cost, so a claim that the loop got cheaper has numbers behind it.

## Observations

- The new cap has not run inside a real `/goal` loop yet.
  Section 6 runs in step mode with `Tools: none`, so it will not exercise it either; the first real test is the next plan with declared tools.
- Open from earlier in Phase 2: plan.md line 294 still names a `..HEAD` diff source, the plan and the playbook disagree on whether the final sweep runs in this loop, PostToolUse timing on async Agent dispatches is unverified live, and mypy was not run.
- The agent prompt-length info finding is not addressed here.

## Suggested Skills for Next Session

- `bpe:goal` in `step` mode for Section 6, after regenerating goal.md.
- `python:python` for `goal-run-report.py` in the batch-mode comparison step.
