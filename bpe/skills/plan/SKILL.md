---
name: plan
description: Transform spec.md into an implementation roadmap (plan.md + todo.md) of TDD Feature steps and non-TDD Task steps
model: opus
disable-model-invocation: true
argument-hint: "[--archive | --regen] [--no-discover]"
---

# Plan Command

## Flag handling

Run this check before anything else in this skill, including Tool discovery.

1. Check for `plan.md` at the repo root.
2. `plan.md` absent: proceed with the rest of this skill and generate a fresh plan. `--archive` and `--regen` are no-ops in this case.
3. `plan.md` present and neither `--archive` nor `--regen` in $ARGUMENTS: refuse and stop. Report in this shape:

   > plan.md exists (last modified <date>, N/M items checked). Use `--archive` to preserve it in .ai-sessions before regenerating, or `--regen` to discard and regenerate.

   Fill `<date>` from the file's modification time (`date -r plan.md +%Y-%m-%d`). Fill `N/M` from todo.md's top-level checkbox counts: N is the checked count, M the total. If todo.md is missing, write "no todo.md" in place of "N/M items checked".
4. `plan.md` present and `--archive` in $ARGUMENTS: run the Archive routine below, then proceed to generate a fresh plan.
5. `plan.md` present and `--regen` in $ARGUMENTS: delete `plan.md` and `todo.md` at the repo root (`rm -f plan.md todo.md`), then proceed to generate a fresh plan.

### Archive routine

Referenced by the `--archive` flag above and by `/bpe:session-summary`'s end-of-goal archive prompt.
The archive layout and the accomplishment.md format are canonically documented in `${CLAUDE_PLUGIN_ROOT}/references/session-management.md` under "Plan Archives (accomplishment.md)"; read that section before step 5 below.

1. Propose a slug for the archive directory based on plan.md's stated goals and the checked items in todo.md. Same 2-3 word kebab-case shape as session-summary slugs (e.g. `add-user-auth`); use `init` or `v1` when the plan has no sharper focus, such as a project's first archive. Ask the user to confirm or edit the slug. Do not touch any files until the user answers.
2. `mkdir -p .ai-sessions/<slug>/`
3. `mv plan.md .ai-sessions/<slug>/plan.md`
4. `mv todo.md .ai-sessions/<slug>/todo.md`
5. Write `.ai-sessions/<slug>/accomplishment.md` following the accomplishment.md template in session-management.md. Populate it from the just-moved plan.md and todo.md plus `git log` commit subjects; the template section documents each field.
6. Proceed to generate a fresh plan (the rest of this skill).

Draft a detailed, step-by-step blueprint for building this project. Then, once you have a solid plan, break it down into small, iterative chunks that build on each other. Look at these chunks and then go another round to break it into small steps. Review the results and make sure that the steps are small enough to be implemented safely with strong testing, but big enough to move the project forward. Iterate until you feel that the steps are right sized for this project.

From here you should have the foundation to provide a series of prompts for a code-generation LLM that will implement each step (test-driven for Feature steps; see the two templates below). Prioritize best practices, incremental progress, and early testing, ensuring no big jumps in complexity at any stage. Make sure that each prompt builds on the previous prompts and (for Feature steps) ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step.

## Testing Guidelines for Generated Prompts

When specifying tests in RED phases, focus ONLY on application logic:

**DO test:**
- Business logic you're implementing
- Data validation rules you define
- Error handling you add
- Custom algorithms or calculations
- Integration between YOUR components

**DO NOT test:**
- Framework functionality (e.g., "Django can connect to database")
- Third-party library behavior (e.g., "requests library makes HTTP calls")
- Language features (e.g., "Python dicts work correctly")
- Configuration loading (unless complex custom logic)
- Trivial code (simple getters, setters, pass-through methods)

**Examples:**
- ❌ BAD: "Test that Django User model can be created" (tests Django)
- ✅ GOOD: "Test that custom password validator rejects weak passwords" (tests YOUR logic)
- ❌ BAD: "Test that database connection works" (tests framework)
- ✅ GOOD: "Test that user registration creates audit log entry" (tests YOUR logic)

## Critical Requirements for Execute-Plan Compatibility

**Each prompt must be structured as numbered sub-steps that execute-plan can follow sequentially:**

### Feature template (TDD RED/GREEN/REFACTOR)

The default template.
Use it for steps where a bug could hide (see the heuristic below).
Feature step titles carry no marker.

