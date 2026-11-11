# Validator protocol

The contract between `bpe:goal` (orchestrator), `bpe:validator` (QA agent), and `bpe:step-executor` modes (`implement`, `fix`, `finalize`). Anyone changing one of those three must read this file first.

Executor-specific detail (mode-by-mode invariants, report field semantics, orchestrator verification steps) lives in the parallel file `references/step-executor-protocol.md`. This file owns the shared state machine and the validator's findings schema; that one owns the executor's dispatch shape.

## Roles

1. `bpe:goal` (orchestrator). Owns the per-step state machine. Reads the per-section Tools block from `plan.md`. Dispatches the executor and the validator(s) in the right order. Enforces the iteration cap. Never commits, never edits files.
2. `bpe:step-executor` (worker). Three modes: `implement` (TDD, no commit), `fix` (apply validator findings, no commit), `finalize` (session summary, commit, push). Owns the commit transaction in `finalize` only.
3. `bpe:validator` (QA). Read-only review of the uncommitted diff against MCPs and skills passed in by the orchestrator, and against the spec's fences (see "Spec fences" below). Emits a structured findings block. Never edits, never commits, never dispatches other agents.

## Per-step dispatch flow

For each unchecked item in `todo.md` the orchestrator runs this state machine. Sequential dispatches only; never parallel.

```
1. Dispatch step-executor (mode=implement)
     => TDD; leaves work uncommitted; returns "ready for validation"

2. Read the current section's Tools block (or legacy "Validator consults:") in plan.md.
     If it is "none" => skip to step 6.

3. iter = 1

4. Dispatch validator(s) with the section's MCP and skill lists.
     The validator also reads spec.md's fences itself; nothing is passed for that.
     Validator returns a findings block per the schema below.
     Orchestrator runs scripts/validate-findings.py on each block.
     A malformed block is a hard failure: stop the loop.

5. Inspect aggregated verdict:
     - verdict == "clean" or only "info" findings => go to step 6.
     - verdict in {"block", "warn"}:
         - if iter == 3: stop the loop, surface unresolved findings as Failure.
         - else: dispatch step-executor (mode=fix) with the findings; iter += 1; go to step 4.

6. Dispatch step-executor (mode=finalize)
     => Final test run, session summary, commit message, single commit, push.
```

## Orchestrator Playbook

The orchestrator reads this section at the start of every turn.
goal.md carries only the condition, the read instruction, and the hard rules, so this section is the procedure.

### Per Turn

1. `git rev-parse --abbrev-ref HEAD`; abort if main/master.
2. INTERRUPTION CHECK: last dispatch ended with no report block (limit pause, crash, kill)?
   Tree is untrusted: `git reset --hard && git clean -fd`; reset iter; redo the item from mode=implement.
3. Read first `- [ ]` in todo.md.
   None remain => run `<test-cmd>`, echo `git log origin/<branch>..HEAD`, stop.
4. Execute one state-machine step from this file against the current todo item (turn 1 implement, optional turns 2..K validator + fix, final turn finalize).
   Track per-step iter; reset it on a new todo item.
5. For a validator dispatch: read the current section's `**Tools:**` block in plan.md (or legacy `**Validator consults:**` line).
   If none or absent, skip validator and dispatch executor mode=finalize next turn.
   Otherwise pass the section name and its Skills, MCPs, and Linters verbatim to bpe:validator with Iteration=iter and Diff source=`git diff HEAD`.
   Pipe its ```findings``` block through `${CLAUDE_PLUGIN_ROOT}/scripts/validate-findings.py`; exit 1 => Failure (malformed output), stop.
6. Verdict handling: clean OR only info => next turn dispatches finalize (carry info findings into the finalize prompt as "Info findings: <list>").
   block/warn and iter<3 => next turn dispatches executor mode=fix with the validated findings block; iter+=1.
   block/warn and iter==3 => Failure, echo unresolved findings, echo RESUME, STOP.
