# Plan: bpe 0.7.4 Setup, Issue Format, and Spec Goals

Implements the `## 0.7.4 Setup, Issue Format, and Spec Goals (2026-11-22, requested)` package at the bottom of spec.md: item 1 (#58 loop follow-ups), item 5 (deterministic artifact checks and templates), item 2 (#48 issue format), item 3 (#55 Goals), item 4 (#28 `/bpe:init`), and item 6 (docs and the version bump).
Only that package is planned here; the shipped packages above it in spec.md are out of scope.
The package's Constraints, Non-goals, and Deferred lists are this plan's fences: no step adds a runtime dependency, edits spec.md, changes a loop contract beyond the sweep-resume pre-flight, or builds a Deferred item.

## How This Plan Runs

Run the loop from a plain `claude` session that loads the installed bpe 0.7.3 plugin, never `--plugin-dir ./bpe`.
Several steps edit the agents, the playbook, and the goal skill; with the installed copy loaded, those edits change the repo and not the loop that is running.
0.7.3 has batch mode, the final sweep, and the context checkpoint, so `/bpe:goal` (full) then `/goal @goal.md` runs the whole plan.

The loop gate is `just check` plus each step's Verify.
The recorded runs of interactive skills are a manual pass after the loop (see "After the Loop"), not loop work.

todo.md has one checkbox per step and no sub-step boxes, in the exact shape `render-artifact.py todo` will emit (Section 2), so the release can check that the renderer reproduces its own todo.md.

## Current Status

- [ ] Section 1: Loop Follow-Ups (#58)
- [ ] Section 2: Deterministic Artifact Checks and Templates
- [ ] Section 3: Structured Issue Format (#48)
- [ ] Section 4: What the Permanent Spec's Goals Holds (#55)
- [ ] Section 5: /bpe:init (#28)
- [ ] Section 6: Docs and Release

Ordering: Section 2 builds the two scripts before any skill is told to call them.
Section 3 needs Section 2's renderer for the `issue` kind.
Section 4 edits several skills that Section 2 already wired to the checker, so it lands on top of those edits.
Section 5 is independent of 3 and 4 and runs after them only to keep the shared skill files on a committed base.
Section 6 writes the docs once everything they describe exists.

## Section 1: Loop Follow-Ups (#58)

**Tools:**
- Skills: python:python, plugin-dev:agent-development
- MCPs: none
- Linters: uv run ruff check ., uv run ruff format --check .

**Batch:** loop-a

Rationale: Steps 1 to 3 touch the goal skill and the report script; Steps 4 and 5 are the two agent trims, batched separately because each moves a lot of text and the validator should judge the trims on their own.

### Step 1: Resume a Fully Checked todo.md into the Final Sweep (task)

**NOTE**: The playbook already runs the sweep when no `- [ ]` remains (`bpe/references/validator-protocol.md` "### Per Turn" step 3).
The only block is `/bpe:goal` pre-flight, which refuses "Zero unchecked items in `todo.md`" (`bpe/skills/goal/SKILL.md` Step 1).
Mason's decision (2026-11-19): pre-flight allows it, no new mode.

```text
1. Scope:
   - Artifact(s): bpe/skills/goal/SKILL.md, bpe/references/validator-protocol.md
   - Desired end state: /bpe:goal in full or section mode accepts a fully checked todo.md when no "Apply final sweep fixes" commit exists on the branch since main, and the goal.md it writes sends the first turn straight to the final sweep.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: grep, claude plugin validate

3. Do the work:
   - In bpe/skills/goal/SKILL.md Step 1, add to the parallel pre-flight block: git log --format=%s "$(git merge-base main HEAD)"..HEAD | grep -c '^Apply final sweep fixes$' || echo 0
   - Replace the refusal bullet "Zero unchecked items in `todo.md`." with three rules, one sentence per line:
     - Zero unchecked items and a sweep commit exists: refuse with "The run is finished: every todo item is checked and the final sweep already committed its fixes."
     - Zero unchecked items in step mode: refuse with "Step mode has no final sweep; there is nothing left to run."
     - Zero unchecked items, full or section mode, no sweep commit: do not refuse; say "Every todo item is checked; this run goes straight to the final sweep." and continue.
   - Add one sentence after those rules: a branch whose earlier sweep returned clean has no sweep commit, so a resumed run sweeps it again; that costs one final-validator dispatch and changes nothing.
   - In section mode, "zero unchecked items" means zero under the named section (match the playbook's section-mode wording).
   - In bpe/references/validator-protocol.md "### Per Turn" step 3, add one line: this also covers the first turn of a resumed run that starts with nothing unchecked, so the sweep is the first dispatch.
   - Do not change the goal.md template, the condition text, or any other playbook step.

4. Verify:
   - grep -n "goes straight to the final sweep" bpe/skills/goal/SKILL.md && grep -n "Apply final sweep fixes" bpe/skills/goal/SKILL.md && grep -n "resumed run" bpe/references/validator-protocol.md && ! grep -n "^- Zero unchecked items in \`todo.md\`\.$" bpe/skills/goal/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none (the skill text is the documentation)
```

### Step 2: Attribute SendMessage Continuation Usage in goal-run-report.py

**NOTE**: `bpe/scripts/goal-run-report.py` reads each subagent's usage from `<session>/subagents/agent-<agentId>.jsonl` and gives a SendMessage continuation a dispatch row with zero usage (module docstring, "Continuations (SendMessage) add a dispatch count and no second copy of the usage").
`.ai-sessions/research/batch-mode-comparison.md` line 73 records the consequence.
Load the script by path with importlib, as `tests/test_review_server.py` does.

```text
1. Investigate before writing tests:
   - Find the 0.7.3 Phase 2 goal-run session transcript (the comparison note names the run; search ~/.claude/projects/-home-mmegger-Code-MasonEgger-bpe-claude-code-plugin/*.jsonl for SendMessage tool_use blocks whose input names an agent id that also appears as an Agent tool_result agentId).
   - For one warm batch, confirm where the continuation's assistant turns land: in the same subagents/agent-<id>.jsonl as the implement dispatch (the spec's assumption) or elsewhere.
   - If they land elsewhere, follow what the transcript shows and append a "## Step 2" entry to .ai-sessions/implementation-notes.md in the Plan said / Deviated / Impact format.

2. RED: Write attribution tests first:
   - Create tests/test_goal_run_report.py with a module-scoped fixture that loads bpe/scripts/goal-run-report.py by path, and a helper that writes a minimal parent transcript plus one subagents/agent-<id>.jsonl into tmp_path.
     - Test that an implement Agent dispatch followed by two SendMessage continuations to the same agent id yields three dispatch rows whose token totals sum to the subagent file's total, with no double counting.
     - Test that each assistant entry is attributed to the dispatch whose window (its tool_use timestamp to its tool_result timestamp in the parent transcript) contains the entry's timestamp.
     - Test that an assistant entry outside every window is not attributed to any dispatch row (and is not silently added to the first one).
     - Test that a cold Agent dispatch with no continuations keeps its whole file's usage, so the 0.7.2 baseline arithmetic is unchanged.

3. Document the attribution rule:
   - Update the goal-run-report.py module docstring: continuations now get the usage of the entries inside their own window; replace the "no second copy of the usage" sentence.

4. GREEN: Write minimal code to make the tests pass:
   - In bpe/scripts/goal-run-report.py, record each dispatch's tool_use and tool_result timestamps while streaming the parent transcript.
   - Replace the per-agent-id usage cache with a pass over each subagent file that adds every assistant entry to the one dispatch row for that agent id whose window contains it.
   - Stdlib only; full type hints; no Any, no cast.

5. RED: Add an integration test:
   - Test that running main() on the fixture session prints a table whose continuation rows show non-zero minutes and cache-read tokens.

6. GREEN: Wire the window attribution into main() minimally.

7. REFACTOR: Remove any helper left with a single caller; keep variable names descriptive.

8. Verify meaningful test coverage of the attribution logic and run `just check`
```

### Step 3: Correct the Batch-Mode Comparison with Continuation Usage (task)

```text
1. Scope:
   - Artifact(s): .ai-sessions/research/batch-mode-comparison.md
   - Desired end state: the Phase 2 figures include continuation usage, and the understatement note at line 73 is replaced by a sentence saying the numbers were recomputed with the fixed script.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: uv run python bpe/scripts/goal-run-report.py <0.7.3 Phase 2 session transcript>

3. Do the work:
   - Run the fixed script on the same transcript the note was built from.
   - Update every Phase 2 number the note reports (dispatches, subagent minutes, subagent cache-read, and any derived comparison) to the new output.
   - Replace the two lines starting "The script finds no subagent transcript for SendMessage continuations" with one line stating the recompute date (2026-11-22 or the run date) and the script change.
   - Keep the 0.7.2 baseline numbers unchanged; if they differ on a rerun, stop and report Failure instead of editing them.

4. Verify:
   - ! grep -n "finds no subagent transcript for SendMessage" .ai-sessions/research/batch-mode-comparison.md

5. Document:
   - none (the note is the document)
```

### Step 4: Trim agents/step-executor.md Under 10,000 Characters (task)

**Batch:** loop-b

**NOTE**: The 2026-07-25 ruling keeps the loop contracts repeated across fresh-context agents on purpose.
Move procedure and examples into `bpe/references/step-executor-protocol.md`, which the agent reads at startup; keep the hard invariants in the agent body.

```text
1. Scope:
   - Artifact(s): bpe/agents/step-executor.md, bpe/references/step-executor-protocol.md
   - Desired end state: wc -c bpe/agents/step-executor.md reports under 10,000, the agent still states every hard invariant, and every moved paragraph exists in the protocol.

2. Tooling:
   - Skills: plugin-dev:agent-development
   - MCPs: none
   - External: wc, grep, claude plugin validate

3. Do the work:
   - Keep in the agent body: frontmatter unchanged, the mode routing, the per-mode procedure as short numbered steps, the return report templates verbatim, and the hard invariants (never commit to main or master, exactly one commit per finalize, never --no-verify, never amend, report blocks emitted verbatim with no prose outside them).
   - Move to bpe/references/step-executor-protocol.md: explanatory paragraphs, rationale, examples, and the "How to follow a referenced skill file" detail; in their place leave one line pointing at the protocol section by heading.
   - Do not change any rule's meaning; a moved sentence keeps its wording.
   - Do not touch frontmatter (name, model, tools, disallowedTools, description).

4. Verify:
   - test "$(wc -c < bpe/agents/step-executor.md)" -lt 10000 && grep -q -- "--no-verify" bpe/agents/step-executor.md && grep -qi "main" bpe/agents/step-executor.md && grep -q "Finalize-Report" bpe/agents/step-executor.md && claude plugin validate ./bpe

5. Document:
   - none
```

### Step 5: Trim agents/validator.md Under 10,000 Characters (task)

**Batch:** loop-b

```text
1. Scope:
   - Artifact(s): bpe/agents/validator.md, bpe/references/validator-protocol.md
   - Desired end state: wc -c bpe/agents/validator.md reports under 10,000, the agent still states its hard invariants, and every moved paragraph exists in the protocol.

2. Tooling:
   - Skills: plugin-dev:agent-development
   - MCPs: none
   - External: wc, grep, claude plugin validate

3. Do the work:
   - Keep in the agent body: frontmatter unchanged, "## Hard invariants" (never edits files, never commits, never dispatches agents, never runs tests, output is the findings block only), the inputs list, the procedure as short numbered steps, and the output format with the findings block shape.
   - Move to bpe/references/validator-protocol.md: the "## Anti-patterns" detail, "## What the orchestrator does with your output", and explanatory prose and examples; leave one pointer line per moved block.
   - Do not change any rule's meaning, the findings schema, or the report caps (notes 80 words, message 240 characters).

4. Verify:
   - test "$(wc -c < bpe/agents/validator.md)" -lt 10000 && grep -q "## Hard invariants" bpe/agents/validator.md && grep -q "findings" bpe/agents/validator.md && claude plugin validate ./bpe

5. Document:
   - none
```

## Section 2: Deterministic Artifact Checks and Templates

**Tools:**
- Skills: python:python, plugin-dev:skill-development
- MCPs: none
- Linters: uv run ruff check ., uv run ruff format --check .

**Batch:** checks-a

Rationale: spec item 5.
Steps 1 and 2 build the checker; Steps 3 to 5 build the renderer and wire both into the skills.
Both scripts are stdlib-only, take full type hints, start with the two-line ABOUTME header, and are tested by loading them by path with importlib.

### Step 1: check-artifacts.py for plan.md and todo.md

**NOTE**: Rules come from spec item 5.
A plan section is a `## ` heading followed by at least one `### Step` heading before the next `## ` heading; other `## ` headings (How This Plan Runs, Current Status, and so on) are not sections.
Step numbers run from 1 within each section.
A todo item's title is the plan step title with any trailing ` (task)` removed.

```text
1. RED: Write plan and todo check tests first:
   - Create tests/test_check_artifacts.py with a module-scoped fixture loading bpe/scripts/check-artifacts.py by path, and small plan/todo strings written into tmp_path per test.
     - Test that a step heading not matching `### Step N: <title>` (optional trailing ` (task)`) inside a section is a hard failure with rule `plan-step-heading`.
     - Test that step numbers 1, 2, 4 in one section fail with rule `plan-step-order`, and that numbering restarting at 1 in the next section passes.
     - Test that a section without a `**Tools:**` line fails with `plan-tools-missing`, and that `**Tools:** none` passes.
     - Test that a section without a `**Batch:**` line fails with `plan-batch-missing`, and that a per-step `**Batch:**` line under every step of the section also passes.
     - Test that a todo line under a section heading that starts with `- ` but is not `- [ ] ` or `- [x] ` fails with `todo-checkbox`.
     - Test that todo items that differ from the plan's steps (missing, extra, reordered, or retitled) fail with `todo-plan-mismatch`, naming the first differing step.
     - Test that the output line format is exactly `path:line: rule: message`.
     - Test that main() exits 1 when any hard failure prints and 0 when only warnings or nothing print.

2. Document the checker:
   - Write the module docstring: what each rule checks, the exit codes, and how the artifact type is detected (filename plan.md, todo.md, spec.md; anything else is an error).

3. GREEN: Create bpe/scripts/check-artifacts.py:
   - ABOUTME header; argparse taking one or more paths; when both plan.md and todo.md are given (or todo.md is given and plan.md sits beside it), run the todo-plan comparison.
   - One problem per line to stdout; exit 1 on any hard failure.
   - Stdlib only.

4. RED: Add an integration test:
   - Test that the checker run on this repo's own plan.md and todo.md exits 0.

5. GREEN: Fix whatever the integration test surfaces in the checker (not in plan.md).

6. REFACTOR: Keep one function per rule family only where it has a real reason to exist; no single-caller private helpers made only to shorten a function.

7. Verify meaningful test coverage and run `just check`
```

### Step 2: check-artifacts.py for spec.md

```text
1. RED: Write spec check tests first (in tests/test_check_artifacts.py):
   - Test that a spec with neither `## Invariants` nor `## Roadmap / phase log` prints exactly one warning with rule `spec-pre-0.7` and no other output, and exits 0.
   - Test that this repo's own spec.md exits 0 with only that warning.
   - Test that a 0.7-form spec with its canonical sections out of order fails with `spec-section-order`.
   - Test that `## External tool candidates` directly after `## Available tooling` is allowed (/bpe:plan writes it there).
   - Test that a 0.7-form spec whose Goals has no `### Feature Status` table warns `goals-status-table` and still exits 0.
   - Test that a Feature Status table whose header is not exactly Feature, State, Open Work, Docs, Code warns `goals-status-columns`.
   - Test that a `###` heading under Goals naming a version (e.g. `### 0.4.0 Material parity`), an issue (`(Issue #30)`), or the word "phase" warns `goals-phase-heading`, and that `### OAuth 2.0 Login` also warns (documented false positive; warnings never fail).
   - Test that `Planned(x):`, `Planned ():`, and `Known gap` without a colon warn `goals-marker`, and that `Planned (containers fixes): ...` passes.

2. Document:
   - Extend the module docstring with the spec rules and why Goals rules only warn.

3. GREEN: Implement the spec checks in bpe/scripts/check-artifacts.py:
   - Read the canonical order list as a constant matching bpe/references/session-management.md "## Spec Section Order (spec.md)"; add a test that parses that reference's numbered list and asserts it equals the constant, so the two cannot drift.

4. RED: Add the drift test described above.

5. GREEN: Make it pass.

6. REFACTOR: Share heading parsing between the plan and spec checks only if both use it identically.

7. Verify meaningful test coverage and run `just check`
```

### Step 3: render-artifact.py for todo and goal

**Batch:** checks-b

**NOTE**: Templates live in `bpe/templates/` as `string.Template` files (`$name` placeholders).
The todo shape is this plan's own todo.md: a `# Todo: <plan title without "Plan: ">` line, one fixed intro line, then per section a blank line, `## <section heading>`, a blank line, and one `- [ ] Step N: <title>` line per step.
The goal template is the fenced block in `bpe/skills/goal/SKILL.md` Step 3, with `<condition>`, `<mode>`, `<test-cmd>`, and `<branch>` becoming `$condition`, `$mode`, `$test_cmd`, `$branch`.

```text
1. RED: Write renderer tests first:
   - Create tests/test_render_artifact.py loading bpe/scripts/render-artifact.py by path.
     - Test that `todo` on a two-section plan emits the exact expected text.
     - Test that `todo` carries `[x]` over by step title from an existing todo.md beside the plan, and that a step whose title changed comes out unchecked.
     - Test that `todo` on this repo's plan.md reproduces this repo's todo.md byte for byte.
     - Test that `goal` with a JSON object {condition, mode, test_cmd, branch} on stdin emits the template with each value substituted and no `$` placeholder left.
     - Test that `goal` exits 1 and prints the length when the rendered text exceeds 4000 characters, and writes nothing to stdout.
     - Test that a missing JSON key exits 1 naming the key.

2. Document:
   - Module docstring: the kinds, their inputs (stdin JSON or plan.md), the output (stdout), exit codes.

3. GREEN: Create bpe/templates/todo.md.tmpl (header and intro only; the script emits the section and step lines), bpe/templates/goal.md.tmpl (copied verbatim from the goal skill's Step 3 block with placeholders converted), and bpe/scripts/render-artifact.py:
   - argparse with a positional kind; `todo` takes `--plan PATH` (default plan.md) and reads todo.md beside it when present.
   - Reuse no code from check-artifacts.py by import; the plan heading rules are restated in a few lines, and a test asserts both scripts agree on this repo's plan.md step list.

4. RED: Add the agreement test (render-artifact todo step list equals check-artifacts plan step list for this repo's plan.md).

5. GREEN: Make it pass.

6. REFACTOR: none beyond naming.

7. Verify meaningful test coverage and run `just check`
```

### Step 4: render-artifact.py for accomplishment

**Batch:** checks-b

**NOTE**: The accomplishment.md shape is "### accomplishment.md Template" in `bpe/references/session-management.md`.
Fields that are prose (the Spec Slice, What Got Done, and so on) come from the JSON; the script owns headings and order.

```text
1. RED: Write tests first (tests/test_render_artifact.py):
   - Test that `accomplishment` with a full JSON object emits every heading of the reference template in its order with the values in place.
   - Test that a list-valued field renders as one `- ` bullet per item.
   - Test that a missing required field exits 1 naming it.
   - Test that the heading list in bpe/templates/accomplishment.md.tmpl equals the headings in the session-management.md template block (drift test).

2. Document:
   - Add the kind and its JSON fields to the module docstring.

3. GREEN: Create bpe/templates/accomplishment.md.tmpl and add the `accomplishment` kind.

4. RED: none further.

5. GREEN: none further.

6. REFACTOR: Share the JSON loading and missing-key error between kinds.

7. Verify meaningful test coverage and run `just check`
```

### Step 5: Wire the Checker and Renderer into the Skills (task)

**Batch:** checks-b

```text
1. Scope:
   - Artifact(s): bpe/skills/plan/SKILL.md, bpe/skills/brainstorm/SKILL.md, bpe/skills/retrofit/SKILL.md, bpe/skills/apply-review/SKILL.md, bpe/skills/goal/SKILL.md
   - Desired end state: each caller named in spec item 5 runs the scripts by `${CLAUDE_PLUGIN_ROOT}/scripts/<name>.py` with `python3`, and todo.md, goal.md, and accomplishment.md are rendered, not written freehand.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: grep, claude plugin validate

3. Do the work:
   - plan/SKILL.md "## Output Format": todo.md is produced by `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-artifact.py todo > todo.md` after plan.md is written; then run `check-artifacts.py plan.md todo.md` and repair plan.md until it exits 0. Replace the sentence saying todo.md tracks each numbered sub-step: todo.md has one checkbox per step.
   - plan/SKILL.md Archive routine step 5: build the JSON for accomplishment.md and render it with `render-artifact.py accomplishment`.
   - brainstorm/SKILL.md and retrofit/SKILL.md Saving: run `check-artifacts.py` on the scratch spec before showing the diff; a hard failure is fixed before the diff is shown; warnings are listed with the diff.
   - apply-review/SKILL.md Step 4 or 5: after edits to spec.md, plan.md, or todo.md, run the checker on the edited file and report its output.
   - goal/SKILL.md Step 1: add `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-artifacts.py plan.md todo.md` to pre-flight and a refusal bullet for a hard failure that names it. Step 3: render goal.md with `render-artifact.py goal` from a JSON object; the script's exit 1 over the cap replaces the hand count; keep the "MUST NOT start with /goal" rule.
   - Do not change any other rule in these skills.

4. Verify:
   - grep -l "check-artifacts.py" bpe/skills/{plan,brainstorm,retrofit,apply-review,goal}/SKILL.md | wc -l | grep -qx 5 && grep -q "render-artifact.py todo" bpe/skills/plan/SKILL.md && grep -q "render-artifact.py goal" bpe/skills/goal/SKILL.md && grep -q "render-artifact.py accomplishment" bpe/skills/plan/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none (Section 6 updates CLAUDE.md)
```

## Section 3: Structured Issue Format (#48)

**Tools:**
- Skills: plugin-dev:skill-development, plugin-dev:command-development, python:python
- MCPs: none
- Linters: uv run ruff check ., uv run ruff format --check .

**Batch:** issues

### Step 1: issue-format.md, the GitHub Template, and the Sync Test

**NOTE**: Section names and order are fixed by spec item 2.
The template file is `.github/ISSUE_TEMPLATE/agent-ready.md` with GitHub's issue-template front matter (name, about, title, labels empty).

```text
1. RED: Write the sync test first:
   - Create tests/test_issue_format.py:
     - Test that the `## ` headings in .github/ISSUE_TEMPLATE/agent-ready.md, in order, equal the full ordered section list defined in bpe/references/issue-format.md (required and optional together, in their defined positions).
     - Test that issue-format.md marks exactly What Is Wanted, What We Already Know, and Acceptance Criteria as required.

2. Document the format:
   - Create bpe/references/issue-format.md: purpose (an agent picks up a conforming issue cold), the imperative-title rule, the six sections in order with required or optional, one or two lines per section on what goes in it, and a short conforming example. One sentence per line. Give the ordered section list a machine-readable form the test parses (a numbered list whose items are the exact headings followed by "(required)" or "(optional)").

3. GREEN: Create .github/ISSUE_TEMPLATE/agent-ready.md with front matter and the six headings, each followed by an HTML comment saying what goes there.

4. RED: none further.

5. GREEN: none further.

6. REFACTOR: none.

7. Verify meaningful test coverage and run `just check`
```

### Step 2: render-artifact.py for issue

```text
1. RED: Write tests first (tests/test_render_artifact.py):
   - Test that `issue` with JSON {title, sections: {heading: body}} emits the title line and the sections in issue-format.md order, skipping absent optional sections.
   - Test that a missing required section exits 1 naming it.
   - Test that an unknown section heading exits 1 naming it.
   - Test that the rendered body's headings pass the same order check as tests/test_issue_format.py uses.

2. Document:
   - Add the `issue` kind to the module docstring.

3. GREEN: Add the `issue` kind; read the section order from bpe/references/issue-format.md at run time (the numbered list) so the reference stays the single source.

4. RED: none further.

5. GREEN: none further.

6. REFACTOR: none beyond naming.

7. Verify meaningful test coverage and run `just check`
```

### Step 3: The /bpe:new-issue Skill (task)

```text
1. Scope:
   - Artifact(s): bpe/skills/new-issue/SKILL.md
   - Desired end state: /bpe:new-issue drafts a conforming issue, shows the full draft, and runs `gh issue create` only after an explicit yes.

2. Tooling:
   - Skills: plugin-dev:skill-development, plugin-dev:command-development
   - MCPs: none
   - External: claude plugin validate

3. Do the work:
   - Frontmatter: name new-issue; a third-person description with trigger phrases ("file an issue", "write up an issue", "open a GitHub issue for this"); model: sonnet; disable-model-invocation: true; allowed-tools covering Bash(gh:*), Bash(python3:*), Read, Write.
   - Body steps: read bpe/references/issue-format.md; gather What Is Wanted, What We Already Know, and Acceptance Criteria from the argument and the conversation, asking one question at a time only for a required section it cannot fill; build the JSON and render with `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-artifact.py issue`; show the full draft; on an explicit yes, write the body to a temp file made with mktemp -u and run `gh issue create --title ... --body-file ...`; print the issue URL. On anything but yes, post nothing.
   - State that it never posts without confirmation, and that /bpe:gh-issue is the reading side.

4. Verify:
   - test -f bpe/skills/new-issue/SKILL.md && grep -q "disable-model-invocation: true" bpe/skills/new-issue/SKILL.md && grep -q "render-artifact.py issue" bpe/skills/new-issue/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none (Section 6 covers README and CLAUDE.md)
```

### Step 4: /bpe:gh-issue Routes on the Format (task)

```text
1. Scope:
   - Artifact(s): bpe/skills/gh-issue/SKILL.md
   - Desired end state: gh-issue says it is the reading side, checks a fetched issue against issue-format.md, and routes conforming issues with acceptance criteria to plan and nonconforming ones (missing sections named) to brainstorm. It never refuses.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: claude plugin validate

3. Do the work:
   - Add an opening sentence: gh-issue fetches an existing issue by number, whoever wrote it; /bpe:new-issue writes issues.
   - Replace step 5's detail-level lists with the conformance rule; keep the reproduce-the-bug guidance in step 4.
   - Leave step 6's route bodies for Section 4 Step 4, which edits them for #55.

4. Verify:
   - grep -q "issue-format.md" bpe/skills/gh-issue/SKILL.md && grep -q "new-issue" bpe/skills/gh-issue/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none
```

## Section 4: What the Permanent Spec's Goals Holds (#55)

**Tools:**
- Skills: plugin-dev:skill-development
- MCPs: none
- Linters: none

**Batch:** goals-a

Rationale: spec item 3.
#55's "Changes, File by File" section (`gh issue view 55`) holds the line-level locations; each step reads it first.
The new rules key on the `### Feature Status` table: a spec without it keeps today's behavior.

### Step 1: The Goals Definition in session-management.md (task)

```text
1. Scope:
   - Artifact(s): bpe/references/session-management.md
   - Desired end state: a "## Goals Section (spec.md)" definition sits beside the Starting Context, Available Tooling, Invariants, and Roadmap definitions and states everything in spec item 3's first bullet group.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: gh issue view 55, grep

3. Do the work:
   - Add "## Goals Section (spec.md)" after "## Starting Context Section (spec.md)" or in canonical order with the other definitions: the feature index, planner depth, the `Planned (ITEM):` and `Known gap:` markers inline on the sentence, the `### Feature Status` table and its five columns, `### Rules Every Feature Follows`, the banned forms, Goals against CLAUDE.md, the 128 KB resync report, and a skeleton block like #55's "A Reference Shape".
   - Rewrite the "`## Goals` is the What..." sentence in "## Spec Section Order (spec.md)" to point at the new definition, and restate Component boundaries and Success criteria as standing descriptions.
   - Update "## Roadmap / Phase Log Section (spec.md)": `**Upcoming:**` items are now added by merge-mode brainstorm and gh-issue's plan route, not only by hand; the Archive routine's fold-in also edits Goals.
   - In "## Plan Archives", say the Spec Slice is captured before the fold-in.
   - Name the checker: `scripts/check-artifacts.py` warns on Goals shape.

4. Verify:
   - grep -q "^## Goals Section (spec.md)" bpe/references/session-management.md && grep -q "Planned (ITEM):" bpe/references/session-management.md && grep -q "Known gap:" bpe/references/session-management.md && grep -q "### Feature Status" bpe/references/session-management.md && grep -q "128 KB" bpe/references/session-management.md && uv run pytest tests/test_check_artifacts.py -q

5. Document:
   - none (the reference is the documentation)
```

### Step 2: Brainstorm Writes Entries, Not Phases (task)

```text
1. Scope:
   - Artifact(s): bpe/skills/brainstorm/SKILL.md
   - Desired end state: merge mode edits or adds feature entries with `Planned (ITEM):` sentences tied to a named `**Upcoming:**` item it adds; new-spec mode writes entries and the Feature Status table; the text no longer says merge mode "adds a phase".

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: gh issue view 55, grep

3. Do the work:
   - Rewrite the "Mode: New Spec or Merge" merge-mode paragraph per spec item 3's brainstorm bullet; keep the Q&A scoped to the change and keep the scratch-diff-confirm flow.
   - Add: the diff shown before saving adds no phase-, release-, or issue-named heading.
   - Adjacency pass: a candidate sorted "now" lands in an entry.
   - Saving: rewrite the Goals, Component boundaries, and Success criteria lines to point at the Goals definition; new-spec mode writes the Feature Status table.
   - A merge on a spec without the Feature Status table keeps today's behavior and suggests `/bpe:retrofit --resync`.

4. Verify:
   - ! grep -q "adds a phase" bpe/skills/brainstorm/SKILL.md && grep -q "Planned (ITEM):" bpe/skills/brainstorm/SKILL.md && grep -q "Feature Status" bpe/skills/brainstorm/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none
```

### Step 3: Plan From the Marker, Fold In on Archive (task)

```text
1. Scope:
   - Artifact(s): bpe/skills/plan/SKILL.md, bpe/skills/session-summary/SKILL.md
   - Desired end state: /bpe:plan plans a named Upcoming item's Planned sentences when the spec has a Feature Status table, stops when nothing is marked, and keeps today's behavior otherwise; the Archive routine has the fold-in; session-summary's archive prompt reaches the Shipped line and the fold-in.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: gh issue view 55, grep

3. Do the work:
   - plan/SKILL.md: after "## Honor the Spec's Fences", add "## What to Plan" with the three cases from spec item 3 (table and a named item; table and nothing marked: stop with a message naming the fix, which is a merge-mode brainstorm; no table: plan the section or package the user names and print one line suggesting `/bpe:retrofit --resync`). The plan header names the item.
   - Archive routine: add a fold-in step after the Shipped line, run only when the plan converged and the spec has the table, in the order spec item 3 gives, ending with show the diff and write after confirmation. A superseded or partial plan, or an old-shape spec, skips it.
   - session-summary/SKILL.md Step 5: run the Archive routine through the Shipped line and the fold-in, stopping only before the routine's fresh-plan step.

4. Verify:
   - grep -q "## What to Plan" bpe/skills/plan/SKILL.md && grep -qi "fold-in" bpe/skills/plan/SKILL.md && grep -qi "fold-in" bpe/skills/session-summary/SKILL.md && ! grep -q "stop after writing \`accomplishment.md\`" bpe/skills/session-summary/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none
```

### Step 4: gh-issue Routes Through Merge Mode and Planned Sentences (task)

**Batch:** goals-b

```text
1. Scope:
   - Artifact(s): bpe/skills/gh-issue/SKILL.md
   - Desired end state: the brainstorm route enters merge mode when spec.md exists; the plan route on a spec with the Feature Status table records the issue's change as Planned sentences and an Upcoming item, shows the diff, writes on confirmation, then plans that item.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: grep

3. Do the work:
   - Rewrite step 6's two route bodies per spec item 3's gh-issue bullet; a spec without the table keeps today's plan route.
   - Keep Section 3 Step 4's conformance routing unchanged.

4. Verify:
   - grep -q "merge mode" bpe/skills/gh-issue/SKILL.md && grep -q "Planned (ITEM):" bpe/skills/gh-issue/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none
```

### Step 5: Retrofit Builds and Checks Goals (task)

**Batch:** goals-b

```text
1. Scope:
   - Artifact(s): bpe/skills/retrofit/SKILL.md
   - Desired end state: the five retrofit bullets in spec item 3 hold: deeper repo read, Goals/Component boundaries/Success criteria described, resync checks entries and offers a rebuild, Structure Migration builds Goals, staged rebuild.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: gh issue view 55, grep

3. Do the work:
   - Apply each of the five bullets at the locations #55 names.
   - Add the 128 KB size report to resync, with the offer to move the longest entries' detail into linked files.
   - Point at "## Goals Section (spec.md)" in session-management.md instead of restating it.

4. Verify:
   - grep -q "Feature Status" bpe/skills/retrofit/SKILL.md && grep -q "128 KB" bpe/skills/retrofit/SKILL.md && grep -qi "changelog" bpe/skills/retrofit/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none
```

### Step 6: Review Units and README for Goals (task)

**Batch:** goals-b

```text
1. Scope:
   - Artifact(s): bpe/skills/review/SKILL.md, bpe/README.md
   - Desired end state: /bpe:review treats each Goals entry and the Feature Status table as decision units; the README's spec.md description matches the Goals definition.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: grep

3. Do the work:
   - review/SKILL.md, the spec.md bullet under "Filling in the content": each Goals feature entry is a unit, the Feature Status table is one unit, Planned sentences render visibly marked.
   - bpe/README.md: rewrite the spec.md paragraphs #55 names (feature-indexed Goals, markers, the status table, fold-in on archive).

4. Verify:
   - grep -q "Feature Status" bpe/skills/review/SKILL.md && grep -q "Feature Status" bpe/README.md && claude plugin validate ./bpe

5. Document:
   - none
```

## Section 5: /bpe:init (#28)

**Tools:**
- Skills: plugin-dev:skill-development, plugin-dev:plugin-settings, python:python
- MCPs: none
- Linters: uv run ruff check ., uv run ruff format --check .

**Batch:** init

### Step 1: The YAML Tier-Map Block and Its Test

**NOTE**: The test needs a YAML parser; add `pyyaml` and `types-PyYAML` to the `dev` dependency group in pyproject.toml (allowed by the `deps: frozen` constraint, which covers runtime only) and run `uv lock`.
The schema is "## Schema" in `bpe/references/model-profiles.md`.

```text
1. RED: Write the tier-map tests first:
   - Create tests/test_model_profiles.py:
     - Test that the newest `### YYYY-MM-DD` heading under "## Recommended Tier Map" is followed by exactly one fenced ```yaml block before the next heading.
     - Test that the block parses and has active_profile and profiles keys, and active_profile names a key under profiles.
     - Test that every skills key names a directory under bpe/skills/ and every agents key names a file under bpe/agents/.
     - Test that every value is an alias (opus, sonnet, haiku) or matches `claude-[a-z]+-[0-9]+(-[0-9]+)*`.

2. Document:
   - Under the 2026-11-09 heading in bpe/references/model-profiles.md, add one sentence saying the YAML block is the machine-readable copy /bpe:init reads, and update the "## Recommended Tier Map" intro sentence that says the example file mirrors this section: /bpe:init reads the newest block.

3. GREEN: Add the fenced YAML block under the 2026-11-09 heading, encoding that table as a `personal` profile (skills: brainstorm, plan, retrofit at claude-fable-5-2; review, apply-review at opus; agents: validator opus, final-validator claude-fable-5-2) in the bpe.local.md frontmatter schema. Add the dev dependencies and run `uv lock`.

4. RED: none further.

5. GREEN: none further.

6. REFACTOR: none.

7. Verify meaningful test coverage and run `just check`
```

### Step 2: The /bpe:init Skill (task)

```text
1. Scope:
   - Artifact(s): bpe/skills/init/SKILL.md
   - Desired end state: /bpe:init runs the profile interview and the repo pre-flight setup from spec item 4, with every write behind the user's consent, and carries the four 2026-11-03 decisions.

2. Tooling:
   - Skills: plugin-dev:skill-development, plugin-dev:plugin-settings
   - MCPs: none
   - External: claude plugin validate

3. Do the work:
   - Frontmatter: name init; third-person description with the trigger phrases "set up bpe", "bpe init", "configure bpe models", "update my bpe models", and a note that it is not the built-in /init; model: sonnet; disable-model-invocation: true.
   - Step 1, current state: read both profile locations, BPE_PROFILE, .gitignore entries, .ai-sessions/, and spec.md's Available tooling; on a re-run, list where the profile differs from the newest YAML block in ${CLAUDE_PLUGIN_ROOT}/references/model-profiles.md.
   - Step 2, profile: one AskUserQuestion per role group (spec-shaping skills; validator and final-validator; step-executor and execute-plan; cheap-research) with the YAML block's values as the recommended option, frontmatter defaults and alias-only as alternatives; then scope and whether to add a work profile. Show a diff before replacing an existing file. Never commit it; for a per-project file confirm .gitignore covers .claude/*.local.md and add the line only with consent.
   - Step 3, repo pre-flight: offer each missing piece the /bpe:goal pre-flight refuses on (gitignore entries for commit-msg.md and goal.md, .ai-sessions/ creation) and the verification-command probe (manifest autodetect as in /bpe:goal, else ask), recorded to spec.md's `**Verification command:**` when a spec exists.
   - Hard rules section: never edits skill or agent frontmatter; never switches the session model or edits settings.json; never commits.

4. Verify:
   - test -f bpe/skills/init/SKILL.md && grep -q "disable-model-invocation: true" bpe/skills/init/SKILL.md && grep -q "model-profiles.md" bpe/skills/init/SKILL.md && grep -q "AskUserQuestion" bpe/skills/init/SKILL.md && claude plugin validate ./bpe

5. Document:
   - none (Section 6)
```

### Step 3: Retire the Example Profile File (task)

```text
1. Scope:
   - Artifact(s): .claude/bpe.local.md.example (deleted), bpe/references/model-profiles.md, bpe/README.md
   - Desired end state: the example file is gone and nothing in bpe/ or README.md points at it; both point at /bpe:init.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: git rm, grep

3. Do the work:
   - git rm .claude/bpe.local.md.example
   - Replace each reference to it in bpe/references/model-profiles.md and bpe/README.md with a pointer to /bpe:init (the README's profile section keeps a short schema example inline if it has one).

4. Verify:
   - test ! -e .claude/bpe.local.md.example && ! grep -rn "bpe.local.md.example" bpe README.md

5. Document:
   - none (Section 6 updates CLAUDE.md)
```

## Section 6: Docs and Release

**Tools:** none

**Batch:** release

### Step 1: CLAUDE.md, READMEs, and Version 0.7.4 (task)

```text
1. Scope:
   - Artifact(s): CLAUDE.md, README.md, bpe/README.md, bpe/.claude-plugin/plugin.json
   - Desired end state: CLAUDE.md names /bpe:init, /bpe:new-issue, the issue template, check-artifacts.py, and render-artifact.py and drops the example hand-sync rule; both READMEs list the two new skills; plugin.json version is 0.7.4.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: grep, claude plugin validate, python3

3. Do the work:
   - CLAUDE.md: the scripts list under "Layout Under bpe/" gains the two scripts and bpe/templates/; "### Model Tiers" replaces the example-file sentence with "/bpe:init reads the newest YAML block in model-profiles.md"; add .github/ISSUE_TEMPLATE/ to the non-shipping list; the "only executable code" sentence counts five scripts.
   - README.md (root) and bpe/README.md: add /bpe:init and /bpe:new-issue to the skill lists.
   - bpe/.claude-plugin/plugin.json: version 0.7.4.

4. Verify:
   - grep -q '"version": "0.7.4"' bpe/.claude-plugin/plugin.json && ! grep -n "bpe.local.md.example" CLAUDE.md && python3 bpe/scripts/render-artifact.py todo | diff - todo.md && python3 bpe/scripts/check-artifacts.py plan.md todo.md && claude plugin validate ./bpe && just check

5. Document:
   - none
```

## After the Loop

The loop ends with the final sweep.
Then, before opening the PR, one interactive session with `claude --plugin-dir ./bpe` (installed bpe disabled at local scope) runs the manual pass from the spec's Verification list in scratch repos, with each spec diff saved for the PR body:

- Merge-mode brainstorm on a spec with entries.
- `/bpe:plan` on a marked spec, a table-but-unmarked spec, and an old-shape spec.
- Archive fold-in on a converged plan and a superseded one.
- A gh-issue plan-route cycle.
- `/bpe:retrofit --resync` on markwright at `274c4fd`.
- `/bpe:new-issue` drafting without posting; `/bpe:gh-issue` naming missing sections.
- `/bpe:init`: fresh run, idempotent re-run, both scopes.
- The skill-creator triggering eval for `/bpe:init`.

## Implementation Guidelines

- Python steps are test-first; `just check` is the gate after every Python step.
- Scripts are stdlib-only with full type hints, no Any or cast, descriptive names, and the two-line ABOUTME header; tests load hyphenated scripts by path with importlib.
- Skill and reference prose follows the writing hard rules: one sentence per line, no em or en dashes, no banned vocabulary.
- A rule lives in one reference; skills point at it.
- Never edit spec.md from the loop.

## Success Metrics

- Every todo item checked, every batch one commit with a session summary, the final sweep clean.
- `just check` green with the new tests: goal-run-report attribution, check-artifacts, render-artifact, issue-format sync, model-profiles block.
- `wc -c` under 10,000 for both trimmed agents.
- `render-artifact.py todo` reproduces todo.md and `check-artifacts.py plan.md todo.md` exits 0.
- `claude plugin validate ./bpe` passes with only the missing-icon warning.
- The manual pass recorded in the PR body.
