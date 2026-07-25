# Session Management

This file is the single source of truth for the format and workflow of session artifacts in `.ai-sessions/`. The `/bpe:session-summary`, `/bpe:execute-plan`, and `/bpe:handoff` commands all read it directly via `${CLAUDE_PLUGIN_ROOT}/references/session-management.md`. It also canonically documents spec.md's `## Starting context` and `## Available tooling` sections (see "Starting Context Section (spec.md)" and "Available Tooling Section (spec.md)" below), which `/bpe:brainstorm` and `/bpe:retrofit` write, and the plan-archive layout that `/bpe:plan --archive` writes (see "Plan Archives (accomplishment.md)" below).

## Purpose

Track structured session history and accumulated lessons in the project's `.ai-sessions/` directory. Write session summaries after each work session. Maintain `lessons.md` with reusable insights organized in a hybrid chronological/categorical format.

## Directory Structure

All session artifacts live in `.ai-sessions/` at the project root:

- `.ai-sessions/lessons.md` — accumulated cross-session learnings
- `.ai-sessions/session-{YYYYMMDD}-{HHMM}-{slug}.md` — individual session summaries (e.g. `session-20260101-0900-plugin-setup.md`)
- `.ai-sessions/handoffs/handoff-{YYYYMMDD}-{HHMM}-{slug}.md` — short-lived forward-looking documents written by `/bpe:handoff` (see "Handoff files" below)
- `.ai-sessions/implementation-notes.md` — gitignored mid-step deviations log written by `bpe:step-executor` (see "implementation-notes.md Format" below)
- `.ai-sessions/{slug}/` — one archived plan per directory, written by `/bpe:plan --archive`; holds the retired `plan.md`, `todo.md`, and an `accomplishment.md` (see "Plan Archives (accomplishment.md)" below)

Create the directory with `mkdir -p .ai-sessions` (or `mkdir -p .ai-sessions/handoffs`) if it does not exist.

## Session Summary Files

### Naming Convention

Files follow the pattern: `session-{timestamp}-{slug}.md`

- **Timestamp**: Generate via `date +%Y%m%d-%H%M`. Do not substitute `date` invocations or shell time variables.
- **Slug**: 2-3 word kebab-case description of the session's primary focus. When a session has no clear single focus, use `mixed-work`.

### Session Summary Template

```markdown
# Session Summary: {Descriptive Title}

**Date**: {YYYY-MM-DD}
**Duration**: {approximate duration}
**Conversation Turns**: {count}
**Estimated Cost**: {estimate based on token usage}
**Model**: {model used}

## Goal Context

_Omit this section entirely if the session was not driven by `/goal` / `/bpe:goal`._

- **Condition**: {the exact /goal condition string used, ≤200 chars}
- **Mode**: {step | section | full}
- **Outcome**: {converged | cleared by user | failed: <reason> | spun without converging}
- **Turn count**: {number}
- **Subagent dispatches**: {number of `bpe:step-executor` invocations}
- **Steps completed**: {N of M unchecked items checked off}

## Key Actions

- {Action 1 with brief description of outcome}
- {Action 2 with brief description of outcome}
- ...

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| {User's prompt or command} | {What Claude did} | {Result} |
| ... | ... | ... |

## Efficiency Insights

**What went well:**
- {Efficient approach or good tool usage}

**What could improve:**
- {Missed opportunity or inefficiency}

**Course corrections:**
- {Any mid-session changes in approach}

## Process Improvements

- {Specific, actionable suggestion for future sessions}
- ...

## Observations

- {Interesting patterns, noteworthy moments, or highlights}
- ...

## Suggested Skills for Next Session

- {Skill name (e.g. `python:python`) — one-line note on why it matters for the likely next step}
- ...
```

### Goal Context Populating Rule

Include the **Goal Context** section only when the session was driven by `/goal` (typically set up via `/bpe:goal`). Detect this by checking whether a `/goal …` invocation appears in the conversation, or whether the orchestrator-loop pattern from `/bpe:goal` was used. Populate from what's visible in the parent transcript:

