# Session Summary: Open-Issue Triage and the 0.7.2 Work Package

**Date**: 2026-11-09 (session opened 2026-11-03 over remote control)
**Duration**: roughly 2 hours of active work spread across a multi-day remote-control session
**Conversation Turns**: 12 user prompts
**Estimated Cost**: moderate; one claude-code-guide subagent (~95k tokens) plus a long interactive triage on Opus 5.5
**Model**: Opus 5.5 (triage and spec writing); Fable 5.1 for the retrofit turn; Sonnet 5.5 for this summary

## Key Actions

- Pulled all 13 open issues, validated each against the current tree, and sorted them into five groups: subagent tool access (#44, #49), goal-loop robustness (#43, #40), review server (#33, #36, #47), review renderer (#17), and new capabilities (#28, #48). Two were already resolved: #24 (fixed in 0.6.3 without closing the issue) and #22 (duplicate of #38).
- Closed #24 and #22 on GitHub with evidence comments.
- Dispatched `claude-code-guide` to confirm how plugin subagents get MCP tools. Finding: an omitted `tools:` inherits every MCP tool, `disallowedTools` exists, and an allowlist cannot name per-project MCP tools. That settled the #44/#49 fix as inherit-plus-deny.
- Ran a decision interview across four `AskUserQuestion` rounds covering bind policy, copy controls, review ordering, MCP access, finalize-red recovery, archive flags, the four `/bpe:init` decisions, the issue-format shape, and release sequencing.
- Designed batch mode for `/bpe:goal` with Mason (plan-time boundaries, warm executor via `SendMessage`, cold validator, one commit per batch, default-on with `**Batch:** single` opt-out) and an end-of-run final sweep on its own profile seat.
- Verified the session transcript JSONL records per-turn usage fields, which makes a 95% context checkpoint hook feasible.
- Filed four new issues (#50 opus unpin, #51 batch mode, #52 final sweep, #53 checkpoint and report budget) in the #48 structured format and cross-linked them.
- Created branch `release-0.7.2`; appended a `## 0.7.2 Fixes` work package to `spec.md` and marked the four `/bpe:init` decisions confirmed with refinements (YAML tier-map block, drift listing on re-run).
- Deferred `/bpe:retrofit --resync` until 0.7.5 ships, because the Structure Migration would archive the active 0.7.2 package. Recorded this and the release sequence in project memory.
- Confirmed the project uses semver (no calver anywhere in manifest, tags, or docs).

## Prompt Inventory

| Prompt/Command | Action Taken | Outcome |
|---|---|---|
| Pull open issues, validate, categorize, plan fixes; ask freely | Fetched 13 issues, grepped current code for each claim, grouped into five categories, launched docs lookup | Two already resolved; four decision rounds followed |
| (AskUserQuestion round 1) | Close #24/#22, tailnet-mandatory bind, both copy controls, server fixes before renderer | Decisions recorded |
| (AskUserQuestion round 2) | Inherit + deny for MCP access, synthesized fix block for finalize-red, `--archive --regen` combined flag | Mason asked for pros/cons on #40 instead of picking |
| #40 discussion: emergency-only clear at 95%, raised bpe slowness | Proposed batch mode design with tradeoffs; asked four follow-ups | Batch mode: plan-time, default-on, one commit per batch, baseline first |
| (AskUserQuestion round 3) | Init decisions, issue format home and fields, release split | Only name confirmed on init; Mason asked for discussion on the other three; patch bumps only until 0.8.0 |
| Init decisions 2 to 4 discussion | Grounded each in repo state; found `.example` file drifted from tier map | Confirmed all three with refinements |
| Tier map direction: Opus 5.5 good again, Fable less and later | Proposed final sweep seat and per-seat defaults | Unpin 4.8 everywhere; Fable for brainstorm/plan/retrofit and the sweep |
| "Go ahead and start" | Filed #50 to #53, branched, wrote the 0.7.2 spec package, updated init decisions | Spec uncommitted on `release-0.7.2` |
| `/bpe:retrofit` (bare) | Refused per skill (spec exists); surfaced the sequencing conflict with the live 0.7.2 package | Resync deferred until 0.7.5; memory notes written |
| Semver or calver? | Checked manifest, tags, docs, release commits | Semver; nothing ever moved |
| Are we good to go / should I merge? | Laid out the close-out sequence; nothing built yet | Commit spec, review, plan, goal, PR |
| "do what we need" | Started the commit process with this summary | In progress |

## Efficiency Insights

**What went well:**
- Grepping the current tree for each issue's claim before asking anything caught two stale issues (#24, #36's `--from` ask) and one false doc claim (`plan/SKILL.md:240` says the executor consults MCPs; it cannot).
- One background `claude-code-guide` dispatch answered the question two issues hinged on while the triage continued.
- Bundling decisions into multi-question `AskUserQuestion` rounds kept the interview to four rounds for roughly fifteen rulings.
- Filing the four new issues in the #48 format was a live test of that format before building the skill for it.

**What could improve:**
- Round 3 offered `/bpe:init` decisions as a bare checklist; Mason checked only the name and asked for discussion. Decisions with tradeoffs need the pros and cons up front, not as a follow-up.
- The 0.7.2 spec package shipped with several defaults Mason never ruled on (per-artifact hash naming, POST logging, rule names). They are flagged for `/bpe:review`, but asking in round 1 would have been cheaper.
- `/bpe:retrofit` was recommended in an earlier reply without checking that a resync would collide with the in-flight spec work. Caught at invocation, not at recommendation.

**Course corrections:**
- #40 moved from "pick from four options" to a pros-and-cons discussion, then to emergency-only clearing at 95% with no persisted state.
- Mason reframed the loop-efficiency problem as batch mode, which absorbed most of #40's motivation and became its own release.
- Release numbering moved from "0.8.0 for loop efficiency" to patch bumps throughout, with 0.8.0 reserved as a version-only bump Mason calls.

## Process Improvements

- When recommending `/bpe:retrofit --resync`, first check whether `spec.md` carries dated packages that are active rather than shipped; the Structure Migration archives dated sections and will try to move live work.
- Sweep every open issue's claim against the tree before triage; fixes that land through PRs without `Closes #N` leave issues open and inflate the backlog.
- Present decisions with tradeoffs as a short pros-and-cons list and a recommendation, then ask; a bare checklist invites "let's discuss" and costs a round.
- Record `(default)` markers on any spec content the user did not rule on, so `/bpe:review` can target them.

## Observations

- Mason's direction on model tiers is "use Fable less and later": Fable for ambiguity (brainstorm, plan, retrofit) and for the final adversarial sweep, Opus for per-batch validation and review, Sonnet for execution.
- The shipped tier map and `.claude/bpe.local.md.example` had drifted (dates 2026-08-08 vs 2026-07-26); the init refinement to generate one from a YAML block fixes the class, not the instance.
- The transcript records `cache_read_input_tokens` and `cache_creation_input_tokens` per assistant turn; their sum with `input_tokens` is the live context size, which is what a checkpoint hook needs.
- The repo's own `spec.md` is still pre-0.7 layout. `/bpe:plan` and `/bpe:goal` read it fine; only the Roadmap log step of archiving is skipped.

## Suggested Skills for Next Session

- `plugin-dev:agent-development`: the #44/#49 fix rewrites `agents/validator.md` and `agents/step-executor.md` frontmatter (`tools:` removal, `disallowedTools`).
- `plugin-dev:skill-development`: edits to `skills/plan/SKILL.md` (archive flags, MCP claim) and `skills/goal/SKILL.md` (pre-flight MCP warning, finalize-red recovery).
- `python:python`: the review-server work (#33/#36/#47) is all in `scripts/review-server.py`.
- `plugin-dev:plugin-structure`: the `plugin.json` version bump to 0.7.2.
