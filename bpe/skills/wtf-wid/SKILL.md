---
name: wtf-wid
description: WTF was I doing? A tight, fits-on-screen recap of the current session so you can re-enter in under 10 seconds
model: sonnet
disable-model-invocation: true
---

# WTF Was I Doing?

Print a tight context-recovery block so the user can re-enter the session without scrolling. The user has stepped away (overnight, days) and needs the *current* state surfaced fast. No preamble. No closing offer. Just the block.

## Hard Output Constraints

- **≤ 30 lines total**, including blanks. If over budget, drop optional sections (`Why`, `Open`, `Refs`) first, then trim the `Status` file list.
- **≤ 144 chars per line.** Truncate paths, commit subjects, and quoted text with `…`.
- **No prose framing** in user-facing text: no "Here's where you were…", no "Hope this helps…", no follow-up questions, no "want me to continue?". Print the block, stop.

## Source Priority

The user explicitly cares about the **current** session, not history. Read sources in this order and privilege the earlier ones:

1. **Current conversation transcript**: your own memory of this session. Primary source. What did the user ask for? What were you doing in the last few turns? What was about to happen next? If the conversation has substantive content, it owns `Problem`, `Next`, `Why`, and `Open`.
2. **Git state**: run in parallel via Bash:
   - `git rev-parse --abbrev-ref HEAD` (branch)
   - `git status --short` (modified/staged/untracked counts + paths)
   - `git log -1 --format="%h %s"` (last commit, subject only)
   - `basename "$PWD"` (repo dir name)
3. **bpe artifacts**: supporting only when they reflect *current* intent, not historical work:
   - `.ai-sessions/handoffs/*.md` (most recent): if present, its focus is a strong signal for `Next`
   - `todo.md`: first unchecked `- [ ]` item, only if it matches what's actually in flight
   - `plan.md` / `spec.md`: pull `Why` if the conversation doesn't already supply it
4. **MEMORY.md**: only if it adds load-bearing project context the conversation doesn't cover.

**Do not** synthesize a "current session" from `.ai-sessions/session-*.md`. Those are *past* sessions. If you must reference one (cold-start fallback only), label it `prev:` so the user knows it's historical.

## Cold-Start Fallback

If the current conversation has no substantive content yet (this command is the first or second turn of a fresh session), fall back in this order for `Problem` / `Next`:

1. Most recent handoff in `.ai-sessions/handoffs/`
2. Most recent `.ai-sessions/session-*.md` (label `prev:`)
3. Branch name + last commit subject as a weak signal

When falling back, make the first line of the block: `Source:  no live context (recovered from <handoff|prev session|git>)`.

## Output Template

Render this shape. Omit any optional row when empty; do not print blank values. Align the colons for readability.

```
Problem: <one-line statement of the active problem, ≤120 chars>
Repo:    <repo-dir-name> (<branch>)
Status:  <N modified, N staged, N untracked>  ·  <up to 3 most-relevant paths, truncated>
Last:    <short-sha> <commit subject ≤80 chars>
Next:    <the immediate next action, ≤120 chars>
Why:     <optional: motivation behind the work, ≤120 chars>
Open:    <optional: unresolved decision or blocker, ≤120 chars>
Refs:    <optional: paths to handoff/plan/todo if user should open them>
```

Field rules:

- **Problem**: concrete, not abstract. "Splitting /bpe:review into 4-option chunks" not "working on the plugin".
- **Status**: if clean, just `clean`. If dirty, counts + up to 3 paths that best characterize the change. Skip the file list if it would push the line past 144 chars.
- **Next**: what *you* (the assistant) were about to do, or what the user was about to decide. Falls back to first unchecked `todo.md` item.
- **Why**: include only when motivation is non-obvious from `Problem` alone. Often skippable.
- **Open**: include only for genuine unresolved decisions/blockers the user must address.
- **Refs**: include only when a file is load-bearing for re-entry (active handoff, current plan step). Never list everything that exists.

## Execution

1. Fire the four git commands in parallel (one message, multiple Bash calls).
2. Quick `ls` on `.ai-sessions/handoffs/` and a `Read` of `todo.md` only if they exist.
3. Synthesize the block from the current conversation + git output. Resist the urge to elaborate.
4. Print the block. Stop.