- **Condition** — copy the exact condition string from the `/goal` invocation. If multiple goals ran in one session, list each.
- **Mode** — read from the orchestrator block's "Mode:" line, or infer (`step` if one item, `section` if one labeled group, `full` if the whole plan).
- **Outcome** — `converged` if the evaluator declared success; `cleared by user` if `/goal clear` was run; `failed` (with reason) if the loop stopped on a subagent `Failure:` report; `spun` if it kept going without making progress.
- **Turn count / dispatches / steps** — count from the transcript. Approximate is fine.

Omit any individual field that's genuinely unknowable. Omit the whole section if no goal ran.

### Suggested Skills Populating Rule

The "Suggested Skills for Next Session" section gives the next `/bpe:execute-plan` run an explicit hint about which skills to invoke at its hardened skill-loading step. Populate it based on what the *next* step needs — not a log of what the current session loaded. Include a skill if the next step will need it (whether or not the current session used it); omit a skill the current session used incidentally if the next step will not need it. For example, if the current session edited Python tooling but the next step is documentation cleanup, omit `python:python` and include only the docs-relevant skills. Omit the section entirely only if the next session genuinely needs no skills.

## Lessons Learned (lessons.md)

### Hybrid Format

The `lessons.md` file uses a hybrid structure combining chronological and categorical organization:

- **Recent section**: The 10 most recent lessons, newest first. Provides quick access to fresh insights.
- **Category sections**: Lessons organized by topic (Python, Testing, Git, Tooling, Architecture, Workflow, Debugging, etc.). Provides lookup by domain.

Each lesson entry includes a date in parentheses: `- Lesson text (YYYY-MM-DD)`

### Lessons.md Template

Use this skeleton when initializing a new `lessons.md`. Category sections are created on demand — the template intentionally does not prescribe a fixed set. Categories are flat top-level (`##`) headings; do not nest them under a `## Categories` parent.

```markdown
# Lessons Learned

## Recent
<!-- 10 most recent lessons, newest first -->
- {Most recent lesson} ({YYYY-MM-DD})

<!--
Category sections live below. Create each one only when at least one
lesson belongs to it. Use the most specific applicable category.
Common starting points: Python, Testing, Git, Tooling, Architecture,
Workflow, Debugging. Other valid examples: Infrastructure,
Documentation, Performance, Security, DevOps, Plugin Development.
Omit categories with zero entries.
-->

## {Category}
- {Lesson} ({YYYY-MM-DD})
```

### Capturing Lessons

When identifying lessons from a session:

1. Focus on **specific, actionable insights** — not generic advice.
2. Prefer concrete over abstract: "Use `just check` instead of running linters individually" beats "Run linters efficiently".
3. **Deduplicate** against existing entries — update wording and date if substantially similar.
4. Keep the Recent section to 10 entries maximum — move older entries to categories only.
5. Create new category headings as needed — use judgment for the most specific fit.

### Category Guidelines

- Create categories as needed — the list above is a starting point, not exhaustive.
- A lesson belongs in the most specific applicable category.
- If a lesson fits multiple categories, pick one — avoid duplicating across categories.
- Categories with zero entries can be omitted from the file.
- Common additional categories: Infrastructure, Documentation, Performance, Security, DevOps, Plugin Development.

### Lesson Quality Examples

**Good lessons (specific, actionable):**
- Use `uv run --script` for standalone Python scripts — no virtualenv needed (2026-02-24)
- The ruff formatter handles import sorting — no need to configure isort separately (2026-02-25)
- Always read the most recent `.ai-sessions/` summary before starting execute-plan (2026-02-25)
- Ansible `--check` flag prevents accidental changes during testing (2026-02-24)

**Bad lessons (too generic, not actionable):**
- Python is good for scripting
- Always write tests
- Use version control
- Read documentation

## Integration with BPE Workflow

### `/bpe:execute-plan` Step 2 — Find the Most Recent Summary

