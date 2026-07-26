# Session Summary: Codify the Model Tier Map and Spec /bpe:init

**Date**: 2026-07-26
**Duration**: ~30 minutes (post-Opus-5-research codification)
**Conversation Turns**: ~3 touching this repo
**Estimated Cost**: low (edits only; the research ran earlier via two web subagents)
**Model**: claude-fable-5

## Key Actions

- Refreshed `.claude/bpe.local.md.example` from the stale claude-opus-4-7 pins to the 2026-07-26 tier map: Fable 5 for spec-shaping skills (brainstorm, retrofit, plan, review, apply-review) and the validator; Opus 5 for execute-plan and the step-executor; the sonnet alias for cheap-research; work profile alias-only.
- Added a dated "Recommended Tier Map" section to `bpe/references/model-profiles.md`: the role-by-role table with rationale, plus three recorded caveats (the instruction-following meme did not survive the research pass; official over-verification and scope-widening warnings for Opus 5; no independent long-horizon head-to-head yet). The section states its own maintenance rule: a stale date is a defect, and the example file mirrors it.
- Updated `bpe/README.md`'s profile quick-start to point at the tier map and use current model IDs in its example.
- Appended a `/bpe:init` work package to spec.md per Mason's request ("I don't want this silently fixed I want it codified"): interactive profile setup (AskUserQuestion per role group, defaults from the tier map read at runtime) plus repo pre-flight setup (everything /bpe:goal refuses on becomes an init fix), with four proposed design decisions marked confirm-at-review and a verification plan.
- Mason's live `~/.claude/bpe.local.md` was written earlier in the session (user-local, uncommitted by design) and matches the example.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "Set this up in the repo, with a readme? Should we have /bpe:init? I want it codified" | Example + docs refresh, README pointer, /bpe:init specced | This branch |

## Efficiency Insights

**What went well:**
- The tier recommendation ships with its evidence caveats attached, so a future reader knows what was known and unknown at adoption time.

**What could improve:**
- The example file and the tier-map section carry the same values in two places; init's read-the-map-at-runtime decision is the long-term fix, but until then both need touching together.

**Course corrections:**
- none

## Observations

- The old example pinned claude-opus-4-7, a model two generations stale: exactly the silent-drift class Mason objected to, and the reason the tier map now carries a date and a maintenance rule.

## Suggested Skills for Next Session

- plugin-dev:skill-development — when /bpe:init gets planned and built
- skill-creator:skill-creator — its triggering eval
