---
name: handoff
description: Create, continue, or close handoff documents for fresh-agent baton passes
argument-hint: create [focus] | continue | close
model: sonnet
disable-model-invocation: true
---

# Handoff Command

Manage forward-looking handoff documents that let a fresh agent pick up where the current conversation left off. Handoffs are short-lived and live under `.ai-sessions/handoffs/` — they are not session summaries. For durable, backwards-looking session records, use `/bpe:session-summary` instead.

This command has three subcommands:

- `create [focus]` — write a new handoff document. The optional focus describes what the next session will work on; it tailors the handoff toward that thread.
- `continue` — read an existing handoff and prime the current conversation with its contents. Does not delete the file.
- `close` — delete a consumed handoff file. Run this once the work described in the handoff has been picked up and the file is no longer useful.

## Argument Routing

Parse `$ARGUMENTS`:

- If the first token is `create`, run **Create Mode**. Treat the remainder of the argument string as the optional focus.
- If the first token is `continue`, run **Continue Mode**. Ignore any trailing tokens.
- If the first token is `close`, run **Close Mode**. Ignore any trailing tokens.
- If `$ARGUMENTS` is empty, default to **Create Mode** with no focus.
- Otherwise, treat the entire argument string as a focus description and run **Create Mode**. This preserves back-compatibility with the original `/bpe:handoff <focus>` form.

State the routed mode in user-facing text before proceeding (e.g. "Running handoff in create mode with focus: deck polish.").

---

# Create Mode

Write a handoff document so a fresh agent can continue the current work without starting from scratch. The handoff is forward-looking and short-lived.

## Step 1: Generate the Path

Handoffs live alongside session summaries under `.ai-sessions/`, in a `handoffs/` subdirectory. This keeps them in the project tree (so the next agent can find them without being told a path) while keeping them separable from durable summaries.

```bash
mkdir -p .ai-sessions/handoffs
date +%Y%m%d-%H%M
```

Then build the path: `.ai-sessions/handoffs/handoff-{timestamp}-{slug}.md`.

- **Timestamp**: the exact output of `date +%Y%m%d-%H%M`. Do not substitute or paraphrase.
- **Slug**: 2-3 word kebab-case description of the focus the next session will pick up. Use `general` if there is no clear single focus.

Do not Read the path first; the file does not exist yet and Read errors on missing files. Write creates it.

## Step 2: Tailor to the Next Session's Focus

If a focus argument was passed, treat it as a description of what the next session will work on. Tailor the handoff toward that focus — emphasize the threads of the current conversation that matter for the stated next step, and elide the rest.

If no focus was passed, write a general-purpose handoff covering the live state of the conversation.

## Step 3: Write the Handoff

Include these sections, in this order:

### Current State
- What is done, what is in progress, and what is queued next.
- Branch name, last commit SHA, and whether work is pushed.
- Files in flight — paths to anything created or modified this session, especially uncommitted work.

### Open Decisions and Blockers
- Anything awaiting input from the user or another agent.
- Trade-offs the current session deferred — what was chosen, what was rejected, and why.

### Suggested Goal (optional)

If the next session is a strong candidate for autonomous-mode execution (clear unchecked todo.md items, tests in place, no open design questions), include a line like:

```
Suggested Goal: /bpe:goal section <name>
```

or the full pre-built `/goal …` condition if you already know it. Omit this section if the next step needs human judgment, design decisions, or anything a `bpe:step-executor` subagent could not handle on its own. When in doubt, omit — false-positive Suggested Goals waste a run.

### Suggested Skills for the Next Session
- List the specific skills the next agent should invoke before starting work, selected by what the next step needs — not a log of what this session loaded. Examples: `python:python`, `temporal:temporal-developer`. Include a skill if the continuation will need it (whether or not the current session used it); omit a skill that was useful this session but is irrelevant to the next step. This matches the populating rule in `${CLAUDE_PLUGIN_ROOT}/references/session-management.md`.
- Note project-stack-specific skills that the next step will need, with a one-line reason each.

