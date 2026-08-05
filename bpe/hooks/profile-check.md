# Profile-Check Hook

A `UserPromptSubmit` command hook that warns when a `/bpe:<name>` invocation's profile-resolved model differs from the current session model.
The hook body is `hooks/profile-check.py`; this file documents its behavior.
The registered configuration lives in `hooks/profile-check.json` (referenced from `.claude-plugin/plugin.json` via its `hooks` field) and runs the script via `${CLAUDE_PLUGIN_ROOT}`.
Resolution semantics are defined in `references/model-profiles.md`, the canonical schema doc for `.claude/bpe.local.md` profile files.

## Behavior

1. On every prompt submission, the script reads the hook-input JSON from stdin and inspects the submitted prompt text.
2. Prompts that do not start with `/bpe:` (after optional leading whitespace) pass through untouched: the script exits 0 with no output and contributes nothing to the transcript.
3. When neither `.claude/bpe.local.md` under the session's `cwd` nor `~/.claude/bpe.local.md` exists, the script also stays silent, even for `/bpe:` invocations. This is the fresh-install fast path; frontmatter defaults apply and no context is injected.
4. For a `/bpe:<name>` invocation with at least one profile file present, the script extracts the skill name and injects `additionalContext` instructing the session agent to:
   1. Re-confirm the profile files exist and skip silently if not (cheap, and keeps the injected instructions self-contained).
   2. Resolve the active profile name once: `BPE_PROFILE` env var when set (checked via Bash), else `active_profile` in the per-project file, else in the user-global file.
   3. Look up `skills.<name>` under that profile in the per-project file, falling through to the user-global file (shadowing is key-level). No entry means the skill's frontmatter `model:` applies and no warning fires.
   4. Compare the resolved value to the current session model. A family alias (`opus`, `sonnet`, `haiku`) matches any session model of that family.
   5. Only on mismatch, emit the warning before proceeding:

      > Note: skill \<name\> profile expects model \<X\>; current session is \<Y\>. Consider /model \<X\> before proceeding.

   6. Continue with the skill either way. The hook warns; it never blocks.

The script always exits 0. On unparseable stdin or a missing prompt field it stays silent rather than failing: this hook must never be able to block a prompt.

## Why a Command Hook

Until 0.6.1 this was a prompt-based hook: an LLM judge received the prompt text and was instructed to respond with exactly `{}` for non-BPE prompts.
In practice the judge would sometimes narrate its reasoning instead of returning bare `{}`, and the harness surfaced that malformed response as a prompt **block**.
The result was that ordinary conversational prompts in any bpe-enabled session were intermittently rejected with "Operation stopped by hook".
Detection of a `/bpe:` prefix is a regex, not a judgment call, so the hook is now a deterministic script: same injected context, no LLM in the loop, fail-open by construction.

## Why the Resolution Is Delegated

The script could read the profile files and `BPE_PROFILE` itself, but it cannot see the current session's model, which the mismatch comparison needs.
The session agent can: it reads both `bpe.local.md` locations, checks `BPE_PROFILE` through Bash, and knows its own model.
So the script handles detection, the fresh-install existence check, and name extraction, and the injected context delegates the precedence walk (see `references/model-profiles.md`, "Lookup Precedence") to the agent.

## Injected Context

The `additionalContext` template lives in `profile-check.py` as `ADDITIONAL_CONTEXT`, with `<name>` substituted at runtime.
Keep its wording in sync with the Behavior list above and with `references/model-profiles.md`.

## Testing

Hooks load at session start; editing this hook, its script, or its JSON requires exiting and restarting Claude Code before the change takes effect.

Static checks, no session reload needed:

```bash
# Non-BPE prompt: expect no output, exit 0.
printf '{"prompt":"hello there","cwd":"."}' | python3 bpe/hooks/profile-check.py

# BPE invocation with a profile file present: expect one JSON object on stdout.
printf '{"prompt":"/bpe:brainstorm","cwd":"<repo-with-.claude/bpe.local.md>"}' | python3 bpe/hooks/profile-check.py

# Garbage stdin: expect no output, exit 0.
echo "not json" | python3 bpe/hooks/profile-check.py

# /bpe: mentioned mid-prompt is NOT an invocation: expect no output, exit 0.
# Detection uses re.match, anchored to the start of the prompt.
printf '{"prompt":"explain what /bpe:brainstorm does before I run it","cwd":"."}' | python3 bpe/hooks/profile-check.py

# /bpe: at the start of a later line is also not an invocation: expect no output, exit 0.
printf '{"prompt":"first line\\nthen /bpe:plan on line two","cwd":"."}' | python3 bpe/hooks/profile-check.py

# Leading whitespace or newlines before /bpe: IS an invocation per the
# "after optional leading whitespace" rule: expect JSON when a profile file exists.
printf '{"prompt":"\\n  /bpe:goal full","cwd":"<repo-with-.claude/bpe.local.md>"}' | python3 bpe/hooks/profile-check.py
```

Also run `claude plugin validate ./bpe` and confirm exit 0, and inspect loaded hooks in-session with `/hooks`.

End-to-end check (requires a reloaded interactive session):

1. Write a `.claude/bpe.local.md` at the repo root pinning `brainstorm` to a model that differs from the session's (for example `claude-fable-5` while the session runs a Sonnet model).
2. Type `/bpe:brainstorm` and confirm the warning line appears in the transcript before the skill runs.
3. Delete the settings file, restart, type `/bpe:brainstorm` again, and confirm no warning appears.
