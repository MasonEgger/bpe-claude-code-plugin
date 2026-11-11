# Plan: bpe 0.7.3 Loop Efficiency

Implements the `## 0.7.3 Loop Efficiency (2026-11-10, requested)` work package in spec.md: item 0 (playbook headroom), #51 batch mode, #52 final sweep, #53 checkpoint and report budget, the measurement item, and the version bump.
Only that package is planned here; the shipped goals above it in spec.md are out of scope.

Every step is Task-shape (Scope / Tooling / Do / Verify / Document).
The repo has no test harness, and spec.md's Available tooling Notes rule out RED/GREEN/REFACTOR for this project.
The two Python steps verify by running the script against real or synthetic input and checking exact output.

## Two Phases

Spec item 4 measures batch mode by running "this release's own remaining plan in batch mode".
The installed plugin is 0.7.2, which has no batch mode, so the run splits at the point where batch mode exists on the branch.

- **Phase 1 (Sections 1 to 3)** runs per-step on the installed 0.7.2 plugin: `/bpe:goal section Phase 1`, then `/goal @goal.md`.
  It frees the playbook headroom, builds batch mode, and lands the measurement script.
  The 0.7.2 orchestrator ignores `**Batch:**` lines, so these sections run one step at a time.
- **Manual gate.** Mason restarts Claude Code with the branch copy loaded (`claude --plugin-dir ./bpe`, disabling the installed bpe in `/plugin` if both load), confirms `/bpe:goal` resolves from the repo, then runs `/bpe:goal` (full) so goal.md is rendered from the branch's new playbook.
- **Phase 2 (Sections 4 to 6)** runs in batch mode on the branch plugin.
  Section 6 measures Phase 2 against the 0.7.2 baseline.

Phase 2 caveat: with `--plugin-dir ./bpe` the plugin files are the working tree, so an agent or protocol file a Phase 2 batch edits takes effect on the next dispatch.
Sections 4 and 5 are additive to the batch-mode machinery, so the run keeps working, but a validator finding inside those files can change the loop that is running.

## Current Status

