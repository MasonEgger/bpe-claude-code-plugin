# Session Summary: Deferred Work Lives in the Spec (v0.7 Step 2)

**Date**: 2026-09-14
**Duration**: ~40 minutes
**Conversation Turns**: ~4 user prompts
**Estimated Cost**: low-moderate (one push, a design reversal, 17 small edits across five files, checks, commit ritual)
**Model**: Fable 5.1

## Key Actions

- Pushed `v0.7-impl` to origin (tracking, in sync) right after the step 1 commit.
- Started plan/SKILL.md and hit a real conflict between two earlier decisions: the out-of-scope pass was locked to brainstorm (Q2) while its output was locked to plan.md (decision 10), and brainstorm only writes spec.md.
- Asked via AskUserQuestion; the user redirected the question itself with a sharper objection: plan.md is ephemeral and archived, so a per-plan list would be regenerated every phase and its durable value thrown away.
- Reframed out-of-scope as two views of one list: the fence for the current phase and the backlog of likely future expansions. That makes it permanent state, which belongs in the spec.
- Locked two calls: the list lives as a `**Deferred:**` list inside `## Roadmap / phase log` (never/later/now maps to Non-goals/Deferred/Goals; the fence for any phase is Non-goals plus Deferred), and the never/later/now sort folds into brainstorm's existing tool-discovery confirm (zero extra questions). Decision 10 is superseded by decision 11.
- Applied the ripple: session-management.md (Deferred in the Roadmap definition, the scope-fence sentence rewritten), brainstorm and retrofit Saving steps (Deferred emitted, Non-goals means never), and v0.7-plan.md (decisions 5, 10, 11; change-set items 1, 2, 3, 4, 5; Reconnaissance).
- Wrote the plan/SKILL.md changes: Archive routine step 6 appends the `**Shipped:**` line to the spec (replacing `- none yet`, skipping with a message on a legacy spec), and a new "Honor the Spec's Fences" section makes plan read Invariants, Non-goals, and Deferred and refuse to plan around them.
- Ran the checks: three frontmatters parse; no dashes, smart quotes, banned words, or parallelism in the diff; no leftover decision-10 wording outside the new text.

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Push it, then start on plan/SKILL.md; ask if needed | Pushed; asked about the pass/output conflict | User chose to clarify |
| Out-of-scope is good to capture, but plan is ephemeral; spec or a new file? | Analysis: durable backlog, belongs in spec; recommended Deferred in Roadmap over a new file | Two calls locked via AskUserQuestion |
| (answers: Deferred in Roadmap; fold confirm into tool discovery) | 17 edits across five files, checks, commit ritual | This commit |

## Efficiency Insights

**What went well:**
- The user's objection was better than my framing of the conflict; presenting the analysis before re-asking meant the second question round closed it in one pass.
- Batching all 17 edits in one turn worked because every edit had a unique anchor from text written in this session or the last.

**What could improve:**
- Decision 10 was locked yesterday without checking the data's lifetime against the file's lifetime. That check is cheap and would have caught it before it went into three files.

**Course corrections:**
- Dropped the planned per-section out-of-scope block in plan.md entirely rather than building on it; plan/SKILL.md shrank to the archive append plus honoring the spec's fences.

## Process Improvements

- Before choosing a home for generated data, compare its lifetime to the artifact's lifetime; anything that must outlive a phase goes in the permanent layer even if it is produced per phase.

## Observations

- The Roadmap section now reads as a timeline: Shipped (done), Upcoming (committed), Deferred (not now). Non-goals stays the only "never".
- A separate backlog file was explicitly deferred, by the same reasoning that kept the constitution as spec top matter.

## Suggested Skills for Next Session

- `plugin-dev:skill-development`: the next v0.7 steps are the brainstorm behavior (merge mode, constraints pass, adjacency pass with the never/later/now sort folded into tool discovery, vendoring) and the retrofit resync mode.
- `plugin-dev:agent-development`: the execute-plan self-check and validator-protocol checks against Invariants, Non-goals, and Deferred touch the agent contracts.
