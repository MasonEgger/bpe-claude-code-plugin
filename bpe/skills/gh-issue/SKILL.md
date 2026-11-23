---
name: gh-issue
description: Fetch a GitHub issue by number and route it to brainstorm or plan based on whether it follows the issue format
allowed-tools: Bash(gh:*), Bash(python3:*), Bash(mktemp:*), Bash(diff:*), Bash(mv:*), Read, Write, Glob, Grep
model: sonnet
disable-model-invocation: true
---

# GitHub Issue Command

Fetches an existing GitHub issue by number, whoever wrote it, and routes it to brainstorm or plan.
`/bpe:new-issue` is the writing side; it drafts issues in the format this command checks.

1. Retrieve issue $ARGUMENTS from GitHub using `gh issue view`.
2. Review the issue title, body, labels, and any linked discussion.
3. Review the codebase to understand the area of code the issue touches.
4. Validate the issue:
   - Run any relevant tests to confirm the problem exists.
   - If no tests exist for this area, write tests that demonstrate the issue.
   - If you cannot reproduce the issue, inform the user with a detailed explanation and stop.

5. Check the issue against `${CLAUDE_PLUGIN_ROOT}/references/issue-format.md`.
   An issue conforms when it has What Is Wanted, What We Already Know, and Acceptance Criteria, in that order, and any optional sections it carries sit in their defined positions.

   **Route to plan** when the issue conforms and its Acceptance Criteria are specific enough to check.

   **Route to brainstorm** in every other case.
   Name the missing sections, or the criteria that cannot be checked, to the user first.
   Never refuse an issue for not conforming.

6. Tell the user which route you chose and why, then execute:
   - **Brainstorm route**: Begin the interactive Q&A process to develop a spec. Use the issue details as the starting idea. Pre-fill any answers you can derive from the issue itself, but still ask the user to confirm and fill gaps.
     When `spec.md` exists, enter merge mode as `/bpe:brainstorm` defines it: scope the Q&A to the issue's change.
     On a spec whose Goals has a `### Feature Status` table, that edits or adds the affected feature entries and marks the new behavior with `Planned (ITEM):` sentences under an `**Upcoming:**` item this run adds; on a spec without the table, merge mode keeps its earlier behavior, as brainstorm defines it.
     When `spec.md` does not exist, save the result as a new spec.md.
   - **Plan route**: Use the issue details as the spec input, then plan from it.
     When `spec.md` exists and its `## Goals` has a `### Feature Status` table, first record the issue's behavior change in the spec, so the archive's fold-in has something to fold.
     Write each changed behavior as a `Planned (ITEM):` sentence in the affected feature entry (add an entry and a table row for a new feature), and add the named item to `**Upcoming:**` in `## Roadmap / phase log`.
     Name the item for the change, never for the issue number alone.
     Write the merged spec to a scratch file, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/check-artifacts.py <scratch>/spec.md`, show `diff -u spec.md <scratch>/spec.md`, and move it over spec.md only after the user confirms.
     Then plan that item as `/bpe:plan` does, "What to Plan", generating plan.md and todo.md in the standard plan format, using TDD Feature steps or non-TDD Task steps as the work warrants.
     When `spec.md` does not exist, or its Goals has no `### Feature Status` table, skip the spec edit and plan from the issue details as before.
