# Step-executor protocol

Contract between `bpe:goal` (orchestrator), `bpe:step-executor` (worker), and the `/goal` evaluator. Anyone changing the executor's dispatch shape, mode routing, or report format must read this file first.

Parallel to `references/validator-protocol.md`, which owns the whole-loop state machine and the validator's findings schema.
Cross-reference that file for how the executor's modes fit into the per-batch dispatch flow; this file owns the executor's contract at each dispatch.

## Role

`bpe:step-executor` is the worker for `/bpe:goal` autonomous runs. It does one batch of BPE steps per dispatch (a batch of one is a step).
The dispatch prompt names the batch and its steps.
The orchestrator sets a `Mode:` field in the dispatch prompt that routes the executor into one of four flows:

- `Mode: implement`. Execute the plan's sub-steps for each step of the batch, in order. Leaves the tree dirty. No commit.
- `Mode: fix`. Apply validator findings. Dirty tree in, dirty tree out (a final sweep fix may start clean). No commit.
- `Mode: finalize`. Final test run, session summary, single commit, push. The only mode that mutates git state.
- No `Mode:` line. Backwards-compatible bundled flow. Runs implement then finalize in one dispatch. Retained for pre-validator callers.

A dispatch may be a continuation.
The orchestrator sends `Mode: fix` or `Mode: finalize` to the agent that ran implement, through SendMessage.
The executor routes on the `Mode:` line of the latest message it received.

The three-mode split lets the orchestrator interleave `bpe:validator` between implement and finalize per the state machine in `validator-protocol.md`.

## Mode contracts

Each row is a hard promise between the executor and the orchestrator. Violating a contract fires the orchestrator's SHA verification or tree-state check.

| Field | implement | fix | finalize | bundled |
|---|---|---|---|---|
| Tree state at start | clean | dirty (clean for a final sweep fix) | dirty | clean |
| Tree state at end | dirty | dirty | clean | clean |
| Commits made | 0 | 0 | exactly 1 | exactly 1 |
| Pushes made | 0 | 0 | exactly 1 | exactly 1 |
| Session summary written | no | no | yes | yes |
| Tests must pass by end | yes | yes | yes | yes |
| Warm continuation | n/a | yes when sent by SendMessage | yes when sent by SendMessage | n/a |
| Report format | `Implement-Report` | `Fix-Report` | `Finalize-Report` | bundled |

A continuation that cannot proceed because its context is exhausted returns a `Failure:` block whose `Failure:` line reads `context exhausted`.
This one Failure triggers the orchestrator's cold fallback (playbook step 4 in `validator-protocol.md`) instead of stopping the loop.

Per-mode additions:

- `implement`: Does the batch's steps in order.
  For each step, executes whichever template shape plan.md declares (Feature or Task); the numbered sub-steps are followed as written.
  After each step, runs that step's Verify (or the project test command) and the spec-fence self-check, then checks off that step in todo.md, before starting the next step.
  A red Verify or a fence violation on any step is `Failure:` naming the step.
  Dirty tree at start aborts with `Failure:`.
  This signals either the prior batch did not finalize, or the orchestrator broke the SEQUENTIAL DISPATCHES rule.
  The spec-fence self-check comes from `skills/execute-plan/SKILL.md` step 8 (Invariants `deps:` and `paths:` mechanically against `git diff HEAD --name-only`, then prose Invariants, Non-goals, and Deferred against the diff; sections absent from spec.md impose nothing).
  A violation is a `Failure:` naming the fence and the files, never a workaround: there is no user to ask in autonomous mode, and the fix is a spec or plan change.
  The validator repeats the same checks independently on sections that declare Tools (see "Spec fences" in `validator-protocol.md`).
- `fix`: Receives a `findings` JSON block matching the validator-protocol schema. Groups `block` and `warn` as must-fix; `info` is not fixed here (the orchestrator hands `info` to `finalize` for the commit body). A malformed findings block is a hard `Failure:`.
- `finalize` with `Step: sweep`: commits the final sweep's fixes.
  It stages the fixed files and the session summary (slug `goal-final-sweep`), leaves todo.md alone, and reports `TodoDelta: none`.
- `finalize`: EXACTLY one commit per dispatch. No follow-ups, no fixups, no amends, no `--no-verify`. A pre-commit hook rejection is `Failure:`; do not retry, do not bypass. If an issue is discovered after commit, that's `Failure:` too. The orchestrator will not make a follow-up commit.
- `bundled`: Runs `implement` then `finalize` inline. No validator handoff between them. Pre-validator legacy path.

## Hard invariants (all modes)

These hold regardless of mode. Violations abort the dispatch with `Failure:`.

- **One batch per invocation; a batch of one is a step.** Do the batch's steps named in the dispatch prompt and nothing else.
  If done early, stop; the orchestrator re-dispatches.
- **Branch check first.** `git rev-parse --abbrev-ref HEAD` before any work. Abort on `main` or `master`.
- **Never `/clear` or `/compact`.** Would break the parent's `/goal` session.
  CHECKPOINT is an orchestrator-only action; the executor never checkpoints, in any mode.
- **No user questions.** There is no user in autonomous mode. Make the reasonable call, or abort with `Failure:` if a load-bearing decision is truly ambiguous.
- **Always end with the mode's report block.** The `/goal` evaluator parses only the report from the parent transcript. No prose after the block.

## Report schemas

