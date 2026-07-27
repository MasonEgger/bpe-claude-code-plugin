# BPE for Claude Code

A [Claude Code](https://docs.anthropic.com/en/docs/claude-code) plugin that packages the Brainstorm-Plan-Execute loop.
Build a spec through dialogue, break it into right-sized TDD steps, then execute them one at a time with continuity across context windows.

This repository is a single-plugin marketplace: the plugin is `bpe` and the marketplace is also `bpe`, so the install target reads `bpe@bpe`.

The `python` plugin formerly hosted here moved to a private marketplace in July 2026 (v2.0.0); the last public version was 0.1.0.

## Commands

| Command | Purpose |
|---|---|
| `/bpe:brainstorm` | Iterative Q&A to develop a project specification (`spec.md`) |
| `/bpe:retrofit` | Retrofit a BPE-compatible `spec.md` onto an existing project that lacks one, via a shortened Q&A focused on the gaps |
| `/bpe:plan` | Transform spec into an implementation roadmap (`plan.md` + `todo.md`) of TDD Feature steps and checklist Task steps |
| `/bpe:execute-plan` | Implement the next unchecked step as written: RED-GREEN-REFACTOR for Feature steps, Scope/Tooling/Do/Verify/Document for Task steps |
| `/bpe:goal` | Wrap the loop in an autonomous `/goal` run: dispatches a fresh subagent per step, gates each one behind a read-only validator, commits per step |
| `/bpe:gh-issue` | Fetch a GitHub issue and route to brainstorm or plan based on detail level |
| `/bpe:commit-message` | Generate a commit message explaining what was changed |
| `/bpe:review` | Generate an HTML view of `spec.md` / `plan.md` / `todo.md` and serve it locally for visual review with annotations |
| `/bpe:apply-review` | Load saved review feedback and apply changes to the reviewed artifact |
| `/bpe:handoff` | `create` writes an ephemeral handoff for a fresh agent; `continue` reads an existing one to prime a new session; `close` deletes a consumed handoff |
| `/bpe:session-summary` | Generate a session recap and capture lessons learned |
| `/bpe:wtf-wid` | "WTF was I doing?" A fits-on-screen recap of the current session for fast re-entry |
| `/bpe:lessons` | View, search, and manage accumulated lessons |

The loop: Brainstorm a spec through dialogue, Plan it into right-sized steps, Execute one step at a time, then Review and Record lessons for next session.
Everything else in the table serves that spine.
`/bpe:review` and `/bpe:apply-review` give you an interactive HTML pass over the BPE artifacts themselves.
`/bpe:handoff` and `/bpe:wtf-wid` exist because a run outlives any single context window.
Format specs and workflow rules for `.ai-sessions/` live in `bpe/references/session-management.md`, read directly by the relevant skills.

## Autonomous Mode

`/bpe:goal` runs the Execute phase unattended on top of Claude Code's `/goal` primitive (requires v2.1.139+).
The parent session orchestrates and dispatches one subagent per step, so the parent transcript stays small and each step starts from a fresh context.

| Agent | Model | Role |
|---|---|---|
| `bpe:step-executor` | sonnet | Executes one plan step per dispatch in `implement`, `fix`, or `finalize` mode |
| `bpe:validator` | opus | Read-only QA gate between implement and finalize; checks the uncommitted diff and returns structured findings |
| `bpe:cheap-research` | haiku | External lookups for `/bpe:plan`, `/bpe:brainstorm`, and `/bpe:retrofit` |

The validator is dispatched by the orchestrator, not invoked directly.
It never edits, never commits, and its findings route back to a `fix` dispatch before the step is allowed to commit.
`/bpe:goal` refuses to run on `main`, requires a clean tree, and enforces exactly one commit per step.
Full contracts and the loop diagram are in the [plugin README](bpe/README.md#autonomous-mode).

## Installation

### Add the Marketplace

Register this repository as a Claude Code marketplace:

```
/plugin marketplace add MasonEgger/bpe-claude-code-plugin
```

### Install the Plugin

```
/plugin install bpe@bpe
```

### Browse Available Plugins

You can also use the interactive plugin manager to discover and install:

```
/plugin
```

Navigate to the **Discover** tab to see all available plugins from registered marketplaces.

### Update Plugins

To pull the latest changes from this repository:

```
/plugin marketplace update bpe
```

### Upgrading From `mmegger-plugins`

The marketplace was renamed from `mmegger-plugins` to `bpe` before 1.0, when this repo dropped to a single plugin.
Claude Code keys marketplaces by name, so an existing registration does not follow the rename.
Remove the old one and re-add:

```
/plugin marketplace remove mmegger-plugins
/plugin marketplace add MasonEgger/bpe-claude-code-plugin
/plugin install bpe@bpe
```

## Repository Structure

- `.claude-plugin/marketplace.json`: plugin registry for Claude Code
- `bpe/.claude-plugin/plugin.json`: BPE plugin manifest
- `bpe/skills/<name>/SKILL.md`: BPE skills (invoked as `/bpe:<name>`)
- `bpe/agents/`: subagents (`step-executor` and `validator` for `/bpe:goal`; `cheap-research` for the spec and plan skills)
- `bpe/scripts/`: bundled helper scripts (`review-server.py` for `/bpe:review`, `validate-findings.py` for the validator schema)
- `bpe/references/`: plugin-bundled reference docs that skills read directly (e.g. `session-management.md`)

## Prerequisites

- **`/bpe:gh-issue`**: `gh` CLI installed and authenticated
- **`/bpe:review`**: Python 3 (uses stdlib only; no extra packages). If `tailscale` is installed and the daemon is up, the review server binds to the local tailnet IP so the page is reachable from other tailnet devices (phone, second laptop). Otherwise it binds to `127.0.0.1`.

## License

MIT
