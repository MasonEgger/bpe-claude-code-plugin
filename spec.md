# BPE Plugin: Non-code Support, Model Tiers, Lifecycle Redesign

Target version: 0.6.0

## Project overview

Extend the BPE (Brainstorm-Plan-Execute) plugin to support four capabilities the current 0.5.x line does not.

1. Non-code work (skills, infra, docs, prose) using the same plan/execute discipline without forcing TDD.
2. Model tier enforcement per skill and subagent (Fable/Opus for planning-heavy work, Sonnet for execution, Haiku for cheap lookups).
3. Lifecycle management for plan.md and todo.md (spec.md permanent, plan/todo archived per project phase).
4. Retrofit path for existing projects that predate BPE and lack a spec.

The redesign is user-initiated (Mason) and self-hosted: BPE is being used to plan and execute changes to BPE itself.

## Starting context

Recorded from the design conversation that produced this spec.

- Mason works ~50/50 code vs non-code across personal and work environments.
- Fable (Opus 4.7 / 4.8 tier) is available on personal subscription for the immediate term; after subscription window closes, Fable becomes metered usage.
- At work, Fable is not allowed; the plugin must gracefully degrade to non-Fable Opus.
- Current `bpe/commands/plan.md` template forces RED/GREEN/REFACTOR sub-steps on every plan step, which does not fit non-code work (ansible playbooks, slidev decks, skills, curriculum design, tutorial writing).
- Claude Code has merged commands and skills: `.claude/commands/foo.md` and `.claude/skills/foo/SKILL.md` both create `/foo`. Skills add `model:`, `disable-model-invocation:`, `allowed-tools:`, `effort:`, `context: fork` fields. Migration is a mechanical enabling step for tier enforcement.
- Existing plugin state at start of this redesign: tasks 1-2 of a prior scope (extract `step-executor-protocol.md` from `step-executor.md`; document `/bpe:goal` resume path with `RESUME:` block and Step 5) are completed but uncommitted. They should land as a preparatory commit before this redesign begins.
- The `thariq.md` article on discovering unknowns (blindspot pass, deviations log) informed two additions to the redesign (goal 5 and goal 6 below).
- Domain research across ansible, slidev, skills, curriculum, tutorials confirmed non-code verification is exit-0 checkable (linters, dry-runs, idempotency checks, invocation checks), which unlocks autonomous mode for non-code work.

## Available tooling

Tools the `bpe:validator` agent should consult and the `bpe:step-executor` should invoke during this redesign.

**MCPs:**
- None directly relevant.

**Skills:**
- `plugin-dev:skill-development` for command-to-skill migration.
- `plugin-dev:plugin-structure` for plugin.json and marketplace concerns.
- `plugin-dev:command-development` for any residual command-file editing during migration.
- `plugin-dev:hook-development` if any advisory hooks land.
- `python:python` for `bpe/scripts/validate-findings.py` schema updates.

**Linters:**
- None required during this redesign. The redesign ADDS linter support to the validator; validating the redesign itself does not require it.

**Verification command:** `just check` if the repository adopts a justfile during this redesign; otherwise per-component verification described inline. This redesign is mostly markdown editing; the primary verifications are (a) plugin loads without error, (b) each skill is invokable, (c) each agent's frontmatter parses.

**Notes:** This redesign is markdown-only. No TDD. Every step is Task-template shape (Scope / Tooling / Do / Verify / Document) regardless of the file type touched. Even the small amount of Python work (`bpe/scripts/validate-findings.py` if Component I changes its schema) is Task-shape: edit the script, run it against a sample input, confirm output. No RED/GREEN/REFACTOR cycles anywhere in this project.

## Goals

Each goal is a load-bearing capability the 0.6.0 release must land. Non-negotiable; individual sub-decisions inside each goal are open for plan-time refinement.

### Goal 1: Task template for plan.md

Add a second plan.md step template for non-TDD work.

Shape:
```
### Step X: [Title] (task)

**NOTE**: [Optional context]

```text
1. Scope:
   - Artifact(s): [exact file paths or resource names]
   - Desired end state: [what "done" looks like]

2. Tooling:
   - Skills: [comma-separated skill names to invoke]
   - MCPs: [comma-separated MCP names to consult]
   - External: [linters, previewers, CLIs the step needs]

3. Do the work:
   - [Specific action 1 with exact path]
   - [Specific action 2 with exact path]

4. Verify:
   - [Single command or invocation returning exit 0, or human-check description]

5. Document:
   - [Exact file + specific note], or "none"
```
```

Feature template (existing TDD RED/GREEN/REFACTOR) unchanged and remains the default. Task steps carry `(task)` marker in the title; feature steps stay unmarked. Executor is template-agnostic (follows numbered sub-steps as written).

**Meta-prompting is the mechanism.** The numbered sub-steps in each plan.md step are prompts the executor will follow literally, not descriptive summaries. `/bpe:plan`'s job is to write good executor prompts, not to summarize what the step is about. This is what makes BPE effective: a well-formed plan.md step reads like a direct instruction to the code-generation LLM (with exact file paths, exact test scenarios, exact commands), and the executor's role reduces to following the instruction verbatim. This applies to both Feature and Task templates equally. Task template's Scope / Tooling / Do / Verify / Document sub-steps are still prompts, just shaped for wiring/config/docs/refactor/scaffolding work instead of the TDD cycle.

Plan-writer heuristic: use Feature when a bug could hide (new logic, custom validation, novel algorithm). Use Task for wiring, renames, config, dependency management, docs, scaffolding, refactors with no behavior change, or any non-code work. Fallback rule: if uncertain, use Feature.

### Goal 2: Per-section Tools block

Replace the current `**Validator consults:**` per-section block with a unified `**Tools:**` block that both step-executor and validator draw from.

Format:
```markdown
**Tools:**
- Skills: content-design:tutorial-writing, plugin-dev:skill-development
- MCPs: mcp__temporal-docs__search_temporal_knowledge_sources
- Linters: vale --config=.vale.ini
```

Executor invokes Skills and consults MCPs during work. Validator consults Skills + MCPs for guidance AND runs Linters as adversarial review. Per-step override allowed (a step can declare its own Tools block that shadows the section default).

Existing plans with `**Validator consults:**` continue to work under a transitional read (validator honors the old block name); new plans emit `**Tools:**` only.

### Goal 3: Automatic tool discovery in /bpe:plan

Extend `/bpe:plan`'s tool-discovery pass beyond session enumeration.

Two-pass discovery:
- Pass 1 (existing): enumerate session skills + MCPs.
- Pass 2 (new): dispatch the `bpe:cheap-research` subagent (Goal 10) to search web + installed marketplaces for skills, plugins, MCPs, or CLIs relevant to the spec's domain. Return ranked shortlist. Ask user which to add.

Opt-out via `/bpe:plan --no-discover` (Pass 2 skipped, Pass 1 still runs).

Cache Pass 2 results into `spec.md` under a `## External tool candidates` sub-section so re-runs on the same spec skip the search.

### Goal 4: /bpe:retrofit skill

New skill for adding a BPE spec to an existing project that lacks one.

Behavior:
1. Read repo state (tree, README, CLAUDE.md, manifest files, top-level docstrings).
2. Run blindspot pass (Goal 5).
3. Run shortened Q&A focused on gaps: project goal, currently in-place vs planned, tooling to declare, out of scope.
4. Share tool-discovery pass with `/bpe:plan` (Goal 3).
5. Write `spec.md` at repo root in the format `/bpe:plan` consumes.

Refuses to overwrite existing spec.md without a `--replace` flag.

### Goal 5: Blindspot pass in brainstorm and retrofit

New Step 0 in `bpe/skills/brainstorm/SKILL.md` and `bpe/skills/retrofit/SKILL.md`, before the Q&A begins.

Step 0 shape:
1. Ask ONE question about starting context: domain familiarity, prior attempts, codebase experience.
2. Given the answer, surface 3-5 unknown-unknowns as questions the user probably does not know to ask. Frame as "you may want to consider" rather than "you must answer".
3. Record the user's context answer verbatim in `spec.md` under `## Starting context`.
4. Proceed with the standard one-question-at-a-time Q&A. The Q&A rhythm is unchanged; the blindspot pass just gives it richer starting context.

### Goal 6: implementation-notes.md deviations log

Add mid-step deviation tracking to `bpe:step-executor` mode=implement.

Behavior:
- During implement, if the executor deviates from the plan.md step's prescription (edge case, blocked path, better approach found mid-work), append a one-line entry to `.ai-sessions/implementation-notes.md` under a `## Step N` heading BEFORE emitting Implement-Report.
- Entry format: `- Plan said: <what>` / `- Deviated: <what actually happened>` / `- Impact: <consequence>`.
- Validator dispatch reads `.ai-sessions/implementation-notes.md` for context so a diff that would look suspicious in isolation is contextualized by the recorded deviation.
- mode=finalize's session-summary step absorbs the step's deviations into the session summary under a new `## Deviations from Plan` section, then clears the step's section from `implementation-notes.md`.

