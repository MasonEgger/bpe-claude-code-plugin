---
name: retrofit
description: "Retrofit a BPE-compatible spec.md onto an existing project that lacks one, or resync an existing spec.md to the code. Reads repo state and runs a shortened Q&A focused on gaps."
model: claude-opus-4-8
disable-model-invocation: true
argument-hint: "[--replace | --resync]"
---

# Retrofit Command

Add a BPE-compatible spec.md to an existing project that never went through `/bpe:brainstorm`.
Most of what a spec needs already lives in the repo; read it there instead of asking.
The shortened Q&A covers only the gaps the repo cannot answer: intent, direction, and scope.
The resulting spec.md matches the format `/bpe:brainstorm` produces, so `/bpe:plan` consumes either without knowing which skill wrote it.
With `--resync`, retrofit instead reconciles an existing spec.md to what the code does now and refreshes any vendored rules (see Resync Mode at the end).

## Procedure

1. **Guard against clobbering.**
   Check for spec.md at the repo root.
   If it does not exist, proceed in new-spec mode.
   If it exists and `--resync` is in $ARGUMENTS, proceed in resync mode (see Resync Mode); the spec is edited in place, never overwritten.
   If it exists and `--replace` is in $ARGUMENTS, proceed in new-spec mode; step 5 overwrites the file.
   If it exists and neither flag is present, refuse: tell the user a spec.md already exists, that `/bpe:retrofit --resync` reconciles it to the code and `/bpe:retrofit --replace` overwrites it, then stop.

2. **Read repo state.**
   Run `ls` at the repo root.
   Read README.md if present.
   Read CLAUDE.md if present.
   Read whichever manifest files exist: package.json, pyproject.toml, go.mod, Cargo.toml.
   If the language is detectable from the manifests, read the top-level module docstrings (or equivalent package-level docs) of the main source directories.
   Use what these reveal to pre-fill draft answers, so the Q&A in step 4 asks only about gaps.
   Derive Invariants candidates from the same read; the repo is a higher-signal source than negating interview answers.
   The manifests give the tech stack (language, runtime, primary frameworks, package manager) as prose bullets.
   A lockfile (uv.lock, package-lock.json, Cargo.lock, go.sum) makes `- deps: frozen` a candidate; propose it only when the dependency set looks settled, and never silently.
   The main source directories make `- paths: <dir>/**[, <dir>/**]` a candidate.
   Anything README.md or CLAUDE.md states as mandatory or forbidden is a prose candidate as written.
   These candidates go to the single confirm in step 4, not to their own question.

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
   - Tooling to declare: run the same pass `/bpe:brainstorm` runs, its "Tool discovery and the single confirm" section, inline.
     Enumerate candidate MCPs with `ToolSearch` using a domain-suited query, pick candidate skills from the session reminder list, build the vendoring proposal per brainstorm's Vendoring section, then ask ONE question with the same four parts brainstorm asks: tools to confirm, drop, or extend; the Invariants candidates from step 2 plus anything the Q&A surfaced; the scope sort from the out-of-scope topic below; and the vendoring proposal (omitted when the repo is private or nothing is vendorable).
     If the user wants suggestions for external tools not in the session, dispatch the `bpe:cheap-research` subagent via the Agent tool with a single research question naming the project domain; the agent returns a ranked list of at most 10 entries (`<name> :: <one-line relevance note> :: <source URL or path>`) or the line `no relevant results` followed by one sentence naming what was searched.
     Only confirmed entries go into spec.md.
     If the repo matches none of the test-runner manifests read in step 2 (package.json, pyproject.toml, go.mod, Cargo.toml), also ask for the exact verification command (e.g. `vale docs/` for a prose project) and record it as a `**Verification command:** <command>` line in the `## Available tooling` section, between `**Skills:**` and `**Notes:**`; `/bpe:goal`'s pre-flight falls back to this field when it can't autodetect a test runner.
   - Out of scope: what the project deliberately does not do, ever, and, for each goal, the three to five adjacent features an eager agent would bolt on without being asked (brainstorm's Adjacency pass, run against the goals the repo and the Q&A establish). Propose never, not now, or now for each, defaulting to not now; the single confirm carries the sort.

5. **Write spec.md at the repo root.**
   Write the sections in the canonical order defined under "Spec Section Order (spec.md)" in `${CLAUDE_PLUGIN_ROOT}/references/session-management.md`, the same order `/bpe:brainstorm` writes, under `# <title>`: `## Starting context`, `## Project overview`, `## Invariants`, `## Available tooling`, `## Roadmap / phase log`, `## Goals`, `## Non-goals`, `## Component boundaries`, `## Success criteria`.
   `## Starting context` records the step 3 context answer verbatim.
   `## Project overview` carries the mission (what the project is and where the user wants it to go); there is no separate mission section.
   `## Invariants` holds the rules that hold across every phase: the tech stack the step 2 manifests reveal, plus every constraint the repo or the user marks as non-negotiable (dependencies not to add, patterns to follow, things the project must never do). One bullet per rule.
   `## Roadmap / phase log` starts with `**Shipped:**` listing one line per existing `.ai-sessions/<slug>/` archive as `- <slug>: <one-line summary> (.ai-sessions/<slug>/)`, or `- none yet` if there are none, `**Upcoming:**` with any later phases the user named in step 4, and `**Deferred:**` with the step 4 out-of-scope answers that are not-now rather than never, one line each with a reason or trigger (or `- none`).
   `## Non-goals` records what the project deliberately does not do, ever; step 4's out-of-scope answers split between here (never) and `**Deferred:**` (not now).
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

   When vendoring was confirmed in step 4, run the Vendoring procedure from `${CLAUDE_PLUGIN_ROOT}/skills/brainstorm/SKILL.md` inline before writing, so the vendored files, the Invariants pointer bullets, and the author's `claudeMdExcludes` entry land together.

## Resync Mode

`/bpe:retrofit --resync` is the corrective for spec drift.
spec.md is permanent and edited in place, so between phases the code can move without the spec following; resync reads the code again and reconciles the spec to it.

1. Read the whole existing spec.md, then run step 2 (Read repo state) against the current tree.
2. Compare what the repo shows against what the spec claims, section by section: `## Project overview` and `## Goals` against what the code does now, `## Invariants` against the manifests and lockfile, `## Available tooling` against the session, `**Shipped:**` against the `.ai-sessions/<slug>/` archives on disk.
3. Ask only about contradictions, one question at a time: a goal the code has plainly delivered or abandoned, an invariant the code no longer honors, a tool that no longer applies.
   Do not re-run the blindspot pass or the full Q&A; resync confirms reality, it does not re-plan intent.
4. Write the reconciled spec to a scratch file, show `diff -u spec.md <scratch>`, and move it over spec.md only after the user confirms.
   Superseded text is rewritten in place, never appended.
5. If `.claude/rules/vendored/` exists, refresh it: for each vendored file, obtain the current source text per brainstorm's Vendoring step 3, write it to the scratch directory, and show `diff -u` against the vendored copy.
   Replace only the files the user confirms.
   Report any vendored file whose source can no longer be found (a renamed skill, a deleted rules file) rather than deleting it.
6. Do not touch plan.md or todo.md; resync is a spec operation.