### Pointers, Not Content
- Reference PRDs, plans, ADRs by path.
- Reference issues and PRs by URL or `gh` invocation.
- Reference commits and diffs by SHA, branch range, or `git log`/`git diff` invocation.
- Reference existing session summaries in `.ai-sessions/` by filename.
- Reference `.ai-sessions/lessons.md` when a relevant cross-session lesson applies — by filename plus the category heading or quoted lesson, not by restating the lesson body.

### Anti-Duplication Rule

Do not duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs, prior session summaries). Reference them by path or URL instead. The handoff is a pointer index, not a content store. If a fact lives somewhere durable, link to it; only restate things the next session cannot trivially recover.

## Step 4: Confirm

After writing the handoff, display:

- The full path to the handoff file (relative to the repo root).
- A one-paragraph summary of what the document covers and the assumed next-session focus.
- A reminder: the next session should run `/bpe:handoff continue` to consume the document, then `/bpe:handoff close` once the work is picked up. If `.ai-sessions/handoffs/` should never be committed, add it to `.gitignore` once.

---

# Continue Mode

Read an existing handoff and prime the current conversation with its contents. This mode is pure-read — it does not delete the file. Use `/bpe:handoff close` once the handoff has been fully consumed and is no longer needed.

## Step 1: Locate the Handoff

List the contents of `.ai-sessions/handoffs/` (use the Glob or Bash tool):

```bash
ls -1 .ai-sessions/handoffs/*.md 2>/dev/null
```

- If the directory does not exist or contains no `.md` files, tell the user there is no handoff to continue and stop. Suggest they may have meant `/bpe:handoff create [focus]`.
- If exactly one handoff is present, select it.
- If multiple handoffs are present, sort filenames lexicographically (timestamp-prefixed names give chronological order). Show the list to the user and ask which to consume. Default the most recent if the user does not specify.

## Step 2: Read and Summarize

Read the chosen handoff in full. Then, in user-facing text, summarize:

- **What the handoff covers**: the current-state snapshot, files in flight, and open decisions/blockers.
- **Suggested next step**: the focus the handoff was written against and what the writer expected the next session to do first.
- **Suggested Goal (if present)**: surface the `Suggested Goal:` line from the handoff verbatim so the user can choose to run `/bpe:goal` directly.
- **Skills to invoke**: enumerate any skills listed in the handoff's "Suggested Skills for the Next Session" section.

## Step 3: Invoke Suggested Skills

For each skill listed in the handoff's "Suggested Skills for the Next Session" section, invoke it via the `Skill` tool before proceeding. Bias toward invoking — double-loading is harmless, skipping is not. Auto-loaded CLAUDE.md rules are not equivalent to invoked skills.

State the invocations in user-facing text: "Invoked: <skill names>" or "No skills listed in the handoff."

## Step 4: Confirm Direction

Ask the user: "Ready to proceed on the next step described in the handoff, or do you want to redirect?" Wait for the user to either confirm or course-correct before doing further work.

Remind the user: once the handoff has been fully picked up, run `/bpe:handoff close` to delete the file. The handoff is not auto-removed.

---

# Close Mode

Delete a handoff file. Run this once the work described in the handoff has been picked up and the file is no longer useful.

## Step 1: Locate the Handoff

Use the same selection logic as Continue Mode:

```bash
ls -1 .ai-sessions/handoffs/*.md 2>/dev/null
```

- If the directory does not exist or contains no `.md` files, tell the user there is nothing to close and stop.
- If exactly one handoff is present, select it.
- If multiple handoffs are present, sort filenames lexicographically and show the list. Ask the user which one to close. Default the most recent if the user does not specify.

## Step 2: Confirm

Show the full path of the file to be deleted and a one-line summary of its contents (slug + first line, or the file's first heading). Ask the user to confirm deletion. Default to keep on uncertainty; delete only on explicit confirmation.

## Step 3: Delete

On explicit confirmation, remove the file:

```bash
rm <path-to-handoff>
```

Report the deletion in user-facing text. If multiple handoffs were present and only one was closed, leave the others in place — they are out of scope for this invocation.