7. For a finalize dispatch return: parse the Finalize-Report.
   VERIFY against the reported SHA (NOT HEAD; HEAD is unreliable if anything raced):
   a. git rev-parse HEAD must equal Commit-sha.
   b. `git show --stat --name-only <sha> | grep -E '^\.ai-sessions/session-.*\.md$'` must be non-empty.
   c. Tests field must indicate exit 0.
   Any check fails => echo "BPE rule violation: <details>", echo RESUME, STOP.
7b. Finalize Failure with test output and iter<3: build a finalize-test-failure block (see "Finalize-red recovery"), validate, dispatch mode=fix (iter+=1), resume.
   iter==3 or non-test failure => RESUME, STOP.
8. Echo `git log -1 --format="%h %s"` and `git status --short`.
   YOUR TURN ENDS.

### RESUME

- Read the Failure or rule-violation reason above.
- Fix root cause (code, hook, plan.md).
- Clean tree: `git commit -S -F commit-msg.md` if commit failed; `git reset --hard && git clean -fd` if partial.
- Mark todo.md `[x]` for any step you completed manually.
- Re-run: `/goal @goal.md` (picks up from first `- [ ]`).

### Hard Rules

- SEQUENTIAL dispatches only.
- Never /clear or /compact (kills the active /goal).
- Never commit on the subagent's behalf, even on Failure.
- Stop after 50 successful step completions with "dispatch cap reached".

## Interrupted dispatches (usage limits, crashes)

A dispatch that ends without its report block (`Implement-Report`, `Fix-Report`, `Finalize-Report`, or a ```findings``` block) was interrupted: a usage-limit pause, a crash, or a killed subagent. The tree it leaves behind is untrusted; a half-applied edit is worse than no edit, because the next dispatch builds on it without knowing it is partial.

Recovery, run by the orchestrator at the start of the next turn, before anything else:

1. `git reset --hard && git clean -fd`. This drops all uncommitted work, tracked and untracked, back to the last commit. It is safe because `/bpe:goal` pre-flight refuses to start with a dirty tree, so everything uncommitted belongs to the interrupted step.
2. Reset the per-step `iter` counter.
3. Redo the current todo item from `mode=implement`, regardless of how far the state machine had progressed. Validator findings from before the interruption are stale; do not carry them forward.

The commit is the only durable unit. Anything short of a verified finalize commit is disposable and gets rebuilt from the plan.

## Iteration cap

Three round trips through the fix loop. If the validator still reports `block` or `warn` after the third executor `mode=fix` dispatch, the orchestrator stops the per-step loop and surfaces the unresolved findings as a `Failure:` block to the `/goal` evaluator. The user resolves manually.

`info` findings never trigger a fix loop. They land in the final commit message body: the orchestrator carries them into the finalize dispatch prompt as an `Info findings:` block (a finalize dispatch is a fresh context and cannot read earlier validator output), and the executor appends them to the commit message.

## Finalize-red recovery

A `mode=finalize` dispatch runs the test suite one final time before it commits.
When that run goes red, the executor returns a `Failure:` block carrying the failing test output instead of a `Finalize-Report`.
The orchestrator, not the validator, recovers from it; the validator never runs tests, so it cannot produce this finding on its own.

The orchestrator synthesizes a findings block holding a single finding:

- `severity: block`
- `rule: finalize-test-failure`
- `message`: the failing test output trimmed to the failing assertion and the test name.
- `file`: the failing test file when the output names one, else the plan section name.

The orchestrator builds the block, pipes it through `scripts/validate-findings.py`, dispatches `step-executor mode=fix` with it, and then continues the normal validator -> finalize path.
The finalize red consumes one fix-loop iteration, under the same 3-iteration cap as any other `block` finding.
Halt the loop with RESUME only when `iter == 3`, or when the finalize `Failure:` is not a test failure (a commit rejection, a push rejection, or a missing session summary); those cases halt immediately.

## Severity guidance

