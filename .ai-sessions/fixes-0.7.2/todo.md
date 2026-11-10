# Todo: bpe 0.7.2 Fixes

Mirrors plan.md. Check off each top-level step as it finalizes; sub-steps track within-step progress.

## Section 1: Model tier aliases (#50)

- [x] Step 1: Swap the claude-opus-4-8 frontmatter pins for the opus alias
  - [x] Change `model: claude-opus-4-8` to `model: opus` in the five skills + validator.md
  - [x] Verify: no frontmatter pin remains; all six frontmatters parse
- [x] Step 2: Add the dated Recommended Tier Map entry and align the doc copies
  - [x] Add `### 2026-11-09` entry to model-profiles.md (keep 2026-08-08 as history)
  - [x] Reconcile `.claude/bpe.local.md.example` (drop opus-4-8 pins, refresh date/comment)
  - [x] Reconcile bpe/README.md tier reference
  - [x] Verify: grep for claude-opus-4-8 hits only the dated history entry; .example parses

## Section 2: Subagent MCP access (#44, #49)

- [x] Step 1: Give both subagents inherited MCP access via inherit-plus-deny
  - [x] validator.md: remove `tools:`, add `disallowedTools: Write, Edit, NotebookEdit`, fix invariant prose
  - [x] step-executor.md: remove `tools:`
  - [x] Verify: no `tools:` lines; disallowedTools present; both parse; plugin validate clean
- [x] Step 2: Emit an mcp-unavailable finding and warn in goal pre-flight
  - [x] validator.md: load-failure emits a `warn` finding `rule: mcp-unavailable`
  - [x] validator-protocol.md: document the `mcp-unavailable` rule
  - [x] goal/SKILL.md: pre-flight warns (not refuses) on a declared-but-absent MCP
  - [x] plan/SKILL.md: correct the executor-consults-MCPs claim
  - [x] Verify: rule present in both files; sample block passes validate-findings.py; frontmatter parses

## Section 3: Finalize-red recovery (#43)

- [x] Step 1: Document and wire the synthesized finalize-test-failure recovery
  - [x] validator-protocol.md: define the synthesized block shape (`rule: finalize-test-failure`)
  - [x] goal/SKILL.md: re-enter the fix loop on a finalize red when iter < cap
  - [x] Verify: rule in both files; sample block passes validate-findings.py; iter guard + halt-at-cap present

## Section 4: plan --archive archives only (#38)

- [x] Step 1: Decouple --archive from regeneration
  - [x] plan/SKILL.md: `--archive` stops; `--archive --regen` combines; refusal message names all three
  - [x] Archive routine step 7 gated on `--regen`
  - [x] session-management.md: note archive-only semantics
  - [x] Verify: decoupled semantics present; routine gate confirmed

## Section 5: Review server reliability (#33, #36, #47)

- [x] Step 1: Key the PID and URL files per artifact
  - [x] review-server.py: per-artifact sha256-keyed PID/URL paths threaded through all call sites
  - [x] review/SKILL.md Step 4: document the matching key computation
  - [x] Verify: module loads; key deterministic + artifact-specific; sha256 in both files
- [x] Step 2: Unlink only self-owned files and announce a kill
  - [x] finally unlinks only when the PID file holds this process's PID
  - [x] kill_existing_server prints when it signals a predecessor
  - [x] Verify: module loads; getpid guard present; concurrent-coexistence check passes
- [x] Step 3: Deterministic port from 9000 and a mandatory tailnet bind
  - [x] pick_bind_address: tailnet-or-exit (no loopback fallback, never 0.0.0.0); `--bind` override kept
  - [x] port loop: 9000 countdown on real binds, bounded, loud give-up
  - [x] Verify: ports 9000/8999 on two runs; --bind loopback works; tailnet-down exits non-zero, no URL file
- [x] Step 4: Relative /save and the Copy/Download controls
  - [x] fetch target becomes relative `/save`
  - [x] Copy JSON (execCommand + secure-context clipboard) and Download JSON (Blob) injected, not comment-gated
  - [x] save-failure catch auto-triggers the download
  - [x] Verify: HTML contains relative /save, both controls, templated artifact_path; payload matches validate_feedback
- [x] Step 5: Saved page shows the JSON and the server logs POSTs
  - [x] Saved page renders exact JSON + feedback path, keeps the shutdown timer
  - [x] log_message logs POSTs and non-200s, quiet on routine 200 GETs
  - [x] Verify: POST response contains the written bytes + path; POST logged; no bare-return log_message

## Section 6: Version bump and docs (#50 tail)

- [x] Step 1: Bump the plugin version to 0.7.2
  - [x] plugin.json version -> 0.7.2
  - [x] Verify: manifest version reads 0.7.2
