# Issue Format

The format for a GitHub issue that an agent can pick up cold.
An agent reading a conforming issue can start work without asking what is wanted or how completion is judged.
`/bpe:new-issue` writes issues in this format, `/bpe:gh-issue` reads them and checks them against it, and `.github/ISSUE_TEMPLATE/agent-ready.md` carries the same headings.
A test keeps the template and this file in step.

## Title

The title is imperative: "Add a retry limit to the review server", not "Retry limit" or "Review server needs retries".

## Sections

The sections, in order, with the exact heading each one uses:

1. What Is Wanted (required)
2. What We Already Know (required)
3. Prior Research and Thoughts (optional)
4. Changes, File by File (optional)
5. Out of Scope (optional)
6. Acceptance Criteria (required)

Each heading is a `## ` heading in the issue body.
An optional section that has nothing to say is left out, never filled with "none".
A present section keeps its position in the list above.

### What Is Wanted

The change, stated as an outcome.
One short paragraph a reader can act on.

### What We Already Know

Facts in hand: the current behavior, the area of code, the error text, the version, what was already tried.
Reproduction steps for a bug go here.

### Prior Research and Thoughts

Links, earlier attempts, and design ideas the author has not settled.
Marked as thoughts, not requirements.

### Changes, File by File

The files expected to change and what changes in each.
Leave it out when the author does not know yet.

### Out of Scope

What this issue does not cover, so the agent does not wander.

### Acceptance Criteria

A checklist of observable results.
Each item can be checked true or false by running something or reading something.

## Example

```markdown
Add a retry limit to the review server

## What Is Wanted

The review server stops after three failed port binds instead of looping.

## What We Already Know

`bpe/scripts/review-server.py` counts down to the next port on a bind failure.
With every port busy it loops without a limit.

## Out of Scope

Choosing the port range.

## Acceptance Criteria

- [ ] A bind failure on three ports in a row exits with code 1.
- [ ] The error message names the ports tried.
- [ ] A test covers the exit.
```
