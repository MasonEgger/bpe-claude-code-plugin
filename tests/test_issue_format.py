# ABOUTME: Tests that the GitHub issue template and bpe/references/issue-format.md define the same sections.
# ABOUTME: The reference is the source of truth; the template and the renderer read or mirror its numbered list.
"""Drift check between the agent-ready issue template and the issue format reference."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FORMAT_PATH = REPO_ROOT / "bpe" / "references" / "issue-format.md"
TEMPLATE_PATH = REPO_ROOT / ".github" / "ISSUE_TEMPLATE" / "agent-ready.md"

SECTION_ITEM = re.compile(r"^\d+\. (.+?) \((required|optional)\)$", re.MULTILINE)


def defined_sections() -> list[tuple[str, str]]:
    return [(match[1], match[2]) for match in SECTION_ITEM.finditer(FORMAT_PATH.read_text())]


def template_headings() -> list[str]:
    return [
        line.removeprefix("## ").strip() for line in TEMPLATE_PATH.read_text().splitlines() if line.startswith("## ")
    ]


def test_template_headings_match_the_reference_order() -> None:
    assert template_headings() == [heading for heading, _ in defined_sections()]


def test_exactly_three_sections_are_required() -> None:
    required = [heading for heading, status in defined_sections() if status == "required"]

    assert required == ["What Is Wanted", "What We Already Know", "Acceptance Criteria"]
