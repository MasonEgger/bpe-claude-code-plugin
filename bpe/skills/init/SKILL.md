---
name: init
description: This skill should be used when the user asks to "set up bpe", "bpe init", "configure bpe models", "update my bpe models", or wants the BPE model profile and repo pre-flight files created or refreshed. Interviews the user, then writes a bpe.local.md model profile and fixes what /bpe:goal pre-flight refuses on, each write behind consent. It is not the built-in /init, which writes CLAUDE.md.
argument-hint: "[profile | repo]"
allowed-tools: AskUserQuestion, Read, Write, Edit, Bash(git:*), Bash(test:*), Bash(grep:*), Bash(ls:*), Bash(mkdir:*), Bash(mktemp:*), Bash(diff:*), Bash(printenv:*)
model: sonnet
disable-model-invocation: true
---

# Init Command

Prepares a user and a repo for BPE work.
The profile half writes a `bpe.local.md` model profile from the newest Recommended Tier Map.
The repo half fixes what the `/bpe:goal` pre-flight refuses on.
Every write waits for the user's yes, and a re-run edits what exists instead of overwriting it.

This is `/bpe:init`, not the built-in `/init`, which writes a project CLAUDE.md.
The namespace tells them apart.

$ARGUMENTS narrows the run: `profile` runs Steps 1 and 2 only, `repo` runs Steps 1 and 3 only, empty runs all three.

## Step 1: Read the Current State

Run these and report the results in user-facing text before asking anything:

```bash
git rev-parse --show-toplevel
test -f .claude/bpe.local.md && echo "project profile: yes" || echo "project profile: NO"
test -f ~/.claude/bpe.local.md && echo "global profile: yes" || echo "global profile: NO"
printenv BPE_PROFILE
grep -nE '^(commit-msg\.md|goal\.md|\.claude/\*\.local\.md)$' .gitignore
test -d .ai-sessions && echo ".ai-sessions: yes" || echo ".ai-sessions: NO"
test -f spec.md && echo "spec: yes" || echo "spec: NO"
```

Then:

1. Read each profile file that exists (`.claude/bpe.local.md`, `~/.claude/bpe.local.md`).
   A missing file is the fresh-install state and not an error.
2. Read `${CLAUDE_PLUGIN_ROOT}/references/model-profiles.md`.
   Find the newest dated `### YYYY-MM-DD` heading under "## Recommended Tier Map" and read the one fenced `yaml` block under it.
   That block is the only source of recommended values; never read the prose table and never hardcode a model ID in this skill.
   If the block is missing or does not parse, stop and tell the user the plugin copy of `model-profiles.md` is broken.
3. Read spec.md's `## Available tooling` section when spec.md exists, for an existing `**Verification command:**`.
4. On a re-run (a profile file exists), list every skill and agent where that file's active profile differs from the YAML block.
   Name each as `<key>: yours <value>, recommended <value>`, and name any key the block lacks.
   This list is the "update my models" report; it changes nothing by itself.

## Step 2: Model Profile (skip when $ARGUMENTS is `repo`)

Ask one AskUserQuestion per role group, in this order, with the YAML block's values as the first and recommended option:

| Group | Skills and agents |
|---|---|
| Spec-shaping skills | `brainstorm`, `plan`, `retrofit` |
| Review and validation | `review`, `apply-review`, and the `validator` and `final-validator` agents |
| Execution | `execute-plan` and the `step-executor` agent |
| Research | the `cheap-research` agent |

Each question offers three options:

- The block's values for that group (recommended).
  A group the block does not list shows as "frontmatter default".
- Frontmatter defaults: write no entry for the group, so each seat keeps the `model:` in its own SKILL.md or agent file.
- Alias-only: the family alias (`opus`, `sonnet`, `haiku`) for each seat, for an environment that cannot pin frontier model IDs.
  Use the alias each seat's frontmatter names; read it from `${CLAUDE_PLUGIN_ROOT}/skills/<name>/SKILL.md` or `${CLAUDE_PLUGIN_ROOT}/agents/<name>.md`.

Then ask two more questions:

1. Scope: user-global `~/.claude/bpe.local.md`, or per-project `.claude/bpe.local.md` at the repo root.
   The per-project file shadows the user-global one key by key.
2. Whether to add a second profile named `work`, built alias-only, and which profile is `active_profile`.

Assemble the file in the `bpe.local.md` frontmatter schema from `${CLAUDE_PLUGIN_ROOT}/references/model-profiles.md` ("## Schema").
A re-run keeps the profile names, keys, and body notes already in the file and changes only the values the user chose.

Write it like this:

1. Build the candidate in a scratch file made with `mktemp`, outside the repo.
2. When the target file exists, run `diff` between it and the candidate, show the diff, and ask before replacing.
   When it does not exist, show the candidate in full and ask before creating it.
3. On a yes, write the target and report its path.
   On a no, change nothing and say so.

Never commit the profile file.
For a per-project file, check that `.gitignore` covers `.claude/*.local.md` (Step 1 already grepped for the line).
When it does not, offer to append that line and add it only on a yes.
A user-global file lives outside the repo and needs no ignore entry.

Tell the user that the `profile-check` hook starts using the file on the next `/bpe:<name>` invocation, and that `BPE_PROFILE=<name> claude` switches profiles per shell.

## Step 3: Repo Pre-Flight (skip when $ARGUMENTS is `profile`)

Offer each missing piece in turn, one AskUserQuestion per piece, and make no change on a no.
These are the pieces the `/bpe:goal` pre-flight refuses on (items 1, 2, and 4), plus `.ai-sessions/`, which the loop's session summaries write to:

1. `commit-msg.md` is not in `.gitignore`: offer to append the line.
2. `goal.md` is not in `.gitignore`: offer to append the line.
3. `.ai-sessions/` does not exist: offer `mkdir -p .ai-sessions`.
4. Verification command.
   Autodetect as `/bpe:goal` does, by manifest file: `pyproject.toml` means `pytest -q`, `package.json` means `npm test --silent`, `Cargo.toml` means `cargo test --quiet`, `go.mod` means `go test ./...`.
   With no manifest match and no `**Verification command:**` already in spec.md, ask the user for the exact command.
   Report what resolved.
   When spec.md exists and its `## Available tooling` section has no `**Verification command:**` line, offer to record the resolved command there, in the format `${CLAUDE_PLUGIN_ROOT}/references/session-management.md` defines.
   Write it only on a yes, and leave an existing line alone.
   With no spec.md, report the resolved command and write nothing.

Append to `.gitignore` with Edit, preserving existing lines, and create the file only on a yes.
Report each change made and each one declined.

## Hard Rules

- Never edit a skill or agent frontmatter.
  Frontmatter lives in the plugin cache and an edit there is wiped by the next update; the profile is the only per-user override layer.
- Never switch the session model and never edit `settings.json` or `settings.local.json`.
  Tell the user to run `/model <X>` themselves when the `profile-check` hook warns.
- Never commit, stage, or push anything.
- Every write (profile file, `.gitignore`, `.ai-sessions/`, spec.md) waits for the user's yes.
- Never replace an existing profile file without showing the diff first.
- Never hardcode a model ID in this skill; values come from the YAML block at run time.
- Write scratch files only to a `mktemp` path outside the repo.
