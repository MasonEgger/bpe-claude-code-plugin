---
name: goal
description: Autonomous-mode BPE run via /goal. Modes — full (default) | section <name> | step. Pre-flights branch safety (refuses on main, requires a clean tree), resolves the project verification command (test-runner autodetect, spec.md fallback, or ask), builds a verifiable completion condition, and writes the assembled /goal block (condition + validator-aware orchestrator playbook + per-commit verification) to goal.md at the repo root for you to paste. Requires Claude Code v2.1.139+; put your session in auto mode before pasting for unattended execution.
argument-hint: [full | section <name> | step]
model: sonnet
disable-model-invocation: true
---

# BPE Autonomous Goal

Set up a `/goal`-driven autonomous BPE run. The parent session orchestrates; each step is executed by the `bpe:step-executor` subagent in modes (`implement`, optional `fix` loop, `finalize`). When the step's plan.md section declares validators, `bpe:validator` runs between `implement` and `finalize` and the orchestrator drives the fix loop (max 3 iterations) per `${CLAUDE_PLUGIN_ROOT}/references/validator-protocol.md`. Fresh context per dispatch; the parent transcript stays tiny; the `/goal` evaluator watches it for completion.

**Requires Claude Code v2.1.139+.** Pairs well with `/auto`. The `/goal` command itself must still be run by the user; slash commands cannot invoke other slash commands programmatically, so this command writes the assembled `/goal` invocation to `goal.md` at the repo root and you paste it from there.

## Mode Routing

Parse `$ARGUMENTS`:

- empty or `full` — autonomous to the end of `todo.md`. **Default.** Use when you trust the plan and have time / quota.
- `section <name>` — autonomous through one labeled section of `todo.md`. A section is a top-level Markdown heading or an explicit comment block like `<!-- section: foo -->`.
- `step` — autonomous through ONE step. Rarely the right tool; for a single interactive step, `/bpe:execute-plan` is simpler. Use `step` only when you want the autonomous-mode contracts (SHA verification, session-summary-per-commit, push, validator pass) on a single item without driving it yourself.

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
- Zero unchecked items in `todo.md`.
- `commit-msg.md` is not gitignored. Tell the user to add it and re-run.
- `goal.md` is not gitignored. Tell the user to add it and re-run; this command writes the `/goal` block there as a working artifact.
- The verification-command cascade resolves nothing: no manifest match, no `**Verification command:**` field in spec.md, and the user didn't supply one.

The Tools-block count from pre-flight (`**Tools:**`, or legacy `**Validator consults:**`) is informational, not a refusal trigger. Zero is fine; the orchestrator treats every section as `none` and skips the validator loop.

Do NOT auto-create branches, auto-edit `.gitignore`, or auto-anything in pre-flight. These are deliberate decisions for the user.

## Step 2: Build the Goal Condition

Mode determines the condition. Substitute `<test-cmd>` with the verification command resolved in Step 1, `<branch>` with the current branch. When the resolved command is not a test runner (e.g. `vale docs/`), drop the "with no failing tests" clause from the condition; exit 0 of the command is the whole success signal.

**step:**
```
The next unchecked item in todo.md at the start of this run is now checked off; <test-cmd> exits 0 with no failing tests; git status --short is empty; the commit for the step is pushed to origin/<branch>.
```

**section <name>:**
```
Every item under the "<name>" section of todo.md is checked off; <test-cmd> exits 0; git status --short is empty; all commits for that section are pushed to origin/<branch>.
```

**full:**
```
Every item in todo.md is checked off; <test-cmd> exits 0 with no failing tests; git status --short is empty; all commits are pushed to origin/<branch>; .ai-sessions/lessons.md contains any new lessons captured during the run.
```

## Step 3: Write the `/goal` Argument to `goal.md`

`/goal` enforces a hard **4000-character cap** on its argument. STRICTLY enforce it: after substituting every placeholder, count the characters of the assembled file content from the condition line through the final `Mode:` line. If the count exceeds 4000, trim the orchestrator prose; NEVER the safety contracts, the per-turn steps, or the verification rules; and recount. NEVER write content over 4000 characters to `goal.md`. The condition leads (the evaluator focuses on its AND clauses); the orchestrator playbook follows in the same message.

The user will run `/goal @goal.md`. Claude Code's `@` expansion inlines the file contents as the `/goal` argument, so `goal.md` must contain ONLY the argument body. **The file MUST NOT start with `/goal `** or the expansion would produce `/goal /goal …`.

Use the Write tool to overwrite `goal.md` at the repo root with exactly the content below. Substitute `<condition>`, `<mode>`, `<test-cmd>`, and `<branch>` from steps 1–2. **Plain text only; no fenced code block, no surrounding ruler lines, no leading `/goal `.** The file contents ARE the `/goal` argument:

