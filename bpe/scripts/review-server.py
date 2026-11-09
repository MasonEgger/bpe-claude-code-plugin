#!/usr/bin/env python3
# ABOUTME: Local HTTP server for /bpe:review.
# Serves a generated HTML review artifact, accepts feedback JSON via POST /save, then exits.

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SHUTDOWN_DELAY_SECONDS = 5  # give the "Saved" page time to render before quitting
TAILSCALE_PROBE_TIMEOUT_SECONDS = 2
SCRIPT_DIR = Path(__file__).resolve().parent
STYLESHEET = SCRIPT_DIR / "review.css"
VALID_DECISIONS = frozenset({"ship", "update", "redirect", "reject", "unset"})


def pick_bind_address() -> str:
    """Return the local Tailscale IPv4 if the daemon is up, otherwise localhost.

    Reviewing on a phone or another laptop is the common case — when Tailscale
    is active, bind to the tailnet IP so other devices on the tailnet can reach
    the review page directly. Falls back silently to 127.0.0.1 if Tailscale is
    not installed, the daemon is down, or the device is logged out.
    """
    if shutil.which("tailscale") is None:
        return "127.0.0.1"
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=TAILSCALE_PROBE_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return "127.0.0.1"
    if result.returncode != 0:
        return "127.0.0.1"
    for line in result.stdout.splitlines():
        ip = line.strip()
        if ip:
            return ip
    return "127.0.0.1"


def state_paths(artifact: Path) -> tuple[Path, Path]:
    """Return the (pid_file, url_file) paths for a given review artifact.

    The files are keyed by the first 8 hex of the sha256 of the artifact's
    absolute real path, so concurrent reviews of different files get their own
    PID and URL files instead of fighting over one machine-wide pair. A second
    review of the same file still resolves to the same key, so restarting a
    review replaces only its own server. The /bpe:review skill recomputes this
    key to read the URL file for the server it just started; keep the "/tmp"
    literal and the realpath hashing in sync with its Step 4 shell.

    Args:
        artifact: The source-markdown path passed on argv.

    Returns:
        The PID file path and the URL file path for this artifact.
    """
    key = hashlib.sha256(os.path.realpath(artifact).encode()).hexdigest()[:8]
    return Path(f"/tmp/bpe-review-{key}.pid"), Path(f"/tmp/bpe-review-{key}.url")


def kill_existing_server(pid_file: Path) -> None:
    """Terminate the server recorded in pid_file and remove the file.

    Reads the PID from pid_file, sends it SIGTERM, then deletes the file so a
    stale entry never blocks a new server for the same artifact. SIGTERM
    delivery errors (a malformed file, a process that already exited, or a
    permission failure) are swallowed; the file is removed either way.

    Args:
        pid_file: Path to the PID file for this artifact's review server.
    """
    if not pid_file.exists():
        return
    try:
        old_pid = int(pid_file.read_text().strip())
        os.kill(old_pid, 15)
    except (ValueError, ProcessLookupError, PermissionError):
        pass
    pid_file.unlink(missing_ok=True)


def write_pid_file(pid_file: Path) -> None:
    """Write this process's PID to pid_file.

    Args:
        pid_file: Path to the PID file for this artifact's review server.
    """
    pid_file.write_text(str(os.getpid()))


def validate_feedback(payload: object) -> str | None:
    """Return a human-readable error string if the payload doesn't match the
    /bpe:apply-review contract, or None if it does.

    Defense-in-depth: the injected client JS always produces a valid shape, but
    /save accepts arbitrary POSTs, so this stops a malformed payload (or one
    crafted by a third party) from landing in the feedback file where
    apply-review would then trip over it.
    """
    if not isinstance(payload, dict):
        return "Payload must be a JSON object."
    sections = payload.get("sections")
    if not isinstance(sections, list):
        return "Payload.sections must be a list."
    for i, sec in enumerate(sections):
        if not isinstance(sec, dict):
            return f"sections[{i}] must be an object."
        for field in ("id", "heading", "decision", "comment"):
            if field not in sec:
                return f"sections[{i}] missing field {field!r}."
            if not isinstance(sec[field], str):
                return f"sections[{i}].{field} must be a string."
        if sec["decision"] not in VALID_DECISIONS:
            return (
                f"sections[{i}].decision must be one of "
                f"{sorted(VALID_DECISIONS)!r}; got {sec['decision']!r}."
            )
    gc = payload.get("global_comment", "")
    if not isinstance(gc, str):
        return "Payload.global_comment must be a string."
    return None


