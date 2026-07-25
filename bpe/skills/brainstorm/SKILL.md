---
name: brainstorm
description: Iterative Q&A to develop a thorough project specification (spec.md)
model: opus
disable-model-invocation: true
---

# Brainstorm Command

Ask me one question at a time so we can develop a thorough, step-by-step spec for this idea. Each question should build on my previous answers, and our end goal is to have a detailed specification I can hand off to a developer who will implement using good TDD practices.

Let's do this iteratively and dig into every relevant detail. Remember, only one question at a time.

## Step 0: Blindspot pass

Run this pass BEFORE the substantive Q&A. It calibrates the rest of the session to what the user already knows.

1. Ask ONE question about the user's starting context: domain familiarity, prior attempts at this idea, experience with this codebase (if one exists).
2. Given the answer, surface 3-5 unknown-unknowns: questions the user probably doesn't know to ask, framed as "you may want to consider" rather than "you must answer". The user may engage with any, all, or none of them.
3. Record the user's context answer verbatim in spec.md under `## Starting context`. Create the section if it doesn't exist. Do not paraphrase; the plan writer and validator calibrate against the user's own words.
4. Proceed to the standard one-question-at-a-time Q&A.

## Critical Focus Areas

**TDD Implementation Ready**: Ensure the spec includes requirements for YOUR application logic that can be converted into failing tests first. Focus on business rules, data validation, error handling, and custom algorithms that YOU will implement, not framework or library behavior. Think about what application-specific behaviors need verification.

**Component Boundaries**: Identify clear, testable components that can be implemented independently and then integrated together. Each component should have well-defined inputs, outputs, and responsibilities.

**Global Claude Config Integration**: Follow the established development patterns and preferences from the user's global Claude configuration (found in ~/.claude/CLAUDE.md and related files). Respect their preferred tools, coding standards, and project structure approaches.

Focus on getting the technical details and component boundaries clear enough that the resulting spec can be broken down into implementable, testable steps that follow the user's established development workflow.

The goal of this is NOT to implement the application or write a bunch of code, but to create a specification file that you will use later to create a plan. I will review this after and make manual changes. You may write _some_ code to illustrate specific points, but do not focus on that. Instead focus on making the specification usable for you to consume and plan with later.

## Tool discovery (before saving spec.md)

After the substantive Q&A and before writing the final spec, run one more pass: enumerate the MCP servers and skills available in this session that might apply to the project's domain. The goal is to populate an `## Available tooling` section in spec.md so `/bpe:plan` can assign validators per section and `/bpe:goal` can dispatch the `bpe:validator` agent with the right consultation set.

Procedure:

1. List candidate MCPs. Use `ToolSearch` with a search query suited to the project's domain (e.g. for a Temporal project, search for "temporal"; for a Postgres project, search for "postgres"). Capture the MCP server names that come back. Also list any plugin-namespaced MCPs visible in the session (e.g. `mcp__claude_ai_Google_Drive__*` for a project that involves Drive). If none look relevant, that's fine; the list can be empty.
2. List candidate skills. Read the available skills from the session reminder. Pick those whose descriptions mention the project's domain (e.g. `temporal:temporal-developer`, `python:python`, `content-design:tutorial-writing`).
3. Ask the user ONE question listing the candidates: "These MCPs and skills look potentially relevant to your project. Which should the validator consult during goal-mode runs? Drop any that don't apply; add any I missed."
4. If the user wants suggestions for external tools not in the session, dispatch the `bpe:cheap-research` subagent with the project domain; present the shortlist for user confirmation. Dispatch via the Agent tool with a single research question naming the project domain; the agent returns a ranked list of at most 10 entries (`<name> :: <one-line relevance note> :: <source URL or path>`) or the line `no relevant results` followed by one sentence naming what was searched. Only confirmed entries go into spec.md.
5. If the project's tech stack matches none of the test-runner manifests `/bpe:goal` autodetects (pyproject.toml, package.json, Cargo.toml, go.mod), ask ONE more question: what exact command verifies the work (e.g. `vale docs/` for a prose project)? Record the answer as a `**Verification command:** <command>` line in the `## Available tooling` section, between `**Skills:**` and `**Notes:**`. `/bpe:goal`'s pre-flight falls back to this field when it can't autodetect a test runner.
6. Record the user's confirmed set in spec.md.

The output section format:

```markdown
## Available tooling

Tools the `bpe:validator` agent should consult when reviewing diffs in `/bpe:goal` runs. `/bpe:plan` propagates these to per-section declarations in plan.md.

**MCPs:**
- mcp__temporal-docs__search_temporal_knowledge_sources

**Skills:**
- temporal:temporal-developer
- python:python

**Notes:** Validator should focus on workflow non-determinism, activity heartbeats, and signal/query semantics in any code under `workflows/` and `activities/`.
```

When step 5 collected a verification command, add a `**Verification command:** <command>` line between `**Skills:**` and `**Notes:**`. Omit the line when a test runner is autodetectable. `${CLAUDE_PLUGIN_ROOT}/references/session-management.md` documents the full section format canonically.

If the user says no validators apply at the project level, write the section with both lists empty and `**Notes:** No domain validators apply for this project. /bpe:plan will declare "**Tools:** none" for every section.` This still creates the section so plan.md has a known structure to read.

## Saving

Once we are done, save the spec as @spec.md. Place the `## Starting context` section from Step 0 between `# <title>` and `## Project overview`. Make sure the `## Available tooling` section is present near the top of the spec (after the project overview, before the detailed requirements).

Here's the idea:
