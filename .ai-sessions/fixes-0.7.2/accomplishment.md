# Accomplishment: BPE 0.7.2 Fixes

**Archived**: 2026-11-10
**Convergence**: converged

## Spec Slice

The `## 0.7.2 Fixes (2026-11-03, requested)` work package in spec.md: five fix items plus a version bump, traced to issues #50, #44, #49, #43, #38, #33, #36, and #47.
12 Task-shape steps across 6 sections.
The shipped goals above the package in spec.md were out of scope.

## What Got Done

- Section 1 (#50): the `claude-opus-4-8` frontmatter pins in five skills and the validator became the `opus` alias; `model-profiles.md` gained the dated 2026-11-09 Recommended Tier Map (Opus unpinned, Fable narrowed to brainstorm, plan, retrofit, and the final sweep), and `.claude/bpe.local.md.example` plus `bpe/README.md` were reconciled to it.
- Section 2 (#44, #49): both subagents dropped their `tools:` allowlists and inherit every MCP tool, with the validator kept read-only through `disallowedTools: Write, Edit, NotebookEdit`; a declared-but-absent MCP now yields a `warn` finding (`rule: mcp-unavailable`) and a non-fatal goal pre-flight warning; the false "executor consults MCPs" claim in `plan/SKILL.md` was corrected.
- Section 3 (#43): a red verification command at finalize time now synthesizes a single `block` finding (`rule: finalize-test-failure`) and re-enters the fix loop while the iteration cap allows, instead of halting the run.
- Section 4 (#38): `/bpe:plan --archive` archives and stops; `--archive --regen` archives then regenerates; the Archive routine's regeneration step is gated on `--regen`.
- Section 5 (#33, #36, #47): the review server keys its PID and URL files per artifact (sha256 of the resolved path), unlinks them only when self-owned, announces when it kills a predecessor, counts down from port 9000, requires a tailnet bind (or an explicit `--bind`), posts saves to a relative `/save`, injects Copy and Download recovery controls, renders the saved JSON on the Saved page, and logs POSTs and non-200 responses.
- Section 6: `bpe/.claude-plugin/plugin.json` reads 0.7.2.

## Deferred or Dropped

- `validator-protocol.md` schema table: the `file` row still says "repo-relative path" while `mcp-unavailable` findings put a plan section name there.
- `review-server.py` USAGE text for `--bind` predates the mandatory-tailnet contract.
- `socket.gaierror` subclasses `OSError`, so an unresolvable `--bind` host burns all 50 port attempts before failing with a "no free port" message.
- `os.kill(old_pid, 15)` could read `signal.SIGTERM` now that `signal` is imported.
- The rendered `goal.md` playbook sits at 3978 of 4000 characters; 0.7.3 should move playbook prose into the protocol reference before batch mode and the checkpoint add to it.
- `/bpe:retrofit --resync` stays deferred until the 0.7.x line ships, because its Structure Migration would have archived this package out of spec.md.

## Notable Decisions

- Inherit-plus-deny was chosen over an allowlist because a plugin agent cannot name per-project MCP tools; the Claude Code subagent docs confirm an omitted `tools:` inherits every MCP tool.
- The tailnet bind is mandatory with no loopback fallback and never `0.0.0.0`; `--bind 127.0.0.1` remains the explicit local option.
- Section 5 Step 2 added a SIGTERM handler the plan did not name, because Python exits on SIGTERM without running `finally`, so the self-owned unlink guard never ran on exactly the kill path it protects (recorded deviation).
- Section 4 inserted `--archive --regen` as rule 5 next to the `--archive` rule and renumbered `--regen` alone to rule 6 (recorded deviation).
- Four validator warn rounds each resolved at iteration 2: the `.example` contradicting the new map, one-sentence-per-line in `goal/SKILL.md`, missing docstrings on two re-signed functions, and the Saved page showing the argv path instead of the resolved one.
- The loop ran on the installed 0.7.1 plugin cache, so the new validator, executor, and server code were never exercised by the run that wrote them.

## Files Touched

33 files versus main (+1783/-99) across 14 commits on `release-0.7.2` before this archive commit.
Highlights: `bpe/scripts/review-server.py`, `bpe/agents/{validator,step-executor}.md`, `bpe/skills/{goal,plan,review,brainstorm,retrofit,apply-review}/SKILL.md`, `bpe/references/{validator-protocol,model-profiles,session-management}.md`, `.claude/bpe.local.md.example`, `bpe/README.md`, `bpe/.claude-plugin/plugin.json`, `spec.md`.

## Lessons Cross-Reference

- Resolve a caller-supplied path once at the argv boundary when several consumers read it (2026-11-09, from the Section 5 Step 5 warn).
- `navigator.clipboard` is undefined off a secure context, so a locally served page needs `execCommand('copy')` first (2026-11-09).
- `socket.gaierror` subclasses `OSError`; a bind-port loop that catches `OSError` swallows a bad host (2026-11-09).
- A `finally` cleanup is unreachable on SIGTERM in Python without a handler (2026-11-09, from Section 5 Step 2).
- State a consulted skill's mechanical rule in the dispatch prompt so the first draft lands correct (2026-11-09, from two warn rounds).
- Commit plan.md and todo.md before suggesting `/bpe:goal`, and settle the verification command at plan time (2026-11-09).
- Check for active dated work packages before running `/bpe:retrofit --resync` (2026-11-09).
- Plugin agent `tools:` allowlists cannot name per-project MCP tools; inherit-plus-deny is the portable shape (2026-11-09).
- Grep the tree for each issue's claim before triage; fixes land without `Closes` lines (2026-11-09).
- The transcript JSONL carries per-turn usage, so a hook can compute live context percentage (2026-11-09).
- Family aliases move drift into doc examples; one machine-readable tier map is the durable fix (2026-11-09).
- Any edit to the goal playbook must be re-rendered and measured against the 4000-character cap (2026-11-09).