def make_handler(
    html_bytes: bytes,
    feedback_path: Path,
    source_artifact: str,
    shutdown_event: threading.Event,
) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_: object) -> None:
            return  # quiet

        def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler API)
            if self.path in ("/", "/index.html"):
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(html_bytes)
                return
            self.send_response(404)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/save":
                self.send_response(404)
                self.end_headers()
                return
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(b"Invalid JSON: body could not be parsed.")
                return
            error = validate_feedback(payload)
            if error is not None:
                self.send_response(400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write(error.encode("utf-8"))
                return
            payload["artifact_path"] = source_artifact
            payload["saved_at"] = datetime.now().isoformat()
            feedback_path.write_text(json.dumps(payload, indent=2))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<!doctype html><meta charset=utf-8>"
                b"<title>Saved</title>"
                b"<style>body{font-family:system-ui;max-width:40rem;margin:4rem auto;padding:0 1rem;line-height:1.5}</style>"
                b"<h1>Saved</h1>"
                b"<p>Feedback recorded. You can close this tab.</p>"
                b"<p>Back in Claude Code, run <code>/bpe:apply-review</code> to load and apply your feedback.</p>"
            )
            threading.Timer(SHUTDOWN_DELAY_SECONDS, shutdown_event.set).start()

    return Handler


HEAD_ASSETS = """
<script src="https://cdn.tailwindcss.com"></script>
<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
  const dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  mermaid.initialize({ startOnLoad: false, theme: dark ? 'dark' : 'default', securityLevel: 'loose' });
  window.__bpeMermaid = mermaid;
</script>
"""


def load_stylesheet() -> str:
    """Return review.css wrapped in a <style> tag, or empty if missing.

    Inlining the stylesheet keeps the served page fully self-contained — the
    browser receives one HTML document with all design rules embedded, no
    external CSS request. review.css is the authoritative design layer; it
    loads after Tailwind so its semantic classes win the cascade.
    """
    if not STYLESHEET.exists():
        return ""
    return f"\n<style>\n{STYLESHEET.read_text(encoding='utf-8')}\n</style>\n"