- `block`: a correctness, security, or contract violation that the user would not want shipped. Triggers a fix loop.
- `warn`: a strong stylistic or maintainability concern grounded in the consulted skill or MCP. Triggers a fix loop. Use this when the diff works but does something the domain says not to do.
- `info`: noteworthy context for the commit record. Does not trigger a fix loop. Use sparingly; the commit-message log is not a notebook.

The verdict at the top of a findings block summarizes the worst severity present: `block` if any finding is block, `warn` if any finding is warn and none are block, `clean` if no findings or only info. `scripts/validate-findings.py` enforces this consistency.

## Findings schema (canonical)

The validator emits one JSON object. Top-level keys:

| Key | Type | Required | Notes |
|---|---|---|---|
| `validator` | string | yes | Agent identifier, conventionally `"bpe:validator"`. |
| `verdict` | string | yes | One of `"block"`, `"warn"`, `"clean"`. Consistency-checked against findings. |
| `iter` | integer (>=1) | yes | The fix-loop iteration this report belongs to. Starts at 1. |
| `findings` | list | yes | Zero or more finding objects. |
| `notes` | string | no | Free-form orchestrator-facing context. |

Each finding object:

| Key | Type | Required | Notes |
|---|---|---|---|
| `severity` | string | yes | One of `"block"`, `"warn"`, `"info"`. |
| `file` | string | yes | Repo-relative path the finding applies to. |
| `message` | string | yes | One-line description of the finding. |
| `line` | integer (>=1) | no | Specific line number when known. |
| `rule` | string | no | Short rule identifier like `"temporal.non-determinism"`. |
| `suggested_fix` | string | no | Concrete fix the executor can apply. |
| `reference` | string | no | URL or section pointer the user can follow. |

### Example

```json
{
  "validator": "bpe:validator",
  "verdict": "block",
  "iter": 1,
  "findings": [
    {
      "severity": "block",
      "file": "workflows/order.py",
      "line": 42,
      "rule": "temporal.non-determinism",
      "message": "Direct datetime.now() call inside a workflow",
      "suggested_fix": "Replace datetime.now() with workflow.now()",
      "reference": "https://docs.temporal.io/workflows#determinism"
    }
  ],
  "notes": "Consulted: temporal-docs MCP, temporal:temporal-developer skill"
}
```

## Linter-sourced findings

Findings the validator produces by running a declared linter use the same JSON schema as skill- and MCP-sourced findings; there is no linter-specific shape, and all sources land in the same findings block.
The `rule` field carries the linter check ID (e.g., `vale.OverusedPhrases`, `ansible-lint.no-changed-when`).
Severity maps from the linter's own levels: `block` for errors, `warn` for warnings, `info` for suggestions; a linter that emits errors only maps every hit to `block`.
The parsing and mapping procedure lives in `agents/validator.md` step 5 (Run declared linters).
Linters are declared per section or per step in plan.md; see the "Tools block" section below for the declaration format.
A linter that fails to run (not installed, config missing) is recorded in the block's `notes`, not emitted as a finding.

## MCP-unavailable findings

When a declared MCP cannot be loaded, the validator emits a `warn` finding with `rule: mcp-unavailable` so the orchestrator sees it in the verdict rather than only in free-text `notes`.
The `message` names the MCP that could not load and the reason when known; `file` is the plan section name, or `plan.md` when the section is unknown.
The validator still records the failure in `notes` and continues consulting the rest of the declared tools.
The finding participates in the fix loop like any other `warn`: the fix is usually a `plan.md` Tools-block correction, or confirming the MCP is configured in the session.

## Auto-discovery fallback

The orchestrator always passes explicit MCP and skill lists. If the validator is dispatched without lists (ad-hoc human use), it falls back to:

1. Use `ToolSearch` to list available MCP servers.
2. Read available skills from the session reminder list.
3. Single judgment pass: given the diff and the candidate tools, pick at most three that apply.
4. Consult only those.

The fallback path is for human debugging, not the automated loop. The validator's `notes` field should record which tools were consulted, regardless of how they were chosen.

