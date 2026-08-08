# Model Profiles

This file is the canonical schema documentation for `.claude/bpe.local.md` profile files, the per-user settings layer that overrides skill and subagent `model:` frontmatter at runtime.
Any BPE component that resolves a model for a skill invocation or a subagent dispatch (including the `profile-check` UserPromptSubmit hook, documented in `bpe/hooks/profile-check.md`) conforms to the schema and precedence rules defined here.
The design rationale lives in spec.md Goal 11.

## Purpose

Skill and agent frontmatter ships fixed `model:` tiers (`opus` and `sonnet` per the Goal 11 tables; `haiku` remains a valid override value).
Aliases resolve to the latest available model in each family, which handles the automatic case but gives the user no lever for "use this specific model ID for brainstorm on my personal machine."
Profiles provide that lever: a settings file maps skill and agent names to model values per named profile, and the user switches profiles per machine, per project, or per shell.

- Model availability changes (subscription, work rules, model retirement): update one file, every skill and subagent adapts.
- Model renames don't break the plugin: the profile map is user-owned and updated in place.
- Fresh install just works: when no settings file exists, everything falls back to frontmatter defaults.

## File Locations

Two locations, checked in order:

1. `.claude/bpe.local.md` at the repo root (per-project).
2. `~/.claude/bpe.local.md` (user-global).

The per-project file shadows the user-global file (same pattern as CLAUDE.md).
Shadowing is key-level, not whole-file: a lookup that finds no entry in the per-project file falls through to the user-global file before falling back to frontmatter.

Profile files are user-local state and must not be committed.
Add `.claude/*.local.md` to `.gitignore` in any project that carries one.

## Schema

YAML frontmatter between `---` markers, followed by an optional markdown body.
The body is free-form user notes; model resolution reads only the frontmatter.

```markdown
---
active_profile: <profile-name>
profiles:
  <profile-name>:
    skills:
      <skill-name>: <model-id-or-alias>
    agents:
      <agent-name>: <model-id-or-alias>
  <another-profile-name>:
    skills:
      <skill-name>: <model-id-or-alias>
    agents:
      <agent-name>: <model-id-or-alias>
---

# Notes

Optional free-form context. Ignored by model resolution.
```

### Field Reference

- **`active_profile`** (string, required): names the profile that is live. Must match a key under `profiles:` for its overrides to take effect. Overridden by the `BPE_PROFILE` env var.
- **`profiles`** (map, required): named profiles. Keys are user-chosen profile names (e.g. `personal`, `work`).
- **`profiles.<name>.skills`** (map, optional): skill-name to model-value overrides. Keys are bare skill names as they appear in `bpe/skills/<name>/SKILL.md` (e.g. `brainstorm`, not `bpe:brainstorm`).
- **`profiles.<name>.agents`** (map, optional): agent-name to model-value overrides. Keys are bare agent names as they appear in `bpe/agents/<name>.md` (e.g. `validator`, not `bpe:validator`).

Model values accept anything the SKILL.md `model:` field accepts: family aliases (`opus`, `sonnet`, `haiku`) or explicit model IDs (`claude-fable-5`).

## Lookup Precedence

To resolve the model for a given skill or agent, walk this chain top to bottom.
An absent key at any level falls through to the next level.

The active profile name is resolved once, before any key lookup: from `BPE_PROFILE` when set, else the per-project file's `active_profile`, else the user-global file's.
That single name selects the profile in both files, even when a skill or agent lookup falls through from the per-project file to the user-global one.

1. **`BPE_PROFILE` env var.** When set, it names the active profile and overrides both files' `active_profile` fields. Enables shell-scoped switching (`BPE_PROFILE=work claude`). When unset, the active profile name comes from the files as described above.
2. **Per-project `.claude/bpe.local.md` at the repo root.** Consulted before the user-global `~/.claude/bpe.local.md`. If the per-project file is absent, or its copy of the active profile has no entry for the skill or agent being resolved, fall through to the user-global file.
3. **The active profile's override map.** Look up the skill name under `skills:` or the agent name under `agents:` in the active profile. A hit resolves the model.
4. **Skill or agent frontmatter `model:` field.** The shipped default tiers (spec.md Goal 11 tables). Always present; the chain terminates here.

