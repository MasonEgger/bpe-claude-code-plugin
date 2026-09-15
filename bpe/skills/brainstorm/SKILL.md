---
name: brainstorm
description: Iterative Q&A to develop a thorough project specification (spec.md), or to merge the next phase into an existing one
model: claude-opus-4-8
disable-model-invocation: true
---

# Brainstorm Command

Ask me one question at a time so we can develop a thorough, step-by-step spec for this idea. Each question should build on my previous answers, and our end goal is to have a detailed specification I can hand off to a developer who will implement using good TDD practices.

Let's do this iteratively and dig into every relevant detail. Remember, only one question at a time.

## Mode: New Spec or Merge

Check for `spec.md` at the repo root before anything else.

- Absent: new-spec mode. Run every section below in order and write a fresh spec.md at the end.
- Present: merge mode. spec.md is permanent and edited in place, so this run adds a phase to it rather than replacing it. Read the whole spec first. Skip the blindspot pass unless the user says their context changed. Scope the Q&A to the new phase only: what this phase adds or changes, not the whole project again. Run the constraints, adjacency, and tool discovery passes against the new goals only; existing Invariants, Non-goals, and Deferred entries are inputs, not questions (a Deferred item this phase takes on moves into Goals; a Goal this phase retires moves to Deferred or Non-goals, by the user's call). Then follow "Saving" in merge mode: write the merged spec to a scratch file, show `diff -u spec.md <scratch>`, and move it over spec.md only after the user confirms. Superseded requirements are rewritten in place, never appended as amendments, so the spec always reads as current intent on one pass.

To start a spec over instead of merging, delete or move spec.md first; there is no overwrite flag.

## Step 0: Blindspot pass

Run this pass BEFORE the substantive Q&A. It calibrates the rest of the session to what the user already knows.

1. Ask ONE question about the user's starting context: domain familiarity, prior attempts at this idea, experience with this codebase (if one exists).
2. Given the answer, surface 3-5 unknown-unknowns: questions the user probably doesn't know to ask, framed as "you may want to consider" rather than "you must answer". The user may engage with any, all, or none of them.
3. Record the user's context answer verbatim in spec.md under `## Starting context`. Create the section if it doesn't exist. Do not paraphrase; the plan writer and validator calibrate against the user's own words.
4. Proceed to the standard one-question-at-a-time Q&A.

## Critical Focus Areas

**TDD Implementation Ready**: Ensure the spec includes requirements for YOUR application logic that can be converted into failing tests first. Focus on business rules, data validation, error handling, and custom algorithms that YOU will implement, not framework or library behavior. Think about what application-specific behaviors need verification.

**Component Boundaries**: Identify clear, testable components that can be implemented independently and then integrated together. Each component should have well-defined inputs, outputs, and responsibilities.

**Global Claude Config Integration**: Follow the established development patterns and preferences from the user's global Claude configuration (found in ~/.claude/CLAUDE.md and related files). Respect their preferred tools, coding standards, and project structure approaches.

Focus on getting the technical details and component boundaries clear enough that the resulting spec can be broken down into implementable, testable steps that follow the user's established development workflow.

The goal of this is NOT to implement the application or write a bunch of code, but to create a specification file that you will use later to create a plan. I will review this after and make manual changes. You may write _some_ code to illustrate specific points, but do not focus on that. Instead focus on making the specification usable for you to consume and plan with later.

## Constraints pass (after the Q&A)

Invariants are the rules that hold across every phase; `${CLAUDE_PLUGIN_ROOT}/references/session-management.md` defines the section under "Invariants Section (spec.md)". Build the candidate list from two sources. Do not ask about them yet; the single confirm in Tool discovery carries them.

1. Negate the stated choices. Every tech choice the user made in the Q&A implies exclusions: "Postgres via Prisma" implies no second datastore and no raw SQL; "hash with the library already in the project" implies no new hashing dependency. Write each implied exclusion as a candidate. Negation over-generates (a test suite may legitimately use SQLite), so these are proposals, never silent additions.
2. Collect the stated non-negotiables. Anything the user called mandatory, forbidden, or "never" during the Q&A is a candidate as spoken.

Write candidates in the two forms the section allows, one bullet each:

- Checkable, with a fixed key prefix the validator can find: `- deps: frozen` (no dependency changes without a spec change) and `- paths: <glob>[, <glob>]` (changes stay inside these paths). Use these only when the user's answers support them; a project that expects to add dependencies freely gets no `deps:` line.
- Prose, for everything a reader must judge: `- never store access tokens in the database`.

Keep the list short. Constraints reduce the executor's latitude, and the Project overview exists so the agent can make sensible calls on what the spec does not say. A rule belongs here only if the user would be annoyed to see it decided differently.

## Adjacency pass (after the Q&A)

For each goal the Q&A produced, list the three to five features an eager agent would bolt on without being asked: the nearest neighbors of the feature (password reset, email verification, and social login next to login; rate limiting and pagination next to an endpoint; a settings page next to a user model). These are the highest-probability scope leaks, which is what makes the list useful. It is a precision aid for the plan writer and the validator, not an inventory of everything the project will never do.

Propose a bucket for each candidate: never (`## Non-goals`), not now (`**Deferred:**` under `## Roadmap / phase log`), or now (promote into `## Goals`). Default is Deferred. Do not ask yet; the single confirm in Tool discovery carries the sort.

## Tool discovery and the single confirm (before saving spec.md)

After the substantive Q&A, the constraints pass, and the adjacency pass, run one more pass: enumerate the MCP servers and skills available in this session that might apply to the project's domain, decide the vendoring proposal, and then ask ONE question that carries every pending decision at once. The tooling half populates `## Available tooling` so `/bpe:plan` can assign validators per section and `/bpe:goal` can dispatch the `bpe:validator` agent with the right consultation set. Nothing in this pass is a separate question; brainstorm is long enough already.

Procedure:

1. List candidate MCPs. Use `ToolSearch` with a search query suited to the project's domain (e.g. for a Temporal project, search for "temporal"; for a Postgres project, search for "postgres"). Capture the MCP server names that come back. Also list any plugin-namespaced MCPs visible in the session (e.g. `mcp__claude_ai_Google_Drive__*` for a project that involves Drive). If none look relevant, that's fine; the list can be empty.
2. List candidate skills. Read the available skills from the session reminder. Pick those whose descriptions mention the project's domain (e.g. `temporal:temporal-developer`, `python:python`, `content-design:tutorial-writing`).
3. Build the vendoring proposal per "Vendoring" below: the shared-repo verdict and the set of skills whose hard rules would be copied into `.claude/rules/vendored/`.
4. Ask the user ONE question with four parts, each carrying a proposed default so a short answer closes all four:
   - Tools: "These MCPs and skills look relevant. Which should the validator consult during goal-mode runs? Drop any that don't apply; add any I missed."
   - Invariants: the candidate list from the constraints pass, checkable and prose. Confirm, drop, or reword each.
   - Scope: the adjacency candidates with their proposed buckets (default Deferred). Move any to never or now.
   - Vendoring: the shared verdict and the proposed vendor set. When the shared verdict is a fence-sitter (see Vendoring step 1), say so and let the user call it; otherwise present it as a default.
5. If the user wants suggestions for external tools not in the session, dispatch the `bpe:cheap-research` subagent with the project domain; present the shortlist for user confirmation. Dispatch via the Agent tool with a single research question naming the project domain; the agent returns a ranked list of at most 10 entries (`<name> :: <one-line relevance note> :: <source URL or path>`) or the line `no relevant results` followed by one sentence naming what was searched. Only confirmed entries go into spec.md.
6. If the project's tech stack matches none of the test-runner manifests `/bpe:goal` autodetects (pyproject.toml, package.json, Cargo.toml, go.mod), fold one more part into the same question: what exact command verifies the work (e.g. `vale docs/` for a prose project)? Record the answer as a `**Verification command:** <command>` line in the `## Available tooling` section, between `**Skills:**` and `**Notes:**`. `/bpe:goal`'s pre-flight falls back to this field when it can't autodetect a test runner.
7. Record the outcome: the confirmed tool set in `## Available tooling`, the confirmed invariants in `## Invariants`, each adjacency candidate in the bucket the user chose, and, when vendoring was confirmed, run the Vendoring procedure before Saving.

The output section format:

```markdown
## Available tooling

Tools the `bpe:validator` agent should consult when reviewing diffs in `/bpe:goal` runs. `/bpe:plan` propagates these to per-section declarations in plan.md.

**MCPs:**
- mcp__temporal-docs__search_temporal_knowledge_sources

**Skills:**
- temporal:temporal-developer
- python:python

**Notes:** Validator should focus on workflow non-determinism, activity heartbeats, and signal/query semantics in any code under `workflows/` and `activities/`.
```

When step 6 collected a verification command, add a `**Verification command:** <command>` line between `**Skills:**` and `**Notes:**`. Omit the line when a test runner is autodetectable. `${CLAUDE_PLUGIN_ROOT}/references/session-management.md` documents the full section format canonically.

If the user says no validators apply at the project level, write the section with both lists empty and `**Notes:** No domain validators apply for this project. /bpe:plan will declare "**Tools:** none" for every section.` This still creates the section so plan.md has a known structure to read.

## Vendoring (only when confirmed in the single question)

Vendoring copies the hard rules from the user's own skills into the repo so a collaborator's agent follows them without having those skills. It is purely a sharing mechanism, so it runs only for a shared repo. On a solo or private repo nothing is written, and `## Invariants` names the governing rulebook in one line instead (`- Python: per the python:python skill`). `${CLAUDE_PLUGIN_ROOT}/references/session-management.md` defines the layout under "Vendored Rules (.claude/rules/vendored/)".

1. Decide shared. Run `gh repo view --json isPrivate --jq .isPrivate` (needs an authenticated `gh`); `false` means shared. Without `gh`, treat a LICENSE file plus a remote on a public host as shared, and anything else as private. A public remote with no LICENSE, or a LICENSE with a private remote, is a fence-sitter: present it in the single question rather than deciding.
2. Pick the artifact classes the project produces (Python code, prose docs, IaC, slides, and so on) from the Q&A and the repo, then the skills and user-level rules that govern each class: skills from the session list, rules from `~/.claude/rules/`. Sort each into a bucket:
   - Always vendor: craft rules for an artifact class the project produces (a Python style guide for a Python project, the tutorial rules for a docs repo).
   - Conditionally vendor: doc-hygiene rules (vocabulary, punctuation, structure). Vendor only when prose docs are a primary artifact of the project, not when the README is a formality.
   - Never vendor: personal-identity rules such as the user's authentic writing voice. A collaborator should not ghost-write in the author's voice. Do not propose these.
3. For each source in the vendor set, obtain its text: invoke a skill through the Skill tool, or Read a user-level rules file. If the source has a section headed "Hard rules" (or an equivalent explicit rules block), copy that section verbatim; do not paraphrase, reorder, or trim it. If it has no such section, extract the must/never rules into a bullet list, show the extract to the user before writing it, and suggest adding a "Hard rules" block to the source so the next resync is a verbatim copy.
4. Write each vendored file to `.claude/rules/vendored/<domain>.md` (`python.md`, `writing.md`, `tutorials.md`) with `paths:` frontmatter matching the artifact class (`**/*.py`; `**/*.md`), then the copied rules. Add one pointer bullet per file to `## Invariants`: `- Python: per .claude/rules/vendored/python.md`.
5. Exclude the vendored rules for the author, whose live skills are the source and would otherwise load twice. Merge `"claudeMdExcludes": ["**/.claude/rules/vendored/**"]` into `.claude/settings.local.json`, creating the file if absent and keeping any existing keys and array entries. Confirm `.claude/settings.local.json` is gitignored; if it is not, add the line and tell the user. Tell the user the exclusion is per machine: another machine needs the same line, or a user-level `claudeMdExcludes` in `~/.claude/settings.json` (which also skips vendored rules in other people's repos).

## Closure before saving

Brainstorm does not end with open questions. The whole point of the session is to answer them. The saved spec must be decision-complete: every question raised during the session is resolved in it, and it contains no "Open questions", "Open items", "TBD", "TODO", or "decide later" section that punts a choice to plan time or to the executing agent.

Before writing spec.md, run a closure pass:

1. Re-read the whole session and list every question, fork, or ambiguity that came up.
2. For each one still unresolved, ask it now, one at a time, until it is closed. Do not save spec.md while the list is non-empty.
3. A deferral IS a closure, not an escape hatch. When the user says "whatever works best", "you decide", or similar, that closes the item: record the concrete choice you made as a decided requirement in spec.md, with a one-line rationale. Never leave it phrased as an unanswered question.
4. The only thing that may carry forward is a review checkpoint: a decision that IS made but that you want the user to eyeball. Phrase these as `Decision: <the decision> (confirm at review)`, never as an open question. Prefer resolving in-session over deferring to review; use a checkpoint only when the choice is genuinely low-stakes or reversible.
5. If a question truly cannot be answered without information nobody has yet (e.g. a value only discoverable during implementation), record it as an explicit assumption with a chosen default, not as an open question.

## Saving

Once we are done, save the spec as @spec.md.
In merge mode, write the merged spec to a scratch file, show `diff -u spec.md <scratch>`, and move it over spec.md only after the user confirms (see "Mode: New Spec or Merge").
Write the sections in the canonical order defined under "Spec Section Order (spec.md)" in `${CLAUDE_PLUGIN_ROOT}/references/session-management.md`.
`/bpe:retrofit` writes the same order, and `/bpe:plan` consumes either without knowing which skill wrote it.
Under `# <title>`:

1. `## Starting context`: the Step 0 context answer, verbatim.
2. `## Project overview`: what the project is and where it is going. This carries the mission; there is no separate mission section.
3. `## Invariants`: the list confirmed in the single question, one bullet per rule: checkable rules with their key prefix (`deps:`, `paths:`), prose rules, the tech stack, and one pointer bullet per vendored rules file (or one line naming the governing skill when nothing was vendored).
4. `## Available tooling`: the confirmed set from Tool discovery, in the format shown above.
5. `## Roadmap / phase log`: `**Shipped:**` with `- none yet` for a new project, `**Upcoming:**` with any later phases the user named, and `**Deferred:**` with every piece of work the user sorted as not-now during the Q&A, one line each with a one-line reason or trigger (or `- none`). The archive routine appends shipped phases later; do not pre-fill them.
6. `## Goals`: the requirements, concrete enough to plan from. Edited in place in later phases, never appended to.
7. `## Non-goals`: what the project deliberately does not do, ever. Permanent exclusions only; work that is merely not-now belongs in `**Deferred:**` under `## Roadmap / phase log`.
8. `## Component boundaries`: the independently implementable components with their inputs, outputs, and responsibilities.
9. `## Success criteria`: how the user will know the project is done.

Here's the idea:
