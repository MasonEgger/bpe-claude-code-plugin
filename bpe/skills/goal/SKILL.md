---
name: goal
description: Autonomous-mode BPE run via /goal. Modes are full (default) | section <name> | step. Pre-flights branch safety (refuses on main, requires a clean tree), resolves the project verification command (test-runner autodetect, spec.md fallback, or ask), builds a verifiable completion condition, and writes the assembled /goal block (condition + a read instruction pointing at the orchestrator playbook in references/validator-protocol.md + the hard rules) to goal.md at the repo root for you to paste. Requires Claude Code v2.1.139+; put your session in auto mode before pasting for unattended execution.
argument-hint: "[full | section <name> | step]"
model: sonnet
disable-model-invocation: true
---

# BPE Autonomous Goal

Set up a `/goal`-driven autonomous BPE run.
The parent session orchestrates; each batch is executed by the `bpe:step-executor` subagent in modes (`implement`, optional `fix` loop, `finalize`).
The executor runs per batch and stays warm across a batch's modes; the orchestrator continues it with `SendMessage`.
A batch of one is a step.
When the batch's plan.md section declares validators, `bpe:validator` runs cold between `implement` and `finalize` and the orchestrator drives the fix loop (a base cap of 3 validator passes per batch, extended to at most 5 while the findings keep shrinking) per `${CLAUDE_PLUGIN_ROOT}/references/validator-protocol.md`.
The parent transcript stays tiny; the `/goal` evaluator watches it for completion.

**Requires Claude Code v2.1.139+.** Pairs well with `/auto`. The `/goal` command itself must still be run by the user; slash commands cannot invoke other slash commands programmatically, so this command writes the assembled `/goal` invocation to `goal.md` at the repo root and you paste it from there.

## Mode Routing

Parse `$ARGUMENTS`:

- empty or `full`: autonomous to the end of `todo.md`. **Default.** Use when you trust the plan and have time / quota.
- `section <name>`: autonomous through one labeled section of `todo.md`. A section is a top-level Markdown heading or an explicit comment block like `<!-- section: foo -->`.
- `step`: autonomous through ONE step. Rarely the right tool; for a single interactive step, `/bpe:execute-plan` is simpler. Use `step` only when you want the autonomous-mode contracts (SHA verification, session-summary-per-commit, push, validator pass) on a single item without driving it yourself.

State the routed mode in user-facing text before pre-flight.

## Step 1: Pre-Flight Checks (refuse on any failure)

Run these in parallel and surface results in user-facing text:

```bash
git rev-parse --abbrev-ref HEAD
git status --short
test -f plan.md && echo "plan: yes" || echo "plan: NO"
test -f todo.md && echo "todo: yes" || echo "todo: NO"
grep -c '^- \[ \]' todo.md 2>/dev/null || echo 0
grep -q '^commit-msg\.md$' .gitignore && echo "gitignore commit-msg.md: ok" || echo "gitignore commit-msg.md: MISSING"
grep -q '^goal\.md$' .gitignore && echo "gitignore goal.md: ok" || echo "gitignore goal.md: MISSING"
grep -cE '^\*\*(Tools|Validator consults):\*\*' plan.md 2>/dev/null || echo 0
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-artifacts.py plan.md todo.md
git log --format=%s "$(git merge-base main HEAD)"..HEAD | grep -c '^Apply final sweep fixes$' || echo 0
```

Then resolve the verification command through a three-stage cascade:

1. Autodetect the test runner by manifest file:
   - `pyproject.toml` present → `pytest -q`
   - `package.json` present → `npm test --silent`
   - `Cargo.toml` present → `cargo test --quiet`
   - `go.mod` present → `go test ./...`
2. No manifest match → read spec.md's `## Available tooling` section for a `**Verification command:**` field (format documented in `${CLAUDE_PLUGIN_ROOT}/references/session-management.md`). If present, use its value verbatim.
3. Still nothing → ask the user for the exact verification command and use what they provide.

The resolved command need not be a test runner; for a prose or config project it can be any exit-0-on-success check (e.g. `vale docs/`). Whatever resolves substitutes for `<test-cmd>` in steps 2-3, and its exit 0 is the goal condition's success signal.

**Refuse and stop if any of these are true:**

- Branch is `main` or `master`. Tell the user: "Refusing to run autonomous mode on main. Create a feature branch first: `git checkout -b <branch-name>`."
- `git status --short` is non-empty. Tell the user: "Refusing to start with uncommitted or untracked changes. The goal loop's interruption recovery resets the tree to HEAD (`git reset --hard && git clean -fd`) and would destroy them. Commit or stash first."
- `plan.md` or `todo.md` is missing.
- `check-artifacts.py plan.md todo.md` exits 1. Print its output and tell the user to repair plan.md or todo.md and re-run (re-render todo.md with `render-artifact.py todo --output todo.md` after a plan fix). This includes a legacy plan with no `**Tools:**` line (a `**Validator consults:**` block only) or no `**Batch:**` line; the fix is to add those lines to each section.
- Zero unchecked items in `todo.md`, and a commit with the subject "Apply final sweep fixes" exists on the branch since main. Tell the user: "The run is finished: every todo item is checked and the final sweep already committed its fixes."
- Zero unchecked items in `todo.md` in step mode. Tell the user: "Step mode has no final sweep; there is nothing left to run."
- `commit-msg.md` is not gitignored. Tell the user to add it and re-run.
- `goal.md` is not gitignored. Tell the user to add it and re-run; this command writes the `/goal` block there as a working artifact.
- The verification-command cascade resolves nothing: no manifest match, no `**Verification command:**` field in spec.md, and the user didn't supply one.