The orchestrator and `/goal` evaluator parse these fields from the executor's returned report. Every field is load-bearing. Concrete templates the agent emits live in `agents/step-executor.md`; this section owns the field semantics.

### Implement-Report

| Field | Purpose |
|---|---|
| `Mode:` | Routes the orchestrator's next dispatch decision. Value: `implement`. |
| `Batch:` | The batch name from the dispatch prompt, or `single`. |
| `Step:` | Which todo items this covers. `N: <description>`, or `N-M: <batch name>` for a batch. |
| `Files:` | Comma-separated paths modified. Cap at 120 chars; truncate with `…`. |
| `Tests:` | Test command + exit code + short result. Exit code must be `0`. |
| `Tree:` | `dirty (<insertions>+ <deletions>-)`. Must be dirty; implement never commits. |
| `TodoDelta:` | One `- [x] Step N: <desc>` line per step checked off, each on its own line. |
| `Ready:` | Fixed string `for validation`. |
| `Blockers:` | `none` or one-line reason. |

### Fix-Report

| Field | Purpose |
|---|---|
| `Mode:` | Value: `fix`. |
| `Step:` | Same as implement. |
| `Iter:` | Fix-loop iteration received from orchestrator (1 to 3). |
| `Findings:` | Count received: `B block, W warn, I info`. |
| `Applied:` | Count of block+warn findings actually fixed. |
| `Deferred:` | `none` or `rule1: reason; rule2: reason` for findings that would not fix without breaking tests. |
| `Tests:` | Command + exit `0` + result. Green mandatory. |
| `Tree:` | Fixed value: `dirty`. |
| `Ready:` | Fixed string `for re-validation`. |
| `Blockers:` | Same as implement. |

### Finalize-Report

| Field | Purpose |
|---|---|
| `Mode:` | Value: `finalize`. |
| `Batch:` | Same as implement. |
| `Step:` | Same as implement. |
| `Files:` | Committed paths, ≤120 chars. |
| `Tests:` | Command + exit `0` + result. |
| `Commit:` | `<short-sha> <subject ≤80 chars>`. Exactly one commit per finalize dispatch, which is one per batch. The orchestrator VERIFIES against this SHA (never HEAD). |
| `Push:` | `ok` or `failed: <reason>`. Any failure stops the loop. |
| `Status:` | `clean`, or `dirty: <reason>` when files remain uncommitted after the commit. A dirty value is a self-reported contract violation; the orchestrator treats it as a Failure. |
| `TodoDelta:` | Same as implement: one line per step checked off. `none` for a final sweep finalize (`Step: sweep`), which checks off no todo items. |
| `Lessons:` | `added: <count>` or `none`. |
| `Info-findings:` | `none` or the count appended to the commit body. |
| `Blockers:` | Same as implement. |

### Backwards-compatible bundled

Same shape as `Finalize-Report`, minus the `Mode:` and `Info-findings:` rows. Emitted when the dispatch prompt had no `Mode:` line.

`Step:`, `Files:`, `Tests:`, `Commit:`, `Push:`, `Status:`, `TodoDelta:`, `Lessons:`, `Blockers:`.

### Report Budget

The orchestrator and the `/goal` evaluator read the report from the parent transcript, so its size counts against the parent's context.

- Report fields stay verbatim from the templates.
- No prose outside the report block, before or after.
- `Blockers:` and `Deferred:` are one line each.
- Detail goes in the session summary, which the orchestrator never reads.

The validator's findings block has matching caps (`message` 240 characters, `notes` 80 words), enforced by `scripts/validate-findings.py`; see "Findings schema (canonical)" in `validator-protocol.md`.

### Failure (any mode)

```
Mode:       <implement | fix | finalize | bundled>
Step:       <N>: <description>
Failure:    <one-line root cause>
Action:     <what was tried, what's needed next>
```

Emitted the moment any invariant fires.
The orchestrator stops the loop on any `Failure:` block, with two exceptions.
A finalize test failure under the iteration cap re-enters the fix loop (playbook step 7b).
A continuation `Failure: context exhausted` takes the cold fallback (playbook step 4).

## What the /goal evaluator must see

The evaluator reads only the parent transcript, and the parent sees only the executor's final report. Every AND clause of the goal condition must be verifiable from the report:

- Mode (tells the evaluator whether a commit is expected).
- Test command + exit status.
- `git status --short` after the dispatch (clean for `finalize`, dirty for `implement` and `fix`).
- For `finalize`: commit SHA, push result, todo item checked off.

## Orchestrator verification

After a `finalize` dispatch returns, the orchestrator verifies against the reported SHA (never HEAD, which is unreliable under race):

1. `git rev-parse HEAD` equals the `Commit:` short SHA.
2. `git show --stat --name-only <sha> | grep '^\.ai-sessions/session-.*\.md$'` returns non-empty.
3. `Tests:` field indicates exit 0.

Any check fails => `BPE rule violation: <details>`, echo RESUME, STOP. The exact commands and stop behavior live in `skills/goal/SKILL.md`'s orchestrator playbook.

## Hard rules (shared with validator-protocol.md)

- Executor `mode=fix` is the only mode that may start with a dirty tree (a final sweep fix may also start clean).
- Executor `mode=finalize` is the only mode that commits or pushes.
- Every commit in the loop includes a new `.ai-sessions/session-*.md`.
- Exactly one commit per finalize dispatch. No amends, no fixups, no `--no-verify`.
- Sequential dispatches only. One `Agent` call per orchestrator turn.
