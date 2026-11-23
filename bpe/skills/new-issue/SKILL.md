---
name: new-issue
description: This skill should be used when the user asks to "file an issue", "write up an issue", or "open a GitHub issue for this". Drafts a GitHub issue in the agent-ready format and posts it only after confirmation.
argument-hint: "[what the issue is about]"
allowed-tools: Bash(gh:*), Bash(python3:*), Bash(mktemp:*), Read, Write
model: sonnet
disable-model-invocation: true
---

# New Issue Command

Drafts a GitHub issue in the format `references/issue-format.md` defines, shows the full draft, and posts it with `gh issue create` only after an explicit yes.
This is the writing side; `/bpe:gh-issue` is the reading side that fetches an issue and routes it.
It never posts without confirmation.

1. Read `${CLAUDE_PLUGIN_ROOT}/references/issue-format.md` for the sections, their order, and which are required.
2. Gather the content from $ARGUMENTS and the conversation so far.
   - Fill What Is Wanted, What We Already Know, and Acceptance Criteria.
   - Ask one question at a time, and only for a required section you cannot fill.
   - Add an optional section only when the conversation supplies real content for it.
3. Write an imperative title.
4. Build one JSON object with a `title` string and a `sections` map of exact heading to body, and render it:
   Write the JSON to a `mktemp` path outside the repo, so it never shows up as an untracked file, then run:
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/render-artifact.py issue < <json-file>`
   A nonzero exit names the missing or unknown section; fix the input and render again.
5. Show the full rendered draft, title included, and ask whether to post it.
6. On an explicit yes:
   - Make a temp path with `mktemp -u`, write the body (everything after the title line) to it, and run `gh issue create --title "<title>" --body-file <path>`.
   - Print the issue URL.
7. On anything other than a yes, post nothing.
   Offer to revise the draft instead.
