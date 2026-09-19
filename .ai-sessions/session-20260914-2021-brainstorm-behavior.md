# Session Summary: Brainstorm Behavior and Vendoring Mechanics (v0.7 Step 3)

**Date**: 2026-09-14
**Duration**: ~1 hour
**Conversation Turns**: ~6 user prompts
**Estimated Cost**: moderate (one subagent doc lookup, two doc fetches, 14 edits across three files, checks, commit ritual)
**Model**: Fable 5.1

## Key Actions

- Pushed the step 2 commit, then opened the brainstorm step with two AskUserQuestion forks; the user asked what an invariant even is, so the questions were restated in plain terms with concrete examples before anything was decided.
- The user raised the real cost of vendoring: on repos he works alone, a vendored copy of his own skill rules would load beside the live skill, doubling tokens and inviting drift. Reframed vendoring as purely a sharing mechanism and gated it on the repo being shared for every bucket.
- The user then asked for something better: keep the vendored rules for contributors but not load them himself. Dispatched the `claude-code-guide` agent rather than guessing; it found `claudeMdExcludes`, and two WebFetch reads of code.claude.com/docs/en/memory confirmed the details: glob patterns against absolute paths, covers `.claude/rules/` files, settable in the gitignored `.claude/settings.local.json`, arrays merge across layers.
- Locked four decisions (12 through 14 plus the exclude placement): shared-repo gate for all vendoring; `.claude/rules/vendored/<domain>.md` as verbatim copies of a source "Hard rules" block; per-repo author exclusion written by brainstorm (chosen over user-level so other people's vendored rules still load for him); checkable invariants as key-prefixed bullets (`deps:`, `paths:`) in the same list as prose.
- Wrote the brainstorm behavior: mode detection with merge mode (scratch file, `diff -u`, confirm, save in place, no overwrite flag), a constraints pass (negation plus stated non-negotiables), an adjacency pass (three to five neighbors per goal, default Deferred), one four-part confirm replacing the tools-only question (the verification-command question folds in too), and the five-step Vendoring procedure including the exclude and its gitignore check.
- Defined the contract in session-management.md: the two-form Invariants format with the `deps:`/`paths:` vocabulary and pointer bullets, and a new "Vendored Rules (.claude/rules/vendored/)" section.
- Checks: brainstorm frontmatter parses after the description change; no dashes, smart quotes, or banned words; one parallelism tell flagged in the plan and reworded; the renumbering left one stale "step 5" cross-reference, fixed to step 6; session-management's pointer to the renamed brainstorm section tightened.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Push it, then continue | Pushed; asked two forks (structured form, ruleset home) | User asked to clarify |
| What is an invariant? What are you asking? | Defined the term with examples; restated both questions plainly | Understood |
| Would vendoring duplicate my skills locally? | Confirmed the cost; gated vendoring on shared repos | Agreed in principle |
| How do you detect shared? Can I keep vendored rules but not load them? | `gh repo view --json isPrivate`; dispatched the guide agent; verified `claudeMdExcludes` in the docs | Mechanism found |
| (answers: per-repo exclude by brainstorm; key-prefixed bullets) | 14 edits, checks, three precision fixes, commit ritual | This commit |

## Efficiency Insights

**What went well:**
- Not guessing at a Claude Code capability and sending the guide agent instead: the answer (`claudeMdExcludes`) turned a compromise ("accept a small overlap") into a clean design ("contributors load the copy, the author loads only the source").
- Restating the questions in plain language when the user asked what an invariant is; the design moved faster once the vocabulary was shared.

**What could improve:**
- The first question round used the term "invariant" as if it were established; it had not been defined in this session. Define a term the first time it carries a decision.

**Course corrections:**
- Dropped the "accept a small token overlap on shared repos" fallback entirely once the exclude mechanism was confirmed.
- Chose per-repo exclusion over a user-level line after noticing the user-level version would also suppress vendored rules in other people's BPE repos.

## Process Improvements

- When a design depends on whether the harness supports something, verify it in the docs (guide agent or WebFetch) before proposing a workaround; a nonexistent limitation was one sentence away from shaping the design.

## Observations

- Brainstorm now asks exactly as many questions as before: the four-part confirm replaced the tools-only question and absorbed the verification-command question.
- The verbatim-copy rule for vendoring needs the user's own python and writing sources to gain a "Hard rules" block; recorded as a deferred item outside this plugin.

## Suggested Skills for Next Session

- `plugin-dev:skill-development`: next is retrofit (resync mode, constraint extraction from the manifest read, adopting the four-part confirm so retrofit's "same Tool discovery pass" claim becomes true again).
- `plugin-dev:agent-development`: after retrofit, the execute-plan self-check and the validator checks against `deps:`/`paths:` bullets, Non-goals, and Deferred.
