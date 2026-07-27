---
name: execute-plan
description: Implement the next unchecked step from plan.md by executing its sub-steps as written (RED-GREEN-REFACTOR for Feature steps; Scope/Tooling/Do/Verify/Document for Task steps)
model: sonnet
disable-model-invocation: true
---

# Execute Plan Command

1. Read @plan.md and @todo.md
   - These files complement each other. @todo.md should track the current state of the implementation of @plan.md
2. Read `${CLAUDE_PLUGIN_ROOT}/references/session-management.md`, the canonical reference for the session-tracking rules used in this step and in step 3 below. Then check for `.ai-sessions/`:
   1. If the directory doesn't exist, do nothing.
   2. If the directory exists, identify the most recent session summary per the find-most-recent rule in the reference, and read it in full. The summary contains what work was completed and lessons learned in the previous session.
   3. If `.ai-sessions/handoffs/` contains any `.md` files, do not consume them here. Mention to the user that `/bpe:handoff continue` is the entry point for picking up a leftover handoff; it reads the file, primes the session, and handles cleanup.
3. **Invoke relevant skills via the Skill tool**: For the project's tech stack (per CLAUDE.md and @plan.md), invoke each matching skill via the `Skill` tool BEFORE proceeding to step 4. Examples:
   - Python project → invoke `python:python` (or `python` if unscoped)
   - Temporal project → invoke `temporal:temporal-developer`
   - Available skills are listed in the available-skills system reminder.
   - If the prior session summary read in step 2 contains a "Suggested Skills for Next Session" section, treat its entries as inputs per the rule in the session-management reference loaded in step 2; invoke them in addition to stack-derived skills.

   Bias toward invoking. If a skill plausibly matches the stack, invoke it; double-loading is harmless, skipping is not. Auto-loaded CLAUDE.md rules (e.g. python.md arriving as a system-reminder) are NOT the same as invoking the skill; the skill carries additional toolchain, workflow, and reference guidance that only loads on invocation.

   Before moving to step 4, make an explicit decision in user-facing text: either "Invoked: <skill names>" or "No matching skill for this stack." Only ask the user if you are genuinely unsure which skill applies.
4. Open @todo.md and select the first unchecked item to work on.
5. Open @plan.md and locate the specific step being implemented
   - Find the detailed numbered prompts for this step (e.g., "1. RED: Write tests...", "2. GREEN: Implement..." for a Feature step; "1. Scope: ...", "2. Tooling: ...", "3. Do: ..." for a Task step)
   - Follow these prompts EXACTLY in the specified order
   - Do NOT deviate from the file paths, test scenarios, or implementation approach specified
6. If you have any questions about the task at hand, ask the user.
7. Implement the plan for this item as specified in @plan.md:
   - Follow the numbered sub-steps as written, with the specific file paths and test scenarios they name (RED/GREEN/REFACTOR for Feature steps; Scope/Tooling/Do/Verify/Document for Task steps)
   - Focus tests on YOUR application logic, not framework or library behavior
   - Verify tests and linting pass and the program builds/runs

   Note: plan.md may mix Feature and Task steps within one plan. Honor whichever sub-step shape the current step declares; the numbered sub-steps ARE the procedure, regardless of template.
8. **Update documentation as specified** in the @plan.md prompts for this step
9. Update @todo.md and mark off the item that was completed
10. Ask the user if there is anything else they want you to do or review for this session.
