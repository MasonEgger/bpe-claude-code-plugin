# Session Summary: Stale Model IDs in Doc Examples

**Date**: 2026-08-03
**Duration**: ~15 minutes (bpe-repo slice of a longer session)
**Conversation Turns**: 2 in this slice
**Estimated Cost**: low; grep sweeps plus an 11-line sed edit
**Model**: claude-fable-5

## Key Actions

- Swept both marketplace repos and the live `~/.claude` config for pinned model IDs after Mason asked whether any skills still ran old Opus or Haiku models.
- Confirmed no functional pins exist: all skill and agent frontmatter uses family aliases (`opus`, `sonnet`, `haiku`), which auto-resolve to the newest release, and Mason's `bpe.local.md` personal profile pins `claude-fable-5` / `claude-opus-5` per the tier map.
- Found the only stale strings were documentation examples: `claude-opus-4-7` in `bpe/references/model-profiles.md` (schema note plus canonical example), `bpe/hooks/profile-check.md` (end-to-end check), and `spec.md` (Goal 11 example and verification), plus one `claude-sonnet-4-6` in spec.md.
- Replaced them with `claude-fable-5` / `claude-sonnet-5` on branch `doc-model-ids`, keeping model-profiles.md's example matching spec.md's as its intro sentence claims.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "Are any of the skills in here using old Opus 4.8 or Haiku 4.5 models?" | Grep swept both repos' md/json/py plus live config for model IDs | No functional pins; doc examples fixed on a branch |

## Efficiency Insights

**What went well:**
- The alias-in-frontmatter, pin-in-profile design adopted with the tier map meant the model generation change required zero functional edits.

**What could improve:**
- The tier-map session updated recommendations but left the schema examples on the prior generation's IDs; example blocks should have been part of that sweep.

## Process Improvements

- When a model generation ships, grep the repo for dated model IDs (`claude-[a-z]*-[0-9]`) in addition to updating the Recommended Tier Map; examples drift separately from recommendations.

## Observations

- spec.md's example commented `claude-opus-4-7` as "explicit Fable model ID", a leftover from when that ID was the frontier pin; the comment now reads "explicit model ID" so it survives future generations.

## Suggested Skills for Next Session

- None; the likely next bpe-repo work (`/bpe:init`, issue #28) starts from its own spec via the BPE flow.
