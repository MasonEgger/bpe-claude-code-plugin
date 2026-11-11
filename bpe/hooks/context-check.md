# Context-Check Hook

A `PostToolUse` command hook, matcher `Agent|SendMessage`, that tells the `/bpe:goal` orchestrator how full its own context window is.
The hook body is `hooks/context-check.py`; this file documents its behavior.
The registered configuration lives in `hooks/hooks.json`, next to the profile-check registration.
Claude Code auto-discovers that path, so `.claude-plugin/plugin.json` has no `hooks` field; naming the file there would register it twice.
The command runs the script via `${CLAUDE_PLUGIN_ROOT}`.
The orchestrator playbook (`references/validator-protocol.md`, `### Checkpoint`) acts on the reading.

## What It Reports

After every `Agent` or `SendMessage` tool call the script injects one line as `additionalContext`:

```text
Context: 95% of 200000
```

Reading it:

1. The hook input carries `transcript_path`, the parent session's JSONL transcript.
   The other common fields (`tool_name`, `tool_input`, `tool_result`) are ignored.
2. The script finds the last entry with `type == "assistant"` and a `message.usage` object, skipping entries marked `isSidechain` so a subagent's usage never stands in for the parent's.
3. It sums `input_tokens`, `cache_read_input_tokens`, and `cache_creation_input_tokens` from that usage.
   Output tokens are not part of the next request's input, so they are left out.
4. The window is 1,000,000 when that entry's `requestedModel` contains `[1m]`, else 200,000.
5. NN is the sum over the window, as a rounded integer percent.

The output shape is `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "..."}}`, the shape the hook-development skill documents for context injection.

## When It Fires

The matcher is `Agent|SendMessage`.
`Agent` carries the cold implement, validator, and fallback dispatches.
`SendMessage` carries the warm fix and finalize continuations, which is where the 90 percent check after a finalize reads its line.
`PostToolUse` fires after a tool call returns.
The last assistant entry in the transcript is the request that issued the call, so the reading covers the parent context up to that request and excludes the report the call returned.
It therefore trails by one report even for a synchronous dispatch.
Agent dispatches in current Claude Code sessions can also return asynchronously.
In that case the hook may fire when the dispatch launches, not when it completes, and the reading lags by one more dispatch.
This file does not claim which of the two a given session uses; the 5-point gap between the two checkpoint thresholds (90 after a finalize, 95 after any dispatch) absorbs the lag.
Fire timing was not established by running a live session; verify with `claude --debug` if the distinction matters.

## Fail-Open Contract

The script always exits 0 and never blocks the tool call.
A missing hook field, a missing or unreadable transcript, malformed JSON, a transcript with no assistant usage entry, or any other exception produces no output.
The script defers annotation evaluation (`from __future__ import annotations`) so it also imports on Python 3.9; the contract holds there too.
The playbook reads no output as no reading, and no reading means no checkpoint.

## Testing

Hooks load at session start; editing this hook, its script, or `hooks/hooks.json` requires restarting Claude Code before the change takes effect.

Static checks, no session reload needed (write the synthetic transcript to a scratch file; do not point the script at a real transcript):

```bash
# Last assistant entry: 10,000 input + 150,000 cache_read + 30,000 cache_creation,
# requestedModel claude-opus-5-5: expect "Context: 95% of 200000".
echo '{"transcript_path":"<scratch-file>","tool_name":"Agent"}' | python3 bpe/hooks/context-check.py

# Same usage with requestedModel claude-opus-5-5[1m]: expect "Context: 19% of 1000000".

# Missing transcript: expect no output, exit 0.
echo '{"transcript_path":"/nonexistent"}' | python3 bpe/hooks/context-check.py; echo "exit=$?"
```

Also run `claude plugin validate ./bpe` and confirm exit 0, and inspect loaded hooks in-session with `/hooks`.