RUNTIME_HELPERS = """
<script>
(function() {
  function enableCheckboxes() {
    document.querySelectorAll('input[type="checkbox"][disabled]').forEach(function(cb) {
      cb.removeAttribute('disabled');
      cb.classList.add('cursor-pointer');
    });
  }
  function convertMermaidBlocks() {
    var blocks = document.querySelectorAll('pre > code.language-mermaid, pre > code.lang-mermaid');
    blocks.forEach(function(code) {
      var pre = code.parentElement;
      var container = document.createElement('div');
      container.className = 'mermaid';
      container.textContent = code.textContent;
      pre.parentNode.replaceChild(container, pre);
    });
  }
  function renderMermaid() {
    if (!window.__bpeMermaid) {
      setTimeout(renderMermaid, 50);
      return;
    }
    var nodes = document.querySelectorAll('.mermaid:not([data-processed="true"])');
    if (nodes.length === 0) return;
    window.__bpeMermaid.run({ nodes: nodes }).catch(function(err) {
      console.error('Mermaid render failed:', err);
    });
  }
  function setupScrollSpy() {
    var sections = Array.prototype.slice.call(document.querySelectorAll('.review-section[id]'));
    if (sections.length === 0) return;
    var visible = {};
    function highlight() {
      var active = null;
      sections.forEach(function(sec) {
        if (visible[sec.id]) {
          if (!active || sec.getBoundingClientRect().top < active.getBoundingClientRect().top) {
            active = sec;
          }
        }
      });
      if (!active) return;
      document.querySelectorAll('[data-toc-for].is-active').forEach(function(a) {
        a.classList.remove('is-active');
      });
      var link = document.querySelector('[data-toc-for="' + active.id + '"]');
      if (link) link.classList.add('is-active');
    }
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) { visible[entry.target.id] = entry.isIntersecting; });
      highlight();
    }, { rootMargin: '-10% 0px -80% 0px', threshold: 0 });
    sections.forEach(function(sec) { observer.observe(sec); });
  }
  function setupProgress() {
    var bar = document.querySelector('.reading-progress');
    if (!bar) return;
    function update() {
      var doc = document.documentElement;
      var max = doc.scrollHeight - doc.clientHeight;
      var ratio = max > 0 ? Math.min(1, doc.scrollTop / max) : 0;
      bar.style.transform = 'scaleX(' + ratio + ')';
    }
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    update();
  }
  function setupDecisionSync() {
    var radios = document.querySelectorAll('input[data-section-decision]');
    function sync() {
      var decided = 0;
      var seen = {};
      document.querySelectorAll('.review-section[data-section-id]').forEach(function(sec) {
        var id = sec.getAttribute('data-section-id');
        var checked = document.querySelector('[data-section-decision="' + id + '"]:checked');
        var link = document.querySelector('[data-toc-for="' + id + '"]');
        var comment = document.querySelector('[data-section-comment="' + id + '"]');
        if (comment) {
          // A comment on "Ship it" is never read (apply-review leaves shipped
          // units untouched), so lock and clear the box rather than collecting
          // text that would silently vanish.
          var shipped = checked !== null && checked.value === 'ship';
          comment.disabled = shipped;
          if (shipped) comment.value = '';
        }
        if (checked) {
          sec.setAttribute('data-decision', checked.value);
          if (link) link.setAttribute('data-decision', checked.value);
          if (!seen[id]) { decided++; seen[id] = true; }
        } else {
          sec.removeAttribute('data-decision');
          if (link) link.removeAttribute('data-decision');
        }
      });
      var counter = document.querySelector('[data-reviewed-count]');
      if (counter) counter.textContent = String(decided);
    }
    radios.forEach(function(r) { r.addEventListener('change', sync); });
    sync();
  }
  function init() {
    enableCheckboxes();
    convertMermaidBlocks();
    renderMermaid();
    setupScrollSpy();
    setupProgress();
    setupDecisionSync();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
</script>
"""


def inject_head_assets(html_text: str) -> str:
    """Inject Tailwind, Mermaid, and the inlined review.css into <head>.

    Tailwind first, then review.css, so the authoritative stylesheet wins the
    cascade for the review chrome while Tailwind remains available for any
    incidental layout in the rendered content.
    """
    assets = HEAD_ASSETS + load_stylesheet()
    if "</head>" in html_text:
        return html_text.replace("</head>", assets + "</head>", 1)
    if "<body" in html_text:
        return html_text.replace("<body", assets + "<body", 1)
    return assets + html_text


def inject_runtime_helpers(html_text: str) -> str:
    """Inject checkbox enabler + Mermaid block converter before </body>."""
    if "</body>" in html_text:
        return html_text.replace("</body>", RUNTIME_HELPERS + "</body>", 1)
    return html_text + RUNTIME_HELPERS


