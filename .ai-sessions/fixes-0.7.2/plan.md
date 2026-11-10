# Plan: bpe 0.7.2 Fixes

Implements the `## 0.7.2 Fixes (2026-11-03, requested)` work package in spec.md.
Five work items plus a version bump, traced to issues #50, #44, #49, #43, #38, #33, #36, #47.

Every step is Task-shape (Scope / Tooling / Do / Verify / Document). No TDD: the repo has no test harness, and review-server changes are verified by serving, matching the package's own verification list. Only the 0.7.2 package is planned here; the shipped goals above it in spec.md are out of scope.

## Current Status

- [ ] Section 1: Model tier aliases (#50)
- [ ] Section 2: Subagent MCP access (#44, #49)
- [ ] Section 3: Finalize-red recovery (#43)
- [ ] Section 4: plan --archive archives only (#38)
- [ ] Section 5: Review server reliability (#33, #36, #47)
- [ ] Section 6: Version bump and docs (#50 tail)

Ordering note: Sections 1 and 2 both edit `agents/validator.md` frontmatter; 2, 3, and 4 share `plan/SKILL.md`, `goal/SKILL.md`, and `references/validator-protocol.md`. Running 1 → 2 → 3 → 4 keeps each file edit on a clean committed base. Section 5 is independent. Section 6 lands last.

## Section 1: Model tier aliases (#50)

**Tools:**
- Skills: plugin-dev:skill-development, plugin-dev:agent-development
- MCPs: none
- Linters: none

Rationale: frontmatter YAML is load-bearing (a stray colon breaks a skill's description); the plugin-dev skills carry the frontmatter conventions the validator checks against. No linter is installed.

### Step 1: Swap the claude-opus-4-8 frontmatter pins for the opus alias (task)

**NOTE**: Seven frontmatter `model:` fields carry the explicit `claude-opus-4-8` pin. Shipped frontmatter must stay alias-only and portable; Fable reaches a seat only through a profile, never through frontmatter.

```text
1. Scope:
   - Artifact(s): bpe/skills/brainstorm/SKILL.md, bpe/skills/plan/SKILL.md, bpe/skills/retrofit/SKILL.md, bpe/skills/review/SKILL.md, bpe/skills/apply-review/SKILL.md, bpe/agents/validator.md
   - Desired end state: every `model:` frontmatter field in those six files reads `opus`, not `claude-opus-4-8`. No other line changes.

2. Tooling:
   - Skills: plugin-dev:skill-development, plugin-dev:agent-development
   - MCPs: none
   - External: none

3. Do the work:
   - In each of the six files, change the single frontmatter line `model: claude-opus-4-8` to `model: opus`.
   - Change only the frontmatter `model:` field. Do not touch any `claude-opus-4-8` string that appears in prose or in a dated tier-map table (those are handled in Step 2 and are deliberately preserved as history).

4. Verify:
   - `grep -rn "^model:" bpe/skills bpe/agents` shows every value as an alias (`opus`, `sonnet`, or `haiku`); none reads `claude-opus-4-8`.
   - For each of the six files, confirm its YAML frontmatter still parses: `python3 -c "import sys,yaml; [yaml.safe_load(open(f).read().split('---')[1]) for f in sys.argv[1:]]" bpe/skills/brainstorm/SKILL.md bpe/skills/plan/SKILL.md bpe/skills/retrofit/SKILL.md bpe/skills/review/SKILL.md bpe/skills/apply-review/SKILL.md bpe/agents/validator.md` exits 0.

5. Document:
   - none (the tier-map entry in Step 2 records the reasoning).
```

### Step 2: Add the dated Recommended Tier Map entry and align the doc copies (task)

**NOTE**: The recommended map is the user-facing guidance for what to put in a profile; it is distinct from the shipped frontmatter defaults. The `.example` and `bpe/README.md` copies had already drifted from the map and must be reconciled to the new entry.

```text
1. Scope:
   - Artifact(s): bpe/references/model-profiles.md, .claude/bpe.local.md.example, bpe/README.md
   - Desired end state: model-profiles.md carries a new dated `### 2026-11-09` Recommended Tier Map entry as the latest; the `.example` personal profile and any tier reference in bpe/README.md match it.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/references/model-profiles.md, under `## Recommended Tier Map`, add a new subsection above the existing `### 2026-08-08` entry:
     - Heading: `### 2026-11-09 (Opus 5.5 unpinned, Fable narrowed to spec-shaping and the final sweep)`
     - A table with the same columns as the prior entry assigning: `brainstorm, plan, retrofit` -> `claude-fable-5-1` (spec-shaping lives in ambiguity); `review, apply-review` -> `opus` (Opus 5.5 is reliable again for decision review); `validator agent` -> `opus` (per-batch adversarial review); `step-executor, execute-plan, cheap-research, and the mechanical skills` -> frontmatter defaults (`sonnet`); note that the final-sweep seat (0.7.3, #52) is where Fable returns in validation.
     - A short "Why the unpin" paragraph: Opus 5.5 proved reliable on bounded work, retiring the 2026-08-08 rollback to pinned Opus 4.8 (#37, #42); the direction is to use Fable less and later (spec-shaping and the end-of-run sweep, not per-step execution or validation).
   - Leave the `### 2026-08-08` entry intact as history (its `claude-opus-4-8` mentions are preserved on purpose).
   - In .claude/bpe.local.md.example, change the `execute-plan: claude-opus-4-8` and `step-executor: claude-opus-4-8` lines so no `claude-opus-4-8` pin remains: drop those two override lines (execution now rides the sonnet frontmatter default) and adjust the surrounding comment to say execution rides the default. Update the dated reference in the file's header comment from 2026-07-26 to 2026-11-09.
   - In bpe/README.md, find any `claude-opus-4-8` reference and change it to describe the `opus` alias / the dated map, matching the new entry.

4. Verify:
   - `grep -rn "claude-opus-4-8" bpe .claude` returns only lines inside the `### 2026-08-08` (and any older) dated tier-map entry in model-profiles.md. No hit in frontmatter, the `.example`, or README.
   - `grep -n "2026-11-09" bpe/references/model-profiles.md` shows the new heading.
   - The `.example` frontmatter parses: `python3 -c "import yaml; yaml.safe_load(open('.claude/bpe.local.md.example').read().split('---')[1])"` exits 0.

5. Document:
   - The new tier-map entry IS the documentation; no separate note.
```

## Section 2: Subagent MCP access (#44, #49)

**Tools:**
- Skills: plugin-dev:agent-development, plugin-dev:skill-development
- MCPs: none
- Linters: none

Rationale: the change is agent frontmatter plus protocol prose; the plugin-dev skills own the `tools:`/`disallowedTools:` grammar and the subagent tool-inheritance rules the edits depend on.

### Step 1: Give both subagents inherited MCP access via inherit-plus-deny (task)

**NOTE**: A plugin cannot enumerate per-project MCP tool names, so an allowlist can never name them; an omitted `tools:` inherits the session's MCP tools (confirmed against the Claude Code subagent docs). The validator must stay read-only, which `disallowedTools` plus the protocol's git rules enforce.

```text
1. Scope:
   - Artifact(s): bpe/agents/validator.md, bpe/agents/step-executor.md
   - Desired end state: validator.md frontmatter has no `tools:` line and gains `disallowedTools: Write, Edit, NotebookEdit`; step-executor.md frontmatter has no `tools:` line (inherits everything). Both bodies' prose about their tool set matches.

2. Tooling:
   - Skills: plugin-dev:agent-development
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/agents/validator.md, remove the `tools: Read, Grep, Glob, Bash, Skill, ToolSearch` frontmatter line and add `disallowedTools: Write, Edit, NotebookEdit`.
   - Update validator.md's "Hard invariants" prose that currently says the tools list excludes write tools "by design": restate it as `disallowedTools` removing Write/Edit/NotebookEdit, with the no-`git add`/`git commit`/`git push` rule still enforced by this protocol because `Bash` cannot be narrowed by a specifier.
   - In bpe/agents/step-executor.md, remove the `tools: Read, Edit, Write, Bash, Grep, Glob, Skill` frontmatter line so the executor inherits the session's full tool set including MCP tools.
   - Leave each agent's `model:`, `name:`, `description:`, `color:` fields untouched.

4. Verify:
   - `grep -n "^tools:" bpe/agents/validator.md bpe/agents/step-executor.md` returns nothing.
   - `grep -n "^disallowedTools:" bpe/agents/validator.md` shows `Write, Edit, NotebookEdit`.
   - Both files' frontmatter parses: `python3 -c "import yaml; [yaml.safe_load(open(f).read().split('---')[1]) for f in ['bpe/agents/validator.md','bpe/agents/step-executor.md']]"` exits 0.
   - `claude plugin validate` (run from repo root against bpe) reports no frontmatter errors for either agent, if the CLI is available; otherwise note it was unavailable.

5. Document:
   - none.
```

### Step 2: Emit an mcp-unavailable finding and warn in goal pre-flight (task)

**NOTE**: Today a declared MCP that will not load is recorded only in the validator's free-text `notes`, invisible to the orchestrator. Surface it as a `warn` finding, and warn (do not refuse) at goal pre-flight when a section declares an MCP absent from the session.

```text
1. Scope:
   - Artifact(s): bpe/agents/validator.md, bpe/references/validator-protocol.md, bpe/skills/goal/SKILL.md, bpe/skills/plan/SKILL.md
   - Desired end state: the validator emits a `warn` finding with `rule: mcp-unavailable` when a declared MCP fails to load; validator-protocol.md documents that rule; goal pre-flight warns on a missing declared MCP; plan/SKILL.md no longer claims the executor consults MCPs as if that were already true.

2. Tooling:
   - Skills: plugin-dev:agent-development, plugin-dev:skill-development
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/agents/validator.md, in the step that loads declared MCPs with ToolSearch, change the "record it in `notes` and continue" instruction so a load failure ALSO emits a finding: `severity: warn`, `rule: mcp-unavailable`, `message` naming the MCP that could not load, `file` set to the plan section name or the spec path. Keep continuing with the rest.
   - In bpe/references/validator-protocol.md, add `mcp-unavailable` to the rule/finding documentation so a reader knows the validator can emit it and what it means.
   - In bpe/skills/goal/SKILL.md Step 1 pre-flight, add a non-fatal check: for each plan section's Tools block MCPs, if the MCP is not present in the session, print a warning naming the section and the MCP and continue (do not refuse). Keep it a warning, distinct from the hard refusals already listed.
   - In bpe/skills/plan/SKILL.md, correct the "the executor invokes the Skills and consults the MCPs" claim (around the Per-section Tools block section) so it reflects that the executor reaches MCPs only now that its allowlist is removed (Section 2 Step 1); keep the validator-consults-MCPs half, which was already true.

4. Verify:
   - `grep -n "mcp-unavailable" bpe/agents/validator.md bpe/references/validator-protocol.md` shows the rule in both.
   - `grep -n "mcp-unavailable\|absent from the session\|not present in the session" bpe/skills/goal/SKILL.md` shows the pre-flight warning text.
   - Construct a sample findings block containing one `mcp-unavailable` warn finding and confirm it passes the schema: `echo '<sample block>' | python3 bpe/scripts/validate-findings.py` exits 0. (Build the sample from the schema in validator-protocol.md.)
   - `python3 -c "import yaml; yaml.safe_load(open('bpe/agents/validator.md').read().split('---')[1])"` exits 0.

5. Document:
   - none (validator-protocol.md is itself the doc).
```

## Section 3: Finalize-red recovery (#43)

**Tools:**
- Skills: none
- MCPs: none
- Linters: none

Rationale: pure orchestrator-protocol prose plus a validate-findings.py round-trip check; no domain skill adds value, and the step's own Verify runs the schema validator.

### Step 1: Document and wire the synthesized finalize-test-failure recovery (task)

**NOTE**: When finalize's test run goes red and the fix cap is not spent, the loop currently halts with no sanctioned path back. Define a synthesized findings block the orchestrator can feed into mode=fix.

```text
1. Scope:
   - Artifact(s): bpe/references/validator-protocol.md, bpe/skills/goal/SKILL.md
   - Desired end state: validator-protocol.md defines the synthesized finalize-red findings block and its shape; goal/SKILL.md's orchestrator playbook re-enters the fix loop on a finalize `Failure:` carrying test output when iter < cap.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/references/validator-protocol.md, add a subsection (near the finalize handling / interrupted-dispatch material) titled for the finalize-red recovery. Define the synthesized block: a single finding with `severity: block`, `rule: finalize-test-failure`, `message` = the failing test output (trimmed), `file` = the failing test file when the output names one, else the section or spec path. State that the orchestrator builds it, pipes it through scripts/validate-findings.py, and dispatches mode=fix with it, then continues the normal validator -> finalize path, honoring the same 3-iteration cap.
   - In bpe/skills/goal/SKILL.md, in the finalize-return handling (Step 3 playbook, the branch that currently treats any `Failure:` as halt), add: if the failure is from mode=finalize AND carries a test-output section AND iter < 3, synthesize the finalize-test-failure block per validator-protocol.md, validate it, dispatch mode=fix (iter += 1), and resume the loop; only halt (echo RESUME) when iter == 3 or the failure is not a test failure.

4. Verify:
   - `grep -n "finalize-test-failure" bpe/references/validator-protocol.md bpe/skills/goal/SKILL.md` shows it in both.
   - Build a sample synthesized block with `rule: finalize-test-failure` and confirm `python3 bpe/scripts/validate-findings.py` accepts it (exit 0).
   - Read back the goal/SKILL.md branch and confirm the iter < 3 guard and the halt-at-cap path are both present.

5. Document:
   - none.
```

## Section 4: plan --archive archives only (#38)

**Tools:**
- Skills: plugin-dev:skill-development
- MCPs: none
- Linters: none

### Step 1: Decouple --archive from regeneration (task)

**NOTE**: `--archive` currently archives and then always regenerates. Make `--archive` stop after archiving; `--archive --regen` is the combined path.

```text
1. Scope:
   - Artifact(s): bpe/skills/plan/SKILL.md, bpe/references/session-management.md
   - Desired end state: plan/SKILL.md's flag-handling makes `--archive` archive-and-stop, `--archive --regen` archive-then-regenerate, `--regen` unchanged; the refusal message and session-management.md describe all three.

2. Tooling:
   - Skills: plugin-dev:skill-development
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/skills/plan/SKILL.md "Flag handling": change rule 4 so `--archive` without `--regen` runs the Archive routine and STOPS (no fresh plan). Add a rule for `--archive --regen`: run the Archive routine, then generate a fresh plan. Keep rule 5 (`--regen` alone) unchanged.
   - In the Archive routine, change step 7 ("Proceed to generate a fresh plan") so it is conditional: proceed to generate only when `--regen` is also present; otherwise stop after step 6 and report the archive location.
   - Update the refusal message (rule 3) so it names all three intents: `--archive` to preserve and stop, `--archive --regen` to preserve and regenerate, `--regen` to discard and regenerate.
   - In bpe/references/session-management.md, under the "Plan Archives (accomplishment.md)" material, note that `--archive` alone archives without regenerating.

4. Verify:
   - `grep -n "archive --regen\|archive and stop\|archives only\|then stop" bpe/skills/plan/SKILL.md` shows the decoupled semantics.
   - Read back the Archive routine step 7 and confirm the "generate a fresh plan" action is gated on `--regen`.
   - `grep -n "archive" bpe/references/session-management.md` shows the archive-only note.

5. Document:
   - none.
```

## Section 5: Review server reliability (#33, #36, #47)

**Tools:**
- Skills: python:python
- MCPs: none
- Linters: none

Rationale: all changes are in `scripts/review-server.py` (plus a matching hash note in the review skill); python:python carries the style and toolchain rules the validator reviews against. No linter is installed in this repo.

Constraint: do NOT touch the review page's HTML generation path (that is #17, 0.7.5, and a Non-goal here). All page changes are server-side injection in `inject_save_script` and the `/save` handler.

### Step 1: Key the PID and URL files per artifact (task)

**NOTE**: The shared `/tmp/bpe-review-server.{pid,url}` paths make the server a machine-wide singleton, so a second review kills the first (#33).

```text
1. Scope:
   - Artifact(s): bpe/scripts/review-server.py, bpe/skills/review/SKILL.md
   - Desired end state: PID and URL file paths derive from a short hash of the resolved source-markdown artifact path; the review skill documents the same naming so Step 4 of the skill can find the right URL file.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/scripts/review-server.py, replace the module-level constants `PID_FILE` and `URL_FILE` with a helper that computes, from the source-markdown path passed on argv, a per-artifact key: `/tmp/bpe-review-<sha256(resolved_artifact_path)[:8]>.pid` and `.url`. Resolve the artifact path to an absolute real path before hashing so the skill and server agree.
   - Thread the artifact path into `kill_existing_server`, `write_pid_file`, and the paths written/unlinked in `main` and the `finally` block.
   - In bpe/skills/review/SKILL.md Step 4 (reading the server URL), document that the URL file name is `/tmp/bpe-review-<first 8 hex of sha256 of the absolute source-markdown path>.url`, and give the exact shell to compute it (e.g. `python3 -c "import hashlib,os,sys; print(hashlib.sha256(os.path.realpath(sys.argv[1]).encode()).hexdigest()[:8])" <artifact>`), so the skill reads the file for the server it just started rather than a global path.

4. Verify:
   - `python3 -c "import importlib.util,sys; spec=importlib.util.spec_from_file_location('rs','bpe/scripts/review-server.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); import inspect; print('pid' in inspect.getsource(m))"` loads the module without error (syntax check).
   - Confirm the key is deterministic and artifact-specific with a one-liner that hashes two different paths and asserts different 8-char keys, and the same path twice gives the same key.
   - `grep -n "sha256" bpe/scripts/review-server.py bpe/skills/review/SKILL.md` shows the matching computation in both.

5. Document:
   - none (the skill text is the user-facing doc).
```

### Step 2: Unlink only self-owned files and announce a kill (task)

**NOTE**: A dying server's `finally` can delete a newer server's files; and a kill is currently silent (#33 secondary race).

```text
1. Scope:
   - Artifact(s): bpe/scripts/review-server.py
   - Desired end state: the shutdown path unlinks the PID/URL files only when they still contain this process's PID; `kill_existing_server` prints a line when it signals a predecessor.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: none

3. Do the work:
   - In the `finally` block of `main`, before unlinking, read the PID file and unlink it (and the URL file) only if its content equals `str(os.getpid())`; otherwise leave both in place.
   - In `kill_existing_server`, when it finds and signals an old PID, print a message to stderr naming the PID it is terminating (so the losing session can see why its page died).

4. Verify:
   - Module still loads: rerun the import syntax check from Step 1.
   - `grep -n "getpid()" bpe/scripts/review-server.py` shows the self-owned guard in the finally path.
   - Start a server on artifact A (background), start a second on a different artifact B, confirm A's process is still alive and A's URL file still exists after B starts (concurrent-coexistence check); then stop both.

5. Document:
   - none.
```

### Step 3: Deterministic port from 9000 and a mandatory tailnet bind (task)

**NOTE**: The server binds a random port and silently falls back to loopback when Tailscale is missing (#47). Make the port predictable and the tailnet bind mandatory with a loud failure.

```text
1. Scope:
   - Artifact(s): bpe/scripts/review-server.py
   - Desired end state: `pick_bind_address` returns the tailnet IPv4 or exits non-zero naming the reason (never loopback fallback, never 0.0.0.0); `--bind` overrides; port selection tries 9000 then counts down on real bind attempts, giving up with a clear error after a bounded number of tries.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: none

3. Do the work:
   - Change `pick_bind_address` so a failure to resolve the tailnet IPv4 (tailscale not on PATH, daemon down / probe non-zero, logged out) raises/exits with a non-zero status and a message naming the specific reason, instead of returning `127.0.0.1`. Keep `--bind <addr>` as the explicit override consulted before this function. Never return `0.0.0.0`.
   - Replace the `HTTPServer((bind_addr, 0), ...)` ephemeral-port bind in `main` with a loop: try to bind port 9000 on `bind_addr`, on `OSError` decrement and retry (9000, 8999, ...) for a bounded count (e.g. 50 attempts), and if none is free exit non-zero with a clear error. Use the actual `HTTPServer` bind as the free-port test so the answer matches what the server gets. Keep writing the final URL to the per-artifact URL file.

4. Verify:
   - Module loads (import syntax check).
   - With Tailscale up: start the server, confirm the URL port is 9000; start a second (different artifact) and confirm it lands on 8999; stop both.
   - `--bind 127.0.0.1` path: start with `--bind 127.0.0.1`, confirm it serves on loopback and the URL reflects it; stop it.
   - Simulate tailnet-unavailable by running `pick_bind_address` with PATH stripped of tailscale (e.g. `env PATH=/usr/bin python3 -c "import importlib.util; spec=importlib.util.spec_from_file_location('rs','bpe/scripts/review-server.py'); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); m.pick_bind_address()"`) and confirm it exits non-zero with a Tailscale-naming message and writes no URL file.

5. Document:
   - none.
```

### Step 4: Relative /save and the Copy/Download controls (task)

**NOTE**: The save URL is absolute and frozen at generation time, and there is no client-side escape hatch (#36, #47). These are server-injected, next to the existing Save button, not part of the HTML template contract (which stays #17 territory).

```text
1. Scope:
   - Artifact(s): bpe/scripts/review-server.py
   - Desired end state: `inject_save_script` posts to the relative `/save`; the page gains "Copy JSON" and "Download JSON" controls beside Save, both building the exact `/save` payload, neither gated on missing comments, with the download auto-triggered when a save fetch fails.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: none

3. Do the work:
   - In `inject_save_script`, change the fetch target from the absolute `http://{bind_addr}:{port}/save` to the relative `/save`. The `save_url` parameter can be dropped or set to `/save`; update `main`'s call site accordingly.
   - Inject two sibling controls next to `#bpe-save-btn`: a "Copy JSON" button and a "Download JSON" button. Both call the same `collectFeedback()` the save path uses and append `artifact_path` (the server's source-markdown path, templated in at injection time) and `saved_at` (an ISO timestamp computed in JS at click time) so the payload is byte-compatible with what `POST /save` writes.
   - Copy uses `document.execCommand('copy')` against an offscreen textarea inside the click handler, with `navigator.clipboard.writeText` used only when `window.isSecureContext` is true. Download uses `URL.createObjectURL` on a Blob plus a synthetic `<a download>` click, named after the feedback file's basename.
   - Neither control is gated on the missing-comment check (they preserve partial work). In the save path's `catch` that renders "Save failed", also trigger the Download handler automatically.

4. Verify:
   - Module loads (import syntax check).
   - Start a server, fetch the page HTML with curl, and confirm: it contains `fetch('/save'` (relative), a Copy control, a Download control, `execCommand('copy')`, `createObjectURL`, and that `artifact_path` is templated into the injected script; stop the server.
   - Confirm the injected payload fields match what `validate_feedback` requires by reading both in the same file.

5. Document:
   - none.
```

### Step 5: Saved page shows the JSON and the server logs POSTs (task)

**NOTE**: The Saved page is a bare confirmation, and the server silences all logging (#36, #47). Show the written JSON and its path, and log POSTs plus non-200s.

```text
1. Scope:
   - Artifact(s): bpe/scripts/review-server.py
   - Desired end state: the `POST /save` response page renders the exact JSON written and the resolved feedback path under the confirmation, keeping the five-second shutdown; the handler logs POST requests and any non-200 response.

2. Tooling:
   - Skills: python:python
   - MCPs: none
   - External: none

3. Do the work:
   - In the `/save` handler, after writing the feedback file, build the Saved page so it includes the exact bytes written (in a `<pre>` block, HTML-escaped) and the resolved feedback path, below the existing "Saved" confirmation. Keep the existing `SHUTDOWN_DELAY_SECONDS` timer; the page is fully delivered before it fires.
   - In `make_handler`, change the `log_message` override so it is no longer fully silent: log POST requests and any response whose status is not 200 (to stderr), while staying quiet on routine 200 GETs.

4. Verify:
   - Module loads (import syntax check).
   - Start a server on a sample artifact, POST a valid feedback payload with curl, and confirm the response body contains the same JSON bytes that landed in the feedback file and the feedback path; confirm the server's stderr logged the POST. Stop the server (or let the POST shut it down).
   - `grep -n "log_message" bpe/scripts/review-server.py` shows the POST/non-200 logging, not a bare `return`.

5. Document:
   - none.
```

## Section 6: Version bump and docs (#50 tail)

**Tools:** none

### Step 1: Bump the plugin version to 0.7.2 (task)

**NOTE**: Single-source the version; one bump for the whole release.

```text
1. Scope:
   - Artifact(s): bpe/.claude-plugin/plugin.json
   - Desired end state: the manifest `version` reads `0.7.2`.

2. Tooling:
   - Skills: none
   - MCPs: none
   - External: none

3. Do the work:
   - In bpe/.claude-plugin/plugin.json, change `"version": "0.7.1"` to `"version": "0.7.2"`.

4. Verify:
   - `python3 -c "import json; print(json.load(open('bpe/.claude-plugin/plugin.json'))['version'])"` prints `0.7.2`.

5. Document:
   - none.
```

## Implementation Guidelines

- Each step is one commit under `/bpe:goal` (batch mode is 0.7.3, not available here). Keep edits within a step's Scope so the commit is self-contained.
- Frontmatter edits are the highest-risk class in this plan: a stray colon in an unquoted YAML scalar breaks a skill's description silently. Every frontmatter step ends with a `yaml.safe_load` parse check in its Verify.
- The review-server steps must stay server-side. Do not edit the HTML template contract in `skills/review/SKILL.md` beyond the hash-naming documentation in Section 5 Step 1; the page generation path is #17 (0.7.5) and a Non-goal here.
- Preserve the `### 2026-08-08` tier-map entry and its `claude-opus-4-8` mentions as history; only new frontmatter and the non-historical doc copies lose the pin.
- No new runtime dependencies. Verification uses the stdlib (`python3 -c`, `curl`, `grep`); the repo has no pytest/ruff and this release does not add them.

## Success Metrics

Mirror the package's verification in spec.md:

1. `grep -r claude-opus-4-8 bpe .claude` hits only the dated 2026-08-08 (and older) tier-map entry.
2. Neither subagent has a `tools:` line; validator has `disallowedTools: Write, Edit, NotebookEdit`; a sample `mcp-unavailable` warn finding passes `validate-findings.py`.
3. A sample `finalize-test-failure` block passes `validate-findings.py`; goal/SKILL.md re-enters the fix loop on a finalize red under the cap.
4. `--archive` archives and stops; `--archive --regen` archives then regenerates; `--regen` unchanged.
5. Two concurrent reviews on different artifacts coexist on 9000 and 8999; a same-artifact restart replaces only its own server; Tailscale-down exits non-zero and writes no URL file; Copy JSON yields a `validate_feedback`-acceptable payload without saving; the Saved page contains the same bytes as the feedback file.
6. `plugin.json` version is `0.7.2`.
