# Session Summary: Goal Step 2 — Dated Tier Map and Doc Copies

**Date**: 2026-11-09
**Duration**: ~10 minutes (implement, validate, fix, finalize dispatches)
**Conversation Turns**: ~8 (across the step's dispatches)
**Estimated Cost**: low (markdown doc edits, no code generation)
**Model**: claude-opus-4-8

## Goal Context

- **Condition**: 0.7.2 fixes release, issue #50: the Recommended Tier Map carries a dated 2026-11-09 entry and the `.claude/bpe.local.md.example` and bpe/README.md copies match it.
- **Mode**: step
- **Outcome**: converged (validator verdict clean at iteration 2, zero findings)
- **Turn count**: 3 executor dispatches (implement, fix, finalize) plus 2 validator passes
- **Subagent dispatches**: 3 `bpe:step-executor` invocations plus 2 `bpe:validator` passes
- **Steps completed**: 1 of 1 top-level items in this dispatch (Step 2 of Section 1)

## Key Actions

- Added a `### 2026-11-09` Recommended Tier Map entry to `bpe/references/model-profiles.md`, above the 2026-08-08 history entry: Fable (`claude-fable-5-1`) for brainstorm, plan, retrofit; `opus` for review, apply-review, and the validator; sonnet frontmatter defaults for execution and research; Fable returns in validation only at the final-sweep seat (0.7.3, #52).
- Recorded why: Opus 5.5 proved reliable on bounded work, retiring the 2026-08-08 rollback to pinned Opus 4.8 (#37, #42); the direction is to use Fable less and later.
- Reconciled `.claude/bpe.local.md.example` to the new entry: refreshed the date and comment, swapped the stale `claude-fable-5` ID for `claude-fable-5-1`, and dropped the review/apply-review/validator/step-executor overrides so they ride their opus and sonnet frontmatter defaults.
- Updated the bpe/README.md tier reference to cite `claude-fable-5-1` instead of the stale pins.
- Left the 2026-08-08 history entry intact; the only remaining `claude-opus-4-8` mention lives inside it.
- Checked off Step 2 and its four sub-steps in `todo.md`.
- Final `claude plugin validate ./bpe` exit 0 (one cosmetic ICON_MISSING warning, expected) before commit.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Orchestrator dispatch (mode=implement) | Added the dated tier-map entry, reconciled the two doc copies, checked off Step 2 | Tree dirty, validate green, ready for validation |
| Validator dispatch (iter 1) | Read-only diff review against issue #50 intent and spec fences | Verdict warn: the `.example` personal profile contradicted the new map (stale date, `claude-fable-5` pin, Fable in review/apply-review/validator seats) |
| Orchestrator dispatch (mode=fix, iter 2) | Reconciled the `.example` to the 2026-11-09 map | Tree dirty, tests green, ready for re-validation |
| Validator dispatch (iter 2) | Re-review of the corrected diff | Verdict clean, zero findings |
| Orchestrator dispatch (mode=finalize) | Session summary, commit message, single signed commit, push | Step 2 landed on `release-0.7.2` |

## Efficiency Insights

**What went well:**
- The validator caught the `.example` drift the implement pass missed: the example still cited 2026-07-26 and pinned Fable in seats the new map moved to opus. A grep for `claude-opus-4-8` alone would not have flagged it, because the contradiction was a stale Fable pin plus wrong seats, not an opus pin.

**What could improve:**
- The implement pass should have reconciled the `.example` seats against the new map in one move; it refreshed the model-profiles.md map but left the example's seat assignments contradicting it, which cost a fix iteration.

**Course corrections:**
- Fix iteration 2 dropped the review/apply-review/validator/step-executor overrides from the `.example` so the file states only the Fable spec-shaping seats and leans on frontmatter defaults for the rest, matching the map exactly.

## Process Improvements

- When a dated recommendation changes, reconcile every hand-synced copy's seat assignments against it in the same pass, not just the headline date and model IDs. A copy can carry the right date and still assign the wrong seats.

## Observations

- The `.example` file is the only place the tier map is hand-duplicated; `/bpe:init` (0.7.4, #28) will generate it from a single machine-readable source, which removes the copy that drifted here.
- Fable reaches a seat only through a `bpe.local.md` profile, never through frontmatter, so the shipped frontmatter stays alias-only and portable across accounts; the dated map is advice, not schema.

## Suggested Skills for Next Session

- None required for the next Section 1 item beyond plain markdown and JSON edits; Section 2 (subagent MCP access, #44/#49) is agent-frontmatter and protocol-text work.
