# Session Summary: Roll the Executor Tier Back to Opus 4.8

**Date**: 2026-08-08
**Duration**: short (cross-repo tier change)
**Conversation Turns**: 1 for this slice
**Estimated Cost**: low
**Model**: claude-opus-4-8 (session), editing bpe tier docs

## Key Actions

- Mason's call: Opus 5 underperformed in lived use ("trash"); revert the executor tier to Opus 4.8 everywhere it was pinned.
- Live `~/.claude/bpe.local.md` (user-local, not version-controlled): personal profile `execute-plan` and `step-executor` changed from `claude-opus-5` to `claude-opus-4-8`; the Notes section rewritten to record the rollback and why (the 2026-07-26 caveats proved out).
- Tier map `bpe/references/model-profiles.md`: the dated section re-dated to 2026-08-08, executor row changed to `claude-opus-4-8` with the rollback rationale, caveats reframed from "re-test later" to "proved out in use".
- `.claude/bpe.local.md.example`: `execute-plan` and `step-executor` lines updated to match; the Opus-5-specific comment dropped.
- Fable 5 pins (spec-shaping, validator) and the sonnet cheap-research line left untouched; only the Opus tier moved.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "reset the tier map and bpe.local.md to opus 4.8. opus 5 is trash" | Live profile edited immediately; tier map + example reverted on a branch | Live change active; PR opened for the repo docs |

## Efficiency Insights

**What went well:**
- The live user-local file was edited first, so Mason's actual runs stopped using Opus 5 immediately, independent of the PR's merge timing.
- Kept the tier-map edit surgical (re-date + one row + caveats) rather than restructuring, to minimize conflict with the open cheap-research PR #35, which edits the same file.

**What could improve:**
- The 2026-07-26 adoption should have set a firmer revisit date; "revisit in a few weeks" let a known-risky pin ride longer than the evidence warranted.

## Observations

- The dated-tier-map convention worked as designed: the adoption block carried explicit caveats, so the rollback is a checklist confirmation rather than a fresh investigation.
- PR #35 (cheap-research sonnet default) and this PR both touch `model-profiles.md` and the example; whichever merges second needs a trivial rebase.

## Suggested Skills for Next Session

- None; the next bpe-repo work (`/bpe:init`, issue #28) starts from its own spec.