```
<condition from step 2>

You're the orchestrator for a validator-aware autonomous BPE run. Loop until the goal condition above is met.

READ ${CLAUDE_PLUGIN_ROOT}/references/validator-protocol.md ONCE AT TURN START. It defines the per-step state machine (implement -> validator + fix loop -> finalize), the findings schema, the iteration cap, and interrupted-dispatch recovery. Follow it exactly.

SEQUENTIAL DISPATCHES ONLY. One Agent call per turn. BPE steps share todo.md, git tree, test suite; parallel dispatches corrupt all three. After one dispatch + verification, YOUR TURN ENDS; the /goal evaluator decides if a new turn begins.

Each committed step is EXACTLY ONE commit. No fixups, amends, or --no-verify. Every commit includes a new .ai-sessions/session-*.md (the executor's mode=finalize creates it; you verify it landed). Any Failure or rule violation => echo RESUME (below) and STOP.

Per turn:
1. git rev-parse --abbrev-ref HEAD; abort if main/master.
2. INTERRUPTION CHECK: last dispatch ended with no report block (limit pause, crash, kill)? Tree is untrusted: git reset --hard && git clean -fd; reset iter; redo the item from mode=implement.
3. Read first `- [ ]` in todo.md. None remain => run <test-cmd>, echo `git log origin/<branch>..HEAD`, stop.
4. Execute one state-machine step from validator-protocol.md against the current todo item (turn 1 implement, optional turns 2..K validator + fix, final turn finalize). Track per-step iter; reset it on a new todo item.
5. For a validator dispatch: read the current section's `**Tools:**` block in plan.md (or legacy `**Validator consults:**` line). If none or absent, skip validator and dispatch executor mode=finalize next turn. Otherwise pass the section name and its Skills, MCPs, and Linters verbatim to bpe:validator with Iteration=iter and Diff source=`git diff HEAD`. Pipe its ```findings``` block through ${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py; exit 1 => Failure (malformed output), stop.
6. Verdict handling: clean OR only info => next turn dispatches finalize (carry info findings into the finalize prompt as "Info findings: <list>"). block/warn and iter<3 => next turn dispatches executor mode=fix with the validated findings block; iter+=1. block/warn and iter==3 => Failure, echo unresolved findings, echo RESUME, STOP.
7. For a finalize dispatch return: parse the Finalize-Report. VERIFY against the reported SHA (NOT HEAD; HEAD is unreliable if anything raced):
   a. git rev-parse HEAD must equal Commit-sha.
   b. git show --stat --name-only <sha> | grep -E '^\.ai-sessions/session-.*\.md$' must be non-empty.
   c. Tests field must indicate exit 0.
   Any check fails => echo "BPE rule violation: <details>", echo RESUME, STOP.
8. Echo `git log -1 --format="%h %s"` and `git status --short`. YOUR TURN ENDS.

RESUME:
- Read the Failure or rule-violation reason above.
- Fix root cause (code, hook, plan.md).
- Clean tree: `git commit -S -F commit-msg.md` if commit failed; `git reset --hard && git clean -fd` if partial.
- Mark todo.md `[x]` for any step you completed manually.
- Re-run: `/goal @goal.md` (picks up from first `- [ ]`).

Hard rules: SEQUENTIAL only. Never /clear or /compact (kills the active /goal). Never commit on the subagent's behalf, even on Failure. Stop after 50 successful step completions with "dispatch cap reached".

Mode: <mode>. Test: <test-cmd>. Branch: <branch>.
```

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

The goal loop halts on any `Failure:` from a subagent or `BPE rule violation:` from the orchestrator. The orchestrator playbook (Step 3) instructs the parent to echo a `RESUME:` block verbatim before stopping. That block is the recovery cheat-sheet; the paths below cover the common failure modes in more detail.

### Resume steps

1. **Read the failure reason.** The parent transcript contains the executor's `Failure:` report (schema in `${CLAUDE_PLUGIN_ROOT}/references/step-executor-protocol.md`) or the orchestrator's `BPE rule violation:` message.
2. **Fix the root cause.** Common cases:
   - Usage-limit pause, crash, or kill mid-dispatch: nothing to fix. The playbook's interruption check (per-turn step 2) resets the tree with `git reset --hard && git clean -fd` and redoes the item from `mode=implement` when the loop resumes. Half-finished dispatch work must never survive into the next dispatch; the commit is the only durable unit.
   - Tests red at implement-time: fix the code or the test.
   - Validator blocks at iter 3: adjust the section's `**Tools:**` block in `plan.md`, or change the code the validator objected to.
   - Pre-commit hook rejects: fix the hook config, or fix the change so the hook passes.
   - Push fails on auth or upstream: resolve auth, or pull upstream and rebase.
   - Session-summary missing on finalize verification: bug in the executor; fix the plugin file.
3. **Restore a clean tree.** Two paths, depending on where the failure landed:
   - **Finalize-stage failure** (commit or push): the work is done. Commit or push it manually. `git commit -S -F commit-msg.md` if the commit was rejected; `git push` if only the push failed.
   - **Implement- or fix-stage failure**: the work is partial and uncommitted. Either `git reset --hard && git clean -fd` to drop it (tracked edits and untracked leftovers both) and let the loop retry the step, or finish the step manually.
4. **Update `todo.md`.** Any step you completed manually needs its checkbox flipped to `- [x]` so the loop skips it on resume.
5. **Re-run.** `/goal @goal.md` picks up from the first `- [ ]` in `todo.md`. The orchestrator playbook, condition, mode, test command, and branch are all baked into `goal.md`, so the resume is a single invocation.

### When to regenerate goal.md

Re-run `/bpe:goal` before `/goal @goal.md` if any of these changed since the last invocation:

- **Mode.** Switching from `full` to `step` (or vice versa) requires a new goal.md so the condition matches.
- **Environment.** Test runner switched, branch was renamed, or plan.md's section names changed.
- **Plugin file fix.** Editing a subagent file (fresh per dispatch) doesn't need regeneration. Editing the orchestrator playbook (`skills/goal/SKILL.md` Step 3) does; re-run `/bpe:goal` to rewrite goal.md.

Do NOT `/goal clear` unless you want to abandon the current goal entirely. `clear` resets the evaluator's state; the next `/goal @goal.md` starts a fresh loop and the transcript loses the failure context.