- [ ] Section 1: Playbook headroom (prerequisite)
- [ ] Section 2: Batch mode (#51)
- [ ] Section 3: Measurement script (#51 acceptance)
- [ ] Section 4: Final sweep (#52)
- [ ] Section 5: Checkpoint and report budget (#53)
- [ ] Section 6: Comparison and release

Ordering: Section 1 moves the per-turn procedure into `references/validator-protocol.md`, and every later section edits the playbook there instead of in `skills/goal/SKILL.md`.
Section 2 must land before Section 3 so the script's dispatch-kind classification knows batch dispatches.
Section 3 lands in Phase 1 so Section 6 can use it.
Sections 4 and 5 both edit the playbook and `step-executor-protocol.md`; 4 before 5 keeps each edit on a committed base.

## Section 1: Playbook Headroom (Prerequisite)

**Tools:**
- Skills: plugin-dev:skill-development
- MCPs: none
- Linters: none

**Batch:** playbook

Rationale: the move must keep every safety contract the goal.md text carries today; the validator checks that nothing was dropped in transit.

### Step 1: Add the Orchestrator Playbook Section to validator-protocol.md (task)

**NOTE**: The per-turn procedure lives today only inside the fenced template in `bpe/skills/goal/SKILL.md` Step 3 (the text between the opening ```` ``` ```` after "Use the Write tool to overwrite `goal.md`" and the closing fence before "After writing the file").
This step copies it into the protocol; Step 2 removes it from the template.
Keeping both copies for one commit is deliberate, so neither commit leaves the loop without its rules.

```text
1. Scope:
   - Artifact(s): bpe/references/validator-protocol.md
   - Desired end state: a new `## Orchestrator Playbook` section, placed directly after `## Per-step dispatch flow`, holds the complete per-turn procedure and the RESUME block from the goal.md template, with placeholders written as `<test-cmd>` and `<branch>`.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: none

3. Do the work:
   - Read bpe/skills/goal/SKILL.md Step 3's template block in full.
   - In bpe/references/validator-protocol.md, add `## Orchestrator Playbook` after `## Per-step dispatch flow`. Open it with two sentences: the orchestrator reads this section at the start of every turn; goal.md carries only the condition, the read instruction, and the hard rules, so this section is the procedure.
   - Under it, add `### Per Turn` holding steps 1 to 8 and 7b from the template, unchanged in meaning. Keep the numbering so `skills/goal/SKILL.md` Step 5's "per-turn step 7b" reference stays true. Replace `${CLAUDE_PLUGIN_ROOT}` paths with the same `${CLAUDE_PLUGIN_ROOT}` form (the orchestrator resolves them from the read instruction's path).
   - Add `### RESUME` holding the template's RESUME bullets verbatim.
   - Add `### Hard Rules` holding the template's "Hard rules:" line split into one bullet per rule.
   - Write committed Markdown prose one sentence per line, with a blank line between paragraphs; Title Case headings.

4. Verify:
   - `grep -n '^## Orchestrator Playbook$' bpe/references/validator-protocol.md` prints one line, and `grep -c '7b\.' bpe/references/validator-protocol.md` is at least 1.
   - For each of these tokens, grep finds it in the new section: `INTERRUPTION CHECK`, `validate-findings.py`, `git rev-parse HEAD must equal`, `finalize-test-failure`, `dispatch cap reached`, `git reset --hard && git clean -fd`.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - none (the section is the documentation)
```

### Step 2: Shrink the goal.md Template to Condition, Read Instruction, and Hard Rules (task)

**NOTE**: The rendered goal.md for the 0.7.2 run measured 3978 characters against a 4000 cap.
The target is under 3000 with real values substituted, measured the same way Step 3 of the skill tells the user.

```text
1. Scope:
   - Artifact(s): bpe/skills/goal/SKILL.md
   - Desired end state: the Step 3 template holds, in order: the condition line; one paragraph naming the orchestrator role and telling it to READ `${CLAUDE_PLUGIN_ROOT}/references/validator-protocol.md` "## Orchestrator Playbook" AT THE START OF EVERY TURN and follow it exactly; a SEQUENTIAL DISPATCHES paragraph; a one-commit-per-unit paragraph with the SHA-verification rule (verify against the reported SHA, not HEAD; session summary in every commit); the Hard rules line (sequential only, never /clear or /compact, never commit on the subagent's behalf, dispatch cap); a one-line RESUME pointer to the protocol's `### RESUME`; and the `Mode:` line. The rendered result is under 3000 characters.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: python3 for the render measurement

3. Do the work:
   - Replace the template's "Per turn:" list and its RESUME block with the read instruction and the RESUME pointer described above. Keep the safety contracts as short sentences in the template itself; they are the defense-in-depth copy the evaluator sees.
   - Update the paragraph above the template: the 4000 cap stays a hard rule; add that the protocol section is the procedure, so a procedure change no longer needs goal.md regeneration.
   - Update Step 5 "When to regenerate goal.md": editing `references/validator-protocol.md` "## Orchestrator Playbook" takes effect on the next turn with no regeneration; editing the template in Step 3 still requires re-running /bpe:goal.
   - Update Step 5's resume steps where they say "per-turn step 2" and "per-turn step 7b" to say "playbook step 2" and "playbook step 7b" in validator-protocol.md.
   - One sentence per line in the prose you touch.

4. Verify:
   - Render the template with real values and measure, writing the render to a scratch file outside the repo: substitute the full-mode condition with `<test-cmd>`=`claude plugin validate ./bpe` and `<branch>`=`release-0.7.3`, replace `${CLAUDE_PLUGIN_ROOT}` with `/home/mmegger/.claude/plugins/cache/bpe/bpe/0.7.3`, and print the character count with `python3 -c "import sys; print(len(open(sys.argv[1]).read()))" <file>`. The count is under 3000.
   - `grep -c 'Orchestrator Playbook' bpe/skills/goal/SKILL.md` is at least 2 (template and Step 5).
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - Record the rendered count in the step's session summary.
```

## Section 2: Batch Mode (#51)

**Tools:**
- Skills: plugin-dev:skill-development, plugin-dev:agent-development
- MCPs: none
- Linters: none

**Batch:** batch-mode

Rationale: these steps rewrite the dispatch contract between three files; the validator checks the three stay consistent with each other and with the confirmed design decisions in spec.md.

### Step 1: Teach /bpe:plan the Batch Line and the Sizing Rule (task)

```text
1. Scope:
   - Artifact(s): bpe/references/validator-protocol.md, bpe/skills/plan/SKILL.md, bpe/skills/review/SKILL.md
   - Desired end state: the `**Batch:**` line grammar is defined once in validator-protocol.md; plan/SKILL.md tells the plan writer to emit it and how to size batches; review/SKILL.md tells the reviewer page to show batch boundaries.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/references/validator-protocol.md, add `## Batch Line` after `## Tools block`. Define: one `**Batch:** <name>` line per plan section, placed after the section's Tools block; `<name>` is kebab-case and unique in the plan; the literal `**Batch:** single` keeps the per-step loop for that section; a section split into several batches uses `<name>-a`, `<name>-b` on per-step `**Batch:**` lines placed under each `### Step` heading (a per-step line shadows the section line); a plan with no Batch lines (written before 0.7.3) runs every section as `single`. A batch's steps are the consecutive todo.md steps sharing one batch name.
   - In bpe/skills/plan/SKILL.md, add `## Batch Boundaries` after `## Per-section Tools block`. Tell the writer: default one section per batch; split a section into `-a`/`-b` batches when it has more than 4 steps or its steps' stated scope exceeds about 400 changed lines; mark a section `single` when its steps need a human check between them or touch files a running loop depends on; batched sections declare Tools at section level only, since the batch validator judges the whole batch against one block. Point to validator-protocol.md `## Batch Line` for the grammar instead of restating it.
   - In bpe/skills/plan/SKILL.md `## Output Format`, add a bullet: the `**Batch:**` line after each section's Tools block.
   - In bpe/skills/review/SKILL.md, extend the `plan.md` bullet under "Filling in the content": each batch is a cluster (heading divider named after the batch), and each batch boundary gets its own decision unit so the reviewer can rule on the grouping.
   - One sentence per line in committed Markdown prose; Title Case headings.

4. Verify:
   - `grep -n '^## Batch Line$' bpe/references/validator-protocol.md`, `grep -n '^## Batch Boundaries$' bpe/skills/plan/SKILL.md`, and `grep -n 'Batch' bpe/skills/review/SKILL.md` each print at least one line.
   - `grep -c '400' bpe/skills/plan/SKILL.md` is at least 1 and `grep -c 'more than 4 steps' bpe/skills/plan/SKILL.md` is 1.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - none
```

### Step 2: Give the Executor the Batch Contract and Warm Continuation (task)

```text
1. Scope:
   - Artifact(s): bpe/references/step-executor-protocol.md, bpe/agents/step-executor.md
   - Desired end state: one implement dispatch does every step of a batch; fix and finalize arrive as continuation messages to the same agent; reports carry per-step todo deltas and the batch name; finalize makes one commit for the batch.

2. Tooling:
   - Skills: plugin-dev:agent-development
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/references/step-executor-protocol.md:
     - Replace the hard invariant "One step per invocation" with "One batch per invocation; a batch of one is a step", and say the dispatch prompt names the batch and its steps.
     - In `## Role`, add that a dispatch may be a continuation: the orchestrator sends `Mode: fix` or `Mode: finalize` to the agent that ran implement, through SendMessage. The executor routes on the `Mode:` line of the latest message it received.
     - In the `implement` per-mode addition: do the batch's steps in order; after each step run that step's Verify (or the project test command) and the spec-fence self-check, then check off that step in todo.md, before starting the next step. A red Verify or a fence violation on any step is `Failure:` naming the step.
     - In the mode contract table, add a row "Warm continuation" with values: implement `n/a`, fix `yes when sent by SendMessage`, finalize `yes when sent by SendMessage`, bundled `n/a`. Add one sentence: a continuation that cannot proceed (context exhausted) returns `Failure:` so the orchestrator falls back to a cold dispatch.
     - In `### Implement-Report`, add the `Batch:` field (batch name, or `single`) and change `TodoDelta:` to one line per step checked.
     - In `### Finalize-Report`, add `Batch:` and the same multi-line `TodoDelta:`. State that "Exactly one commit per finalize" applies per batch.
     - In `## Hard invariants (all modes)`, replace "Never `/clear` or `/compact`. ... every dispatch has fresh context." with "Never `/clear` or `/compact`. Would break the parent's `/goal` session." (Section 5 changes the orchestrator's rule; the executor's stays absolute.)
   - In bpe/agents/step-executor.md:
     - Under `## Mode routing`, add: route on the `Mode:` line of the latest message; a continuation message skips the "read protocol files" preamble when they are already in context.
     - `## Mode: implement` step 3: loop over the batch's steps, running each step's Verify and the fence check before the next, checking off each in todo.md as it lands.
     - `## Mode: finalize` step 3: session summary slug `goal-batch-<name>` for a batch, `goal-step-N-<short-desc>` for single. Step 5: the commit subject names the batch; the body lists each step's title on its own line. Step 6(b): todo.md carries every checked step of the batch.
     - Update the Implement-Report and Finalize-Report templates with the `Batch:` field and the per-step `TodoDelta:` lines.
   - One sentence per line in committed Markdown prose.

4. Verify:
   - `grep -n 'One batch per invocation' bpe/references/step-executor-protocol.md` prints one line, and `grep -c 'One step per invocation' bpe/references/step-executor-protocol.md` is 0.
   - `grep -c '^Batch:' bpe/agents/step-executor.md` is at least 2.
   - `python3 -c "import yaml,sys; t=open('bpe/agents/step-executor.md').read().split('---')[1]; yaml.safe_load(t); print('ok')"` prints ok.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - none
```

### Step 3: Drive Batches from the Orchestrator Playbook (task)

**NOTE**: `SendMessage` is a deferred tool in Claude Code sessions; the orchestrator loads it with `ToolSearch` `select:SendMessage` before the first continuation.
The agent id comes from the implement dispatch's tool result.

```text
1. Scope:
   - Artifact(s): bpe/references/validator-protocol.md, bpe/skills/goal/SKILL.md
   - Desired end state: the state machine and the Orchestrator Playbook run one batch at a time with a warm executor, a cold validator, a per-batch fix cap, one commit per batch, and the cold-dispatch fallback; goal.md's hard-rules text says one commit per batch and still renders under 3000 characters.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: python3 for the render measurement

3. Do the work:
   - In bpe/references/validator-protocol.md `## Per-step dispatch flow`: rename the heading to `## Per-batch dispatch flow`, say "for each batch (a batch of one is a step)", change step 1 to dispatch implement for the batch's steps, step 4 to validate the batch's whole diff (`git diff HEAD`) against the section's Tools block, and steps 5 and 6 to send fix and finalize as SendMessage continuations to the implement agent. Add one line: a continuation that errors, or returns no report block, falls back to a cold dispatch in the same mode, since the tree carries the work.
   - Update every in-file cross-reference to the renamed heading (grep for "Per-step dispatch flow").
   - `## Interrupted dispatches`: the batch's base commit is HEAD until finalize, so the reset drops the whole batch, unchecks its todo.md steps, and the batch is redone from implement.
   - `## Iteration cap`: the cap is 3 fix iterations per batch.
   - `## Orchestrator Playbook` `### Per Turn`: step 3 reads the first `- [ ]` and resolves its batch per `## Batch Line` (steps sharing the batch name); step 4 dispatches implement for the whole batch and records the returned agent id; fix and finalize turns use SendMessage to that id (load it with ToolSearch `select:SendMessage` first) and fall back to a cold Agent dispatch on error or a missing report; step 7 verification is unchanged but checks every `TodoDelta:` line; reset the agent id and iter when a new batch starts.
   - In bpe/skills/goal/SKILL.md Step 3's template: "Each committed step is EXACTLY ONE commit" becomes "Each batch (a batch of one is a step) is EXACTLY ONE commit". Update the skill's intro paragraph (top of file) to say the executor runs per batch and stays warm across a batch's modes.
   - One sentence per line in committed Markdown prose.

4. Verify:
   - `grep -c 'Per-step dispatch flow' bpe/references/validator-protocol.md` is 0 and `grep -c 'Per-batch dispatch flow' bpe/references/validator-protocol.md` is at least 1.
   - `grep -c 'SendMessage' bpe/references/validator-protocol.md` is at least 2 and `grep -c 'cold' bpe/references/validator-protocol.md` is at least 2.
   - Render goal.md as in Section 1 Step 2's Verify; the count is under 3000.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - Record the rendered count in the session summary.
```

## Section 3: Measurement Script (#51 Acceptance)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

**Batch:** report-script

Rationale: the script is the only new logic in Phase 1; python:python carries the style and docstring rules the validator checks against.
No Python linter is installed in this repo.

### Step 1: Land goal-run-report.py and Reproduce the Baseline (task)

**NOTE**: The baseline arithmetic is documented in `.ai-sessions/research/baseline-0.7.2-goal-run.md` "How It Was Measured".
Transcript layout: the parent is `~/.claude/projects/<project>/<session>.jsonl`; each Agent tool_result entry carries `toolUseResult.agentId` and `toolUseResult.resolvedModel`; the subagent transcript is `<session>/subagents/agent-<agentId>.jsonl`.
Continuation messages (SendMessage) add turns to an existing subagent transcript rather than creating a new one, which is why per-transcript totals stay correct under batch mode.

```text
1. Scope:
   - Artifact(s): bpe/scripts/goal-run-report.py
   - Desired end state: `bpe/scripts/goal-run-report.py <session.jsonl> [--since ISO] [--until ISO]` prints the per-dispatch table, the totals by dispatch kind, and the orchestrator totals for the span; run on the 0.7.2 session with the baseline span it reproduces the baseline numbers.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: uv (the script uses the same `#!/usr/bin/env -S uv run --script` header and inline metadata block as bpe/scripts/validate-findings.py)

3. Do the work:
   - Create bpe/scripts/goal-run-report.py: stdlib only, Python >=3.11, a module docstring with usage and exit codes, type hints, Google-style docstrings on every function, `argparse` for the CLI.
   - Parse the parent transcript line by line, skipping lines that are not JSON. Collect Agent tool_use blocks (id, timestamp, subagent_type, description) whose timestamp falls in the span, and map each to its tool_result's `toolUseResult.agentId` and `resolvedModel`. Also collect SendMessage tool_use blocks in the span, counted as continuation dispatches against the agent they target.
   - For each agent id, sum over the subagent transcript's assistant entries: assistant turns, tool_use blocks, `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`, `output_tokens`; minutes = last timestamp minus first timestamp.
   - Classify each dispatch by kind from its description's first word, case-insensitive: implement, validate or re-validate as validator, fix, finalize, sweep; anything else is other.
   - Sum the same usage fields over the parent's assistant entries in the span for the orchestrator line.
   - Print three Markdown tables (per-dispatch, by kind, orchestrator), numbers with thousands separators.
   - Exit 1 with a one-line stderr message when the transcript path does not exist.

4. Verify:
   - Run `bpe/scripts/goal-run-report.py ~/.claude/projects/-home-mmegger-Code-MasonEgger-bpe-claude-code-plugin/562f6f3a-4df4-409c-ae81-62d107c74ffa.jsonl --since 2026-11-09T22:40:00Z --until 2026-11-10T01:00:00Z` and confirm: 42 dispatches; total subagent cache-read 76,767,488; total cache-create 9,572,146; total output 1,277,439; kind counts implement 12, validator 14, fix 4, finalize 12; orchestrator cache-read 108,704,747.
   - Run it on a nonexistent path and confirm exit 1 with one stderr line.

5. Document:
   - In .ai-sessions/research/baseline-0.7.2-goal-run.md "How It Was Measured", replace the "Script: an ad hoc Python pass..." bullet with the exact command from Verify.
```

## Section 4: Final Sweep (#52)

**Tools:**
- Skills: plugin-dev:agent-development, plugin-dev:skill-development
- MCPs: none
- Linters: none

**Batch:** sweep

Rationale: a new agent plus protocol and playbook edits; the agent-development skill carries the frontmatter rules the new agent file must follow.

### Step 1: Add the final-validator Agent and Its Profile Seat (task)

```text
1. Scope:
   - Artifact(s): bpe/agents/final-validator.md, bpe/references/model-profiles.md, .claude/bpe.local.md.example, bpe/README.md
   - Desired end state: a `final-validator` agent exists with `model: opus` and the validator's read-only shape; the profile docs name it as an agent key; the 2026-11-09 tier-map row names `final-validator`.

2. Tooling:
   - Skills: plugin-dev:agent-development
   - MCPs: none
   - External: none

3. Do the work:
   - Create bpe/agents/final-validator.md. Frontmatter: `name: final-validator`, a `description` saying it runs once at the end of a /bpe:goal run over the whole branch diff, `model: opus`, `color: magenta`, `disallowedTools: Write, Edit, NotebookEdit`. Body: read `${CLAUDE_PLUGIN_ROOT}/agents/validator.md` and `${CLAUDE_PLUGIN_ROOT}/references/validator-protocol.md`, then follow validator.md's procedure with exactly three differences: the diff source is `git diff $(git merge-base main HEAD)..HEAD` (with `--name-only` for the fence checks); the tools consulted are the union of every section's Tools block in plan.md, plus the spec fences; it runs even when every section declared `Tools: none`. Its findings block uses `"validator": "bpe:final-validator"`. Keep it short and point to validator.md instead of restating its procedure.
   - In bpe/references/model-profiles.md: in the agents key description under `### Field Reference`, list `final-validator` alongside the existing agent names; in the 2026-11-09 tier map, rename the row "final-sweep seat (0.7.3, #52)" to "final-validator agent (end-of-run sweep)".
   - In .claude/bpe.local.md.example personal profile `agents:`, add `final-validator: claude-fable-5-1` with a comment pointing at the 2026-11-09 map, and update the existing "final-sweep seat" comment to name the agent.
   - In bpe/README.md, add `final-validator` wherever the agents are listed.

4. Verify:
   - `python3 -c "import yaml; t=open('bpe/agents/final-validator.md').read().split('---')[1]; d=yaml.safe_load(t); assert d['name']=='final-validator' and d['model']=='opus'; print('ok')"` prints ok.
   - `python3 -c "import yaml; t=open('.claude/bpe.local.md.example').read().split('---')[1]; yaml.safe_load(t); print('ok')"` prints ok.
   - `grep -c 'final-validator' bpe/references/model-profiles.md` is at least 2.
   - `claude plugin validate ./bpe` exits 0 and lists the new agent.

5. Document:
   - none
```

### Step 2: Run the Sweep at the End of the Loop (task)

```text
1. Scope:
   - Artifact(s): bpe/references/validator-protocol.md, bpe/references/step-executor-protocol.md, bpe/agents/step-executor.md, bpe/skills/goal/SKILL.md
   - Desired end state: after the last todo item finalizes in full or section mode, the orchestrator dispatches `bpe:final-validator`, runs the fix loop on block or warn, finalizes any fixes as one "Apply final sweep fixes" commit, and only then reports the goal met; the goal condition carries the sweep clause.

2. Tooling:
   - Skills: plugin-dev:skill-development, plugin-dev:agent-development
   - MCPs: none
   - External: python3 for the render measurement

3. Do the work:
   - In bpe/references/validator-protocol.md, add `## Final Sweep` after `## Finalize-red recovery`: when it runs (after the last todo item finalizes, full and section modes, never step mode); the dispatch fields (Diff source as above, Iteration, Section `all`); findings through validate-findings.py; block or warn => executor `mode=fix` (cold dispatch, since no warm agent spans the whole branch), then final-validator again, 3-iteration cap; clean with no fixes => no commit; clean after fixes => one `mode=finalize` with `Step: sweep`, subject "Apply final sweep fixes", `TodoDelta: none`; block or warn at the cap => Failure with unresolved findings and RESUME.
   - In `## Roles`, add `bpe:final-validator`.
   - In `## Orchestrator Playbook` `### Per Turn` step 3: when no `- [ ]` remains, run the final sweep per `## Final Sweep` before running `<test-cmd>` and the push check.
   - In bpe/references/step-executor-protocol.md and bpe/agents/step-executor.md `## Mode: finalize`: a `Step: sweep` finalize stages the fixed files and the session summary (slug `goal-final-sweep`), leaves todo.md alone, and reports `TodoDelta: none`.
   - In bpe/skills/goal/SKILL.md Step 2: add "; the final sweep returned clean" to the full and section conditions, not the step condition.
   - One sentence per line in committed Markdown prose.

4. Verify:
   - `grep -n '^## Final Sweep$' bpe/references/validator-protocol.md` prints one line; `grep -c 'final sweep returned clean' bpe/skills/goal/SKILL.md` is 2.
   - Sample block check: pipe `{"validator":"bpe:final-validator","verdict":"block","iter":1,"findings":[{"severity":"block","file":"spec.md","rule":"spec.invariant","message":"planted violation"}]}` through `bpe/scripts/validate-findings.py`; exit 0.
   - Render goal.md as in Section 1 Step 2's Verify; the count is under 3000.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - none
```

## Section 5: Checkpoint and Report Budget (#53)

**Tools:**
- Skills: plugin-dev:hook-development, python:python, plugin-dev:skill-development
- MCPs: none
- Linters: none

**Batch:** checkpoint

Rationale: one new hook script, a hook registration change, playbook text, and caps in validate-findings.py; the hook-development skill carries the PostToolUse input and output shapes the validator checks against.

### Step 1: Add the context-check Hook and Register It (task)

**NOTE**: `bpe/.claude-plugin/plugin.json` takes one `hooks` path today (`./hooks/profile-check.json`).
This step merges both registrations into one `bpe/hooks/hooks.json`.
Agent dispatches in current Claude Code sessions can return asynchronously, so PostToolUse on `Agent` may fire at launch rather than at completion; the reading is then one dispatch behind, which the 5-point gap between thresholds absorbs.
Confirm the hook input fields against plugin-dev:hook-development before writing.

```text
1. Scope:
   - Artifact(s): bpe/hooks/context-check.py, bpe/hooks/hooks.json, bpe/hooks/profile-check.json (removed), bpe/.claude-plugin/plugin.json, bpe/hooks/profile-check.md, bpe/hooks/context-check.md
   - Desired end state: a PostToolUse hook on matcher `Agent` emits `Context: NN% of <window>` as additionalContext, fails open, and is registered alongside profile-check from one hooks.json.

2. Tooling:
   - Skills: plugin-dev:hook-development, python:python
   - MCPs: none
   - External: none

3. Do the work:
   - Create bpe/hooks/context-check.py modeled on bpe/hooks/profile-check.py (stdlib only, module docstring with the exit contract, type hints, Google-style docstrings). Read the hook JSON from stdin; open `transcript_path`; find the last entry with `type == "assistant"` and a `message.usage` object; sum `input_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`; window = 1,000,000 when that entry's `requestedModel` contains `[1m]`, else 200,000; print `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "Context: NN% of <window>"}}` with NN as a rounded integer. On any missing file, missing field, JSON error, or other exception, print nothing and exit 0.
   - Create bpe/hooks/hooks.json holding both registrations: the existing UserPromptSubmit entry from profile-check.json unchanged, and a PostToolUse entry with matcher `Agent` running `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/context-check.py"` with timeout 10. Delete bpe/hooks/profile-check.json with `git rm`.
   - Point bpe/.claude-plugin/plugin.json `hooks` at `./hooks/hooks.json`.
   - Update bpe/hooks/profile-check.md where it names profile-check.json as the registration file.
   - Create bpe/hooks/context-check.md: what it reports, when it fires, the window rule, the fail-open contract, and that the orchestrator playbook acts on it.

4. Verify:
   - Write a synthetic transcript to a scratch file whose last assistant entry has usage 10,000 input + 150,000 cache_read + 30,000 cache_creation and `requestedModel` `claude-opus-5-5`; run `echo '{"transcript_path":"<file>","tool_name":"Agent"}' | python3 bpe/hooks/context-check.py` and confirm the additionalContext reads `Context: 95% of 200000`.
   - Same with `requestedModel` `claude-opus-5-5[1m]`: `Context: 19% of 1000000`.
   - `echo '{"transcript_path":"/nonexistent"}' | python3 bpe/hooks/context-check.py; echo "exit=$?"` prints only `exit=0`.
   - `echo '{"prompt":"/bpe:plan","cwd":"'"$PWD"'"}' | python3 bpe/hooks/profile-check.py` still prints its additionalContext JSON (profile-check unaffected).
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - bpe/hooks/context-check.md (above).
```

### Step 2: Act on the Reading with a CHECKPOINT Block (task)

```text
1. Scope:
   - Artifact(s): bpe/references/validator-protocol.md, bpe/skills/goal/SKILL.md, bpe/references/step-executor-protocol.md
   - Desired end state: the playbook ends the turn with a CHECKPOINT block at 90 percent after a finalize or 95 percent after any dispatch; "Never /clear or /compact" becomes "only on CHECKPOINT" for the orchestrator; one paragraph covers long arcs and tight credits.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: python3 for the render measurement

3. Do the work:
   - In bpe/references/validator-protocol.md `## Orchestrator Playbook`, add `### Checkpoint`: after every dispatch read the latest `Context: NN% of <window>` line the hook injected; at NN >= 90 after a verified finalize, or NN >= 95 after any dispatch, echo a block starting `CHECKPOINT:` with the reading, the last commit, and the two commands `/clear` then `/goal @goal.md`, and end the turn without dispatching. No reading (hook absent or failed open) means no checkpoint. Resume is the existing path: first `- [ ]`, with a dirty tree handled by the interruption check. Then one paragraph: on long arcs or tight credits, a checkpoint at a commit boundary loses nothing, so prefer resuming fresh over pushing past 90.
   - In `### Per Turn`, add the checkpoint read as the step after verification and before "YOUR TURN ENDS".
   - In `### Hard Rules`, change "Never /clear or /compact" to "Never /clear or /compact except on CHECKPOINT".
   - In bpe/skills/goal/SKILL.md Step 3's template hard-rules line, make the same change. In Step 5, add a short "### Resuming from a CHECKPOINT" subsection: run `/clear`, then `/goal @goal.md`; no regeneration needed.
   - In bpe/references/step-executor-protocol.md, leave the executor's absolute "Never /clear or /compact" rule as Section 2 Step 2 left it, and add one sentence: CHECKPOINT is an orchestrator-only action.
   - One sentence per line in committed Markdown prose.

4. Verify:
   - `grep -n '^### Checkpoint$' bpe/references/validator-protocol.md` prints one line; `grep -c 'except on CHECKPOINT' bpe/skills/goal/SKILL.md` is at least 1; `grep -c '90' bpe/references/validator-protocol.md` and `grep -c '95' bpe/references/validator-protocol.md` are each at least 1.
   - Render goal.md as in Section 1 Step 2's Verify; the count is under 3000.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - none
```

### Step 3: Enforce the Report Budget (task)

```text
1. Scope:
   - Artifact(s): bpe/scripts/validate-findings.py, bpe/references/validator-protocol.md, bpe/references/step-executor-protocol.md, bpe/agents/validator.md, bpe/agents/step-executor.md, bpe/agents/final-validator.md
   - Desired end state: validate-findings.py rejects a finding `message` over 240 characters and a `notes` over 80 words; the protocols state the budget; the agent templates follow it.

2. Tooling:
   - Skills: python:python, plugin-dev:agent-development
   - MCPs: none
   - External: uv

3. Do the work:
   - In bpe/scripts/validate-findings.py: add module constants `MAX_MESSAGE_CHARS = 240` and `MAX_NOTES_WORDS = 80`; in `check_finding`, fail when `len(f["message"]) > MAX_MESSAGE_CHARS` naming the index and length; in `check_top`, fail when `len(data["notes"].split()) > MAX_NOTES_WORDS` naming the count. Add Google-style docstrings to the functions you touch. Update the module docstring with the two caps.
   - In bpe/references/validator-protocol.md `## Findings schema (canonical)`: add the caps to the `message` and `notes` rows, and one sentence that validate-findings.py enforces them.
   - In bpe/references/step-executor-protocol.md `## Report schemas`: add a `### Report Budget` subsection: report fields stay verbatim; no prose outside the report block; `Blockers:` and `Deferred:` are one line each; detail goes in the session summary, which the orchestrator never reads.
   - In bpe/agents/validator.md and bpe/agents/final-validator.md: state the two caps where the output format is described. In bpe/agents/step-executor.md: state the one-line rule for `Blockers:` and `Deferred:` beside the templates.
   - One sentence per line in committed Markdown prose.

4. Verify:
   - A finding whose message is 241 characters: validate-findings.py exits 1 with a message naming the length. A 240-character message: exit 0.
   - A block whose notes is 81 words: exit 1. 80 words: exit 0.
   - The example block in validator-protocol.md `### Example` still passes: extract it and pipe it through; exit 0.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - none
```

## Section 6: Comparison and Release

**Tools:** none

**Batch:** release

Rationale: a measurement write-up and a version bump; nothing for a domain validator to judge.
The final sweep, which Section 4 builds, does not run in this goal loop: the Phase 2 goal.md was rendered before Section 4 landed.

### Step 1: Record the Batch-Mode Comparison (task)

**NOTE**: The span to measure starts at the last Phase 1 commit (Section 3) and runs to now.
The parent transcript is the most recently modified `.jsonl` in `~/.claude/projects/-home-mmegger-Code-MasonEgger-bpe-claude-code-plugin/`, which is the Phase 2 session.
This step runs inside the span it measures, so its own dispatches are partly counted; say so in the write-up.

```text
1. Scope:
   - Artifact(s): .ai-sessions/research/batch-mode-comparison.md
   - Desired end state: a dated note comparing the Phase 2 batch run against the 0.7.2 baseline on dispatches, subagent minutes, subagent and orchestrator cache-read tokens, and warn rate per first-pass validation.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: bpe/scripts/goal-run-report.py, git

3. Do the work:
   - Get the span start with `git log -1 --format=%cI` on the Section 3 commit (find it with `git log --format='%h %cI %s' | grep -i 'goal-run-report'`).
   - Run `bpe/scripts/goal-run-report.py <phase-2 transcript> --since <span start>`.
   - Write .ai-sessions/research/batch-mode-comparison.md: a short header (date, plan, profile models as the tool results reported them), a table with one row per measure and columns 0.7.2 baseline, Phase 2 batch run, and per-step normalized values (divide by steps done in each run: 12 for the baseline, the count of Phase 2 steps checked for the batch run), the warn rate per first-pass validation in both runs, then three to five sentences on what the numbers show and what they cannot show (different plan content, a partly counted final step, no sweep in this run).
   - One sentence per line; Title Case headings.

4. Verify:
   - `test -s .ai-sessions/research/batch-mode-comparison.md` and `grep -c '0.7.2 baseline' .ai-sessions/research/batch-mode-comparison.md` is at least 1.

5. Document:
   - The note is the document.
```

### Step 2: Bump the Plugin Version to 0.7.3 (task)

```text
1. Scope:
   - Artifact(s): bpe/.claude-plugin/plugin.json
   - Desired end state: `"version": "0.7.3"`.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: none

3. Do the work:
   - Change the version field from 0.7.2 to 0.7.3.

4. Verify:
   - `python3 -c "import json; assert json.load(open('bpe/.claude-plugin/plugin.json'))['version']=='0.7.3'; print('ok')"` prints ok.
   - `claude plugin validate ./bpe` exits 0.

5. Document:
   - none
```

## Implementation Guidelines

- Verification command for the loop: `claude plugin validate ./bpe` (exit 0; the one cosmetic missing-icon warning is expected).
- Committed Markdown prose: one sentence per line, blank line between paragraphs, Title Case headings, no em or en dashes, straight quotes.
- Python: stdlib only, Python >=3.11, type hints, Google-style docstrings on every new or re-signed function.
- Every playbook-touching step re-renders goal.md with real values and confirms it is under 3000 characters.
- After any contract change, grep for the old phrasing across `bpe/` before reporting ready; stale claims in sibling files are the most common warn in this repo's history.

## Success Metrics

- Phase 1 lands Sections 1 to 3 as one commit per step on the installed 0.7.2 loop.
- Phase 2 lands Sections 4 to 6 as one commit per batch on the branch plugin: three commits for six steps.
- goal.md renders under 3000 characters at every playbook edit.
- goal-run-report.py reproduces the baseline totals exactly.
- The comparison note exists and states dispatches, minutes, cache-read tokens, and warn rate against the baseline.
- `claude plugin validate ./bpe` exits 0 and plugin.json reads 0.7.3.
