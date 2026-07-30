---
name: review
description: Render spec.md, plan.md, or todo.md as a fine-grained, decision-by-decision review page in your browser, then write the feedback as JSON for /bpe:apply-review to consume.
argument-hint: spec | plan | todo (defaults to most recent)
model: opus
disable-model-invocation: true
---

# Review Command

Generate a styled, interactive HTML view of `spec.md`, `plan.md`, or `todo.md` and serve it on a local HTTP server for human review. The artifact is broken into fine-grained **decision units**; the user marks each one Ship it / Close, but update / Completely off, do this instead / Absolutely reject and delete, leaves comments, and clicks Save. Feedback is written to JSON for `/bpe:apply-review` to consume.

The server runs in the background; this command does not block the Claude Code terminal. Continue working or wait; either is fine.

## Step 1: Determine the Artifact

Resolve the target artifact:

- If the user passed an argument, map it: `spec` → `spec.md`, `plan` → `plan.md`, `todo` → `todo.md`.
- If no argument was passed, pick the most recently modified of `spec.md`, `plan.md`, `todo.md` in the project root.
- If none exist, tell the user and stop.

## Step 2: Generate the HTML Artifact

Read the chosen markdown file and render it into the **fixed template below**. Your job is to fill the template with content, not to invent layout or typography; the design is owned by `review.css`, which the server inlines into the page. Emitting the semantic classes from the contract is what keeps every review page consistently readable. Do not restyle the chrome (`.review-toc`, `.review-section`, `.decision`, `.review-controls`) with your own CSS or Tailwind utilities; that reintroduces the per-run drift the template exists to prevent.

### Decompose into the smallest decidable units

A **decision unit** is the smallest thing the reviewer would want to accept, tweak, redirect, or kill *on its own*. One decision unit = one `<section>` with one set of decision buttons. **Do not bundle.** If an artifact heading like "Mode-by-mode changes" describes three modes, that is **three** decision units (one per mode), not one; bundling them forces a single verdict on independent ideas and is exactly what makes review painful.

Err aggressively toward more units. The test: *"Could the reviewer plausibly ship one part and say 'completely off, do this instead' to the next?"* If yes, split them. Every distinct proposal, design choice, open question, or assumption you'd want a ruling on becomes its own unit with its own buttons. Many small units is the goal, not a side effect.

Group related units under a **heading divider** (`.review-section--heading`), a context block with no buttons that introduces the cluster and gives the TOC a collapsible group. Standalone units that belong to no cluster sit at the top level of the TOC.

### Required structure (the server's injected JavaScript and `review.css` both depend on these)

The TOC is **exactly two levels**: top-level entries are either standalone decision units or cluster groups; cluster groups contain a nested `<ol>` of decision units, and that's it. No third level; `review.css` doesn't style `ol ol ol`, and a deeper structure tells the reviewer the wrong story about what's decidable. If a cluster needs sub-clusters, that's a sign you should hoist the sub-clusters up to top-level and let proximity in the doc carry the relationship.

The `<h2>` tag does double duty: it's the unit heading inside a decision unit *and* the cluster name inside a heading divider. The divider's CSS class is what changes the visual treatment; the tag stays `<h2>` either way.

Emit this skeleton. Repeat decision-unit `<section>`s freely; wrap clusters in a heading divider + a nested TOC `<ol>`:

