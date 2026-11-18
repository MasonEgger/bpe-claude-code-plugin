# Accomplishment: BPE 0.7.3 Loop Efficiency

**Archived**: 2026-11-18
**Convergence**: converged

## Spec Slice

The `## 0.7.3 Loop Efficiency (2026-11-10, requested)` work package in spec.md: playbook headroom, #51 batch mode, #52 the end-of-run final sweep, #53 the context checkpoint and report budget, the measurement item, and the version bump.
13 Task-shape steps across 6 sections, run in two phases.
Phase 1 (Sections 1 to 3) ran per step on the installed 0.7.2 plugin; Phase 2 (Sections 4 to 6) ran in batch mode on the branch plugin under `claude --plugin-dir ./bpe`.

## What Got Done

- Section 1: the per-turn procedure moved from the goal.md template into `validator-protocol.md` "## Orchestrator Playbook", and the template shrank to the condition, a read instruction, and the hard rules (about 1,780 rendered characters, against 3,978 in 0.7.2).
- Section 2 (#51): the `**Batch:**` line and the sizing rule in `/bpe:plan`, batch boundaries in `/bpe:review`, the executor's batch contract with warm `SendMessage` continuation, and an orchestrator playbook that drives one batch per implement dispatch with a cold validator and a cold-dispatch fallback.
- Section 3: `bpe/scripts/goal-run-report.py`, which reproduces the 0.7.2 baseline totals exactly.
- Section 4 (#52): the `bpe:final-validator` agent with its own profile seat, and the `## Final Sweep` flow at the end of full and section runs.
- Section 5 (#53, the agreed parts of #40): the `context-check` PostToolUse hook on `Agent|SendMessage`, the CHECKPOINT stop at 90 percent after a finalize or 95 percent after any dispatch, "never /clear except on CHECKPOINT", and report caps (finding `message` 240 characters, `notes` 80 words) enforced by `validate-findings.py`.
- Section 6: `.ai-sessions/research/batch-mode-comparison.md` and `plugin.json` at 0.7.3.
- Beyond the plan: exhaustive validator passes, re-check passes with `Previous findings:` and a `Fix delta:`, and a convergence-aware cap (base 3 passes, ceiling 5) in `3827949`, after both Phase 2 batches hit the old cap.
- Beyond the plan: a hand-dispatched final sweep over the whole branch (2 warn, then clean) and its fixes in `2adbf58`, which brought `bpe/README.md` up to the 0.7.3 loop.

Commits, oldest first: `973c310` spec, `49a6f0a` lesson, `9fdd53a` review-page fix, `a44cc0d` plan, `e80ded9`, `c93c4dd`, `0c8ce05`, `6be6a74`, `66a3894`, `e4c07ef` (Phase 1), `d1afbc9`, `44d06c8`, `3827949`, `11271c4`, `2adbf58` (Phase 2).

## Deferred or Dropped

- The playbook's automatic final-sweep trigger has never fired: both full-mode loops stopped at the cap first, and the sweep that ran was dispatched by hand because `/bpe:goal` pre-flight refuses a fully checked todo.md.
- That refusal also means a run that finishes its last item but stops before the sweep cannot be resumed into the sweep.
- The convergence-aware cap has not run inside a real goal loop.
- No run has reached 90 percent context, so the CHECKPOINT stop is untested; the hook itself fired live after both `Agent` and `SendMessage` calls.
- `goal-run-report.py` cannot see `SendMessage` continuations, so the comparison note understates Phase 2 subagent cost.
- Final sweep info findings left open: the goal skill's frontmatter description still says goal.md holds the playbook; the README's SEQUENTIAL line says one Agent call per turn rather than one dispatch; `validate-findings.py` line 219 fails strict mypy (no runtime effect).
- The validator and step-executor agent prompts are 12,608 and 14,034 characters against a 10,000-character guideline.
- mypy was not run on the branch.
- The profile has no `final-validator` entry, so the sweep ran on the shipped `opus` default rather than Fable.

## Notable Decisions

- `plugin.json` has no `hooks` field, because `hooks/hooks.json` is auto-discovered and naming it registered the file twice.
- The hook matcher is `Agent|SendMessage`, not `Agent` as the plan said, so warm continuations also produce a reading.
- The final validator's diff source is `git diff $(git merge-base main HEAD)` plus `git status --short`, not the plan's `..HEAD` form, so uncommitted sweep fixes are visible; plan.md line 294 still carries the old wording.
- Both Phase 2 batches hit the 3-iteration cap: `sweep` was finished by hand, and `checkpoint` got a fourth fix pass outside the loop.
  The diagnosis (rationed findings, unreviewed fix surface, two fix rounds) is in `.ai-sessions/session-20261113-1523-validator-loop-convergence.md`.
- `9fdd53a` changed the review renderer against the package non-goal; it was a maintainer-directed bugfix during spec review, and the sweep recorded it as info.

## Files Touched

- `bpe/.claude-plugin/plugin.json`
- `bpe/README.md`
- `bpe/agents/final-validator.md`, `bpe/agents/step-executor.md`, `bpe/agents/validator.md`
- `bpe/hooks/context-check.md`, `bpe/hooks/context-check.py`, `bpe/hooks/hooks.json`, `bpe/hooks/profile-check.json` (removed), `bpe/hooks/profile-check.md`
- `bpe/references/model-profiles.md`, `bpe/references/step-executor-protocol.md`, `bpe/references/validator-protocol.md`
- `bpe/scripts/goal-run-report.py`, `bpe/scripts/review-server.py`, `bpe/scripts/review.css`, `bpe/scripts/validate-findings.py`
- `bpe/skills/execute-plan/SKILL.md`, `bpe/skills/goal/SKILL.md`, `bpe/skills/plan/SKILL.md`, `bpe/skills/review/SKILL.md`
- `.claude/bpe.local.md.example`, `spec.md`
- `.ai-sessions/research/baseline-0.7.2-goal-run.md`, `.ai-sessions/research/batch-mode-comparison.md`, `.ai-sessions/lessons.md`, and the session summaries from 2026-11-10 to 2026-11-18

## Lessons Cross-Reference

- `.ai-sessions/lessons.md` Recent, 2026-11-13: a validator loop that trips its cap on every batch is usually rationing findings.
- 2026-11-13: `git diff HEAD --name-only` leaves out untracked files; the temporary-index tree snapshot.
- 2026-11-11: a recovery that resets a dirty tree needs a commit-first rule everywhere resuming is documented.
- 2026-11-11: a plan section that adds a new flow to the goal state machine needs that flow walked end to end at plan time.
- 2026-11-11: when the playbook says STOP, put `/goal clear` in the same message as the RESUME block.
- 2026-11-11: auto mode's classifier can refuse Edits on live `--plugin-dir` plugin files; dogfood with `claude --plugin-dir ./bpe`.
- 2026-11-10: the orchestrator's own context is the largest token sink in a goal run.
