# Session Summary: Drop the Opus 5 Example From the Profile Docs

**Date**: 2026-08-22
**Duration**: short
**Model**: claude-opus-4-8

## Key Actions

- Swept every plugin repo, the user-level skills/agents, and the bpe references for `claude-opus-5` pins after Mason confirmed Opus 5 is out of the model roster (Fable 5, Sonnet 5, Opus 4.8, latest Haiku).
- Found zero model-frontmatter pins to Opus 5 in any skill or subagent: bpe agents and skills use family aliases or `claude-fable-5`, and the live `~/.claude/bpe.local.md` already routes executor to Sonnet 5 and validator to Opus 4.8.
- The only residue was `bpe/README.md:113`, which used `claude-opus-5` as an example pinned model ID. Changed it to `claude-opus-4-8`.
- Left the `model-profiles.md` "Opus 5 rolled back" history intact: it is the record of rejecting Opus 5, which is what keeps a future session from re-adopting it.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "update any skills or subagents pinned to opus 5 to Opus 4.8" | Swept repos; found no pins; fixed the one README example | No pins existed; doc example corrected |

## Observations

- The shipped tier map still recommends Opus 4.8 for the executor, while the live personal profile now runs Sonnet 5 there (a 2026-08-17 budget move, documented in bpe.local.md as a cost tradeoff, not a quality retraction). The map is a generic quality recommendation, so it was left as-is; flagged for Mason.

## Suggested Skills for Next Session

- None.