Before beginning work in `/bpe:execute-plan`, check whether `.ai-sessions/` exists. If it does, identify the most recent session summary by sorting filenames lexicographically — the embedded `{YYYYMMDD}-{HHMM}` timestamp makes lexicographic order equal chronological order. Do not rely on filesystem mtime, which can be misleading after edits or git operations. Read that summary in full before beginning implementation.

### `/bpe:execute-plan` Step 3 — Honor "Suggested Skills for Next Session"

If the latest summary contains a "Suggested Skills for Next Session" section, treat its entries as inputs to the hardened skill-loading step. Invoke those skills in addition to any the agent identifies from the current tech stack — the previous session's recommendation is a hint, not a cap.

### Relationship to `/bpe:handoff`

For mid-session, forward-looking baton passes (handing the conversation to a fresh agent without finishing the current work), use `/bpe:handoff` instead of writing a session summary. Handoffs live in `.ai-sessions/handoffs/` so the next agent can find them without being told a path, but they are **not** durable artifacts. They are intended to be deleted once consumed.

## Handoff files

### Naming and location

Handoff files follow the pattern: `.ai-sessions/handoffs/handoff-{timestamp}-{slug}.md`

- **Timestamp**: same `date +%Y%m%d-%H%M` rule as session summaries.
- **Slug**: 2-3 word kebab-case description of the focus the next session will pick up. Use `general` if there is no clear single focus.

### Lifecycle

Handoffs follow a three-step lifecycle, each step driven by an explicit subcommand:

1. `/bpe:handoff create [focus]` — write the document at the end of a session.
2. `/bpe:handoff continue` — at the start of the next session, read the document and prime the conversation. This is pure-read; it does not delete the file.
3. `/bpe:handoff close` — delete the document once the handoff has been picked up and is no longer useful. This is the primary cleanup path.

`/bpe:session-summary` keeps a safety-net scan: at the end of a session, it checks `.ai-sessions/handoffs/` for any leftover `.md` files and prompts the user about cleanup, so stale handoffs do not slip into a commit if `close` was forgotten.

### Cleanup paths

- **Primary**: `/bpe:handoff close` — explicit deletion after the handoff has been consumed.
- **Safety net**: `/bpe:session-summary` — end-of-session scan that prompts about any remaining handoffs.

In both cases: default to keep on uncertainty; delete only on explicit confirmation.

### Gitignore guidance

`.ai-sessions/handoffs/` may or may not be tracked depending on project preference. If handoffs should never be committed, add `.ai-sessions/handoffs/` to `.gitignore`. Otherwise, lean on the cleanup prompts to remove individual handoffs once consumed.

### Not auto-read

Unlike session summaries, handoffs are **not** auto-read by `/bpe:execute-plan` at startup. The next agent should run `/bpe:handoff continue` to read an existing handoff, then `/bpe:handoff close` once the work has been picked up. If `/bpe:execute-plan` notices a leftover handoff file, it points the user at `/bpe:handoff continue` rather than consuming the file itself.

## implementation-notes.md Format

`.ai-sessions/implementation-notes.md` is the deviations log: a short-lived scratch file where `bpe:step-executor` Mode: implement records mid-step departures from plan.md, so that context survives to the finalize dispatch (which runs with a fresh context).

- **Purpose**: mid-step deviation tracking. When implement work departs from plan.md's prescription (edge case, blocked path, better approach found mid-work), the deviation and its consequence are recorded when they happen instead of dying with the dispatch.
- **Format**: one `## Step N` heading per affected step, followed by a bullet list: `- Plan said: <what>`, `- Deviated: <what actually happened>`, `- Impact: <consequence>`. Steps with no deviation get no section.
- **Lifecycle**: created by Mode: implement (its deviations-log step) when the first deviation occurs. Absorbed during Mode: finalize: the session-summary procedure extracts the step's section into a `## Deviations from Plan` section of the session summary, then removes the absorbed section from implementation-notes.md, deleting the file when no sections remain. Gitignored; never staged.

## Plan Archives (accomplishment.md)

