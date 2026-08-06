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

## /bpe:init (2026-07-26, requested)

Mason's ask, verbatim intent: profile and repo setup must be codified, not silently configured by an agent editing user-local files ad hoc.

### Goal

A `/bpe:init` skill that interactively prepares a user and a repo for BPE work, then writes the results to their proper homes.
Two concerns, both owned by init:

1. **Model profile setup.** Walk the user through the tier map (AskUserQuestion, one question per role group): spec-shaping skills, validator, step-executor/execute-plan, cheap-research. Offer the current Recommended Tier Map from references/model-profiles.md as the default answers, with the frontmatter defaults and full-alias setups as alternatives. Ask scope (user-global ~/.claude/bpe.local.md vs per-project .claude/bpe.local.md) and whether to define a second profile (work). Write the file; never commit it; confirm .gitignore covers .claude/*.local.md when writing per-project.
2. **Repo pre-flight setup.** Everything /bpe:goal refuses on becomes something init fixes with consent: gitignore entries for commit-msg.md and goal.md, .ai-sessions/ creation, and a verification-command probe (manifest autodetect, else prompt) recorded to spec.md's Available tooling section when a spec exists.

### Design decisions (proposed, confirm at review)

- Decision: name is `/bpe:init` despite the built-in /init; the namespace disambiguates, and the concept (initialize this context for BPE) matches user expectation. (confirm at review)
- Decision: init reads the Recommended Tier Map section at runtime rather than hardcoding model IDs, so the skill never goes stale when the map updates. (confirm at review)
- Decision: init is re-runnable: it shows current resolved state (existing profile file, existing gitignore entries) and edits rather than overwrites; an existing profile is never clobbered without showing a diff first. (confirm at review)
- Decision: init does NOT touch skill/agent frontmatter defaults; those remain the shipped tiers, and profiles remain the only per-user override layer (Goal 11 unchanged). (confirm at review)

### Verification

skill-creator triggering eval (should fire on "set up bpe", "bpe init", "configure bpe models"; not on generic /init asks); manual smoke test in a throwaway repo (fresh init, re-run idempotence, per-project vs global scope); profile file it writes passes the model-profiles.md schema.

### Sequencing

Layers on the 0.6.x line after the fable-alignment package or alongside it; touches no autonomous-loop contracts.
