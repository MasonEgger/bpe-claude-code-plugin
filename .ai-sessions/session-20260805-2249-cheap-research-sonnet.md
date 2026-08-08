# Session Summary: Align cheap-research Shipped Default With the Tier Map

**Date**: 2026-08-05
**Duration**: ~30 minutes
**Conversation Turns**: 4 in this segment
**Estimated Cost**: ~$3 (Opus 5, ~20 tool calls)
**Model**: Opus 5 (`claude-opus-5[1m]`)

## Key Actions

- Audited every skill and agent for pre-5 models. Found none: all 13 skills and 3 agents use family aliases, which resolve to the newest release per family, so `opus` is already Opus 5 and `sonnet` is already Sonnet 5.
- Corrected the premise that Haiku 4.5 is outdated. There is no Haiku 5; 4.5 is the current Haiku, so `haiku` was already latest-in-family.
- Identified the one component that could move onto a 5-family model: `cheap-research`, shipping `model: haiku` while the dated tier map has recommended `sonnet` since 2026-07-26.
- Changed the frontmatter default to `sonnet` and updated the five documents that state that tier, including the Goal 11 acceptance criterion at `spec.md:503`, which asserted the old trio and would otherwise have contradicted the code.
- Declined to pin explicit model IDs in frontmatter. Pinning would not change which model runs today and would remove the auto-upgrade the work profile depends on.
- Rebased onto `main` after PR #34 merged mid-segment, confirming no conflict between its doc-example edits and this tier change.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "Are any of the skills using old Opus 4.8 or Haiku 4.5?" | Extracted every model field; checked pinned IDs across the repo | No pre-5 models in use; Haiku 4.5 premise corrected |
| "update every skill to the latest model of that class" | Explained aliases already do this; found and fixed the one real gap | `cheap-research` moved to sonnet |
| "didnt i just solve this with a different pr?" | Diffed PR #34; confirmed it changed zero model fields | Two changes disambiguated |
| "check whats been merged on main and see if these changes are still relevant" | Swept main, PRs, branches, worktrees; then checked user-local state | Found the override in `~/.claude/bpe.local.md` |
| "ship it" | Committed and opened the PR | |

## Efficiency Insights

**What went well:**

- Reading the model catalog before answering prevented a wrong answer. The prompt assumed Haiku 4.5 was stale; it is the current Haiku, and treating the question as a simple yes would have produced a pointless migration.
- Checking `~/.claude/bpe.local.md` when the repo showed no other changes is what actually resolved the question. Everything in git said the change was needed; the user-local override said their own environment had been correct for over a week. Both were true, and only checking outside git surfaced the distinction.
- Basing the branch on `main` rather than stacking on the open `doc-model-ids` branch kept the tier change reviewable on its own. The two touched the same files but different lines, and the later rebase was clean.

**What could improve:**

- Raising the doc-example drift and the tier drift in one answer led directly to the "didn't I just solve this?" confusion. Two unrelated findings in one response read as one task; they should have been separated when first reported.
- The first branch attempt was cut from `doc-model-ids` because the working branch was not checked before running `checkout -b`. Cheap to fix, but confirming the current branch is part of branching, not a follow-up.

**Course corrections:**

- Started toward changing frontmatter across all 16 components as literally requested, then narrowed to one after confirming aliases already resolve to the 5 generation. The request's goal was already met everywhere except `cheap-research`.
- Considered rewording the agent's "cheap tier" prose, then left it alone. `sonnet` is still the cheapest tier in use, and rewriting an agent's identity is a larger call than a tier change.

## Process Improvements

- When auditing for stale models, read the current model catalog first. Family aliases and generation gaps (no Haiku 5) make "is this old" unanswerable from the version number alone.
- When the repo shows no pending work but the user reports having made changes, check gitignored user-local state before concluding nothing exists. Profile files, settings, and local overrides are invisible to every git query.
- Report unrelated findings as separate items even when discovered in the same pass, so each can be accepted or dropped independently.

## Observations

- The drift persisted because the maintainer's own override masked it. `~/.claude/bpe.local.md` has set `cheap-research: sonnet` since 2026-07-26, so every dispatch on this machine already used Sonnet 5 while every fresh install got Haiku 4.5. The environment that would have noticed was the one environment configured not to.
- The tier map carries a date and a maintenance rule precisely to catch staleness, and it worked: the recommendation was current. What had no such mechanism was the shipped frontmatter, which is what the recommendation is supposed to govern.
- This is the third consecutive session where the commit ritual ran by hand. The `disable-model-invocation` fix landed in #32 on 2026-07-30, but this session's skill registry was loaded on 2026-07-27, so the change still has not taken effect here.

## Suggested Skills for Next Session

- `plugin-dev:plugin-validator`: confirm the agent tiers load correctly after a session restart, which is also the first chance to verify the #32 invocation change actually works.
