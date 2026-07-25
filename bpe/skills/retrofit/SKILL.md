---
name: retrofit
description: "Retrofit a BPE-compatible spec.md onto an existing project that lacks one. Reads repo state and runs a shortened Q&A focused on gaps."
model: opus
disable-model-invocation: true
argument-hint: "[--replace]"
---

# Retrofit Command

Add a BPE-compatible spec.md to an existing project that never went through `/bpe:brainstorm`.
Most of what a spec needs already lives in the repo; read it there instead of asking.
The shortened Q&A covers only the gaps the repo cannot answer: intent, direction, and scope.
The resulting spec.md matches the format `/bpe:brainstorm` produces, so `/bpe:plan` consumes either without knowing which skill wrote it.

## Procedure

1. **Guard against clobbering.**
   Check for spec.md at the repo root.
   If it exists and `--replace` is NOT in $ARGUMENTS, refuse: tell the user a spec.md already exists and that `/bpe:retrofit --replace` overwrites it, then stop.
   If it exists and `--replace` is present, proceed; step 5 overwrites the file.
   If it does not exist, proceed.

2. **Read repo state.**
   Run `ls` at the repo root.
   Read README.md if present.
   Read CLAUDE.md if present.
   Read whichever manifest files exist: package.json, pyproject.toml, go.mod, Cargo.toml.
   If the language is detectable from the manifests, read the top-level module docstrings (or equivalent package-level docs) of the main source directories.
   Use what these reveal to pre-fill draft answers, so the Q&A in step 4 asks only about gaps.

3. **Blindspot pass.**
   Run this pass BEFORE the shortened Q&A. It calibrates the rest of the session to what the user already knows. Same shape as `/bpe:brainstorm` Step 0; `${CLAUDE_PLUGIN_ROOT}/references/session-management.md` documents the resulting `## Starting context` section canonically.
   1. Ask ONE question about the user's starting context: domain familiarity, prior attempts at this idea, experience with this codebase. The repo state from step 2 informs the question; it does not answer it.
   2. Given the answer, surface 3-5 unknown-unknowns: questions the user probably doesn't know to ask, framed as "you may want to consider" rather than "you must answer". The user may engage with any, all, or none of them.
   3. Keep the user's context answer verbatim; step 5 writes it into spec.md under `## Starting context`. Do not paraphrase; the plan writer and validator calibrate against the user's own words.
   4. Proceed to the shortened Q&A in step 4.

4. **Shortened Q&A.**
   One question at a time, same rule as `/bpe:brainstorm`.
   Cover four topics, skipping any the repo state from step 2 already answers:
   - Project goal: what the project does and where the user wants it to go.
   - Currently in place vs planned: which parts exist and work today, which are aspirational.
   - Tooling to declare: run the same Tool discovery pass `/bpe:brainstorm` runs before saving.
     Enumerate candidate MCPs with `ToolSearch` using a domain-suited query, pick candidate skills from the session reminder list, then ask ONE question presenting the candidates for the user to confirm, drop, or extend.
     If the user wants suggestions for external tools not in the session, dispatch the `bpe:cheap-research` subagent via the Agent tool with a single research question naming the project domain; the agent returns a ranked list of at most 10 entries (`<name> :: <one-line relevance note> :: <source URL or path>`) or the line `no relevant results` followed by one sentence naming what was searched.
     Only confirmed entries go into spec.md.
     If the repo matches none of the test-runner manifests read in step 2 (package.json, pyproject.toml, go.mod, Cargo.toml), also ask for the exact verification command (e.g. `vale docs/` for a prose project) and record it as a `**Verification command:** <command>` line in the `## Available tooling` section, between `**Skills:**` and `**Notes:**`; `/bpe:goal`'s pre-flight falls back to this field when it can't autodetect a test runner.
   - Out of scope: what the project deliberately does not do.

5. **Write spec.md at the repo root.**
   Match the format `/bpe:plan` consumes, sections in this order under `# <title>`: `## Starting context`, `## Project overview`, `## Available tooling`, `## Goals`, `## Non-goals`, `## Component boundaries`, `## Success criteria`.
   `## Starting context` records the step 3 context answer verbatim.
   `## Available tooling` uses the exact section format `/bpe:brainstorm` writes:

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

   If the user says no validators apply at the project level, write the section with both lists empty and `**Notes:** No domain validators apply for this project. /bpe:plan will declare "**Tools:** none" for every section.` This still creates the section so plan.md has a known structure to read.
