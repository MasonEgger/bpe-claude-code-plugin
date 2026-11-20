#!/usr/bin/env python3
"""UserPromptSubmit hook: model-profile check for /bpe:<name> invocations.

Deterministic replacement for the prompt-based hook that shipped with 0.6.0.
Behavior and rationale: hooks/profile-check.md.
Resolution semantics: references/model-profiles.md.

Exit contract: always exit 0 with either no output (non-BPE prompt, or no
profile file exists) or a single hookSpecificOutput JSON object on stdout.
This hook never blocks a prompt; on any unexpected input it stays silent.
"""

import json
import os
import re
import sys

BPE_INVOCATION = re.compile(r"\s*/bpe:([A-Za-z0-9-]+)")

# Injected verbatim except for <name> substitution. Must stay in sync with
# the "Injected Context" section of hooks/profile-check.md.
ADDITIONAL_CONTEXT = (
    "Model-profile check for bpe skill '<name>'. Before executing the skill, "
    "resolve its profile model per the bpe plugin's references/model-profiles.md: "
    "(1) If neither .claude/bpe.local.md at the repo root nor ~/.claude/bpe.local.md "
    "exists, skip this check silently; frontmatter defaults apply. "
    "(2) Resolve the active profile name once: the BPE_PROFILE environment variable "
    "when set (check it with a Bash echo of BPE_PROFILE), else active_profile in the "
    "per-project file, else in the user-global file. "
    "(3) Look up skills.<name> under that profile in the per-project file, falling "
    "through to the user-global file (shadowing is key-level). If no entry exists, "
    "skip silently; the skill's frontmatter model applies. "
    "(4) Compare the resolved value to the current session model; a family alias "
    "(opus, sonnet, haiku) matches any session model of that family. "
    "(5) Only on mismatch, state before proceeding: Note: skill <name> profile "
    "expects model <X>; current session is <Y>. Consider /model <X> before "
    "proceeding. Then continue with the skill either way."
)


def profile_file_exists(cwd: str) -> bool:
    project_exists = bool(cwd) and os.path.isfile(os.path.join(cwd, ".claude", "bpe.local.md"))
    user_global = os.path.expanduser("~/.claude/bpe.local.md")
    return project_exists or os.path.isfile(user_global)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    match = BPE_INVOCATION.match(payload.get("prompt") or "")
    if not match:
        return
    if not profile_file_exists(payload.get("cwd") or ""):
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": ADDITIONAL_CONTEXT.replace("<name>", match.group(1)),
                }
            }
        )
    )


if __name__ == "__main__":
    main()