`/bpe:plan --archive` retires a finished or superseded plan into `.ai-sessions/<slug>/` before generating a fresh one.
This section is the canonical definition of the archive layout and the accomplishment.md format; the plan skill's Archive routine conforms to it.

### Archive Layout

```
.ai-sessions/
  <slug>/                 e.g. init, v1, add-user-auth
    plan.md
    todo.md
    accomplishment.md
```

- **Slug**: 2-3 word kebab-case, proposed from plan.md's stated goals and the checked todo items (`init` or `v1` for a project's first archive). The user confirms or edits the slug before any file moves.
- **plan.md / todo.md**: the retired files, moved verbatim from the repo root. Do not edit them during the move.
- **accomplishment.md**: written fresh at archive time per the template below. It is the durable record of what the plan achieved; the moved files are the raw material.

### accomplishment.md Template

```markdown
# Accomplishment: {Descriptive Title}

**Archived**: {YYYY-MM-DD}
**Convergence**: {converged | partial: N of M items checked | failed: <one-line reason>}

## Spec Slice

{The spec.md slice this plan implemented: copied when short, summarized when long}

## What Got Done

- {Checked todo item or commit subject}
- ...

## Deferred or Dropped

- {Unchecked item or mid-flight cut, with a one-line reason}
- ...

## Notable Decisions

- {Mid-execution decision worth remembering, e.g. from session summaries' Deviations from Plan sections}
- ...

## Files Touched

- {path}
- ...

## Lessons Cross-Reference

- {Pointer to lessons.md entries captured during this plan, quoted or dated, or "none captured"}
```

Populate "What Got Done" from todo.md's checked top-level items and the plan's commit subjects (`git log --oneline` over the plan's branch).
Use "Deferred or Dropped" and "Notable Decisions" sparingly; an empty section may be omitted, matching the lessons.md rule for empty categories.

## Starting Context Section (spec.md)

The blindspot pass in `/bpe:brainstorm` (Step 0) and `/bpe:retrofit` (procedure step 3) records the user's starting-context answer in spec.md.
This section is the canonical definition of that record; both skills conform to it.

- **Format**: an H2 heading, `## Starting context`, followed by the user's context answer verbatim. Do not paraphrase, summarize, or clean up the user's words.
- **Placement**: between `# <title>` and `## Project overview` in spec.md.
- **Purpose**: calibrates the plan writer and the validator. `/bpe:plan` reads it to pitch step granularity to what the user already knows; the `bpe:validator` agent reads it to weight findings against the user's stated familiarity.

## Available Tooling Section (spec.md)

The tool discovery pass in `/bpe:brainstorm` (Tool discovery section) and `/bpe:retrofit` (procedure step 4) records the user's confirmed validator tooling in spec.md.
This section is the canonical definition of that record; both skills conform to it.

- **Format**: an H2 heading, `## Available tooling`, followed by one intro sentence, then labeled fields in this order: `**MCPs:**` (bullet list), `**Skills:**` (bullet list), `**Verification command:**` (optional single line, see below), `**Notes:**` (free-form validator guidance). Empty MCP and skill lists are valid; the section still exists so plan.md has a known structure to read.
- **Placement**: after `## Project overview`, before the detailed requirements in spec.md.
- **Purpose**: `/bpe:plan` propagates the MCP and skill lists to per-section `**Tools:**` declarations in plan.md (legacy plans: `**Validator consults:**`); `/bpe:goal` passes them to the `bpe:validator` agent when dispatching it.
- **Verification command field**: a single line, `**Verification command:** <command>`, e.g. `**Verification command:** vale docs/`. Written only when the project's tech stack matches none of the test-runner manifests `/bpe:goal` autodetects (pyproject.toml, package.json, Cargo.toml, go.mod). `/bpe:goal`'s pre-flight resolves its verification command through a cascade: manifest autodetect, then this field, then asking the user. Exit 0 of the resolved command is the goal condition's success signal, so the command must succeed only when the work is verifiably done.