```
### Step X: [Descriptive Title]

**NOTE**: [Any important context about existing implementation]

```text
[Prompt for code-generation LLM with numbered instructions]:

1. RED: Write [specific type] tests first:
   - Create/modify [exact file path]:
     - Test [specific scenario 1]
     - Test [specific scenario 2]
     - Test [specific edge case]

   Example RED phase (GOOD):
   1. RED: Write validation tests first:
      - Create tests/test_user_validation.py:
        - Test that custom password validator rejects passwords without special chars
        - Test that email validator rejects disposable email domains
        - Test that username validator blocks profanity

   Example RED phase (BAD - Don't do this):
   1. RED: Write model tests first:
      - Create tests/test_models.py:
        - Test that User model can be created  ← Testing Django, not your code
        - Test that database saves User correctly  ← Testing Django ORM
        - Test that email field stores email  ← Testing Django field behavior

2. Document [specific component]:
   - Create/update [exact file path]
   - Document [specific behavior/rules]
   - Include [specific examples/configurations]

3. GREEN: Write MINIMAL code to make tests pass:
   - Create [exact file path]
   - Implement [specific functionality]
   - Use [specific patterns/libraries]
   - Just enough to pass tests

4. RED: Add integration tests:
   - Test [specific integration scenario]
   - Test [specific error conditions]

5. GREEN: Wire up integration minimally

6. REFACTOR: Improve [specific aspects]

7. Update documentation with [specific updates]

8. Verify meaningful test coverage of YOUR application logic and run `just check`
```

### Task template (non-TDD generic)

Use this template for steps where the TDD cycle adds nothing.
Task step titles carry a trailing `(task)` marker; feature steps stay unmarked.

````
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
````

### Choosing between templates (plan-writer heuristic)

Use Feature when a bug could hide: new logic, custom validation, a novel algorithm.
Use Task for wiring, renames, config, dependency management, docs, scaffolding, refactors with no behavior change, or any non-code work.
Fallback rule: if uncertain, use Feature.

### Meta-prompting

**Meta-prompting is the mechanism.** The numbered sub-steps in each plan.md step are prompts the executor will follow literally, not descriptive summaries.
This skill's job is to write good executor prompts, not to summarize what each step is about.
A well-formed plan.md step reads like a direct instruction to the code-generation LLM: exact file paths, exact test scenarios, exact commands.
The executor's role reduces to following the instruction verbatim.
This applies to both Feature and Task templates equally.
The Task template's Scope / Tooling / Do / Verify / Document sub-steps are still prompts, just shaped for wiring/config/docs/refactor/scaffolding work instead of the TDD cycle.

## Prompt Generation Requirements

1. **Executable Instructions**: Each numbered sub-step must be a specific instruction that execute-plan can follow exactly, not general guidance

2. **File Path Specificity**: Every prompt must specify exact file paths (e.g., "tests/test_activities/test_validation.py", not "test files")

3. **Test Scenario Detail**: Each RED phase must list specific test scenarios to implement, not generic "write tests"

4. **Template Structure**: Every Feature prompt must follow RED-GREEN-REFACTOR with clear phases; every Task prompt must follow Scope / Tooling / Do / Verify / Document

5. **Sequential Dependencies**: Each prompt builds on previous prompts with no orphaned code

6. **Integration Requirements**: Every Feature prompt ends with wiring the new code into existing systems; Task prompts end with their Verify and Document sub-steps

Make sure and separate each prompt section. Use markdown. Each prompt should be tagged as text using code tags. The goal is to output prompts that execute-plan can follow step-by-step, but context and architectural decisions are important as well.

## Tool discovery

Run tool discovery before drafting the per-section Tools blocks.
Discovery has two passes.

**Pass 1: session enumeration (existing).**
Read spec.md's `## Available tooling` section.
`/bpe:brainstorm` populated it by enumerating the MCPs and skills present in the session.
This list seeds the project-wide pool that the per-section Tools blocks narrow down; Pass 2 results cached under `## External tool candidates` join it.

**Pass 2: external discovery via `bpe:cheap-research` (on by default).**
Dispatch the `bpe:cheap-research` subagent through the Agent tool to find marketplace skills and public plugins the session pool misses.
Sample dispatch prompt:

> Given the project domain in spec.md's Project overview, find installed marketplace skills and public plugins that could apply. Rank by relevance. Return up to 10.

Inline the Project overview text (or a one-paragraph digest) in the dispatch alongside the question; the agent can Read spec.md itself, but pasting the overview saves it a round trip.
Per the agent's output contract, the return is a ranked plain-text list of at most 10 entries, one line per result as `<name> :: <one-line relevance note> :: <source URL or path>`, or the line `no relevant results` followed by one sentence naming what was searched when the search comes up empty.
Treat returned entries as candidates, not automatic additions: fold one into a Tools block only when it plausibly applies to that section, and never invent tool names the agent did not cite.

### The `--no-discover` flag

If `--no-discover` appears in $ARGUMENTS, skip Pass 2 entirely.
Pass 1 still runs; it is a file read and costs nothing.
Use the flag when the session pool already covers the project domain or when the user wants a fast, offline planning pass.

### Caching results to spec.md

After Pass 2 returns usable results, append them to spec.md under a `## External tool candidates` section.
If the section is absent, create it directly after `## Available tooling`.
Keep each candidate on its own line in the agent's `<name> :: <note> :: <source>` shape so provenance survives.
On later `/bpe:plan` runs, skip Pass 2 when `## External tool candidates` is already populated and reuse the cached list.
(Re-running discovery with a `--refresh-discover` flag is future work, not yet implemented.)
A `no relevant results` return caches nothing: leave spec.md untouched and tell the user discovery found nothing.

## Per-section Tools block

Read spec.md's `## Available tooling` section (Pass 1 of Tool discovery above) before drafting plan.md.
For each plan section (top-level `##` heading in plan.md), decide which subset of the project's available skills, MCPs, and linters applies to that section's steps.
Both consumers draw from the same block: the executor invokes the Skills and consults the MCPs while doing the work; the `bpe:validator` consults the Skills and MCPs for guidance AND runs the Linters as adversarial review.
Record the decision immediately under the section heading using this exact format:

```markdown
## Section 2: Workflow implementation

**Tools:**
- Skills: temporal:temporal-developer
- MCPs: mcp__temporal-docs__search_temporal_knowledge_sources
- Linters: ruff check --output-format=json
```

Sub-field values are comma-separated.
Linters entries are shell commands the validator runs verbatim against the working tree.
Use a literal `none` for an empty sub-field (e.g. `- Linters: none`).

Sections that do not need domain validation (e.g. wiring config files, writing fixtures, scaffolding the project layout) use:

```markdown
**Tools:** none
```

A literal `none` value disables the validator dispatch for every step in that section.

### Shadowing (section default and per-step override)

- spec.md's `## Available tooling` list, plus any cached `## External tool candidates` entries, is the project-wide pool.
- A `**Tools:**` block per section shadows the project-wide default: it narrows the pool down to what that section's steps actually need.
- A `**Tools:**` block per step (placed immediately under the step's `### Step X:` heading) shadows the section default further: that step resolves against its own block and ignores the section's.

### Backwards compatibility

Existing plans that declare the legacy `**Validator consults:**` block still work.
The validator honors the old block name and treats it as a Tools block declaring Skills and MCPs with an empty Linters list.
New plans emit `**Tools:**` only; never write `**Validator consults:**` in fresh output.

### Guidance for picking tools per section

- A section that touches `workflows/`, `activities/`, or other Temporal-specific paths should declare the Temporal MCP and skill.
- A section that writes Python application code should declare `python:python` for style and toolchain rules, and the project's Python linter command under Linters.
- A section that writes pure scaffolding, fixtures, or framework-trivial code should declare `none`.
- Validator passes cost real tokens. Lean toward `none` when the declared tools would have nothing useful to say.

If the project-wide pool is empty (spec.md's `## Available tooling` lists no MCPs and no skills, and no `## External tool candidates` entries are cached), every plan section declares `**Tools:** none`. The plan still gets written; the validator-aware loop simply runs zero validator dispatches.

If spec.md has no `## Available tooling` section at all (legacy spec), proceed as if every section declares `none`. Do not retroactively prompt the user; the user can re-run `/bpe:brainstorm` if they want validators on this project.

## Output Format

Store the plan in @plan.md with:
- Current Status section showing implementation progress
- Each step as a detailed prompt with numbered sub-instructions
- Implementation Guidelines section
- Success Metrics section
- The `**Tools:**` block immediately under each section heading

Also create a @todo.md that:
- Mirrors the plan.md structure with checkboxes
- Tracks completion of each numbered sub-step
- Can be updated by execute-plan as work progresses

The spec is in the file called @spec.md