```html
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Review: <!-- artifact filename --></title>
</head>
<body>
  <div class="reading-progress" aria-hidden="true"></div>
  <div class="review-layout">

    <aside class="review-toc">
      <div>
        <p class="review-toc__eyebrow">Reviewing</p>
        <h1 class="review-toc__title"><!-- e.g. spec.md --></h1>
        <p class="review-toc__progress"><span data-reviewed-count>0</span> of N units marked</p>
      </div>
      <nav class="review-toc__nav" aria-label="Sections">
        <ol>
          <!-- A standalone decision unit: flat top-level leaf -->
          <li>
            <a href="#section-1" data-toc-for="section-1">
              <span class="review-toc__dot" aria-hidden="true"></span>
              <span><!-- short unit label --></span>
            </a>
          </li>
          <!-- A cluster: group label linking to its heading divider, then nested units -->
          <li class="review-toc__group">
            <a href="#group-1" data-toc-for="group-1" class="review-toc__grouplink"><!-- e.g. Mode-by-mode changes --></a>
            <ol>
              <li><a href="#section-2" data-toc-for="section-2"><span class="review-toc__dot" aria-hidden="true"></span><span>Mode 1: Call Analysis</span></a></li>
              <li><a href="#section-3" data-toc-for="section-3"><span class="review-toc__dot" aria-hidden="true"></span><span>Mode 2: Workload Extraction</span></a></li>
            </ol>
          </li>
        </ol>
      </nav>
      <button id="bpe-save-btn" class="review-save">Save review</button>
    </aside>

    <main class="review-main">

      <!-- Decision unit -->
      <section id="section-1" class="review-section"
               data-section-id="section-1" data-section-heading="<!-- exact unit heading -->">
        <div class="review-section__body prose">
          <h2><!-- Unit heading --></h2>
          <!-- rendered content: paragraphs, lists, code, tables, diagrams -->
        </div>
        <footer class="review-controls">
          <fieldset class="decision">
            <legend class="sr-only">Decision for this unit</legend>
            <label class="decision__opt decision__opt--ship" title="Accept as-is. The unit is left untouched; no comment is saved.">
              <input type="radio" name="decision-section-1" data-section-decision="section-1" value="ship">
              <span>Ship it</span>
            </label>
            <label class="decision__opt decision__opt--update" title="Right direction. Your comment is applied as a tweak; the unit's structure is preserved.">
              <input type="radio" name="decision-section-1" data-section-decision="section-1" value="update">
              <span>Close, but update</span>
            </label>
            <label class="decision__opt decision__opt--redirect" title="Wrong approach. The unit is rewritten from your comment; its current content is discarded.">
              <input type="radio" name="decision-section-1" data-section-decision="section-1" value="redirect">
              <span>Completely off, do this instead</span>
            </label>
            <label class="decision__opt decision__opt--reject" title="Delete the unit entirely.">
              <input type="radio" name="decision-section-1" data-section-decision="section-1" value="reject">
              <span>Absolutely reject and delete</span>
            </label>
          </fieldset>
          <textarea class="review-comment" data-section-comment="section-1" rows="2"
                    placeholder="Comments for this unit. Required for Close, but update / Completely off / Absolutely reject. Ship it locks this box."></textarea>
        </footer>
      </section>

      <!-- Cluster: heading divider (no buttons) … -->
      <section id="group-1" class="review-section review-section--heading">
        <div class="review-section__body prose">
          <h2><!-- Cluster name, e.g. Mode-by-mode changes --></h2>
          <p><!-- one or two lines of context for the whole cluster --></p>
        </div>
      </section>
      <!-- … followed by its decision units (section-2, section-3, …), each exactly like section-1 above -->

      <!-- Always last: overall comment, no decision buttons -->
      <section class="review-section review-section--global">
        <div class="review-section__body prose">
          <h2>Overall</h2>
          <p>Anything that spans the whole document: overall direction, missing pieces, next steps.</p>
        </div>
        <footer class="review-controls">
          <textarea id="global-comment" class="review-comment" rows="3"
                    placeholder="Overall notes…"></textarea>
        </footer>
      </section>

    </main>
  </div>
</body>
</html>
```

Hard requirements (do not deviate; the save script and stylesheet key off them):

- **Decision unit:** `<section>` carries `id="section-N"` **and** `data-section-id="section-N"` (same value) plus `data-section-heading="<exact heading>"`, and ends with a `<footer class="review-controls">`. Its TOC link uses `data-toc-for="section-N"`.
- **Heading divider:** `<section id="group-N" class="review-section review-section--heading">` with body only: **no** `data-section-id` and **no** `<footer class="review-controls">`. The absence of `data-section-id` is what excludes the divider from the JS that counts decided units and collects feedback, so you don't need any extra opt-out class; just leave the attribute off. Its TOC group label uses `data-toc-for="group-N"` and class `review-toc__grouplink`.
- The four radios per unit carry `name="decision-section-N"`, `data-section-decision="section-N"`, and the four `value`s **exactly**: `ship`, `update`, `redirect`, `reject`, paired with classes `decision__opt--ship`, `--update`, `--redirect`, `--reject` and labels "Ship it", "Close, but update", "Completely off, do this instead", "Absolutely reject and delete".
- The per-unit comment is `<textarea class="review-comment" data-section-comment="section-N">`; the final global one is `<textarea id="global-comment" class="review-comment">`. The save script blocks the reviewer from saving if any unit decided as `update`, `redirect`, or `reject` has an empty comment; `apply-review` has nothing to act on without one, and we'd rather catch that at Save time than mid-apply. The inverse holds for `ship`: the injected script disables and clears the comment box while Ship it is selected, because `apply-review` leaves shipped units untouched and a comment there would never be read.
- The save button is `<button id="bpe-save-btn">`. In the progress line, replace "N" with the count of **decision units** (sections that have buttons; exclude heading dividers and the Overall block).

