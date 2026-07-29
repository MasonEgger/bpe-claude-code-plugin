---
name: session-summary
description: Generate session recap in .ai-sessions/ and capture lessons learned
model: sonnet
---

# Session Summary Command

Create a complete session summary and capture lessons learned. This command performs two actions:
1. Generates a session summary file in `.ai-sessions/`
2. Appends lessons learned to `.ai-sessions/lessons.md`

## Step 1: Load the Format Reference and Setup

Read the canonical format reference at `${CLAUDE_PLUGIN_ROOT}/references/session-management.md`. Treat that file as the single source of truth for templates, naming conventions, and lesson capture guidance; do not restate or reinterpret its rules in this command.

If `.ai-sessions/` does not exist, create it:
```bash
mkdir -p .ai-sessions
```

Generate the timestamp using this exact command:
```bash
date +%Y%m%d-%H%M
```

## Step 2: Generate Session Summary

Create `.ai-sessions/session-{timestamp}-{slug}.md` per the naming convention and section template in the format reference ("Session Summary Template" section).

Populate every required section. Pull content from this conversation:
- Header metadata (date, duration, conversation turns, estimated cost, model)
- Goal Context (only if a `/goal` ran in this session, per "Goal Context Populating Rule" in the reference; omit the section entirely otherwise)
- Key actions taken
- Prompt inventory (table of user prompts → actions → outcomes)
- Efficiency insights, process improvements, observations
- Suggested skills for next session (which skills the next `/bpe:execute-plan` should invoke at its hardened skill-loading step; see "Suggested Skills Populating Rule" in the reference)

If `.ai-sessions/implementation-notes.md` exists and contains a `## Step <N>` section for the step this summary covers, extract its bullets and add a `## Deviations from Plan` section to the session summary with them.
Then remove that `## Step N` section from `implementation-notes.md`: keep the file if other sections remain, else delete the file.
The entry format (`- Plan said: <what>` / `- Deviated: <what actually happened>` / `- Impact: <consequence>` under a `## Step N` heading) is defined in the format reference ("implementation-notes.md Format" section).

If the session has no clear single focus, use `mixed-work` as the slug.

## Step 3: Capture Lessons Learned

Update `.ai-sessions/lessons.md` per the rules in the format reference ("Capturing Lessons" and "Lessons.md Template" sections). In short:

- If `lessons.md` does not exist, initialize it from the template in the reference.
- Identify specific, actionable lessons from this session, not generic advice.
- Prepend new lessons to the `## Recent` section with a `(YYYY-MM-DD)` date suffix; cap Recent at 10 entries (move overflow into category-only).
- Place each lesson under the most specific applicable category heading per the category guidelines in the reference. Create new category headings on demand.
- Deduplicate against existing entries; update wording and date in place when substantially similar.

## Step 4: Offer to Clean Up Stale Handoffs

Check `.ai-sessions/handoffs/` for any `.md` files (per the "Handoff files" section of the format reference). For each one present, ask the user whether it can be removed now that this session is wrapping up. Default to keep on uncertainty; delete only on explicit confirmation. This prevents stale handoffs from being accidentally committed alongside the session summary.

## Step 5: Archive Prompt (End of /goal Only)

Skip this step entirely when this procedure runs inline inside a `bpe:step-executor` dispatch (mode=finalize): there is no user to ask, and todo.md still has unchecked items mid-run. The prompt belongs to the interactive parent session after the loop ends.

Otherwise, detect whether this session was driven by `/goal` per the "Goal Context Populating Rule" in the format reference. Offer the archive prompt only when all of these hold:
- The session was `/goal`-driven and the loop has ended (goal condition met, or the user stopped iterating; do not prompt mid-loop while top-level todo items remain unchecked and the loop is still running).
- `todo.md` exists at the repo root.
- `todo.md` has a non-zero count of checked top-level items.

If all hold, ask: "Archive plan.md and todo.md to `.ai-sessions/<slug>/`?"
- On yes: follow the Archive routine in `${CLAUDE_PLUGIN_ROOT}/skills/plan/SKILL.md` inline, including its slug confirmation, but stop after writing `accomplishment.md`. Do not run the routine's final step (generating a fresh plan); that belongs to `/bpe:plan`.
- On no: leave `plan.md` and `todo.md` at the repo root, and note that the next `/bpe:plan` invocation will refuse until they are archived (or discarded with `--regen`).

If any condition fails, skip silently.

## Step 6: Confirm

After completing both files, display:
- The path to the session summary file
- How many lessons were captured
- A brief preview of the lessons added
- A note about any handoff files that were deleted (or kept) in step 4
- The archive prompt outcome from step 5, when it fired (archived to `.ai-sessions/<slug>/`, or declined)

Ask the user if they want to adjust anything before the session ends.