Fall-through consequences worth spelling out:

- Unset skills or subagents fall back to their frontmatter `model:` field. Profiles only need to list the overrides that differ from the defaults.
- If the active profile name (from `BPE_PROFILE` or `active_profile`) matches no key under `profiles:`, the profile contributes no overrides and every lookup falls back to frontmatter.
- If no settings file exists in either location, all lookups resolve to frontmatter defaults. This is the fresh-install state.

## Example

Matches the canonical example in spec.md Goal 11.
The `personal` profile pins specific skills and agents to an explicit model ID; the `work` profile uses the `opus` alias so the same overrides resolve to whatever Opus the work environment offers.

```markdown
---
active_profile: personal
profiles:
  personal:
    skills:
      brainstorm: claude-fable-5        # explicit model ID
      apply-review: claude-fable-5
    agents:
      validator: claude-fable-5
  work:
    skills:
      brainstorm: opus                    # alias resolves to work-available Opus
      apply-review: opus
    agents:
      validator: opus
---
```

With this file at `~/.claude/bpe.local.md` and no per-project file:

- `/bpe:brainstorm` resolves to `claude-fable-5` (personal profile, skills map hit).
- `/bpe:plan` resolves to `opus` (no entry in the personal profile; frontmatter default).
- A `bpe:validator` dispatch resolves to `claude-fable-5` (personal profile, agents map hit).
- `BPE_PROFILE=work /bpe:brainstorm` resolves to `opus` (env var selects the work profile).

## Recommended Tier Map

Dated recommendations, not schema.
This section is re-evaluated when a model generation ships or a recommendation proves out (or fails) in use; a stale date here is a defect, and the `.claude/bpe.local.md.example` file at the repo root mirrors whatever this section currently says.

### 2026-08-08 (Opus 4.8 executor, Opus 5 rolled back)

| Role | Recommendation | Why |
|---|---|---|
| brainstorm, retrofit, plan, review, apply-review | `claude-fable-5` | Spec-shaping and decision review live in ambiguity, where Fable 5 keeps the edge ("for ambiguous work" per week-one practitioner consensus and Anthropic's own "highest available capability" framing) |
| validator agent | `claude-fable-5` | Adversarial review wants the strongest judgment available; the validator's whole job is catching what the executor missed |
| step-executor agent, execute-plan | `claude-opus-4-8` | Bounded execution against a decision-complete plan. Opus 5 was adopted here on 2026-07-26 and rolled back after lived use: it improvised and widened scope more than Opus 4.8 on bounded plan work, so 4.8 is the reliable executor |
| cheap-research agent | frontmatter default (`sonnet`) | Fast external lookups; Sonnet 5 handles search-and-summarize well above Haiku at modest cost. This was an override recommendation on 2026-07-26 and is now the shipped default, so no profile entry is needed. |
| Everything else (goal, session-summary, commit-message, handoff, lessons, wtf-wid, gh-issue) | frontmatter defaults | Mechanical work; the shipped `sonnet` tiers hold |

Why the rollback: the 2026-07-26 adoption caveats below proved out in use rather than passing a re-test.

- The community claim that Opus 5 follows instructions better than Fable never survived the 2026-07-26 research pass; week-one reports showed more improvisation than prior Opus. The executor pin rested on cost and capability, not obedience, and the improvisation is what sank it in practice.
- Anthropic's Opus 5 prompting guide warned that explicit verification instructions cause over-verification and that the model can widen task scope; both showed up on bounded plan execution, which is exactly the executor's job.
- No independent long-horizon head-to-head between Fable 5 and Opus 5 existed at adoption time; lived use stood in for the missing benchmark and pointed back to Opus 4.8 for the executor tier.