Lifecycle: gitignored working artifact (parallel to `commit-msg.md` and `goal.md`).

### Goal 7: Plan archive lifecycle

Introduce `--archive` and `--regen` flags to `/bpe:plan` and the archived-plan directory layout.

Behavior:
- `/bpe:plan` (no flags) with no existing plan.md: generates fresh plan from `spec.md`.
- `/bpe:plan` (no flags) with existing plan.md: REFUSE. Message: "plan.md exists (last modified <date>, N/M items checked). Use `--archive` to preserve it in .ai-sessions before regenerating, or `--regen` to discard and regenerate."
- `/bpe:plan --archive`: migrate `plan.md` and `todo.md` to `.ai-sessions/<slug>/` with `accomplishment.md`, then generate fresh plan.
- `/bpe:plan --regen`: discard current `plan.md` and `todo.md` (no archive), regenerate from `spec.md`. For the iterating-on-the-spec case where the current plan is a draft.

Archive layout:
```
.ai-sessions/
  <slug>/                 e.g. init, v1, add-user-auth
    plan.md
    todo.md
    accomplishment.md
```

Slug: LLM proposes based on what got accomplished (or "init" / "v1" for the first archive). User confirms or edits at the archive prompt.

accomplishment.md content:
- Archive date
- Convergence status: `converged` / `partial: N of M items checked` / `failed: <one-line reason>`
- The `spec.md` slice this plan implemented (copied or summarized)
- What got done (from checked todo items + commit subjects)
- What was deferred or dropped
- Notable mid-execution decisions worth remembering
- Files touched
- Cross-reference to lessons captured during this plan

Trigger for the archive prompt: `/bpe:session-summary` at the end of a `/goal` loop asks: "Archive plan.md and todo.md?" If declined, the next `/bpe:plan` invocation still refuses until archive happens (hard-block).

### Goal 8: Autonomous mode for non-code work

Add a project-declared verification command as the "test passed" signal for `/bpe:goal` on non-code projects.

Change:
- `spec.md`'s `## Available tooling` section gains an optional `**Verification command:**` field.
- `/bpe:goal` pre-flight cascade: autodetected test runner (existing behavior) → `spec.md` `**Verification command:**` field (new) → prompt the user (existing fallback).
- The goal condition uses the resolved verification command's exit-0 as the success signal in place of the test-runner exit-0.

The verification command is free-form and single-line. Examples: `vale --minAlertLevel=error docs/`, `yamllint . && ansible-lint`, `slidev build && test -f dist/index.html`. Non-code projects declare it; code projects with a standard test runner do not need it.

### Goal 9: Validator with linter findings

Extend `bpe:validator` to run Linters declared in a section's Tools block and emit their output as findings.

Change:
- Validator reads the section's `Linters:` list.
- For each linter, run as subprocess. Capture output.
- Parse into findings JSON per the existing schema in `bpe/references/validator-protocol.md`:
  - `severity`: derived from linter output level (`block` for errors, `warn` for warnings, `info` for suggestions).
  - `file`: path emitted by the linter.
  - `line`: line number if the linter emits one.
  - `rule`: the linter check ID (e.g., `vale.OverusedPhrases`, `ansible-lint.no-changed-when`).
  - `message`: one-line description.
  - `reference`: linter config path or documentation URL if available.
- Emit alongside skill/MCP-sourced findings in the same block.

Vale is the canonical example. Nothing prevents ansible-lint, mdl, yamllint, or any exit-code linter fitting the same slot.

Update `bpe/scripts/validate-findings.py` only if the schema needs changes (probably fine as-is).

### Goal 10: bpe:cheap-research subagent

New subagent for external lookups (web + marketplace search) at a lower model tier.

Frontmatter:
```yaml
name: cheap-research
description: Fast, cheap external research subagent for tool discovery, docs lookup, quick fact-checks. Dispatched by /bpe:plan, /bpe:brainstorm, /bpe:retrofit when they need external info.
model: sonnet
tools: WebFetch, WebSearch, Read, Grep, Glob
```

Contract:
- Input: a research question in the dispatch prompt plus a return-shape spec (JSON schema or plain-text format).
- Output: structured data matching the return-shape spec, or a "no relevant results" response.
- No writes. Read-only tools only.

Reusable across `/bpe:plan` (external tool discovery), `/bpe:brainstorm` (initial domain research if user opts in), `/bpe:retrofit` (find existing skills that match the retrofit context), and future callers.

### Goal 11: Model tier enforcement via skill migration

Migrate all `bpe/commands/*.md` files to `bpe/skills/<name>/SKILL.md`. Add `disable-model-invocation: true` and a `model:` field per skill. Update subagent frontmatter for tier enforcement. (The blanket invocation flag was later narrowed to the workflow-entry skills; see the rule below the tier table.)

Skill tier assignments:

| Skill | model | Rationale |
|---|---|---|
| brainstorm | opus | Q&A depth matters; turn-1 setup gets enforcement |
| retrofit | opus | Same as brainstorm |
| plan | opus | Single-turn: full enforcement |
| execute-plan | sonnet | Focused implementation; Sonnet's strength |
| review | opus | Single-turn: unit decomposition benefits from Opus |
| apply-review | opus | Single-turn: nuanced comment application |
| commit-message | sonnet | Single-turn: mechanical + judgment |
| session-summary | sonnet | Single-turn |
| handoff | sonnet | Mostly single-turn per subcommand |
| wtf-wid | sonnet | Single-turn |
| lessons | sonnet | Single-turn |
| goal | sonnet | Single-turn (writes goal.md and exits) |
| gh-issue | sonnet | Single-turn |

Skills that open a BPE workflow carry `disable-model-invocation: true`: `brainstorm`, `retrofit`, `plan`, `execute-plan`, `goal`, `gh-issue`, `apply-review`, `handoff`, `lessons`. Starting one of those is the user's decision, and auto-triggering it is a bug not a feature. `lessons` stays blocked for a second reason: its `promote` mode writes into `~/.claude/rules/`, outside the repo.

Four skills omit the flag and may be model-invoked: `session-summary`, `commit-message`, `review`, `wtf-wid`. These are steps inside work the agent is already doing rather than entry points into it, and none of them asks the user a question. Blocking the first two made the commit ritual in the user's global CLAUDE.md (`/bpe:session-summary` then `/bpe:commit-message`) impossible for an agent to execute, which is what prompted the split.

The flag is a main-loop control only. Subagents cannot invoke slash commands at all, so `bpe:step-executor` reads the relevant `SKILL.md` and executes its procedure inline regardless of this setting (see `references/step-executor-protocol.md`).

Subagent tier assignments (frontmatter in `bpe/agents/*.md`):

| Agent | model | Rationale |
|---|---|---|
| bpe:step-executor | sonnet | Focused code work with clear prompts |
| bpe:validator | opus | Adversarial review needs Opus judgment |
| bpe:cheap-research | sonnet | External lookups; Sonnet handles search-and-summarize well above Haiku at modest cost |

The runtime resolves `opus`, `sonnet`, `haiku` aliases to the latest available model in each family. That handles the automatic case where the current model in each family is fine, but it does NOT give the user an explicit "use Fable specifically for brainstorm on my personal machine" lever. `opus` resolving to whichever Opus is latest is not the same as `opus` resolving to Fable when Fable is what the user wants.

**Per-user profile mechanism (`.claude/bpe.local.md`).** The plugin ships with a settings-file lookup layer that overrides skill and subagent `model:` fields at runtime. The file has YAML frontmatter declaring per-user profiles with per-skill and per-subagent overrides:

```markdown
---
active_profile: personal
profiles:
  personal:
    skills:
      brainstorm: claude-fable-5        # explicit model ID
      apply-review: claude-fable-5
    agents:
      validator: claude-fable-5
  work:
    skills:
      brainstorm: opus                    # alias resolves to work-available Opus
      apply-review: opus
    agents:
      validator: opus
---
```

The `active_profile` field selects which profile is live. `BPE_PROFILE=work` env var overrides the file for shell-scoped switching. Overrides accept any value the SKILL.md `model:` field accepts (aliases or explicit model IDs). Unset skills or subagents fall back to their frontmatter `model:` field.
The canonical schema documentation, including the full lookup precedence chain, is `bpe/references/model-profiles.md`.

Advantages:
- Fable comes and goes (subscription, work rules, model retirement). User updates one file, every skill and subagent adapts.
- Model renames don't break the plugin. Tokens/aliases stay stable; user updates the profile map when a rename happens.
- Per-project override: repo-local `.claude/bpe.local.md` shadows user-global (same pattern as CLAUDE.md).
- Plugin ships sensible defaults when no settings file exists. Fresh install just works.

Cost: one settings-lookup step per skill invocation and per subagent dispatch. Small. Worth it.

## Non-goals

Explicit no-goes for this redesign. Rejecting these once, in writing, prevents scope creep.