**Do NOT generate the save fetch logic, the scroll-spy, the progress bar, or the decision-state coloring.** The server injects standardized JavaScript that wires `#bpe-save-btn` to collect feedback and POST to `/save`, highlights the active TOC entry on scroll, drives `.reading-progress`, stamps `data-decision` onto units and TOC dots as the reviewer chooses, and locks a unit's comment box while Ship it is selected. Generating your own will conflict.

### Filling in the content

Render the markdown faithfully inside each `.prose` block: headings (`<h3>`/`<h4>` for sub-points; the `<h2>` is the unit heading), paragraphs, lists, code, tables. The stylesheet handles all spacing and type; don't add inline styles or Tailwind utilities to prose elements.

- **Scannability:** keep paragraphs short, lead with the key point, use lists and `<strong>` for keywords; reviewers scan before they read.
- **`spec.md`:** each goal, non-goal, constraint, and open question is its own decision unit where it warrants a ruling; wrap supporting context in `<div class="callout callout--goal">` (or `--warn` / `--danger`) with a `<span class="callout__label">Goals</span>` header. Cluster them under heading dividers (Goals, Constraints, Open questions).
- **`plan.md`:** **each step is its own decision unit.** Tag its TDD phase with `<span class="phase-tag phase-tag--red">RED</span>` (or `--green` / `--refactor`), surface affected file paths in `<code>`, and cluster steps under a heading divider per milestone/phase.
- **`todo.md`:** group tasks under a heading divider per section; render `- [x]` / `- [ ]` as real `<input type="checkbox">` (checked when `[x]`). A task list a reviewer only checks off can stay one unit per group; if the reviewer should *rule on* individual tasks, split them into units. Do NOT add `disabled`; checkboxes must be clickable.

**Mermaid diagrams:** emit any diagram as a fenced code block with the `mermaid` language tag (`<pre><code class="language-mermaid">…</code></pre>`) or a `<div class="mermaid">…</div>`. The server converts and renders them with the theme matched to light/dark. Do not inline the Mermaid script.

**Tailwind** is still injected and available for incidental layout *inside* content (e.g. a two-up grid of examples), but `review.css` owns the page chrome and prose, so reach for the semantic classes first and use Tailwind only where the content genuinely needs ad-hoc layout.

## Step 3: Write the HTML and Start the Server

Generate a unique path for the HTML file. The `-u` flag makes `mktemp` print a name **without creating the file**; this matters because the Write tool refuses to overwrite an existing file it has not Read, so a pre-created empty file makes the very next Write call fail.

```bash
mktemp -u -t bpe-review-XXXXXX.html
```

Then create the file at that path with the Write tool.

Compute the feedback path by replacing `.html` with `-feedback.json` on the same path.

Start the server in the background. Use `run_in_background: true` so the terminal returns immediately:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/review-server.py <html-path> <feedback-path> <source-markdown-path>
```

If the user is on a Tailscale-up machine but explicitly wants the page reachable only locally (e.g. they're reviewing in the browser on the same box), pass `--bind 127.0.0.1`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/review-server.py <html-path> <feedback-path> <source-markdown-path> --bind 127.0.0.1
```

The script:

- Kills any prior `/bpe:review` server via the PID file at `/tmp/bpe-review-server.pid`.
- Binds to the local Tailscale IPv4 if `tailscale` is installed and the daemon is up, unless `--bind` overrides it; otherwise falls back to `127.0.0.1`. Picks a random free port either way. Tailscale binding lets the user review on a phone or second laptop without extra configuration.
- Writes the URL to `/tmp/bpe-review-server.url` for Step 4 to read, then removes the file on clean shutdown.
- Inlines `review.css` (the authoritative design layer), Tailwind, and Mermaid into the page `<head>`.
- Injects the save, scroll-spy, progress-bar, and decision-sync JavaScript into the HTML.
- Auto-opens the URL in the user's default browser **only** when bound to `127.0.0.1`; on a tailnet binding the browser is more likely to live on a different device, so we print the URL instead of guessing.
- Validates incoming feedback against the schema in `/bpe:apply-review` and rejects malformed payloads with HTTP 400.
- Writes feedback JSON on `POST /save`, then exits.

## Step 4: Confirm

Read the server URL from `/tmp/bpe-review-server.url` (preferred; survives the background process's stdout going wherever it goes) or, failing that, from the background process's stdout where the script prints `BPE review server: http://…:PORT/`. Then tell the user:

- The server URL (clickable).
- The artifact being reviewed.
- That they should mark each unit, leave comments for anything other than "Ship it", then click Save. The Save button blocks until every `update` / `redirect` / `reject` unit has a comment; those units get highlighted so the reviewer can jump to them.
- When done, run `/bpe:apply-review` to load the feedback and apply changes.
- If they walk away or close the browser without saving, just re-run `/bpe:review`; it kills the prior server cleanly.
