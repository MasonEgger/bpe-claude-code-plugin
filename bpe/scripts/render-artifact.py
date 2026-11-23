#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
# ABOUTME: Deterministic renderer for the BPE artifacts: todo.md, goal.md, accomplishment.md, and issues.
# ABOUTME: Fills the string.Template files in bpe/templates/ and writes the result to stdout; exits 1 on bad input.
"""Render a BPE artifact from a template, so a skill never writes its fixed shape freehand.

Usage:
    render-artifact.py todo [--plan PATH] [--output PATH]
    render-artifact.py goal [--output PATH] < input.json
    render-artifact.py accomplishment [--output PATH] < input.json
    render-artifact.py issue [--output PATH] < input.json

Output goes to stdout, or to the file named by `--output PATH`, which is written only after every input is read.
Use `--output todo.md` to refresh an existing todo.md: a shell redirect onto it would truncate the file before the
script reads the `[x]` marks to carry over.
Problems go to stderr with exit code 1, and nothing is written to stdout or to the `--output` file.

Kinds.
    todo            Reads plan.md (--plan, default plan.md) and emits todo.md: a `# Todo: <title>` line with the
                    plan title minus its "Plan: " prefix, one fixed intro line, then per section a `## ` heading
                    and one `- [ ] Step N: <title>` line per step.
                    A step title ends without its ` (task)` marker.
                    When a todo.md sits beside the plan, a step whose title is checked there stays `[x]`;
                    a step whose title changed comes out unchecked.
    goal            Reads a JSON object from stdin with the keys condition, mode, test_cmd, and branch, and emits
                    goal.md, with the absolute plugin root filled in where the playbook path goes.
                    /goal caps its argument at 4000 characters; a longer result prints its length to stderr,
                    exits 1, and writes nothing to stdout.
    accomplishment  Reads a JSON object from stdin and emits the accomplishment.md that
                    references/session-management.md "accomplishment.md Template" defines.
                    Required keys: title, archived, convergence, spec_slice, what_got_done, files, lessons.
                    Optional keys: deferred, decisions.
                    A list value (what_got_done, deferred, decisions, files, lessons) renders as one `- ` bullet
                    per item; a plain string is accepted for any of them and renders as one bullet.
                    An absent optional list renders as `- none`.
    issue           Reads a JSON object from stdin with the keys title and sections (a map of heading to body)
                    and emits the title line, then each section as a `## ` heading and its body, in the order the
                    numbered list in references/issue-format.md defines.
                    The order and the required sections are read from that file at run time.
                    Absent optional sections are skipped; a missing required section or an unknown heading exits 1.

Exit codes:
    0  The artifact was rendered to stdout.
    1  The plan or the JSON input was unreadable, a required key was missing, or goal.md ran over the cap.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from string import Template

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = PLUGIN_ROOT / "templates"
GOAL_CHAR_CAP = 4000

FENCE = re.compile(r"^\s*(```|~~~)")
STEP_HEADING = re.compile(r"^### Step (\d+): (\S.*?)(?: \(task\))?\s*$")
CHECKED_ITEM = re.compile(r"^- \[x\] (?:Step \d+: )?(.*?)\s*$")

ISSUE_FORMAT_PATH = Path(__file__).resolve().parent.parent / "references" / "issue-format.md"
ISSUE_SECTION_ITEM = re.compile(r"^\d+\. (.+?) \((required|optional)\)$", re.MULTILINE)

GOAL_KEYS = ("condition", "mode", "test_cmd", "branch")
ACCOMPLISHMENT_REQUIRED = ("title", "archived", "convergence", "spec_slice", "what_got_done", "files", "lessons")
ACCOMPLISHMENT_LISTS = ("what_got_done", "deferred", "decisions", "files", "lessons")


class RenderError(Exception):
    """Input the renderer cannot turn into an artifact."""


def plan_steps(text: str) -> tuple[str, list[tuple[str, int, str]]]:
    """Read plan.md into its title and its steps.

    A step belongs to the nearest `## ` heading above it, and a `## ` heading with no step under it is not read.
    Lines inside code fences are skipped.

    Args:
        text: The plan.md contents.

    Returns:
        The plan title without its "Plan: " prefix, and one (section heading, number, title) tuple per step.
    """
    title = ""
    heading = ""
    steps: list[tuple[str, int, str]] = []
    inside_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            inside_fence = not inside_fence
        elif inside_fence:
            continue
        elif line.startswith("# ") and not title:
            title = line.removeprefix("# ").removeprefix("Plan: ").strip()
        elif line.startswith("## "):
            heading = line.removeprefix("## ").strip()
        elif (step := STEP_HEADING.match(line)) and heading:
            steps.append((heading, int(step[1]), step[2]))
    return title, steps


def checked_titles(todo_text: str) -> set[str]:
    """Collect the titles of the steps an existing todo.md has checked off.

    Args:
        todo_text: The todo.md contents.

    Returns:
        The step titles on `- [x]` lines, without their `Step N: ` prefix.
    """
    return {match[1] for line in todo_text.splitlines() if (match := CHECKED_ITEM.match(line))}


def render_todo(plan_path: Path) -> str:
    """Render todo.md from a plan, keeping the checks an existing todo.md beside it holds.

    Args:
        plan_path: The plan.md file.

    Returns:
        The todo.md text.

    Raises:
        RenderError: The plan cannot be read, or it has no steps.
    """
    try:
        title, steps = plan_steps(plan_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RenderError(f"cannot read {plan_path}: {error.strerror}") from error
    if not steps:
        raise RenderError(f"{plan_path} has no '### Step N: <title>' headings under a '## ' section")

    todo_path = plan_path.with_name("todo.md")
    checked = checked_titles(todo_path.read_text(encoding="utf-8")) if todo_path.is_file() else set()

    lines: list[str] = []
    current_heading = ""
    for heading, number, step_title in steps:
        if heading != current_heading:
            lines.extend(["", f"## {heading}", ""])
            current_heading = heading
        mark = "x" if step_title in checked else " "
        lines.append(f"- [{mark}] Step {number}: {step_title}")

    header = Template((TEMPLATES_DIR / "todo.md.tmpl").read_text(encoding="utf-8")).substitute(title=title)
    return header + "\n".join(lines) + "\n"


def load_json_object(stream_text: str, required: tuple[str, ...]) -> dict[str, object]:
    """Parse the JSON object a kind reads from stdin and check its required keys.

    Args:
        stream_text: The raw stdin text.
        required: The keys the kind needs.

    Returns:
        The parsed object.

    Raises:
        RenderError: The text is not a JSON object, or a required key is missing.
    """
    try:
        data = json.loads(stream_text)
    except json.JSONDecodeError as error:
        raise RenderError(f"stdin is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise RenderError("stdin must hold a JSON object")
    for key in required:
        if key not in data:
            raise RenderError(f"missing required key: {key}")
    return data


def render_goal(stream_text: str) -> str:
    """Render goal.md from the condition, mode, test command, and branch.

    Args:
        stream_text: The JSON object text from stdin.

    Returns:
        The goal.md text.

    Raises:
        RenderError: The JSON is bad, or the text runs over the /goal argument cap.
    """
    data = load_json_object(stream_text, GOAL_KEYS)
    text = Template((TEMPLATES_DIR / "goal.md.tmpl").read_text(encoding="utf-8")).substitute(
        {**{key: str(data[key]) for key in GOAL_KEYS}, "plugin_root": str(PLUGIN_ROOT)}
    )
    if len(text) > GOAL_CHAR_CAP:
        raise RenderError(f"goal.md is {len(text)} characters, over the {GOAL_CHAR_CAP} cap")
    return text


def bullets(value: object) -> str:
    """Format a field as `- ` bullets, one per item.

    Args:
        value: A list of items, a single string, or None for an absent optional list.

    Returns:
        The bullet lines joined by newlines; `- none` when the value is None or an empty list.
    """
    if value is None:
        return "- none"
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = list(value)
    else:
        items = [str(value)]
    return "\n".join(f"- {item}" for item in items) if items else "- none"


def render_accomplishment(stream_text: str) -> str:
    """Render accomplishment.md from the archived plan's facts.

    Args:
        stream_text: The JSON object text from stdin.

    Returns:
        The accomplishment.md text.

    Raises:
        RenderError: The JSON is bad or a required key is missing.
    """
    data = load_json_object(stream_text, ACCOMPLISHMENT_REQUIRED)
    fields: dict[str, str] = {key: str(value) for key, value in data.items() if key not in ACCOMPLISHMENT_LISTS}
    for key in ACCOMPLISHMENT_LISTS:
        fields[key] = bullets(data.get(key))
    fields.setdefault("title", "")
    return Template((TEMPLATES_DIR / "accomplishment.md.tmpl").read_text(encoding="utf-8")).substitute(fields)


def render_issue(stream_text: str) -> str:
    """Render a GitHub issue body from a title and its sections.

    Args:
        stream_text: The JSON object text from stdin, with a title string and a sections map.

    Returns:
        The title line, then each present section in issue-format.md order.

    Raises:
        RenderError: The JSON is bad, a required section is missing, or a heading is not in the format.
    """
    data = load_json_object(stream_text, ("title", "sections"))
    sections = data["sections"]
    if not isinstance(sections, dict):
        raise RenderError("sections must be a JSON object mapping heading to body")
    try:
        defined = [
            (match[1], match[2] == "required")
            for match in ISSUE_SECTION_ITEM.finditer(ISSUE_FORMAT_PATH.read_text(encoding="utf-8"))
        ]
    except OSError as error:
        raise RenderError(f"cannot read {ISSUE_FORMAT_PATH}: {error.strerror}") from error
    known = {heading for heading, _ in defined}
    for heading in sections:
        if heading not in known:
            raise RenderError(f"unknown section: {heading}")
    for heading, required in defined:
        if required and heading not in sections:
            raise RenderError(f"missing required section: {heading}")

    title = data["title"]
    if not isinstance(title, str) or not title.strip() or "\n" in title.strip():
        raise RenderError("title must be a non-empty single-line string")
    for heading, body in sections.items():
        if not isinstance(body, str) or not body.strip():
            raise RenderError(f"section body must be a non-empty string: {heading}")

    parts = [title.strip()]
    parts.extend(f"## {heading}\n\n{sections[heading].strip()}" for heading, _ in defined if heading in sections)
    return "\n\n".join(parts) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Render the requested kind to stdout.

    Args:
        argv: The command line without the program name; sys.argv when None.

    Returns:
        The exit code.
    """
    parser = argparse.ArgumentParser(description="Render a BPE artifact from its template.")
    parser.add_argument("kind", choices=("todo", "goal", "accomplishment", "issue"))
    parser.add_argument("--plan", type=Path, default=Path("plan.md"), help="plan.md path for the todo kind")
    parser.add_argument(
        "--output",
        type=Path,
        help="write here instead of stdout, after all input is read, so it can safely replace an input file",
    )
    args = parser.parse_args(argv)

    try:
        if args.kind == "todo":
            text = render_todo(args.plan)
        elif args.kind == "goal":
            text = render_goal(sys.stdin.read())
        elif args.kind == "issue":
            text = render_issue(sys.stdin.read())
        else:
            text = render_accomplishment(sys.stdin.read())
    except RenderError as error:
        print(f"render-artifact.py: {error}", file=sys.stderr)
        return 1

    if args.output is None:
        sys.stdout.write(text)
    else:
        args.output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
