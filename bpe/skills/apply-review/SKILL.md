---
name: apply-review
description: Load saved review feedback from /bpe:review and apply changes to the reviewed artifact
argument-hint: "[feedback-json-path] (optional; defaults to the most recent /tmp/bpe-review-*-feedback.json)"
model: opus
disable-model-invocation: true
---

# Apply Review Command

Consume the feedback JSON written by `/bpe:review` and apply the user's annotations to the reviewed markdown artifact. The user has already reviewed in the browser and clicked Save — this command surfaces their decisions and applies the changes after explicit confirmation.

## Step 1: Find the Feedback File

If the user passed a feedback path as an argument, use that file. This is the escape hatch for replaying an older review or for the case where the user ran two reviews in parallel and the wrong one is "most recent."

Otherwise, find the most recent feedback JSON in the temp directory (`/bpe:review` generates the path with `mktemp`, which honors `$TMPDIR`):

```bash
ls -t "${TMPDIR:-/tmp}"/bpe-review-*-feedback.json 2>/dev/null | head -1
```

If none exists, tell the user to run `/bpe:review` first and stop.

If the chosen file's `saved_at` timestamp is more than 24 hours old, surface that to the user and ask whether they meant to apply this older feedback or run `/bpe:review` again.

## Step 2: Load and Summarize

Read the feedback JSON. Expected shape:

```json
{
  "sections": [
    {
      "id": "section-N",
      "heading": "<heading text>",
      "decision": "ship" | "update" | "redirect" | "reject" | "unset",
      "comment": "<free-text feedback>"
    }
  ],
  "global_comment": "<free-text>",
  "artifact_path": "<absolute path to the reviewed markdown file>",
  "saved_at": "<ISO timestamp>"
}
```

Each entry is one **decision unit** — the review is intentionally fine-grained, so expect many entries. Display a summary that **front-loads the destructive decisions**, since those are what the user most needs to verify before saying yes in Step 3:

- One-line counts header: `N reject, N redirect, N update, N unset, N ship`.
- Then group the non-`ship` entries under sub-headings, in **this exact order** (most-destructive first):
  1. **Absolutely reject and delete** (`reject`) — list each unit's heading + comment. These are about to be removed; surface them first so the user can catch a mistake before authorizing.
  2. **Completely off, do this instead** (`redirect`) — list each unit's heading + comment. These are full rewrites driven by the comment.
  3. **Close, but update** (`update`) — list each unit's heading + comment. These are tweaks.
  4. **No decision recorded** (`unset`) — list any units that have a comment (those'll be treated as `update`) and any that don't (those'll be left alone).
- The global comment, if non-empty.
- The artifact path that will be modified.

`ship` units don't need to appear in the summary — they're the silent majority by design and listing them adds noise. One exception: a `ship` entry with a non-empty comment. The review page locks the comment box while Ship it is selected, so this only appears in feedback saved by an older page — but when it does, list it under a **Ship, with comment** sub-heading rather than dropping the comment silently.

## Step 3: Confirm Before Mutating

Ask the user explicitly: "Apply these changes to `<artifact_path>`?" Do not proceed without a clear yes.

How to interpret each decision (increasing severity):

- **ship** ("Ship it") — leave the unit unchanged. If the entry somehow carries a non-empty comment (older feedback files only; the current page prevents it), ask the user whether to treat it as an `update` directive or ignore it — never discard it without surfacing it.
- **update** ("Close, but update") — the direction is right; apply the comment as a directive, rewriting the unit to incorporate the feedback while preserving its structure and surrounding context.
- **redirect** ("Completely off, do this instead") — the approach is wrong. Discard the current content of the unit and replace it with what the comment describes. The comment is the new direction, not a tweak — treat it as a rewrite-from-intent, not an edit. If the comment is too thin to act on, ask the user before rewriting.
- **reject** ("Absolutely reject and delete") — remove the unit entirely. This is destructive and explicit: the user wants it gone, not redone. Still confirm the specific deletions in Step 3 before cutting, and watch for ripple effects (references elsewhere in the artifact to the deleted unit).
- **unset** — no decision recorded. If the unit has a comment, treat it as **update**; otherwise leave it alone and note that it had no decision.

Apply the **global_comment** as a holistic directive across the artifact (e.g. "tighten language", "add a glossary", "split into two files").

## Step 4: Apply the Changes

Read the artifact via the Read tool. Make targeted edits via the Edit tool — one Edit per affected section. Do not rewrite the whole file unless the global comment explicitly requests it. Preserve formatting, list styles, and unrelated sections exactly.

## Step 5: Confirm

After applying, show the user:

- A brief diff summary (which sections changed, one line each).
- Any feedback that could not be applied automatically and why.
- Suggested next step: `/bpe:review` again to re-review, `/bpe:plan` to regenerate downstream artifacts (if `spec.md` was edited), or continue.