- **Per-domain plan templates** (ansible / slidev / skills / curriculum / tutorials as separate templates). Rejected in favor of one generic Task template. Domain shape is captured in the Task step's Tooling + Verify sub-steps.
- **Enforced session-model switching for multi-turn interactive commands beyond turn 1.** Accepted as a Claude Code platform constraint (skill `model:` field is per-turn). Advisory-only for follow-up turns.
- **Web-search-for-tools without opt-out.** Discovery is default-on with `--no-discover` opt-out.
- **HTML mockup/prototype phase in brainstorm.** Belongs upstream of BPE.
- **Post-implementation quiz** (from thariq.md). Breaks autonomous mode; `wtf-wid` + `/bpe:review` cover intent.
- **Reordering plan.md to lead with tweakable decisions** (from thariq.md). `/bpe:review`'s decision-unit model already provides this at review time without imposing structure on plan.md itself.
- **Feature-lite template** (unit-tests-only, no integration wiring) as a third middle-ground template. Two templates is enough; user manually elides the wiring phase when it does not apply.
- **Automated ranking algorithm for `bpe:cheap-research` external tool discovery.** The subagent shape lands in this redesign; the ranking heuristic is a follow-up.
- **Convert `/bpe:apply-review` to forked-subagent execution** for fully-enforced Opus tier. Considered; deferred as premature optimization.

## Component boundaries

Eleven independently implementable components. Component A must land first (bootstrap for tier enforcement); components B through K proceed largely in parallel afterward, with K landing last since it references J's tier assignments.

### Component A: Skill migration

**Scope:** Convert `bpe/commands/*.md` to `bpe/skills/<name>/SKILL.md`. Update plugin.json if needed. Verify all `/bpe:<name>` invocations still work.

**Files touched:**
- `bpe/commands/*.md` (moved)
- `bpe/skills/*/SKILL.md` (created)
- `bpe/.claude-plugin/plugin.json` (updated if skills-vs-commands are declared)
- `bpe/scripts/review-server.py` moved into the review skill's directory if it needs to travel with the skill

**Verification:** Each `/bpe:<name>` slash command still resolves. No behavior change other than added frontmatter.

**Enables:** Every other component's tier enforcement.

### Component B: Plan template family and Tools block

**Scope:** Add Task template to `bpe/skills/plan/SKILL.md`. Add unified Tools block schema. Make `bpe/skills/execute-plan/SKILL.md` and `bpe/agents/step-executor.md` template-agnostic.

**Files touched:**
- `bpe/skills/plan/SKILL.md` (Task template section, heuristic guidance, Tools block schema, transitional support for old `Validator consults:` block)
- `bpe/skills/execute-plan/SKILL.md` (template-agnostic wording, per-step Tools invocation)
- `bpe/agents/step-executor.md` (template-agnostic mode=implement wording)
- `bpe/references/step-executor-protocol.md` (Task template contract note)
- `bpe/references/validator-protocol.md` (Tools block schema note)

**Verification:** Existing plan.md files parse (backward compat). New plan.md files can mix Feature and Task steps in one document.

### Component C: bpe:cheap-research subagent + tool discovery pass

**Scope:** Create `bpe/agents/cheap-research.md`. Extend `bpe/skills/plan/SKILL.md` and `bpe/skills/brainstorm/SKILL.md` to dispatch it during discovery. Add `--no-discover` flag.

**Files touched:**
- `bpe/agents/cheap-research.md` (new)
- `bpe/skills/plan/SKILL.md` (discovery pass integration, `--no-discover` flag)
- `bpe/skills/brainstorm/SKILL.md` (optional discovery dispatch)

**Verification:** Manual invocation of the subagent returns structured shortlist. Discovery pass caches results into `spec.md`.

### Component D: /bpe:retrofit skill

**Scope:** New skill for producing spec.md from an existing repo.

**Files touched:**
- `bpe/skills/retrofit/SKILL.md` (new)

**Verification:** Running `/bpe:retrofit` on a repo without spec.md produces one that `/bpe:plan` accepts.

### Component E: Blindspot pass in brainstorm and retrofit

**Scope:** Add Step 0 to brainstorm and retrofit skills.

**Files touched:**
- `bpe/skills/brainstorm/SKILL.md`
- `bpe/skills/retrofit/SKILL.md`
- `bpe/references/session-management.md` if the `## Starting context` section needs canonical documentation

**Verification:** Running `/bpe:brainstorm` produces spec.md with a `## Starting context` section populated from the user's turn-1 answer.

### Component F: implementation-notes.md deviations log

**Scope:** Extend step-executor mode=implement to write deviations. Validator reads for context. session-summary absorbs into summary and clears.

**Files touched:**
- `bpe/agents/step-executor.md` (mode=implement writes; mode=finalize absorbs and clears)
- `bpe/agents/validator.md` (reads implementation-notes.md as diff context)
- `bpe/references/step-executor-protocol.md` (deviations behavior in mode=implement contract)
- `bpe/skills/session-summary/SKILL.md` (absorb step)
- `bpe/references/session-management.md` (implementation-notes.md format and lifecycle)
- `.gitignore` (add `.ai-sessions/implementation-notes.md`)

**Verification:** A step with a recorded deviation produces a session summary containing a `## Deviations from Plan` section; the working file is empty after the step's finalize dispatch.

### Component G: Plan archive lifecycle

**Scope:** Add `--archive` and `--regen` flags to `/bpe:plan`. Design `accomplishment.md` template. Wire archive prompt into `/bpe:session-summary`.

**Files touched:**
- `bpe/skills/plan/SKILL.md` (flag parsing, refuse-without-flag behavior, archive routine, regen routine)
- `bpe/skills/session-summary/SKILL.md` (archive prompt at end of goal loop)
- `bpe/references/session-management.md` (archive layout, accomplishment.md format)

**Verification:** After a converged `/goal` run and the archive prompt, `.ai-sessions/<slug>/plan.md`, `todo.md`, and `accomplishment.md` exist. `/bpe:plan` on the now-empty repo root generates a fresh plan.

### Component H: Autonomous mode for non-code (verification_command)

**Scope:** Extend `bpe/skills/goal/SKILL.md` pre-flight with the verification_command cascade. Document the `spec.md` field.

**Files touched:**
- `bpe/skills/goal/SKILL.md` (pre-flight cascade)
- `bpe/references/session-management.md` (spec.md tooling section format)
- `bpe/skills/brainstorm/SKILL.md` and `bpe/skills/retrofit/SKILL.md` (prompt user for verification_command when the project has no autodetectable test runner)

**Verification:** A non-code project with a declared verification_command runs `/bpe:goal` autonomously; the goal condition uses the declared command's exit-0 as the success signal.

### Component I: Validator linter integration

**Scope:** Extend `bpe:validator` to run Linters listed in a section's Tools block and emit their output as findings.

**Files touched:**
- `bpe/agents/validator.md` (Linters consult type, linter subprocess handling, output-to-findings translation)
- `bpe/references/validator-protocol.md` (linter-sourced findings schema note)
- `bpe/scripts/validate-findings.py` (only if schema needs updates; probably no change)

**Verification:** A section declaring `Linters: vale --config=.vale.ini` on a prose project produces vale findings in the validator's output.

### Component J: Model tier enforcement wiring

**Scope:** Update subagent frontmatter (`bpe/agents/*.md`) with tier assignments. Add `model:` field to each skill migrated in Component A.

**Files touched:**
- `bpe/agents/step-executor.md` (`model: sonnet`)
- `bpe/agents/validator.md` (`model: opus`)
- `bpe/agents/cheap-research.md` (`model: sonnet`) (from Component C)
- Each `bpe/skills/<name>/SKILL.md` (tier per the table in Goal 11)

**Verification:** Dispatching each subagent respects the tier. Invoking each skill switches the current turn's model to the declared tier.

### Component K: Per-user profile system

**Scope:** Ship a per-user profile file (`.claude/bpe.local.md`) that maps skills and subagents to specific model IDs, overriding the ship-with-plugin defaults from Component J. Support `active_profile:` toggle for personal-vs-work modes and `BPE_PROFILE` env var override. Per-project shadow overrides in project-local `.claude/bpe.local.md`.

**Enforcement mechanism (to nail down during plan phase):** Options include (a) UserPromptSubmit hook that warns if session model does not match profile expectation, (b) documented manual workflow where user runs `/model <id>` before invoking a skill per the profile, (c) SessionStart hook that sets the session model per profile at session start. The specific mechanism depends on Claude Code platform capabilities at implementation time.

**Files touched:**
- `bpe/references/model-profiles.md` (new: canonical schema documentation and lookup semantics)
- `bpe/hooks/profile-check.md` (new: UserPromptSubmit hook to warn on mismatch, per-invocation basis)
- `.claude/bpe.local.md.example` (new: commented example file for users to copy to their `.claude/` directory)
- `bpe/README.md` (updated: profile documentation section)

