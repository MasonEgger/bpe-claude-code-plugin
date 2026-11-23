---
name: gh-issue
description: Fetch a GitHub issue by number and route it to brainstorm or plan based on whether it follows the issue format
allowed-tools: Bash(gh:*), Read, Write, Glob, Grep
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
   - **Brainstorm route**: Begin the interactive Q&A process to develop a spec. Use the issue details as the starting idea. Pre-fill any answers you can derive from the issue itself, but still ask the user to confirm and fill gaps. Save the result as spec.md.
   - **Plan route**: Use the issue details as the spec input. Generate the implementation plan (plan.md + todo.md) following the standard plan format, using TDD Feature steps or non-TDD Task steps as the work warrants.
