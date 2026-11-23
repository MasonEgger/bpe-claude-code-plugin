#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
# ABOUTME: Deterministic checker for the BPE artifacts: plan.md, todo.md, and spec.md.
# ABOUTME: Prints one `path:line: rule: message` line per problem and exits 1 when any hard failure is found.
"""Check BPE artifacts against the rules the skills write them by.

Usage:
    check-artifacts.py PATH [PATH ...]

The artifact type comes from the filename: plan.md, todo.md, or spec.md.
Any other filename is a hard failure with rule `artifact-type`, and a path that does not exist is a hard failure
with rule `artifact-missing`.

A todo.md is compared against the plan.md in its own directory.
That plan is parsed silently when it was not also given; its own problems print only when it is given.

plan.md rules (all hard).
A plan section is a `## ` heading followed by at least one `### Step` heading before the next `## ` heading;
other `## ` headings (How This Plan Runs, Current Status, and so on) are not sections.
Lines inside code fences are never read as headings.
    plan-step-heading   A `### Step` heading does not read `### Step N: <title>` with an optional trailing ` (task)`.
    plan-step-order     Step numbers in a section do not run 1, 2, 3, and so on with no gaps or repeats.
                        Numbering restarts at 1 in each section.
    plan-tools-missing  The section has no `**Tools:**` line before its first step (`**Tools:** none` counts).
    plan-batch-missing  The section has no `**Batch:**` line before its first step, and not every step has its own.

todo.md rules (all hard).
Only top-level lines (those that start with `- `) under a `## ` heading are items.
    todo-checkbox       An item line is not `- [ ] ` or `- [x] `.
    todo-plan-mismatch  The items differ from plan.md's steps, which are compared one for one, in order, by section
                        heading and `Step N: <title>`.
                        A todo item's title is the plan step title with any trailing ` (task)` removed.
                        Only the first difference is reported, and the comparison is skipped while a checkbox
                        failure stands.

spec.md rules.
A spec with neither `## Invariants` nor `## Roadmap / phase log` is in the pre-0.7 layout.
It gets one warning and no other check, so a project that has not migrated still passes.
    spec-pre-0.7        Warning. The spec is in the pre-0.7 layout; no section checks ran.
A 0.7-form spec gets these checks.
    spec-section-order  Hard. The canonical `## ` sections do not appear in the order that
                        references/session-management.md "Spec Section Order (spec.md)" lists.
                        Other `## ` headings (`## External tool candidates` after Available tooling) are ignored.
Goals rules are warnings only.
A heading check has false positives ("### OAuth 2.0 Login" reads as a version) and false negatives
("### Active phase" names no version), so a warning is the strongest signal it can carry.
    goals-status-table    Warning. Goals has no `### Feature Status` table.
    goals-status-columns  Warning. The table header is not exactly Feature, State, Open Work, Docs, Code.
    goals-phase-heading   Warning. A `###` heading under Goals names a version, an issue number, a release,
                          or a phase.
    goals-marker          Warning. A `Planned (ITEM):` or `Known gap:` marker is malformed.

Exit codes:
    0  No hard failure was found; warnings, if any, were printed.
    1  At least one hard failure was found.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

STEP_PREFIX = re.compile(r"^### Step\b")
STEP_HEADING = re.compile(r"^### Step (\d+): (\S.*?)(?: \(task\))?\s*$")
TOOLS_LINE = re.compile(r"^\*\*Tools:\*\*")
BATCH_LINE = re.compile(r"^\*\*Batch:\*\*")
CHECKBOX = re.compile(r"^- \[( |x)\] (.*)$")
FENCE = re.compile(r"^\s*(```|~~~)")
PHASE_HEADING = re.compile(r"\d+\.\d+|#\d+|\bphase\b|\brelease\b", re.IGNORECASE)
PLANNED_START = re.compile(r"Planned\s*\(")
PLANNED_MARKER = re.compile(r"Planned \([^()\s][^()]*\):")
KNOWN_GAP_MISSING_COLON = re.compile(r"Known gap\b(?!:)")

# Mirrors references/session-management.md "Spec Section Order (spec.md)"; a test keeps the two equal.
SPEC_SECTION_ORDER = (
    "## Starting context",
    "## Project overview",
    "## Invariants",
    "## Available tooling",
    "## Roadmap / phase log",
    "## Goals",
    "## Non-goals",
    "## Component boundaries",
    "## Success criteria",
)
STATUS_COLUMNS = ["Feature", "State", "Open Work", "Docs", "Code"]


@dataclass(frozen=True)
class Problem:
    """One finding, printed as `path:line: rule: message`."""

    path: Path
    line: int
    rule: str
    message: str
    hard: bool = True

    def render(self) -> str:
        """Format the problem as one output line.

        Returns:
            The `path:line: rule: message` string.
        """
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


@dataclass
class PlanStep:
    """A well-formed `### Step N: <title>` heading in a plan section."""

    number: int
    title: str
    has_batch: bool = False


@dataclass
class PlanSection:
    """A plan section: a `## ` heading that owns at least one `### Step` heading."""

    heading: str
    line: int
    step_heading_count: int = 0
    has_tools: bool = False
    has_batch: bool = False
    steps: list[PlanStep] = field(default_factory=list)


def outside_fences(text: str) -> Iterator[tuple[int, str]]:
    """Yield each line that is not inside a code fence.

    Args:
        text: The file contents.

    Yields:
        The one-based line number and the line text.
    """
    inside_fence = False
    for line_number, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            inside_fence = not inside_fence
        elif not inside_fence:
            yield line_number, line


def parse_plan(path: Path, text: str) -> tuple[list[PlanSection], list[Problem]]:
    """Read plan.md into its sections and report the plan rules.

    Args:
        path: The plan file, used in the problem lines.
        text: The file contents.

    Returns:
        The plan's sections, and the problems found.
    """
    sections: list[PlanSection] = []
    problems: list[Problem] = []
    current: PlanSection | None = None
    current_step: PlanStep | None = None
    expected_number = 1

    def close_section(section: PlanSection | None) -> None:
        # A `## ` heading with no step headings under it is not a plan section.
        if section is None or section.step_heading_count == 0:
            return
        if not section.has_tools:
            problems.append(
                Problem(path, section.line, "plan-tools-missing", f"'{section.heading}' has no **Tools:** line")
            )
        every_step_has_batch = bool(section.steps) and all(step.has_batch for step in section.steps)
        if not (section.has_batch or every_step_has_batch):
            problems.append(
                Problem(path, section.line, "plan-batch-missing", f"'{section.heading}' has no **Batch:** line")
            )
        sections.append(section)

    for line_number, line in outside_fences(text):
        if line.startswith("## "):
            close_section(current)
            current = PlanSection(heading=line.removeprefix("## ").strip(), line=line_number)
            current_step = None
            expected_number = 1
        elif current is None:
            continue
        elif STEP_PREFIX.match(line):
            current.step_heading_count += 1
            heading = STEP_HEADING.match(line)
            if heading is None:
                current_step = None
                problems.append(
                    Problem(path, line_number, "plan-step-heading", "step heading must read '### Step N: <title>'")
                )
                continue

            number = int(heading[1])
            if number != expected_number:
                problems.append(
                    Problem(
                        path, line_number, "plan-step-order", f"expected Step {expected_number}, found Step {number}"
                    )
                )
            expected_number = number + 1
            current_step = PlanStep(number=number, title=heading[2])
            current.steps.append(current_step)
        elif TOOLS_LINE.match(line) and current.step_heading_count == 0:
            current.has_tools = True
        elif BATCH_LINE.match(line):
            if current.step_heading_count == 0:
                current.has_batch = True
            elif current_step is not None:
                current_step.has_batch = True

    close_section(current)
    return sections, problems


def check_todo(path: Path, text: str, plan_sections: list[PlanSection] | None) -> list[Problem]:
    """Report the todo.md rules, comparing against the plan when one is given.

    Args:
        path: The todo file, used in the problem lines.
        text: The file contents.
        plan_sections: The sections of the matching plan.md, or None when there is no plan to compare against.

    Returns:
        The problems found.
    """
    problems: list[Problem] = []
    items: list[tuple[str, str, int]] = []
    section_heading: str | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.startswith("## "):
            section_heading = line.removeprefix("## ").strip()
        elif section_heading is not None and line.startswith("- "):
            checkbox = CHECKBOX.match(line)
            if checkbox is None:
                problems.append(
                    Problem(path, line_number, "todo-checkbox", "item must start with '- [ ] ' or '- [x] '")
                )
            else:
                items.append((section_heading, checkbox[2].strip(), line_number))

    # A malformed checkbox already stands as a failure; comparing would only repeat it as a mismatch.
    if plan_sections is None or problems:
        return problems

    expected = [
        (section.heading, f"Step {step.number}: {step.title}") for section in plan_sections for step in section.steps
    ]
    actual = [(heading, label) for heading, label, _ in items]
    for position in range(max(len(expected), len(actual))):
        want = expected[position] if position < len(expected) else None
        got = actual[position] if position < len(actual) else None
        if want == got:
            continue

        # Past the end of the todo, point at its last item (or the top of the file when it has none).
        report_line = items[min(position, len(items) - 1)][2] if items else 1
        want_text = f"'{want[1]}' under '## {want[0]}'" if want else "no more items"
        got_text = f"'{got[1]}' under '## {got[0]}'" if got else "nothing"
        problems.append(
            Problem(path, report_line, "todo-plan-mismatch", f"expected {want_text} from plan.md, found {got_text}")
        )
        break

    return problems


def check_spec(path: Path, text: str) -> list[Problem]:
    """Report the spec.md rules.

    Args:
        path: The spec file, used in the problem lines.
        text: The file contents.

    Returns:
        The problems found; a pre-0.7 spec yields one warning and nothing else.
    """
    lines = list(outside_fences(text))
    h2_headings = [(line_number, line) for line_number, line in lines if line.startswith("## ")]

    if not {"## Invariants", "## Roadmap / phase log"} & {heading for _, heading in h2_headings}:
        return [Problem(path, 1, "spec-pre-0.7", "pre-0.7 layout; section checks skipped", hard=False)]

    problems: list[Problem] = []

    # Canonical sections must keep their relative order; any other `## ` heading is ignored.
    furthest_position = -1
    for line_number, heading in h2_headings:
        if heading not in SPEC_SECTION_ORDER:
            continue
        position = SPEC_SECTION_ORDER.index(heading)
        if position < furthest_position:
            problems.append(
                Problem(path, line_number, "spec-section-order", f"'{heading}' is out of the canonical section order")
            )
        furthest_position = max(furthest_position, position)

    # Goals shape: warnings only.
    goals_start = next((line_number for line_number, heading in h2_headings if heading == "## Goals"), None)
    if goals_start is None:
        return problems

    goals_lines: list[tuple[int, str]] = []
    in_goals = False
    for line_number, line in lines:
        if line.startswith("## "):
            in_goals = line == "## Goals"
        elif in_goals:
            goals_lines.append((line_number, line))

    status_heading_line = next((number for number, line in goals_lines if line.startswith("### Feature Status")), None)
    status_header = None
    if status_heading_line is not None:
        status_header = next(
            ((number, line) for number, line in goals_lines if number > status_heading_line and line.startswith("|")),
            None,
        )
    if status_header is None:
        problems.append(
            Problem(path, goals_start, "goals-status-table", "Goals has no '### Feature Status' table", hard=False)
        )
    else:
        columns = [cell.strip() for cell in status_header[1].strip().strip("|").split("|")]
        if columns != STATUS_COLUMNS:
            problems.append(
                Problem(
                    path,
                    status_header[0],
                    "goals-status-columns",
                    f"Feature Status columns must be {', '.join(STATUS_COLUMNS)}",
                    hard=False,
                )
            )

    for line_number, line in goals_lines:
        if line.startswith("### ") and PHASE_HEADING.search(line):
            problems.append(
                Problem(
                    path,
                    line_number,
                    "goals-phase-heading",
                    "Goals headings name features, not versions, issues, or phases",
                    hard=False,
                )
            )
        has_bad_planned = any(not PLANNED_MARKER.match(line, match.start()) for match in PLANNED_START.finditer(line))
        if has_bad_planned or KNOWN_GAP_MISSING_COLON.search(line):
            problems.append(
                Problem(
                    path, line_number, "goals-marker", "marker must read 'Planned (ITEM):' or 'Known gap:'", hard=False
                )
            )

    return problems


def main(argv: Sequence[str] | None = None) -> int:
    """Check each artifact path and print its problems.

    Args:
        argv: Command-line arguments; sys.argv[1:] when None.

    Returns:
        1 when any hard failure was found, else 0.
    """
    parser = argparse.ArgumentParser(description="Check BPE artifacts (plan.md, todo.md, spec.md) against their rules.")
    parser.add_argument(
        "paths", nargs="+", type=Path, metavar="PATH", help="plan.md, todo.md, or spec.md files to check"
    )
    args = parser.parse_args(argv)

    problems: list[Problem] = []
    plan_cache: dict[Path, list[PlanSection]] = {}

    for path in args.paths:
        if path.name not in {"plan.md", "todo.md", "spec.md"}:
            problems.append(Problem(path, 1, "artifact-type", "filename must be plan.md, todo.md, or spec.md"))
            continue
        if not path.is_file():
            problems.append(Problem(path, 1, "artifact-missing", "file does not exist"))
            continue

        text = path.read_text()
        if path.name == "plan.md":
            sections, plan_problems = parse_plan(path, text)
            plan_cache[path.resolve()] = sections
            problems.extend(sorted(plan_problems, key=lambda problem: problem.line))
            continue

        if path.name == "spec.md":
            problems.extend(check_spec(path, text))
            continue

        # todo.md: compare against the plan.md beside it, parsing it silently when it was not given.
        plan_path = (path.parent / "plan.md").resolve()
        if plan_path not in plan_cache and plan_path.is_file():
            plan_cache[plan_path], _ = parse_plan(plan_path, plan_path.read_text())
        problems.extend(check_todo(path, text, plan_cache.get(plan_path)))

    for problem in problems:
        print(problem.render())

    return 1 if any(problem.hard for problem in problems) else 0


if __name__ == "__main__":
    sys.exit(main())