**Verification:**
- Example profile file loads without YAML parse errors.
- Personal profile with `brainstorm: claude-fable-5` and current session on `claude-sonnet-5`: hook fires warning on `/bpe:brainstorm`.
- `BPE_PROFILE=work` env var: work profile takes precedence over `active_profile: personal` in the file.
- Absent profile file: no warnings; skills use their frontmatter defaults.

**Dependencies:** Lands after Components A (skills exist to reference) and J (subagents have `model:` fields to reference). Independent of B-I.

## Plan generation approach

The redesign uses `/bpe:plan` in its current 0.5.x form with a natural-language directive to skip TDD for this specific project. Sample invocation: pass an instruction like *"spec.md is markdown-heavy meta-project work; produce Task-shape numbered instructions per step, no RED/GREEN/REFACTOR cycles, no test scenarios, verify with concrete checks (ls, grep, plugin loads, slash command resolves)."* The LLM running `/bpe:plan` honors the instruction by producing numbered task prompts instead of the default TDD-cycle prompts.

This is a one-off exception for this meta-project. Once Component B lands the real Task template in the plan skill, subsequent `/bpe:plan` runs on other projects use the template natively without an override directive.

Every step in the resulting plan.md is Task shape. No RED phases. No test scenarios. No `just check`. Verification per step is whichever concrete check fits (`ls path/`, `head -20 path`, `grep pattern path`, plugin loads, slash command resolves, etc.).

## Ordering constraint

Component A (skill migration) is mechanical bootstrap and must land first. It converts commands to skills; every subsequent component edits skill files that exist as a result of A.

Suggested execution order:

```
A → B → C → D → E → F → G → H → I → J → K
```

Components after A are largely independent; the sequential order above is a suggested cadence, not a hard requirement. J happens incrementally as each skill in A is migrated and each agent is edited. K lands last since it references the tier assignments from J.

Explicit dependencies:
- B and I both touch the validator-protocol schema. Merge sequence matters; B should land first.
- C creates the `bpe:cheap-research` subagent. D uses it in the retrofit skill.
- E adds Step 0 to brainstorm and retrofit. D creates retrofit. E can update brainstorm independently and update retrofit after D lands.
- F, G, H, I are independent of each other and of D, E.
- K depends on A (skills exist) and J (subagents and skills have `model:` fields to override). Otherwise independent.

## Success criteria

The 0.6.0 release converges when all of the following hold.

1. All existing BPE commands still work under `/bpe:<name>` (backward compat).
2. `/bpe:plan` produces plans that can mix Feature and Task template steps in one document.
3. `/bpe:plan --archive` and `/bpe:plan --regen` behave as specified. `/bpe:plan` refuses to overwrite an existing plan without a flag.
4. `/bpe:retrofit` produces a `spec.md` on an existing repo that `/bpe:plan` accepts.
5. `/bpe:brainstorm` and `/bpe:retrofit` both begin with a blindspot pass that populates `## Starting context` in `spec.md`.
6. `bpe:step-executor` mode=implement writes deviations to `.ai-sessions/implementation-notes.md`; mode=finalize absorbs them into the session summary and clears the file.
7. `/bpe:goal` runs a non-code project autonomously using a `spec.md`-declared `**Verification command:**`.
8. `bpe:validator` emits Vale-sourced findings on a prose project with `Linters: vale ...` in the Tools block.
9. `.ai-sessions/<slug>/` archive directories exist for completed plans, with `plan.md`, `todo.md`, and `accomplishment.md`.
10. Subagent frontmatter enforces model tiers: `step-executor: sonnet`, `validator: opus`, `cheap-research: sonnet`. Skill frontmatter enforces per-turn tier per the Goal 11 table. `.claude/bpe.local.md` profile system supports per-skill and per-subagent overrides with `active_profile:` toggle and `BPE_PROFILE` env var. Personal profile can pin specific skills to an explicit model ID; work profile defaults to `opus` alias.
11. `bpe/.claude-plugin/plugin.json` version bumped to 0.6.0.

## Out of scope (future work, tracked)

Design was considered and deferred to a later release.

- UserPromptSubmit hook that warns loudly when a skill is invoked below its recommended tier.
- Feature-lite template as a third middle-ground.
- Ranking algorithm improvements for `bpe:cheap-research` external tool discovery.
- Converting `/bpe:apply-review` to forked-subagent execution for fully-enforced Opus tier.
- Retrofit variants: `/bpe:retrofit --plan` (add plan to a specced-but-unplanned project), `/bpe:retrofit --lessons` (extract lessons from git history).
- Automatic slug generation for archive directories using commit history as input to the LLM proposal.

## Prior work to land as a preparatory commit

Before this redesign begins, the following completed-but-uncommitted work from a prior session should land on the `fable` branch:

- `bpe/references/step-executor-protocol.md` (new): protocol extracted from `bpe/agents/step-executor.md`. Owns mode contracts, hard invariants, report field semantics, orchestrator verification steps.
- `bpe/agents/step-executor.md` (rewritten): trimmed to procedural playbook + emit-verbatim report templates. Cross-references the new protocol.
- `bpe/references/validator-protocol.md` (edited): cross-reference sentence pointing at `step-executor-protocol.md`.
- `bpe/commands/goal.md` (edited): `RESUME:` block in the orchestrator playbook that the parent echoes verbatim on any `Failure:` or `BPE rule violation:` before stopping; Step 5 "Resume Path on Failure" in the command docs.

Commit these as a single preparatory commit (or two if you prefer to separate protocol extraction from resume-path documentation) before generating the plan for this redesign.

## Fable-era context alignment (2026-07-25 audit)

A 2026-07-25 audit swept this plugin against Thariq's "The new rules of context engineering for Claude 5 models" (2026-07-24) and the Claude Fable field guide.
This section records the findings as a work package for a post-0.6.2 release; the private marketplace repo's spec.md carries the sibling sweep for the other plugins.

Audit context, so the review sees the full picture: bpe scored strongest of all plugins on interface design (validate-findings.py as executable contract, read-only enforced by tool allowlists, exit-0 verification, SHA-based commit checks) and on unknowns methodology (blindspot pass, interview, deviation log, handoff).
The findings below are structural debt, concentrated in the older interactive skills; the autonomous-loop contracts are correct and deliberately redundant across fresh-context agents (defense-in-depth, keep).

Quick fix already applied on this branch: `execute-plan/SKILL.md` lost its bold-caps "Key Requirements" block (it restated steps 5-9 verbatim), both CRITICAL tags, and a banned-vocabulary word; the single canonical statement of each rule remains in the numbered steps.

### Findings

1. `plan/SKILL.md` is a 290-line monolith, the weakest progressive disclosure in the plugin.
Split the two templates, the meta-prompting philosophy, and the tool-discovery two-pass into references/ files; SKILL.md keeps the workflow and a router.
2. The DO/DON'T-test material is stated three times inside `plan/SKILL.md` (:41-63, :96-102, :174-188) and echoed in `execute-plan` and `brainstorm`.
One canonical statement (suggest: a short reference file or one section in plan), everything else cites it.
3. The Tools-block grammar lives in three places: `plan/SKILL.md:230-251`, `validator-protocol.md:134-158`, `session-management.md:298-306`.
Pick one canonical home (validator-protocol.md is the natural one) and replace the other two with pointers; three copies of a schema is drift waiting to happen.
4. The legacy `**Validator consults:**` back-compat rule is restated in plan, validator-protocol, and goal.
Canonicalize alongside finding 3.
5. The blindspot-pass paragraph is duplicated between `brainstorm/SKILL.md:14-22` and `retrofit/SKILL.md:32-37`; retrofit says "same shape as brainstorm Step 0" and then restates it in full anyway.
Retrofit points, does not restate.
6. Emphasis-inflation sweep across the remaining skills: MANDATORY/CRITICAL tags on ordinary steps (`step-executor.md:68,80`, `plan/SKILL.md:65`) dilute the genuine guardrails (main-branch refusal, no --no-verify, sequential dispatch).
Model-tier nuance: skills pinned to sonnet tiers may deliberately keep firmer language for weaker models; decide per file at plan time and record the ruling, so firmness is a choice rather than an accident.
7. The `mktemp -u` rationale is stated in both `review/SKILL.md:169` and `handoff/SKILL.md:51`; fold into the agent-shell hygiene reference this spec already plans (D4 in the portfolio spec), then cite it.
8. Handoff gitignore advice differs in firmness between `handoff/SKILL.md:103` and `session-management.md:214-216`; align the wording.
9. Field-guide gap: the plan template does not tell the planner to lead with the decisions most likely to change (data model, interfaces, anything user-facing).
Add that instruction to the plan skill's step-ordering guidance.
10. Field-guide gap: no prototype-before-implementation path.
For UI-shaped or design-heavy projects, brainstorm gains an optional "mockup or single-file prototype before the spec hardens" step; skip for library and infra work.

### Non-goals for this package

