# Todo: bpe 0.7.3 Loop Efficiency

Mirrors plan.md. Check off each top-level step as it finalizes; sub-steps track within-step progress.

## Phase 1

Per-step run on the installed 0.7.2 plugin: `/bpe:goal section Phase 1`, then `/goal @goal.md`.

### Section 1: Playbook headroom

- [x] Step 1: Add the Orchestrator Playbook section to validator-protocol.md
  - [x] `## Orchestrator Playbook` after `## Per-step dispatch flow`, with Per Turn, RESUME, Hard Rules
  - [x] Verify: section present; safety tokens grep-found; plugin validate clean
- [x] Step 2: Shrink the goal.md template to condition, read instruction, and hard rules
  - [x] Template trimmed; Step 5 references and regeneration note updated
  - [x] Verify: rendered goal.md under 3000 chars; plugin validate clean

### Section 2: Batch mode (#51)

- [x] Step 1: Teach /bpe:plan the Batch line and the sizing rule
  - [x] `## Batch Line` in validator-protocol.md; `## Batch Boundaries` in plan/SKILL.md; review/SKILL.md plan bullet
  - [x] Verify: headings present; sizing rule present; plugin validate clean
- [x] Step 2: Give the executor the batch contract and warm continuation
  - [x] step-executor-protocol.md: one batch per invocation, continuation routing, per-step verify, report fields
  - [x] agents/step-executor.md: routing, implement loop, finalize slug and commit body, templates
  - [x] Verify: old invariant gone; Batch fields present; frontmatter parses; plugin validate clean
- [x] Step 3: Drive batches from the orchestrator playbook
  - [x] Per-batch dispatch flow, SendMessage continuation, cold fallback, per-batch cap, recovery
  - [x] goal/SKILL.md template: one commit per batch; intro paragraph
  - [x] Verify: heading renamed; SendMessage and fallback present; render under 3000; plugin validate clean

### Section 3: Measurement script (#51 acceptance)

- [ ] Step 1: Land goal-run-report.py and reproduce the baseline
  - [ ] Script with span flags, kind classification, three tables
  - [ ] Verify: baseline totals reproduced exactly; missing path exits 1
  - [ ] Baseline note's script bullet replaced with the command

## Phase 2

Manual gate first: restart with `claude --plugin-dir ./bpe`, confirm `/bpe:goal` resolves from the repo, run `/bpe:goal`, then `/goal @goal.md`.
These sections run in batch mode.

### Section 4: Final sweep (#52)

- [ ] Step 1: Add the final-validator agent and its profile seat
  - [ ] agents/final-validator.md; model-profiles.md key and tier-map row; .example entry; README
  - [ ] Verify: frontmatter and .example parse; plugin validate clean
- [ ] Step 2: Run the sweep at the end of the loop
  - [ ] `## Final Sweep` in validator-protocol.md; playbook step 3; executor sweep finalize; goal condition clause
  - [ ] Verify: sample block passes validate-findings.py; render under 3000; plugin validate clean

### Section 5: Checkpoint and report budget (#53)

- [ ] Step 1: Add the context-check hook and register it
  - [ ] hooks/context-check.py and .md; hooks/hooks.json; plugin.json; profile-check.json removed
  - [ ] Verify: 95% and 19% synthetic readings; missing path silent exit 0; profile-check unaffected
- [ ] Step 2: Act on the reading with a CHECKPOINT block
  - [ ] `### Checkpoint` in the playbook; hard rules "except on CHECKPOINT"; Step 5 resume note
  - [ ] Verify: render under 3000; plugin validate clean
- [ ] Step 3: Enforce the report budget
  - [ ] validate-findings.py caps; protocol schema rows; executor report budget; agent templates
  - [ ] Verify: 241 chars and 81 words rejected; 240 and 80 accepted; protocol example passes

### Section 6: Comparison and release

- [ ] Step 1: Record the batch-mode comparison
  - [ ] Run goal-run-report.py over the Phase 2 span; write batch-mode-comparison.md
- [ ] Step 2: Bump the plugin version to 0.7.3
  - [ ] plugin.json version -> 0.7.3
  - [ ] Verify: manifest reads 0.7.3; plugin validate clean