## Tools block

Plan sections declare their tooling in a `**Tools:**` block immediately under the section heading:

```markdown
**Tools:**
- Skills: temporal:temporal-developer
- MCPs: mcp__temporal-docs__search_temporal_knowledge_sources
- Linters: ruff check --output-format=json
```

Three sub-fields, each comma-separated:

- `Skills`: skill identifiers. The executor invokes them while working; the validator consults them when reviewing the diff.
- `MCPs`: MCP tool or server names. Same dual use as Skills.
- `Linters`: shell commands. Validator-only; the validator runs them verbatim against the working tree as adversarial review.

A `**Tools:**` block per section shadows the project-wide default (the `## Available tooling` list in spec.md).
A `**Tools:**` block per step, placed immediately under the step's `### Step X:` heading, shadows the section default further: that step resolves against its own block alone.
A literal `**Tools:** none` disables validator dispatch for every step in that section.

### Transitional read of legacy plans

Plans written before 0.6.0 declare `**Validator consults:**` instead of `**Tools:**`.
The validator and orchestrator honor the legacy block name: treat it as a Tools block declaring Skills and MCPs with an empty Linters list.
New plans emit `**Tools:**` only.

## Tool-list propagation

`bpe:brainstorm` enumerates available MCPs and skills, asks the user which apply to the project, and writes them to `spec.md` under `## Available tooling`. `bpe:plan` propagates that list per-section under `**Tools:**` (legacy plans: `**Validator consults:**`, per the transitional read above). `bpe:goal` reads the per-section block when dispatching the validator for a step in that section.

## Spec fences

spec.md carries three fences that hold across every phase, defined in `references/session-management.md`: `## Invariants` (rules, some of them checkable), `## Non-goals` (never), and the `**Deferred:**` list under `## Roadmap / phase log` (not now).
Three layers enforce them.
The plan writer honors them when drafting (`skills/plan/SKILL.md`, "Honor the Spec's Fences").
The executor self-checks the diff against them before reporting ready (`skills/execute-plan/SKILL.md` step 8 interactively; the same check in `mode=implement`, per `step-executor-protocol.md`).
The validator checks them on every dispatch as an independent second look, reading spec.md itself; the orchestrator passes nothing for this.

Checks and the findings they produce:

| Fence | Check | Severity | `rule` |
|---|---|---|---|
| `- deps: frozen` | The diff touches a dependency manifest or lockfile (pyproject.toml, uv.lock, package.json, package-lock.json, Cargo.toml, Cargo.lock, go.mod, go.sum, or equivalents). Mechanical: `git diff HEAD --name-only`. | block | `spec.deps-frozen` |
| `- paths: <glob>[, <glob>]` | A changed file matches none of the globs. Mechanical: `git diff HEAD --name-only` against the globs. | block | `spec.paths` |
| Any other Invariants bullet | The diff violates the rule as written. Judged, grounded in the bullet's text. | block for a contract violation, warn for a pattern or style rule | `spec.invariant` |
| A `## Non-goals` entry | The diff implements something listed there. Judged. | block | `spec.non-goal` |
| A `**Deferred:**` entry | The diff implements something listed there. Judged. A scope leak, not a bonus: the fix is to remove it, or to promote the item into `## Goals` by a spec change. | warn | `spec.deferred` |

Fence findings use the same schema as every other finding.
`message` names the fence text and the offending file; `reference` points at the spec section.
A spec that lacks a section has no fence of that kind; do not invent one.
A section whose Tools block is `none` gets no validator dispatch and relies on the executor's self-check: the plan writer chose that cost trade-off, and the plan itself was drafted inside the fences.

## Hard rules

- Validator never edits files, never commits, never dispatches other agents.
- Executor `mode=fix` is the only mode that may start with a dirty tree.
- Executor `mode=finalize` is the only mode that commits or pushes.
- Orchestrator never commits, never edits, never bypasses the iteration cap.
- All findings blocks pass through `scripts/validate-findings.py` before being acted on.