- No change to the autonomous-loop contracts (sequential dispatch, one-commit finalize, SHA verification, findings schema); their cross-file repetition is deliberate defense-in-depth for fresh-context agents.
- No re-litigating the 0.6.x design decisions above; this package layers on top.

## 0.7.2 Fixes (2026-11-03, requested)

The first of four patch releases triaged from the open issues on 2026-11-03.
The later three are loop efficiency (0.7.3: #51 batch mode, #52 final sweep, #53 checkpoint and report budget), setup (0.7.4: #28 `/bpe:init`, #48 issue format, later widened to #55 spec Goals and the open #58 items), and the review renderer (0.7.5: #17).
Versions keep bumping the patch number; Mason calls the 0.8.0 bump separately, as a version-only change.

### Goal

Fix the confirmed bugs that lose work or silently disable declared tooling, and drop the Opus 4.8 pin.
Five work items, each traceable to an issue.

1. **Use the `opus` alias everywhere (#50).**
   Replace every `claude-opus-4-8` pin with `opus` in skill and agent frontmatter, `references/model-profiles.md`, `bpe/README.md`, and `.claude/bpe.local.md.example`.
   Add a new dated Recommended Tier Map entry: Fable for brainstorm, plan, retrofit; `opus` for review, apply-review, validator; `sonnet` for step-executor, execute-plan, cheap-research, and the mechanical skills.
   Shipped frontmatter stays alias-only and portable; Fable reaches a seat only through a profile.
2. **Subagent MCP access (#44, #49).**
   Remove the `tools:` allowlists from `agents/validator.md` and `agents/step-executor.md`, so both inherit the session's MCP tools.
   The validator gets `disallowedTools: Write, Edit, NotebookEdit`; its no-git-writes rule stays protocol-enforced, since `Bash` cannot be narrowed by specifier.
   A declared MCP that fails to load becomes a `warn` finding (`rule: mcp-unavailable`) instead of a `notes` line, so the orchestrator sees it.
   `/bpe:goal` pre-flight warns (does not refuse) when a plan section's Tools block names an MCP absent from the session.
   Correct `plan/SKILL.md`'s claim that the executor consults MCPs, which is only true after this change.
3. **Recovery from a failing suite at finalize (#43).**
   When `mode=finalize` returns `Failure:` with failing test output and the fix-loop cap is not exhausted, the orchestrator synthesizes a findings block with a single `block` finding (`rule: finalize-test-failure`, the failure text as the message, the failing file when known), validates it with `scripts/validate-findings.py`, dispatches `mode=fix`, and continues through validation and finalize.
   The synthesized-finding shape is documented in `references/validator-protocol.md`.
4. **`/bpe:plan --archive` archives only (#38).**
   `--archive` archives and stops.
   `--archive --regen` archives, then regenerates.
   `--regen` is unchanged.
   The refusal message and `references/session-management.md` describe all three.
5. **Review server reliability (#33, #36, #47).** All in `scripts/review-server.py`.
   - PID and URL files are keyed by a short hash of the resolved artifact path; the skill computes the same name. Restarting a review of the same artifact replaces its own server; a different artifact is never touched.
   - A dying server unlinks its PID and URL files only when they still hold its own PID. A server that kills a predecessor prints a line saying so.
   - Port selection starts at 9000 and walks downward on real bind attempts against the chosen address, giving up with a clear error after a bounded number of tries. No random port fallback.
   - The tailnet IPv4 is the mandatory bind address. When it cannot be resolved, the server exits non-zero naming the reason (`tailscale` missing, daemon down, logged out) and writes no URL file. `--bind` stays as the explicit override. Never `0.0.0.0`.
   - The injected save script posts to the relative `/save`.
   - Two controls are injected next to Save: "Copy JSON" (`document.execCommand('copy')` on an offscreen textarea, with `navigator.clipboard` only when `window.isSecureContext`) and "Download JSON" (Blob). Both build the payload from `collectFeedback()` plus `artifact_path` and `saved_at`, matching what `/save` writes, and neither is gated on missing comments. A failed save triggers the download automatically.
   - The Saved page renders the exact JSON written and the resolved feedback path, keeping the five-second shutdown.
   - The server logs POSTs and non-200 responses.

### Design decisions (confirmed 2026-11-03)

- Decision: inherit-plus-deny for subagent tools rather than allowlists. MCP tool names are per-project, so a plugin cannot enumerate them, and the Claude Code subagent docs confirm an omitted `tools:` inherits the session's MCP tools.
- Decision: a finalize-stage red re-enters the fix loop through a synthesized finding, not a validator re-dispatch; the validator never runs tests.
- Decision: tailnet bind is mandatory (#47 wins over #36's loopback suggestion).
- Decision: both copy and download controls ship, since the clipboard API is unavailable on the plain-http tailnet origin.
- Decision: #47 item 3 is satisfied by the copy control; #36's `--from <path>` ask is already met by `/bpe:apply-review`'s path argument.

### Verification

- `grep -r claude-opus-4-8 bpe .claude` matches only historical mentions inside dated Tier Map entries.
- A validator dispatch with a declared MCP loads it, and one with a bogus MCP name returns a `warn` finding that passes `validate-findings.py`.
- A synthesized `finalize-test-failure` block passes `validate-findings.py`.
- Review server: two concurrent runs on different artifacts coexist on 9000 and 8999; a restart on the same artifact replaces only its own server; with Tailscale stopped the server exits non-zero naming Tailscale and writes no URL file; Copy JSON on the tailnet origin yields a payload `validate_feedback` accepts without saving; the Saved page contains the same bytes as the feedback file.
- `plugin.json` version is 0.7.2.

### Non-goals for this package

- No batch mode, final sweep, or checkpoint work (0.7.3).
- No change to the review page's generation path (0.7.5, #17).

## 0.7.3 Loop Efficiency (2026-11-10, requested)

The second of the four patch releases triaged on 2026-11-03.
It covers #51 batch mode, #52 the end-of-run final sweep, and #53 the 95 percent context checkpoint with a report budget, which together implement the agreed parts of #40.
The baseline it must beat is recorded in `.ai-sessions/research/baseline-0.7.2-goal-run.md`: the 0.7.2 run spent 42 dispatches and 89 subagent minutes on 12 steps, finalize dispatches alone took 27 percent of subagent time, and the orchestrator's own turns read more tokens than all 42 subagents combined.

### Goal

Cut dispatches, wall-clock, and tokens per plan without lowering the validator's bar.
Four work items, each traceable to an issue, plus the version bump.

0. **Free the playbook headroom (prerequisite).**
   The rendered `goal.md` argument sits at 3978 of `/goal`'s 4000-character cap, and items 1 and 3 both add to it.
   Move the orchestrator's per-turn procedure out of `skills/goal/SKILL.md` Step 3 into a new `## Orchestrator playbook` section of `references/validator-protocol.md`, which the playbook already tells the orchestrator to read once per turn.
   The `goal.md` text keeps the condition, the read instruction, the hard rules (sequential, one commit per unit, SHA verification, RESUME, dispatch cap), and the `Mode:` line, and must render under 3000 characters so later releases have room.
   `/bpe:goal` Step 3's cap check stays and the count it prints is the real rendered length.
1. **Batch mode (#51).**
   - `/bpe:plan` writes batch boundaries into plan.md: a `**Batch:**` line under each section heading, after the Tools block, reading `<name>` for a batch of the section's steps or `single` to keep the per-step loop.
     Default is one section per batch, split into `<section>-a`, `<section>-b` when the section exceeds 4 steps or its steps' stated scope exceeds about 400 changed lines.
     `/bpe:plan` documents the sizing rule and the `single` override; `/bpe:review` shows the boundaries as decision units.
   - The executor stays warm across a batch.
     One `mode=implement` dispatch does every step in the batch in order, running the step's Verify (or `<test-cmd>`) and the spec-fence self-check after each step before starting the next, and checking off each step in todo.md as it lands.
     Its `Implement-Report` carries one `TodoDelta:` line per step and a `Batch:` field naming the batch.
   - Fix and finalize continue the same agent through `SendMessage` on the agent id the implement dispatch returned, so the agent that wrote the code also fixes and commits it.
     When the continuation fails or returns no report block (agent gone, context exhausted), the orchestrator falls back to a cold dispatch in the same mode; the tree carries the work, so nothing is lost.
   - The validator runs cold, once per batch, over the batch's whole diff (`git diff HEAD`), judging against the section's Tools block.
     The base cap is 3 validator passes per batch, extended one pass at a time to a ceiling of 5 while the count of block and warn findings keeps dropping.
     From the second pass on, the validator also receives the previous findings and the exact fix delta.
   - One commit per batch.
     The commit subject names the batch; the body lists each step's subject line; the session summary covers the batch.
     The orchestrator verifies the commit against the reported SHA exactly as today.
   - Interrupted-dispatch recovery is unchanged in mechanism (`git reset --hard && git clean -fd`), because HEAD is still the batch's base commit until finalize; the orchestrator unchecks any todo.md step the interrupted batch had checked (the reset does that, since todo.md is tracked) and redoes the batch from `mode=implement`.
   - `references/step-executor-protocol.md` replaces "One step per invocation" with "One batch per invocation; a batch of one is a step", and the mode table gains the warm-continuation rows.
     "Exactly one commit per finalize" stays as written; it now applies per batch.
2. **End-of-run final sweep (#52).**
   - A new agent, `agents/final-validator.md`, with frontmatter `model: opus`, so a profile can pin its seat separately from `validator` (Mason's profile sets Fable).
     Its body is the validator protocol with three differences: the diff source is `git diff $(git merge-base main HEAD)..HEAD`, the Tools it consults are the union of every section's Tools block plus the spec fences, and it runs even when every section declared `Tools: none`.
   - The orchestrator dispatches it once after the last todo item finalizes and before declaring the goal met.
     Its findings go through `validate-findings.py` like any other.
   - block or warn findings dispatch the executor `mode=fix` with the findings, then the final validator again, under the same iteration cap.
     A clean verdict makes no commit.
     An eventually clean sweep that made fixes ends with one `mode=finalize` dispatch whose `Step:` reads `sweep` and whose commit subject is "Apply final sweep fixes"; `TodoDelta:` reads `none`.
     Block or warn at the cap is `Failure:` with the unresolved findings echoed and RESUME.
   - The goal condition in `/bpe:goal` Step 2 gains the clause "the final sweep returned clean" for full and section modes; step mode has no sweep.
   - `references/model-profiles.md` lists `final-validator` as an agent key and the 2026-11-09 tier map gains its row.
3. **Context checkpoint and report budget (#53).**
   - A new hook, `hooks/context-check.py`, registered on `PostToolUse` with matcher `Agent|SendMessage`, reads the hook input's `transcript_path`, sums `input_tokens`, `cache_read_input_tokens`, and `cache_creation_input_tokens` from the last assistant entry, divides by the window for that entry's `requestedModel` (1,000,000 when the id carries `[1m]`, else 200,000), and returns `additionalContext` reading `Context: NN% of <window>`.
     It fails open: unreadable transcript, missing fields, or any exception produce no output.
   - The orchestrator playbook reads that line after every dispatch.
     At 90 percent or more after a finalize (a commit boundary) or 95 percent or more after any dispatch, it echoes a `CHECKPOINT:` block naming `/clear` then `/goal @goal.md` and ends the turn without dispatching.
     Resume is the existing path: the first `- [ ]` in todo.md, with a dirty tree treated as an interrupted dispatch.
   - "Never `/clear` or `/compact`" in `skills/goal/SKILL.md`, `references/step-executor-protocol.md`, and the playbook becomes "only on CHECKPOINT", with one paragraph on long arcs and tight credits.
   - Report budget: the report block fields are unchanged and stay verbatim; prose outside the block is forbidden; `Blockers:` and `Deferred:` are one line each; the validator's `notes` field is capped at 80 words and each finding's `message` at 240 characters.
     `validate-findings.py` enforces the two validator caps; the executor caps are protocol text plus the agent templates.
4. **Measurement (#51 acceptance).**
   - Land the baseline script as `scripts/goal-run-report.py`: given a session transcript path, it prints the per-dispatch table and the kind totals from the baseline note, using the same arithmetic.
   - After batch mode lands, run this release's own remaining plan in batch mode and record the comparison in `.ai-sessions/research/batch-mode-comparison.md`: dispatches, subagent minutes, subagent and orchestrator cache-read tokens, and warn rate per first-pass validation, against the baseline.
5. **Version bump** to 0.7.3.

### Design decisions (confirmed 2026-11-11)

- Decision: batch boundaries are plan-time and section-shaped; the orchestrator never regroups at run time (2026-11-03).
- Decision: the warm executor continues through `SendMessage`, with a cold dispatch in the same mode as the fallback; the alternative, a fresh dispatch per mode, is exactly the cost the baseline measures.
- Decision: the batch validator stays cold and independent of the author; only the executor is warm.
- Decision: per-batch validation runs on `opus` and the final sweep is the one seat where Fable belongs, so the sweep is its own agent name rather than a flag on `validator` (profiles key on agent name).
- Decision: the sweep runs on every full or section run, including all-`Tools: none` plans, because the #40 run's two weakly validated commits were in exactly such sections.
- Decision: two checkpoint thresholds, 90 percent at a commit boundary and 95 percent anywhere, because a resume from a commit boundary costs nothing and a resume mid-batch redoes the batch.
- Decision: the checkpoint hook is `PostToolUse` on `Agent|SendMessage`, since the orchestrator's turns in a `/goal` loop are Stop-hook driven and do not reliably fire `UserPromptSubmit`.
- Decision: no persisted loop state, no automatic `/clear`, no per-step commits inside a batch (all rejected 2026-11-03).

### Verification

- `/bpe:goal` renders `goal.md` under 3000 characters with the playbook moved, and the orchestrator still finds every per-turn rule in `validator-protocol.md`.
- `/bpe:plan` on a 6-step section writes two batches; `**Batch:** single` on a section yields per-step dispatches in a dry run of the playbook.
- A 3-step batch produces one implement dispatch, one validator dispatch, one commit whose body lists three steps, three checked todo lines, and a SHA that verifies.
- Killing the warm agent between implement and finalize makes the orchestrator fall back to a cold `mode=finalize` that commits the same tree.
- The final validator on a branch with a planted invariant violation returns a `block` finding that passes `validate-findings.py`; a clean branch returns `clean` and makes no commit.
- `hooks/context-check.py` fed a transcript whose last assistant entry sums to 190,000 tokens on a 200,000 window prints `Context: 95% of 200000`; fed a missing path it prints nothing and exits 0.
- `validate-findings.py` rejects a finding with a 241-character `message` and a block whose `notes` exceeds 80 words.
- `scripts/goal-run-report.py` on the 0.7.2 session reproduces the baseline table.
- `plugin.json` version is 0.7.3.

### Non-goals for this package

- No `/bpe:init`, issue format, or `/bpe:new-issue` (0.7.4).
- No change to the review renderer (0.7.5, #17).
- No sweep from `/bpe:execute-plan`; interactive mode is unchanged.
- No orchestrator-side regrouping, no persisted loop state, no automatic `/clear`.

## 0.7.4 Setup, Issue Format, and Spec Goals (2026-11-22, requested)

The third of the patch releases triaged on 2026-11-03, widened on 2026-11-19.
It covers #28 (`/bpe:init`), #48 (a structured issue format), #55 (what the permanent spec's `## Goals` holds and how it stays current), and the five items still open on #58.
This package replaces the `## /bpe:init (2026-07-26, requested)` section that used to sit above the 0.7.2 package; that section's confirmed design decisions are carried below unchanged.
This repo's own `spec.md` stays in the pre-0.7 layout through 0.7.5.
Its migration into the new Goals shape is the post-0.7.5 `/bpe:retrofit --resync`, and that run is the worked example #55 asks for in its item 9.

### Goal

Five work items, four traceable to an issue and one from the 2026-11-22 spec review, plus docs and the version bump.
#55's "Changes, File by File" section holds the line-level locations for item 3; this package states the requirements and the decisions.

1. **Loop follow-ups (#58).**
   - `/bpe:goal` pre-flight accepts a fully checked `todo.md` when the branch since `main` has no commit whose subject is "Apply final sweep fixes".
     It writes `goal.md` as usual, and the playbook in `references/validator-protocol.md` says that a turn which finds no unchecked top-level item and no clean sweep earlier in this run dispatches `final-validator`.
     A branch that already has an "Apply final sweep fixes" commit and a fully checked `todo.md` is refused with a message saying the run is finished.
     Assumption: a branch whose earlier sweep returned clean has no sweep commit either, so a resumed run sweeps it again; that costs one `final-validator` dispatch and changes nothing.
     No new goal mode.
   - `scripts/goal-run-report.py` reports usage for `SendMessage` continuations instead of zero.
     The first step inspects a real batch-mode transcript (the 0.7.3 Phase 2 session) to learn where a continuation's turns land.
     Assumption: they land in the same `subagents/agent-<id>.jsonl` as the implement dispatch, and the script attributes each assistant entry to the dispatch whose tool_use-to-tool_result window contains its timestamp.
     If the transcript shows otherwise, the attribution follows what the transcript shows, recorded as a deviation.
     The fix is test-first with a fixture transcript under `tests/`.
     After it lands, rerun the script on the 0.7.3 session and correct the Phase 2 numbers and the understatement note in `.ai-sessions/research/batch-mode-comparison.md`.
   - `agents/step-executor.md` and `agents/validator.md` each come in under 10,000 characters.
     Procedural detail and examples move into `references/step-executor-protocol.md` and `references/validator-protocol.md`, which each agent already reads at startup.
     The hard invariants stay restated in each agent body: never commit to main, exactly one commit per finalize, never `--no-verify`, the validator is read-only, and report blocks are emitted verbatim.
   - The convergence-aware validator cap and the CHECKPOINT stop get exercised by this release's own goal run where the run reaches them.
     The accomplishment records whether each fired; a path the run never reaches stays open on #58.
2. **Structured issue format (#48).**
   - `references/issue-format.md` defines the format.
     Required: an imperative title, then `## What Is Wanted`, `## What We Already Know`, and `## Acceptance Criteria`, in that order.
     Optional, in this order where present: `## Prior Research and Thoughts` (after What We Already Know), `## Changes, File by File`, and `## Out of Scope` (both before Acceptance Criteria).
     The bar the format sets: an agent reading a conforming issue can start work without asking what is wanted or how completion is judged.
   - A new skill, `/bpe:new-issue`, drafts an issue in the format from the conversation and the user's argument, shows the full draft, and runs `gh issue create` only after the user confirms.
     Frontmatter: `model: sonnet`, `disable-model-invocation: true` (it posts to an outside service).
   - `/bpe:gh-issue` is the reading side: it fetches an existing GitHub issue by number, whoever wrote it, and routes it to brainstorm or plan; `/bpe:new-issue` is the writing side.
     It checks a fetched issue against the format.
     A conforming issue with acceptance criteria takes the plan route.
     A nonconforming issue gets its missing sections named to the user, then takes the brainstorm route.
     It never refuses an issue.
   - `.github/ISSUE_TEMPLATE/agent-ready.md` is a GitHub issue template with the required and optional sections as headings.
     A pytest asserts that its section headings, in order, match the ones `references/issue-format.md` defines, so the two cannot drift.
3. **What the permanent spec's Goals holds (#55).**
   - `references/session-management.md` gains a "Goals Section (spec.md)" definition beside the Invariants, Roadmap, and Available tooling definitions:
     - Goals describes the project as it behaves today, indexed by feature or component, never by phase, release, or issue.
     - One entry per feature, at planner depth: what a planner needs to change the feature without reading the code (the user-visible surface, the contract others depend on, options and defaults, and the rules that were decisions), with no examples, rationale, or history.
     - A sentence that starts `Planned (ITEM):` is behavior the named `**Upcoming:**` item will build; it loses the prefix when the item ships.
       A sentence that starts `Known gap:` is a place where the code or docs fall short of the entry, naming the Upcoming item or issue that covers it.
       The marker is inline, on the sentence, because planned behavior written in the present tense reads as built.
     - A `### Feature Status` table opens Goals, with the columns Feature, State, Open Work, Docs, and Code.
       It carries release state; `**Shipped:**` stays the archive index of converged plans, and the table wins when the two disagree.
     - A `### Rules Every Feature Follows` subsection states cross-cutting behavior once.
     - Banned forms: a heading named for a phase, release, or issue, and phase notes such as "renamed everywhere".
     - Goals holds behavior and contract; CLAUDE.md holds how the code is built; neither repeats the other.
     - No hard size cap.
       Decision: `/bpe:retrofit --resync` reports when `spec.md` passes 128 KB and offers to move the longest entries' detail into linked files, since very large projects can have large specs (2026-11-22 review).
     - `## Component boundaries` and `## Success criteria` are restated as standing descriptions of the project, not per-phase lists.
     - The file's other text that describes who edits `**Upcoming:**` and Goals changes to match the rules below.
   - Brainstorm merge mode edits or adds feature entries and marks the new behavior `Planned (ITEM):`, tied to a named `**Upcoming:**` item that the same run adds.
     The Q&A stays scoped to the change.
     The diff shown before saving must add no phase-, release-, or issue-named heading.
     New-spec mode writes feature entries and the Feature Status table from the start.
     An adjacency candidate sorted "now" lands in an entry.
   - `/bpe:plan` on a spec whose Goals has a Feature Status table plans the `Planned (ITEM):` sentences of the Upcoming item the user names, names that item in the plan header, and stops with a message when nothing is marked.
     On a spec without the table it keeps today's behavior (plan the section or package the user names) and prints one line suggesting `/bpe:retrofit --resync`.
   - The Archive routine in `skills/plan/SKILL.md` gains a fold-in step that runs only when the archived plan converged and the spec has a Feature Status table.
     It captures the `## Spec Slice` in `accomplishment.md` first, then removes the item's `Planned` prefixes, corrects the entries to what was built, updates the Feature Status table and `**Upcoming:**`, shows the spec diff, and writes it only after the user confirms.
     A superseded or partial plan, or an old-shape spec, leaves Goals untouched.
   - `skills/session-summary/SKILL.md` Step 5 runs the Archive routine through the `**Shipped:**` line and the fold-in, stopping only before the routine's fresh-plan step.
     Today it stops after `accomplishment.md` and skips the Shipped line.
   - `/bpe:gh-issue`: the brainstorm route enters merge mode when `spec.md` exists.
     The plan route on a spec with a Feature Status table first records the issue's behavior change as `Planned (ITEM):` sentences in the affected entry and an `**Upcoming:**` item, shows the diff, writes it after confirmation, and then plans that item.
   - `/bpe:retrofit`:
     - The repo read covers the docs, the changelog, and the public API, not only top-level docstrings.
     - The skill describes Goals, Component boundaries, and Success criteria in the format above.
     - `--resync` checks Goals entry by entry against the code and offers a rebuild when Goals has no Feature Status table.
     - Structure Migration builds Goals from the repo when the old spec has no project-level requirements.
     - A rebuild is staged: the Feature Status table first, then entries confirmed with the user in groups.
   - `skills/review/SKILL.md` treats each Goals entry and the Feature Status table as decision units.
   - `bpe/README.md`'s description of spec.md matches the Goals definition.
4. **`/bpe:init` (#28).**
   - A new skill, `/bpe:init`, prepares a user and a repo for BPE work and writes the results to their proper homes.
     Frontmatter: `model: sonnet`, `disable-model-invocation: true`.
     Mason's intent (2026-07-26): profile and repo setup must be codified, not silently configured by an agent editing user-local files ad hoc.
   - Model profile setup: one AskUserQuestion per role group (spec-shaping skills, validator and final-validator, step-executor and execute-plan, cheap-research), offering the newest Recommended Tier Map as the default answers, with the frontmatter defaults and an alias-only setup as alternatives.
     It asks the scope (user-global `~/.claude/bpe.local.md` or per-project `.claude/bpe.local.md`) and whether to define a second profile (work).
     It writes the file and never commits it; for a per-project file it confirms `.gitignore` covers `.claude/*.local.md`, adding the line with consent.
   - Repo pre-flight setup: everything `/bpe:goal` pre-flight refuses on becomes something init fixes with consent: `.gitignore` entries for `commit-msg.md` and `goal.md`, `.ai-sessions/` creation, and a verification-command probe (manifest autodetect, else a prompt) recorded to the target repo's `spec.md` `## Available tooling` when a spec exists.
   - `references/model-profiles.md` gains a fenced YAML profile block under its newest dated Recommended Tier Map heading, in the `bpe.local.md` frontmatter schema.
     Init reads that block at run time, never the prose table and never hardcoded model IDs.
     A pytest asserts the newest block parses and every key in it names a shipped skill or agent.
   - `.claude/bpe.local.md.example` is deleted.
     `model-profiles.md`, `bpe/README.md`, and `CLAUDE.md` point at `/bpe:init` instead.
   - Design decisions confirmed 2026-11-03, carried unchanged:
     - The name is `/bpe:init` despite the built-in `/init`; the namespace disambiguates.
     - Init reads the Recommended Tier Map at run time, so the skill never goes stale when the map updates, and always offers an alias-only option for environments that cannot pin frontier IDs.
     - Init is re-runnable: it shows the current resolved state (existing profile file, existing gitignore entries) and edits rather than overwrites, never replaces an existing profile without showing a diff first, and lists where the user's profile differs from the newest recommended map, so it doubles as the "update my models" tool.
     - Init never touches skill or agent frontmatter; profiles stay the only per-user override layer, since frontmatter lives in the plugin cache and an edit there is wiped on the next update.
5. **Deterministic artifact checks and templates (2026-11-22 review).**
   Mason's direction: spec.md, plan.md, and todo.md are validated with deterministic tools, and output that should be the same every time is rendered from templates so it can be rendered and validated, not written freehand.
   Both scripts are stdlib-only and live in `bpe/scripts/`, with pytest coverage under `tests/`.
   - `scripts/check-artifacts.py <path>...` checks the BPE artifacts it is given and prints one line per problem, `path:line: rule: message`.
     It exits 1 when any hard failure is found and 0 otherwise; warnings print and never fail.
     - plan.md, hard: step headings read `### Step N: <title>`, with an optional trailing `(task)`; step numbers run in order with no gaps or repeats; every section declares a `**Tools:**` block (or `**Tools:** none`) and a `**Batch:**` line.
     - todo.md, hard: every item line is a `- [ ]` or `- [x]` checkbox; the top-level items match plan.md's steps one for one, in the same order, with the same titles.
     - spec.md in the 0.7 form, hard: the canonical section order from `references/session-management.md`.
       Warnings: the Goals shape (the Feature Status table and its columns, a heading named for a phase, release, or issue, malformed `Planned (ITEM):` and `Known gap:` markers), since a heading check has false positives ("OAuth 2.0") and false negatives ("### Active phase").
     - spec.md in the pre-0.7 layout (no `## Invariants` and no `## Roadmap / phase log`): one `pre-0.7 layout` warning and no section checks, so this repo's own spec passes.
     - Callers: `/bpe:plan` after it writes plan.md and todo.md, repairing until clean; `/bpe:brainstorm`, `/bpe:retrofit`, and `/bpe:apply-review` before they show a spec diff; `/bpe:goal` pre-flight, which refuses on a hard failure and names it.
   - `scripts/render-artifact.py <kind>` renders fixed-shape output from `string.Template` files in `bpe/templates/`, taking its values as JSON on stdin or, for todo.md, from plan.md itself.
     - `todo`: todo.md derived from plan.md's step headings, so todo.md is no longer written by the model; existing `[x]` marks carry over by step title.
     - `goal`: goal.md from the mode, the condition, and the resolved verification command; the 4,000-character cap check moves into the script, which exits 1 over the cap.
     - `accomplishment`: the accomplishment.md skeleton for the Archive routine, with the prose fields filled from the JSON.
     - `issue`: the `/bpe:new-issue` body, with the sections in the `references/issue-format.md` order, so the draft conforms by construction.
     - The skills that write these four artifacts call the script instead of writing them freehand; prose inside a field stays model-written.
   - Spec and plan bodies stay model-written; the checker validates them.
6. **Docs and version.**
   - `CLAUDE.md` drops the hand-sync rule for the retired example and names `/bpe:init`, `/bpe:new-issue`, the issue template, `check-artifacts.py`, and `render-artifact.py`.
   - `plugin.json` version is 0.7.4.

### Design decisions (confirmed 2026-11-19 and 2026-11-22)

- Decision: #55 and the remaining #58 items fold into 0.7.4 beside #28 and #48 (2026-11-19).
- Decision: the sweep resume is a pre-flight change, not a new mode (2026-11-19).
- Decision: this repo's spec takes 0.7.4 as an appended package and migrates in the post-0.7.5 resync; the 2026-11-07 deferral stands.
- Decision: #55's five owner defaults are taken as written: planner depth, no hard size cap with a resync report, the Feature Status table winning over `**Shipped:**`, Goals against CLAUDE.md, and release state in the table updated by the project's own release checklist.
- Decision: the new Goals rules key on the Feature Status table; a spec without it keeps today's planning behavior, honoring the 0.7 rule of no forced migration.
- Decision: the issue format has three required sections and three optional ones; `/bpe:new-issue` posts only after confirmation; `/bpe:gh-issue` routes on conformance and never refuses.
- Decision: the GitHub issue template ships in 0.7.4, kept in step with `issue-format.md` by a test.
- Decision: `.claude/bpe.local.md.example` is retired; the YAML block in `model-profiles.md` is the one machine-readable copy of the map.
- Decision: the agent trims move procedure into the protocol references and keep the hard invariants restated in each agent, preserving the 2026-07-25 defense-in-depth ruling.
- Decision: the goal loop gates on text-level checks and `just check`; the recorded runs of interactive skills happen in a manual pass before the PR.
- Decision: no vendored rules for this repo; it has one contributor, and 0.7.2 and 0.7.3 vendored nothing.
- Decision: deterministic artifact checks and fixed-shape templates land in 0.7.4, stdlib-only (`string.Template`, no Jinja), so `deps: frozen` holds and no new prerequisite reaches users (2026-11-22 review).
- Decision: the resync size report threshold is 128 KB (2026-11-22 review).

### Constraints

- `deps: frozen`: the scripts and hooks stay stdlib-only; no dependency changes beyond the dev group.
- `paths: bpe/**, tests/**, .github/ISSUE_TEMPLATE/**, .claude/bpe.local.md.example, CLAUDE.md, README.md`
- The loop never edits this repo's `spec.md`, which stays in the pre-0.7 layout.
- Shipped frontmatter stays alias-only; `/bpe:init` never edits frontmatter and never commits a profile file.
- `/bpe:new-issue` never posts without the user's confirmation.
- No loop-contract change beyond the sweep-resume pre-flight: sequential dispatch, one commit per batch, SHA verification, and the findings schema all hold.
- Python behavior changes are test-first under `just check`.
- Python: per the python:python skill. Prose: per the user's writing hard rules.

### Tools

**Skills:** plugin-dev:skill-development, plugin-dev:agent-development, python:python, skill-creator:skill-creator

**MCPs:** none

**Verification command:** `just check`

### Verification

The goal loop's gate, checkable by reading files or running commands:

- `just check` passes, including the new tests: goal-run-report continuation attribution, issue template headings against `issue-format.md`, the newest YAML tier-map block, and `check-artifacts.py` and `render-artifact.py` on fixtures (a clean plan and todo pair, a todo that drifted from its plan, a 0.7-form spec out of order, this repo's pre-0.7 spec, a goal.md over the cap).
- `render-artifact.py todo` on the release's own plan.md reproduces its todo.md, and `check-artifacts.py plan.md todo.md` exits 0.
- `wc -c bpe/agents/step-executor.md bpe/agents/validator.md` reports under 10,000 for each, and each still states the hard invariants listed in item 1.
- `skills/goal/SKILL.md` pre-flight and the playbook state the fully checked `todo.md` rule and the sweep dispatch.
- `references/session-management.md` has a Goals definition that states the index, the entry shape, the depth rule, both markers, the Feature Status table, and the banned forms.
- `skills/brainstorm/SKILL.md` no longer says a merge-mode run "adds a phase", and new-spec mode writes entries and the Feature Status table.
- `skills/plan/SKILL.md` says what it plans in a spec with a Feature Status table, what it does when nothing is marked, and what it does on a spec without the table; its Archive routine has the fold-in with the converged-only condition.
- `skills/session-summary/SKILL.md` reaches the Shipped line and the fold-in.
- `skills/gh-issue/SKILL.md` covers both routes when `spec.md` exists and routes on the issue format.
- `skills/retrofit/SKILL.md` describes Goals, Component boundaries, and Success criteria, deepens the repo read, and builds Goals in Structure Migration.
- `skills/init/SKILL.md` and `skills/new-issue/SKILL.md` exist; `claude plugin validate ./bpe` passes with only the expected missing-icon warning.
- `.claude/bpe.local.md.example` is gone, and `grep -rn "bpe.local.md.example" bpe CLAUDE.md README.md` matches nothing.
- `plugin.json` version is 0.7.4.

The manual pass before the PR, run in one interactive session with `--plugin-dir ./bpe` in scratch repos, with each spec diff attached to the PR body:

- A merge-mode brainstorm on a spec with entries edits or adds entries with `Planned (ITEM):` sentences and adds no phase-, release-, or issue-named heading.
- `/bpe:plan` on that spec plans only the named item; on a spec with a Feature Status table and nothing planned it stops with a message; on an old-shape spec it plans the named package and prints the resync suggestion.
- Archiving the converged plan leaves Goals describing the new behavior as current, with no `Planned` prefix for that item and the table updated; archiving a superseded plan changes nothing in Goals.
- A cycle through `/bpe:gh-issue`'s plan route leaves Goals describing the new behavior after the archive.
- `/bpe:retrofit --resync` on markwright at `274c4fd` proposes a feature-indexed Goals built from the code and docs.
- `/bpe:new-issue` drafts a conforming issue and posts nothing until confirmed; `/bpe:gh-issue` on a nonconforming issue names the missing sections.
- `/bpe:init` in a throwaway repo: a fresh run, a re-run that changes nothing, both scopes, and the written profile passing the `model-profiles.md` schema.
- A skill-creator triggering eval: `/bpe:init`'s description fires on "set up bpe", "bpe init", and "configure bpe models", and not on generic `/init` asks.

### Non-goals for this package

- No `/bpe:init` switching the session model or editing `settings.json`.
- No new goal mode for sweep-only resumes.
- No migration of this repo's `spec.md` (post-0.7.5 resync).
- No change to the review renderer (0.7.5, #17).

### Deferred

- Rendering spec.md and plan.md bodies from contracts instead of model-written prose; revisit after 0.7.5's renderer lands.
- Reconciling `**Upcoming:**` and `**Deferred:**` against open GitHub issues, as a report-only step in resync and merge mode.
- Reordering the canonical sections so Roadmap and Goals come before Invariants; it would make every existing 0.7 spec non-canonical.
- The validator reading Starting context "to weight findings", which `session-management.md` claims and `agents/validator.md` never says.
- `/bpe:init` writing CLAUDE.md or starting a brainstorm.
- `/bpe:gh-issue` reformatting an existing issue to conform.