Zero unchecked items in full or section mode, with no sweep commit on the branch, is not a refusal.
Say "Every todo item is checked; this run goes straight to the final sweep." and continue.
In section mode, "zero unchecked items" means zero under the named section.
A branch whose earlier sweep returned clean has no sweep commit, so a resumed run sweeps it again; that costs one final-validator dispatch and changes nothing.

The Tools-block count from pre-flight (`**Tools:**`, or legacy `**Validator consults:**`) is informational, not a refusal trigger. Zero is fine; the orchestrator treats every section as `none` and skips the validator loop.

**Warn (do not refuse) on a declared-but-absent MCP.**
For each plan section's `**Tools:**` block, read its `MCPs:` sub-field (skip `none`, a missing sub-field, or a legacy `**Validator consults:**` block with no MCPs).
For each MCP named, check whether it is present in the session: use `ToolSearch` with `select:<name>` (or scan the session's tool list) and treat a tool that will not resolve as not present in the session.
When an MCP is not present in the session, print a warning naming the section and the MCP, then continue; the validator will re-check at dispatch and emit an `mcp-unavailable` finding if it still cannot load.
This is a warning only, distinct from the hard refusals above; it never stops the run.

Do NOT auto-create branches, auto-edit `.gitignore`, or auto-anything in pre-flight. These are deliberate decisions for the user.

## Step 2: Build the Goal Condition

Mode determines the condition. Substitute `<test-cmd>` with the verification command resolved in Step 1, `<branch>` with the current branch. When the resolved command is not a test runner (e.g. `vale docs/`), drop the "with no failing tests" clause from the condition; exit 0 of the command is the whole success signal.

**step:**
```
The next unchecked item in todo.md at the start of this run is now checked off; <test-cmd> exits 0 with no failing tests; git status --short is empty; the commit for the step is pushed to origin/<branch>.
```

**section <name>:**
```
Every item under the "<name>" section of todo.md is checked off; <test-cmd> exits 0; git status --short is empty; all commits for that section are pushed to origin/<branch>; the final sweep returned clean.
```

**full:**
```
Every item in todo.md is checked off; <test-cmd> exits 0 with no failing tests; git status --short is empty; all commits are pushed to origin/<branch>; the final sweep returned clean; .ai-sessions/lessons.md contains any new lessons captured during the run.
```

## Step 3: Write the `/goal` Argument to `goal.md`

`/goal` enforces a hard **4000-character cap** on its argument.
The renderer enforces it: `render-artifact.py goal` exits 1 and prints the length when the assembled text runs over, and writes no output.
If it exits 1, shorten the `condition` value (the only free-form input) and render again; NEVER trim the safety contracts or the verification rules in the template, and NEVER write over-cap content to `goal.md`.
The condition leads (the evaluator focuses on its AND clauses); the orchestrator prose follows in the same message.
The procedure itself lives in `${CLAUDE_PLUGIN_ROOT}/references/validator-protocol.md` "## Orchestrator Playbook", which the orchestrator reads at the start of every turn.
The template (`${CLAUDE_PLUGIN_ROOT}/templates/goal.md.tmpl`) keeps only the condition, the read instruction, and the hard rules, so a procedure change no longer needs goal.md regeneration.

The user will run `/goal @goal.md`. Claude Code's `@` expansion inlines the file contents as the `/goal` argument, so `goal.md` must contain ONLY the argument body. **The file MUST NOT start with `/goal `** or the expansion would produce `/goal /goal …`.

Do not write goal.md by hand.
Build a JSON object with the keys `condition` (from step 2), `mode`, `test_cmd`, and `branch` (from steps 1-2).
Write it to a `mktemp` path outside the repo, never into the working tree: an untracked file there would read as a dirty tree on the first `/goal` turn.
Then render it:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-artifact.py goal --output goal.md < <json-file>
```

The output is plain text only: no fenced code block, no surrounding ruler lines, no leading `/goal `. The file contents ARE the `/goal` argument.
Count the characters of the written file for the report line below (`wc -m goal.md`).

After writing the file, print this in user-facing text; concise, no fenced /goal block, no tilde rulers, no inlined contents:

```
Wrote /goal argument to goal.md (Mode: <mode>, Test: <test-cmd>, Branch: <branch>, length: <N>/4000 chars).
Run with: /goal @goal.md
Put your session into auto mode first, so subagent tool calls don't prompt you mid-loop.
If the loop stops on Failure or a rule violation, follow the RESUME block the parent echoes; see Step 5 for the full recovery paths.
```

Do NOT paste the contents of `goal.md` inline. The whole point of writing to a file is to avoid dumping a multi-thousand-character block into the transcript every invocation; and the user no longer needs to copy anything, since `@goal.md` will inline the file at invocation time.

## Step 4: Do NOT Run It Yourself

This command writes the `/goal` argument to disk; it does not execute it. The user must run `/goal @goal.md` themselves; slash commands can't invoke other slash commands programmatically. If the user asks you to "just run it," remind them they need to type `/goal @goal.md` so the `/goal` evaluator owns the session loop.

## Step 5: Resume Path on Failure

The goal loop halts on any `Failure:` from a subagent or `BPE rule violation:` from the orchestrator, with two exceptions.
A `mode=finalize` `Failure:` that carries failing test output and arrives with `iter < 3` re-enters the fix loop (playbook step 7b in `validator-protocol.md`) instead of halting, and only halts when `iter` is 3 or more or the failure is not a test failure.
A continuation `Failure: context exhausted` also does not halt; it takes the cold fallback (playbook step 4).
A `CHECKPOINT:` block is a pause, not a failure: the orchestrator echoes it and STOPs; see "Resuming from a CHECKPOINT" below.
The orchestrator playbook (`validator-protocol.md` "## Orchestrator Playbook") instructs the parent to echo its `### RESUME` block verbatim before stopping.
That block is the recovery cheat-sheet; the paths below cover the common failure modes in more detail.

### Resume steps

1. **Read the failure reason.** The parent transcript contains the executor's `Failure:` report (schema in `${CLAUDE_PLUGIN_ROOT}/references/step-executor-protocol.md`) or the orchestrator's `BPE rule violation:` message.
2. **Fix the root cause.** Common cases:
   - Usage-limit pause, crash, or kill mid-dispatch: nothing to fix.
     The playbook's interruption check (playbook step 2 in `validator-protocol.md`) resets the tree with `git reset --hard && git clean -fd` and redoes the item from `mode=implement` when the loop resumes.
     Half-finished dispatch work must never survive into the next dispatch; the commit is the only durable unit.
   - Tests red at implement-time: fix the code or the test.
   - Validator still reports block or warn at the iteration cap: adjust the section's `**Tools:**` block in `plan.md`, or change the code the validator objected to.
   - Pre-commit hook rejects: fix the hook config, or fix the change so the hook passes.
   - Push fails on auth or upstream: resolve auth, or pull upstream and rebase.
   - Session-summary missing on finalize verification: bug in the executor; fix the plugin file.
3. **Restore a clean tree.** Two paths, depending on where the failure landed:
   - **Finalize-stage failure** (commit or push): the work is done. Commit or push it manually. `git commit -S -F commit-msg.md` if the commit was rejected; `git push` if only the push failed.
   - **Implement- or fix-stage failure**: the work is partial and uncommitted. Either `git reset --hard && git clean -fd` to drop it (tracked edits and untracked leftovers both) and let the loop retry the step, or finish the step manually and commit it.
   - **Edits to `plan.md` or a plugin file** made while fixing the root cause: commit them too, or discard them on purpose.
     `/goal @goal.md` skips pre-flight, and a fresh context treats any dirty tree as an interrupted batch and resets it, which would discard the edits.
     Do not rely on an exception for a context that still holds the batch's agent id; commit first.
4. **Update `todo.md`.** Any step you completed manually needs its checkbox flipped to `- [x]` so the loop skips it on resume.
5. **Re-run.** The tree must be clean first (see step 3). `/goal @goal.md` picks up from the first `- [ ]` in `todo.md`.
   The condition, mode, test command, and branch are baked into `goal.md`, and the playbook is read fresh each turn, so the resume is a single invocation.

### Resuming from a CHECKPOINT

When the playbook ends a turn with a `CHECKPOINT:` block, the context is nearly full and nothing is wrong.
Run `/clear`, then `/goal @goal.md`.
No regeneration is needed: goal.md carries the condition and the playbook is read fresh each turn.
The tree must be clean or hold only the interrupted batch's work: commit any edit of your own first, because the fresh context resets every uncommitted change.
The next run starts at the first `- [ ]`.
A dirty tree from a mid-batch checkpoint is reset by the playbook's fresh-context reset (step 2: no recorded agent id and a non-empty `git status --short`), and the batch is redone from `mode=implement`.

### When to regenerate goal.md

Re-run `/bpe:goal` before `/goal @goal.md` if any of these changed since the last invocation:

- **Mode.** Switching from `full` to `step` (or vice versa) requires a new goal.md so the condition matches.
- **Environment.** Test runner switched, branch was renamed, or plan.md's section names changed.
- **Plugin file fix.** Editing a subagent file (fresh per dispatch) doesn't need regeneration.
  Editing `references/validator-protocol.md` "## Orchestrator Playbook" takes effect on the next turn with no regeneration.
- **Template change.** Editing `templates/goal.md.tmpl` still requires re-running `/bpe:goal` to rewrite goal.md.

Do NOT `/goal clear` unless you want to abandon the current goal entirely. `clear` resets the evaluator's state; the next `/goal @goal.md` starts a fresh loop and the transcript loses the failure context.
