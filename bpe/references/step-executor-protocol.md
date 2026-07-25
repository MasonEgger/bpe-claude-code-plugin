# Step-executor protocol

Contract between `bpe:goal` (orchestrator), `bpe:step-executor` (worker), and the `/goal` evaluator. Anyone changing the executor's dispatch shape, mode routing, or report format must read this file first.

Parallel to `references/validator-protocol.md`, which owns the whole-loop state machine and the validator's findings schema. Cross-reference that file for how the executor's modes fit into the per-step dispatch flow; this file owns the executor's contract at each dispatch.

## Role

`bpe:step-executor` is the worker for `/bpe:goal` autonomous runs. It does one BPE step per dispatch. The orchestrator sets a `Mode:` field in the dispatch prompt that routes the executor into one of four flows:

- `Mode: implement`. Execute the plan's sub-steps for the next unchecked `todo.md` item. Leaves the tree dirty. No commit.
- `Mode: fix`. Apply validator findings. Dirty tree in, dirty tree out. No commit.
- `Mode: finalize`. Final test run, session summary, single commit, push. The only mode that mutates git state.
- No `Mode:` line. Backwards-compatible bundled flow. Runs implement then finalize in one dispatch. Retained for pre-validator callers.

The three-mode split lets the orchestrator interleave `bpe:validator` between implement and finalize per the state machine in `validator-protocol.md`.

## Mode contracts

Each row is a hard promise between the executor and the orchestrator. Violating a contract fires the orchestrator's SHA verification or tree-state check.

| Field | implement | fix | finalize | bundled |
|---|---|---|---|---|
| Tree state at start | clean | dirty | dirty | clean |
| Tree state at end | dirty | dirty | clean | clean |
| Commits made | 0 | 0 | exactly 1 | exactly 1 |
| Pushes made | 0 | 0 | exactly 1 | exactly 1 |
| Session summary written | no | no | yes | yes |
| Tests must pass by end | yes | yes | yes | yes |
| Report format | `Implement-Report` | `Fix-Report` | `Finalize-Report` | bundled |

Per-mode additions:

- `implement`: Executes whichever template shape plan.md declares for the current step (Feature or Task); the numbered sub-steps are followed as written. Dirty tree at start aborts with `Failure:`. This signals either the prior step did not finalize, or the orchestrator broke the SEQUENTIAL DISPATCHES rule.
- `fix`: Receives a `findings` JSON block matching the validator-protocol schema. Groups `block` and `warn` as must-fix; `info` is not fixed here (the orchestrator hands `info` to `finalize` for the commit body). A malformed findings block is a hard `Failure:`.
- `finalize`: EXACTLY one commit per dispatch. No follow-ups, no fixups, no amends, no `--no-verify`. A pre-commit hook rejection is `Failure:`; do not retry, do not bypass. If an issue is discovered after commit, that's `Failure:` too. The orchestrator will not make a follow-up commit.
- `bundled`: Runs `implement` then `finalize` inline. No validator handoff between them. Pre-validator legacy path.

## Hard invariants (all modes)

These hold regardless of mode. Violations abort the dispatch with `Failure:`.

- **One step per invocation.** Do the next unchecked `todo.md` item and nothing else. If done early, stop; the orchestrator re-dispatches.
- **Branch check first.** `git rev-parse --abbrev-ref HEAD` before any work. Abort on `main` or `master`.
- **Never `/clear` or `/compact`.** Would break the parent's `/goal` session. Unnecessary anyway; every dispatch has fresh context.
- **No user questions.** There is no user in autonomous mode. Make the reasonable call, or abort with `Failure:` if a load-bearing decision is truly ambiguous.
- **Always end with the mode's report block.** The `/goal` evaluator parses only the report from the parent transcript. No prose after the block.

## Report schemas

The orchestrator and `/goal` evaluator parse these fields from the executor's returned report. Every field is load-bearing. Concrete templates the agent emits live in `agents/step-executor.md`; this section owns the field semantics.

### Implement-Report

| Field | Purpose |
|---|---|
| `Mode:` | Routes the orchestrator's next dispatch decision. Value: `implement`. |
| `Step:` | Which todo item this covers. `N — <description>`. |
| `Files:` | Comma-separated paths modified. Cap at 120 chars; truncate with `…`. |
| `Tests:` | Test command + exit code + short result. Exit code must be `0`. |
| `Tree:` | `dirty (<insertions>+ <deletions>-)`. Must be dirty; implement never commits. |
| `TodoDelta:` | The `- [x] step N — <desc>` line that was checked off. |
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
| `Step:` | Same as implement. |
| `Files:` | Committed paths, ≤120 chars. |
| `Tests:` | Command + exit `0` + result. |
| `Commit:` | `<short-sha> <subject ≤80 chars>`. The orchestrator VERIFIES against this SHA (never HEAD). |
| `Push:` | `ok` or `failed: <reason>`. Any failure stops the loop. |
| `Status:` | `clean`, or `dirty: <reason>` when files remain uncommitted after the commit. A dirty value is a self-reported contract violation; the orchestrator treats it as a Failure. |
| `TodoDelta:` | The checked-off line. |
| `Lessons:` | `added: <count>` or `none`. |
| `Info-findings:` | `none` or the count appended to the commit body. |
| `Blockers:` | Same as implement. |

### Backwards-compatible bundled

Same shape as `Finalize-Report`, minus the `Mode:` and `Info-findings:` rows. Emitted when the dispatch prompt had no `Mode:` line.

`Step:`, `Files:`, `Tests:`, `Commit:`, `Push:`, `Status:`, `TodoDelta:`, `Lessons:`, `Blockers:`.

### Failure (any mode)

```
Mode:       <implement | fix | finalize | bundled>
Step:       <N — description>
Failure:    <one-line root cause>
Action:     <what was tried, what's needed next>
```

Emitted the moment any invariant fires. The orchestrator stops the per-step loop on any `Failure:` block.

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

- Executor `mode=fix` is the only mode that may start with a dirty tree.
- Executor `mode=finalize` is the only mode that commits or pushes.
- Every commit in the loop includes a new `.ai-sessions/session-*.md`.
- Exactly one commit per finalize dispatch. No amends, no fixups, no `--no-verify`.
- Sequential dispatches only. One `Agent` call per orchestrator turn.
