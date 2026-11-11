#!/usr/bin/env python3
"""PostToolUse hook: report the parent session's context fill after an Agent or SendMessage call.

Behavior and rationale: hooks/context-check.md.

Input: the hook JSON on stdin. Only `transcript_path` is read. The other
common fields (`tool_name`, `tool_input`, `tool_result`) are ignored, so the
script does not depend on which tool matched.

Output: one hookSpecificOutput JSON object on stdout carrying
`additionalContext` of the form `Context: NN% of <window>`, where NN is a
rounded integer and <window> is 200000 or 1000000.

Exit contract: always exit 0. On a missing or unreadable transcript, a missing
field, malformed JSON, or any other exception, print nothing. This hook
reports only; it never blocks the tool call. Annotations are deferred
(`from __future__ import annotations`) so the script imports on Python 3.9.
"""

from __future__ import annotations

import json
import sys

DEFAULT_WINDOW = 200_000
LARGE_WINDOW = 1_000_000
LARGE_WINDOW_MARKER = "[1m]"
TOKEN_FIELDS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")


def last_assistant_entry(path: str) -> dict[str, object] | None:
    """Find the last transcript entry that is an assistant turn with usage.

    Args:
        path: Filesystem path to a JSONL transcript.

    Returns:
        The last parsed entry whose `type` is `assistant`, is not a sidechain
        (subagent) entry, and whose `message` holds a `usage` object, or None when there is no such entry.
        Lines that are not valid JSON are skipped.
    """
    found: dict[str, object] | None = None
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            if not isinstance(entry, dict) or entry.get("type") != "assistant":
                continue
            if entry.get("isSidechain") is True:
                continue
            message = entry.get("message")
            if isinstance(message, dict) and isinstance(message.get("usage"), dict):
                found = entry
    return found


def context_reading(entry: dict[str, object]) -> str:
    """Build the `Context: NN% of <window>` line for a transcript entry.

    Args:
        entry: An assistant entry from `last_assistant_entry`.

    Returns:
        The reading, for example `Context: 95% of 200000`.

    Raises:
        KeyError: When the entry lacks a usable message or usage object.
        TypeError: When a token field is not numeric.
    """
    message = entry["message"]
    if not isinstance(message, dict) or not isinstance(message.get("usage"), dict):
        raise KeyError("usage")
    usage = message["usage"]
    total = sum(usage.get(name) or 0 for name in TOKEN_FIELDS)
    model = entry.get("requestedModel")
    large = isinstance(model, str) and LARGE_WINDOW_MARKER in model
    window = LARGE_WINDOW if large else DEFAULT_WINDOW
    return f"Context: {round(total * 100 / window)}% of {window}"


def main() -> None:
    """Read the hook JSON from stdin and print the context reading, or nothing."""
    try:
        payload = json.load(sys.stdin)
        entry = last_assistant_entry(payload["transcript_path"])
        if entry is None:
            return
        reading = context_reading(entry)
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": reading,
            }
        }))
    except Exception:  # fail open on any input or output problem
        return


if __name__ == "__main__":
    main()
