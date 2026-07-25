---
name: commit-message
description: Generate a commit message explaining what was changed and write it to commit-msg.md
argument-hint: optional focus hint (e.g. "the spec rewrite, not the formatting fixes")
allowed-tools: Bash(git:*), Read, Write
model: sonnet
disable-model-invocation: true
---

# Commit Message Command

Inspect the staged changes, write a commit message that captures the *why* of the change, and save it to `commit-msg.md` at the repo root for the user to feed into `git commit -F commit-msg.md`.

## Step 1: Inspect the Changes

Run these in parallel:

- `git status` — see all untracked files and modifications.
- `git diff --staged` — the exact set of changes that will be committed.
- `git diff` — what is modified but NOT yet staged. Do not narrate work that is in this diff but not the staged one.
- `git log --oneline -10` and `git log -3 --pretty=full` — match the repository's commit-message style and signing/conventions.

## Step 2: Identify the Why

Analyze the staged diff. Answer:

- What problem does this commit solve, or what capability does it add?
- Why is this approach the right one — only if non-obvious from the code.
- Was anything explicitly NOT changed that a reader might expect (deferred, out of scope, separate commit)?

If the user passed an argument, treat it as a focusing hint — bias the message toward the threads they named, not the full diff.

## Step 3: Compose the Message

Format:

- **Subject line:** imperative mood, ~50 characters target, ~72 characters hard cap. No trailing period.
- **Blank line.**
- **Body:** one or more paragraphs, wrapped at ~72 characters. Lead with the *why* — the problem solved or the capability added — then the *what* only when not obvious from the diff. Use bulleted lists where they actually help; flowing prose otherwise.

Avoid:

- Restating WHAT the diff already says when the WHY is obvious.
- Listing every file changed.
- Marketing language ("dramatically improves", "robust", "comprehensive", "powerful").
- Self-references like "this commit" or "this PR" — the message *is* the commit.
- Co-authored-by or AI-attribution trailers unless the user explicitly asks.
- Bumping versions, regenerating lockfiles, or any side action — this command only writes the message.

Match the repository's existing style observed in `git log` (subject-line case, conventional-commits prefix or not, trailers).

## Step 4: Write to commit-msg.md

Write the message to `commit-msg.md` at the repo root with the Write tool. The user's git workflow then runs:

```bash
git commit -S -F commit-msg.md
```

Do NOT execute the commit yourself — only write the file.

## Step 5: Gitignore Check

`commit-msg.md` is a working artifact and must never be tracked. Verify it is gitignored:

```bash
grep -F "commit-msg.md" .gitignore 2>/dev/null
```

If it is not present, append it to `.gitignore`. Tell the user when you do this.

## Step 6: Confirm

Display:

- The full message you wrote.
- The path to `commit-msg.md`.
- Whether you needed to add `commit-msg.md` to `.gitignore`.

Stop there. The user reviews the message, then runs the commit themselves.