def inject_save_script(html_text: str, save_url: str) -> str:
    # 'ship' is "leave it alone" and 'unset' is "no decision yet" — neither
    # gives apply-review anything to act on, so they don't need a comment.
    # update/redirect/reject all need text the consumer can act on; we block
    # Save until those have comments so /bpe:apply-review never runs on
    # directionless feedback.
    script = f"""
<script>
(function() {{
  var DECISIONS_REQUIRING_COMMENT = {{ 'update': true, 'redirect': true, 'reject': true }};
  var SAVE_LABEL = 'Save review';

  function collectFeedback() {{
    var sections = [];
    document.querySelectorAll('[data-section-id]').forEach(function(el) {{
      var id = el.getAttribute('data-section-id');
      var heading = el.getAttribute('data-section-heading') || '';
      var commentEl = document.querySelector('[data-section-comment="' + id + '"]');
      var decisionEl = document.querySelector('[data-section-decision="' + id + '"]:checked');
      sections.push({{
        id: id,
        heading: heading,
        comment: commentEl ? commentEl.value : '',
        decision: decisionEl ? decisionEl.value : 'unset'
      }});
    }});
    var globalEl = document.getElementById('global-comment');
    return {{
      sections: sections,
      global_comment: globalEl ? globalEl.value : ''
    }};
  }}

  function findMissingComments() {{
    var missing = [];
    document.querySelectorAll('.review-section[data-section-id]').forEach(function(sec) {{
      var id = sec.getAttribute('data-section-id');
      var decisionEl = document.querySelector('[data-section-decision="' + id + '"]:checked');
      if (!decisionEl) return;
      if (!DECISIONS_REQUIRING_COMMENT[decisionEl.value]) return;
      var commentEl = document.querySelector('[data-section-comment="' + id + '"]');
      var text = commentEl ? commentEl.value.trim() : '';
      if (text === '') {{
        missing.push({{ section: sec, comment: commentEl, heading: sec.getAttribute('data-section-heading') || id }});
      }}
    }});
    return missing;
  }}

  function markMissing(missing) {{
    // Clear any previous marks first so units that just got a comment lose theirs.
    document.querySelectorAll('.review-section[data-comment-missing]').forEach(function(s) {{
      s.removeAttribute('data-comment-missing');
    }});
    missing.forEach(function(m) {{
      m.section.setAttribute('data-comment-missing', 'true');
    }});
  }}

  function bindCommentClearers() {{
    // Clear the missing mark on a unit the moment its comment becomes non-empty,
    // so the reviewer sees the red highlight disappear as they type.
    document.querySelectorAll('.review-comment[data-section-comment]').forEach(function(t) {{
      t.addEventListener('input', function() {{
        var id = t.getAttribute('data-section-comment');
        var sec = document.querySelector('.review-section[data-section-id="' + id + '"]');
        if (sec && t.value.trim() !== '') sec.removeAttribute('data-comment-missing');
      }});
    }});
  }}

  function bindSave() {{
    var btn = document.getElementById('bpe-save-btn');
    if (!btn) return;
    btn.addEventListener('click', function() {{
      var missing = findMissingComments();
      if (missing.length > 0) {{
        markMissing(missing);
        var label = missing.length === 1
          ? 'Add a comment to 1 unit'
          : 'Add comments to ' + missing.length + ' units';
        btn.textContent = label;
        btn.classList.add('review-save--needs-comments');
        // Send the reviewer to the first offender.
        missing[0].section.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        if (missing[0].comment) setTimeout(function() {{ missing[0].comment.focus(); }}, 250);
        // Reset the label after a beat so the next click can re-validate.
        setTimeout(function() {{
          btn.textContent = SAVE_LABEL;
          btn.classList.remove('review-save--needs-comments');
        }}, 3500);
        return;
      }}
      btn.disabled = true;
      btn.textContent = 'Saving…';
      fetch('{save_url}', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(collectFeedback())
      }}).then(function(r) {{
        return r.text().then(function(t) {{ return {{ ok: r.ok, body: t }}; }});
      }}).then(function(res) {{
        if (res.ok) {{
          document.open(); document.write(res.body); document.close();
        }} else {{
          btn.disabled = false;
          btn.textContent = SAVE_LABEL;
          alert('Save rejected by server: ' + res.body);
        }}
      }}).catch(function(err) {{
        btn.disabled = false;
        btn.textContent = SAVE_LABEL;
        alert('Save failed: ' + err);
      }});
    }});
  }}

  function init() {{
    bindCommentClearers();
    bindSave();
  }}
  if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', init);
  }} else {{
    init();
  }}
}})();
</script>
"""
    if "</body>" in html_text:
        return html_text.replace("</body>", script + "</body>", 1)
    return html_text + script


