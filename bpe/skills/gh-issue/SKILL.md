---
name: gh-issue
description: Fetch a GitHub issue and route to brainstorm or plan based on detail level
allowed-tools: Bash(gh:*), Read, Write, Glob, Grep
model: sonnet
disable-model-invocation: true
---

# GitHub Issue Command

1. Retrieve issue $ARGUMENTS from GitHub using `gh issue view`.
2. Review the issue title, body, labels, and any linked discussion.
3. Review the codebase to understand the area of code the issue touches.
4. Validate the issue:
   - Run any relevant tests to confirm the problem exists.
   - If no tests exist for this area, write tests that demonstrate the issue.
   - If you cannot reproduce the issue, inform the user with a detailed explanation and stop.

5. Assess the issue's **detail level** to decide the next step:

   **Route to brainstorm** (interactive spec development) when the issue is:
   - A feature request with only a high-level description
   - Missing acceptance criteria or specific requirements
   - Ambiguous about scope, approach, or expected behavior
   - Broad enough that multiple implementation strategies exist

   **Route to plan** (implementation roadmap) when the issue is:
   - A well-defined bug with clear reproduction steps
   - A feature request with specific acceptance criteria
   - Scoped narrowly enough that the implementation path is clear
   - Already has a linked spec or detailed technical description

6. Tell the user which route you chose and why, then execute:
   - **Brainstorm route**: Begin the interactive Q&A process to develop a spec. Use the issue details as the starting idea. Pre-fill any answers you can derive from the issue itself, but still ask the user to confirm and fill gaps. Save the result as spec.md.
   - **Plan route**: Use the issue details as the spec input. Generate the implementation plan (plan.md + todo.md) following the standard plan format, using TDD Feature steps or non-TDD Task steps as the work warrants.
