# Session Summary: Retrofit Structure Migration for Pre-0.7 Specs

**Date**: 2026-09-20
**Duration**: single focused change (discovery + one skill edit + version bump)
**Model**: claude-fable-5

## Key Actions

- Discovery against the 0.7.0 release confirmed the gap Mason suspected: v0.7-plan.md line 168 promises "Mason can retrofit-resync them into the new shape when he wants to," but the shipped Resync Mode only reconciles content drift.
It compares section by section assuming the canonical headings already exist, so a pre-0.7 spec (missing Invariants and Roadmap, accreted phase addenda, drifted heading names) has no defined migration path.
- Extended Resync Mode in bpe/skills/retrofit/SKILL.md with a structure check (step 2) and a Structure Migration pass: map existing sections onto the canonical nine, relocate phase content (dated addenda, work packages, interview agendas, research notes) into .ai-sessions/ archives with per-section confirmation, create the missing sections (Starting context dated at migration, Invariants from the repo read plus the old spec's mandates, Roadmap Shipped derived from archives on disk), and handle phase-shaped specs by re-opening only the Q&A topics the old file cannot answer.
- Migration folds into the existing scratch-file diff-and-confirm gate: one diff, one confirm, nothing silently dropped.
- Bumped the plugin to 0.7.1.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| "extend the retrofit command to support retrofitting old specs" | Structure Migration pass added to Resync Mode | Branch retrofit-spec-migration, PR to follow |

## Observations

- The first consumer is claude-code-plugin-private's own spec.md: fifteen accreted sections, two dated work packages, no Invariants, no Roadmap.
It is the acceptance test for this procedure.

## Suggested Skills for Next Session

- plugin-dev:skill-development if the migration pass needs refinement after its first live run.
