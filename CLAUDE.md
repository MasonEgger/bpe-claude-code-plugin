# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A single-plugin Claude Code marketplace.
`.claude-plugin/marketplace.json` at the root registers one plugin, `bpe`, whose source is the `bpe/` directory, so the install target is `bpe@bpe`.
Everything under `bpe/` ships to users; everything outside it (tests, `pyproject.toml`, `justfile`, `spec.md`, `.ai-sessions/`) is development material and does not ship.

Most of the plugin is Markdown that instructs an agent: skills, agent prompts, and reference files.
The only executable code is three Python scripts in `bpe/scripts/` and two hooks in `bpe/hooks/`.

## Commands

```bash
just check                      # the gate: ruff check, ruff format --check, mypy --strict, pytest
just fmt                        # ruff format, then ruff check --fix
just test                       # pytest only
uv run pytest tests/test_review_server.py::TestBindServer::test_port_in_use_counts_down_to_the_next_port
claude plugin validate ./bpe    # manifest and component check; a missing-icon warning is expected
```

CI (`.github/workflows/ci.yml`) runs `just check` on pushes to `main` and on pull requests.

The scripts have hyphenated filenames (`review-server.py`), so tests load them by path with `importlib` instead of importing them by name.
Skills reference those paths, so do not rename a script to make it importable.

## Running the Repo Copy of the Plugin

An installed `bpe@bpe` and the repo copy under `bpe/` are different files.
A session normally loads the installed copy from the plugin cache, so an edit under `bpe/` does not change the running session's behavior until the plugin is released and updated.

To run the repo copy: `claude --plugin-dir ./bpe`, then `claude plugin disable bpe@bpe --scope local` and `/reload-plugins`.
Use that setup only for sessions that exercise the plugin.
Edit files under `bpe/` from a session that loads the installed copy (`claude plugin enable bpe@bpe --scope local`, plain `claude`); auto mode has refused edits to `bpe/` while that directory was the live `--plugin-dir` plugin.

## Architecture

### Layout Under `bpe/`

- `skills/<name>/SKILL.md`: one per slash command (`/bpe:brainstorm`, `/bpe:plan`, `/bpe:execute-plan`, `/bpe:goal`, and the rest).
- `agents/`: the subagents `/bpe:goal` dispatches (`step-executor`, `validator`, `final-validator`) plus `cheap-research`.
- `references/`: the contracts that skills and agents read at run time through `${CLAUDE_PLUGIN_ROOT}/references/...`.
- `hooks/`: `hooks.json` wires two Python hooks; each has a sibling `.md` that documents its behavior.
- `scripts/`: `review-server.py` (serves the `/bpe:review` page), `validate-findings.py` (schema check for validator output), `goal-run-report.py` (token and dispatch accounting for a goal run).

### References Are the Source of Truth

A rule that more than one skill or agent depends on lives in exactly one reference file, and the skills point at it instead of restating it.

- `session-management.md`: formats for everything in `.ai-sessions/`, plus the spec.md section order and the plan-archive layout.
- `validator-protocol.md`: the findings schema and the Orchestrator Playbook, which is the per-turn procedure for a `/bpe:goal` run.
- `step-executor-protocol.md`: the executor's `implement`, `fix`, and `finalize` modes.
- `model-profiles.md`: the per-user model profile schema and the dated Recommended Tier Map.

When a change alters a contract, grep for the old wording across `skills/`, `agents/`, `references/`, and both READMEs.
Stale claims in frontmatter descriptions and intro sentences are the most common review finding in this repo.

### The Artifacts the Skills Pass Between Each Other

`/bpe:brainstorm` (or `/bpe:retrofit`) writes `spec.md`, which is permanent and edited in place.
`/bpe:plan` turns a slice of it into `plan.md` and `todo.md`.
`/bpe:execute-plan` implements the next unchecked todo item.
`/bpe:plan --archive` retires a finished plan into `.ai-sessions/<slug>/` with an `accomplishment.md`.
`/bpe:session-summary` writes `.ai-sessions/session-*.md` and appends to `.ai-sessions/lessons.md`; `/bpe:execute-plan` reads the newest summary at startup.

### The Goal Loop

`/bpe:goal` writes `goal.md`, a short block the user runs with `/goal @goal.md`.
`goal.md` holds only the completion condition, an instruction to re-read the Orchestrator Playbook every turn, and the hard rules; the procedure itself lives in `validator-protocol.md`, so changing it needs no regeneration.
The parent session is the orchestrator and makes exactly one dispatch per turn.

Per batch: the executor implements (uncommitted), the read-only validator reviews the diff and returns a findings block, the executor fixes and the validator re-checks until clean or the iteration cap, then the executor finalizes with one commit that must include a new session summary.
At the end of a full or section run, `final-validator` sweeps the whole branch diff.
`goal.md` is capped at 4,000 characters, which is why the template stays thin.

### Model Tiers

Shipped frontmatter uses family aliases only (`opus`, `sonnet`, `haiku`).
A pinned model ID reaches a seat only through a user's `bpe.local.md` profile, which the `profile-check` hook surfaces on each `/bpe:<name>` invocation.
`.claude/bpe.local.md.example` mirrors the newest dated tier map in `model-profiles.md`; update both together.

## Repo Conventions

- This repo uses its own plugin on itself: `spec.md`, `plan.md`, `todo.md`, and `.ai-sessions/` here are BPE artifacts for developing BPE.
- `spec.md` at the root is still in the pre-0.7 layout, with dated work packages appended at the bottom. Do not run `/bpe:retrofit --resync` on it mid-release; the migration would archive packages a plan is about to read.
- Releases are patch bumps to `version` in `bpe/.claude-plugin/plugin.json`, one release branch and one squash-merged PR per release. A docs-only change does not bump the version.
- The repo had no test harness before November 2026, so most plan steps are task-shaped and end in a concrete check (`grep`, an exit code, `claude plugin validate`). Python behavior changes are test-first.
- `commit-msg.md`, `goal.md`, `.ai-sessions/implementation-notes.md`, and `.claude/*.local.md` are gitignored working files.
- Handoff files in `.ai-sessions/handoffs/` are short-lived and are not committed.