USAGE = (
    "Usage: review-server.py <html-path> <feedback-output-path> <source-markdown-path> "
    "[--bind <address>]\n"
    "  --bind <address>   Force a specific bind address (e.g. 127.0.0.1 to skip the "
    "Tailscale auto-bind when reviewing locally on a Tailscale-up machine)."
)


def parse_argv(argv: list[str]) -> tuple[Path, Path, str, str | None]:
    """Parse argv into (html_path, feedback_path, source_artifact, bind_override).

    `--bind <addr>` is optional and can appear anywhere among the positional
    args. Anything else after the positionals is rejected so a typo doesn't
    silently change behavior.
    """
    bind_override: str | None = None
    positionals: list[str] = []
    i = 0
    while i < len(argv):
        token = argv[i]
        if token == "--bind":
            if i + 1 >= len(argv):
                print("--bind requires an address argument.", file=sys.stderr)
                sys.exit(2)
            bind_override = argv[i + 1]
            i += 2
            continue
        if token in ("-h", "--help"):
            print(USAGE)
            sys.exit(0)
        positionals.append(token)
        i += 1
    if len(positionals) != 3:
        print(USAGE, file=sys.stderr)
        sys.exit(2)
    return Path(positionals[0]), Path(positionals[1]), positionals[2], bind_override


def main() -> None:
    html_path, feedback_path, source_artifact, bind_override = parse_argv(sys.argv[1:])

    if not html_path.exists():
        print(f"HTML file not found: {html_path}", file=sys.stderr)
        sys.exit(1)

    pid_file, url_file = state_paths(Path(source_artifact))
    kill_existing_server(pid_file)
    url_file.unlink(missing_ok=True)
    write_pid_file(pid_file)

    html_text = html_path.read_text(encoding="utf-8")
    shutdown_event = threading.Event()

    bind_addr = bind_override if bind_override is not None else pick_bind_address()
    server = HTTPServer((bind_addr, 0), BaseHTTPRequestHandler)
    port = server.server_address[1]
    save_url = f"http://{bind_addr}:{port}/save"
    html_text = inject_head_assets(html_text)
    html_text = inject_runtime_helpers(html_text)
    html_with_script = inject_save_script(html_text, save_url).encode("utf-8")
    server.RequestHandlerClass = make_handler(
        html_with_script, feedback_path, source_artifact, shutdown_event
    )

    url = f"http://{bind_addr}:{port}/"
    # Write the URL to a well-known file so the /bpe:review command can surface
    # it to the user reliably, even when stdout from the background process is
    # not directly readable. Removed on clean shutdown.
    url_file.write_text(url)
    print(f"BPE review server: {url}", flush=True)
    if bind_addr != "127.0.0.1":
        print(
            f"  (bound to {bind_addr} — open this URL on whichever device you want to review on)",
            flush=True,
        )
    print(f"Reviewing: {source_artifact}", flush=True)
    print(f"Feedback will be written to: {feedback_path}", flush=True)
    print("Click Save in the browser when done. Re-run /bpe:review to restart.", flush=True)

    # Only auto-open the browser when we are bound to the loopback interface.
    # On a Tailscale binding the server is just as likely to be remote from the
    # user's actual browser (e.g. headless dev box, phone reviewing a laptop),
    # so popping a local browser would land on the wrong device.
    if bind_addr == "127.0.0.1":
        threading.Thread(target=lambda: webbrowser.open(url), daemon=True).start()
    threading.Thread(target=server.serve_forever, daemon=True).start()

    try:
        shutdown_event.wait()
    finally:
        server.shutdown()
        pid_file.unlink(missing_ok=True)
        url_file.unlink(missing_ok=True)
    print(f"Saved feedback to {feedback_path}", flush=True)


if __name__ == "__main__":
    main()
