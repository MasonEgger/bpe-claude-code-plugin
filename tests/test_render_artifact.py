# ABOUTME: Tests for bpe/scripts/render-artifact.py, the renderer for todo.md, goal.md, accomplishment.md, and issues.
# ABOUTME: Loads the scripts by path because their hyphenated filenames cannot be imported by name.
"""Tests for the kinds render-artifact.py renders and the drift checks that tie it to the references."""

import importlib.util
import io
import json
import re
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
RENDERER_PATH = REPO_ROOT / "bpe" / "scripts" / "render-artifact.py"
CHECKER_PATH = REPO_ROOT / "bpe" / "scripts" / "check-artifacts.py"
TEMPLATES_DIR = REPO_ROOT / "bpe" / "templates"
SESSION_MANAGEMENT_PATH = REPO_ROOT / "bpe" / "references" / "session-management.md"
ISSUE_FORMAT_PATH = REPO_ROOT / "bpe" / "references" / "issue-format.md"

TWO_SECTION_PLAN = """# Plan: Demo Plan

## How This Plan Runs

Not a section.

## Section 1: First

**Tools:** none

**Batch:** one

### Step 1: Build the thing

1. Do it.

### Step 2: Document the thing (task)

1. Write it.

## Section 2: Second

**Tools:** none

**Batch:** two

### Step 1: Ship it

1. Ship.
"""

EXPECTED_TODO = """# Todo: Demo Plan

Mirrors plan.md, one checkbox per step; check off each step as it finalizes.

## Section 1: First

- [ ] Step 1: Build the thing
- [ ] Step 2: Document the thing

## Section 2: Second

- [ ] Step 1: Ship it
"""

ACCOMPLISHMENT_INPUT = {
    "title": "Demo",
    "archived": "2026-11-22",
    "convergence": "converged",
    "spec_slice": "The slice.",
    "what_got_done": ["Built it", "Shipped it"],
    "deferred": ["Docs: no time"],
    "decisions": ["Chose stdlib"],
    "files": ["a.py", "b.py"],
    "lessons": ["none captured"],
}


def load_script(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def renderer() -> ModuleType:
    return load_script(RENDERER_PATH, "render_artifact")


@pytest.fixture(scope="module")
def checker() -> ModuleType:
    return load_script(CHECKER_PATH, "check_artifacts_for_render")


def run_todo(renderer: ModuleType, plan_path: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = renderer.main(["todo", "--plan", str(plan_path)])
    return code, capsys.readouterr().out


def run_with_stdin(
    renderer: ModuleType,
    kind: str,
    payload: Mapping[str, object] | str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> tuple[int, str, str]:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    monkeypatch.setattr("sys.stdin", io.StringIO(text))
    code = renderer.main([kind])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


class TestTodo:
    def test_two_section_plan_renders_exact_text(
        self, renderer: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text(TWO_SECTION_PLAN)

        code, out = run_todo(renderer, plan, capsys)

        assert code == 0
        assert out == EXPECTED_TODO

    def test_checks_carry_over_by_title_and_retitled_steps_come_out_unchecked(
        self, renderer: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text(TWO_SECTION_PLAN)
        (tmp_path / "todo.md").write_text(
            EXPECTED_TODO.replace("- [ ] Step 1: Build the thing", "- [x] Step 1: Build the thing").replace(
                "- [ ] Step 1: Ship it", "- [x] Step 1: Ship it (old title)"
            )
        )

        _, out = run_todo(renderer, plan, capsys)

        assert "- [x] Step 1: Build the thing" in out
        assert "- [ ] Step 1: Ship it" in out
        assert "- [x] Step 1: Ship it" not in out

    def test_output_flag_refreshes_an_existing_todo_and_keeps_its_checks(
        self, renderer: ModuleType, tmp_path: Path
    ) -> None:
        plan = tmp_path / "plan.md"
        plan.write_text(TWO_SECTION_PLAN)
        todo = tmp_path / "todo.md"
        todo.write_text(EXPECTED_TODO.replace("- [ ] Step 1: Ship it", "- [x] Step 1: Ship it"))

        code = renderer.main(["todo", "--plan", str(plan), "--output", str(todo)])

        assert code == 0
        assert todo.read_text() == EXPECTED_TODO.replace("- [ ] Step 1: Ship it", "- [x] Step 1: Ship it")

    def test_repo_plan_reproduces_repo_todo_byte_for_byte(
        self, renderer: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out = run_todo(renderer, REPO_ROOT / "plan.md", capsys)

        assert code == 0
        assert out == (REPO_ROOT / "todo.md").read_text()

    def test_step_list_agrees_with_the_checker_on_the_repo_plan(
        self, renderer: ModuleType, checker: ModuleType
    ) -> None:
        plan_path = REPO_ROOT / "plan.md"
        text = plan_path.read_text()

        _, rendered_steps = renderer.plan_steps(text)
        sections, _ = checker.parse_plan(plan_path, text)
        checker_steps = [(section.heading, step.number, step.title) for section in sections for step in section.steps]

        assert rendered_steps == checker_steps

    def test_missing_plan_exits_1(
        self, renderer: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out = run_todo(renderer, tmp_path / "plan.md", capsys)

        assert code == 1
        assert out == ""


class TestGoal:
    GOAL_INPUT = {
        "condition": "Every item is checked off.",
        "mode": "full",
        "test_cmd": "pytest -q",
        "branch": "release-0.7.4",
    }

    def test_values_are_substituted_and_no_placeholder_is_left(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, _ = run_with_stdin(renderer, "goal", self.GOAL_INPUT, monkeypatch, capsys)

        assert code == 0
        assert out.startswith("Every item is checked off.\n\nYou're the orchestrator")
        assert "Mode: full. Test: pytest -q. Branch: release-0.7.4." in out
        assert "${CLAUDE_PLUGIN_ROOT}/references/validator-protocol.md" in out
        assert not re.search(r"\$(condition|mode|test_cmd|branch)", out)

    def test_over_the_cap_exits_1_with_the_length_and_empty_stdout(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        payload = {**self.GOAL_INPUT, "condition": "x" * 4000}

        code, out, err = run_with_stdin(renderer, "goal", payload, monkeypatch, capsys)

        assert code == 1
        assert out == ""
        assert re.search(r"\d{4,}", err)

    def test_over_the_cap_with_output_leaves_an_existing_file_untouched(
        self,
        renderer: ModuleType,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        goal = tmp_path / "goal.md"
        goal.write_text("previous")
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({**self.GOAL_INPUT, "condition": "x" * 4000})))

        code = renderer.main(["goal", "--output", str(goal)])

        assert code == 1
        assert goal.read_text() == "previous"

    def test_missing_key_exits_1_naming_it(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        payload = {key: value for key, value in self.GOAL_INPUT.items() if key != "test_cmd"}

        code, out, err = run_with_stdin(renderer, "goal", payload, monkeypatch, capsys)

        assert code == 1
        assert out == ""
        assert "test_cmd" in err


class TestAccomplishment:
    def test_full_input_emits_every_template_heading_in_order_with_values(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code, out, _ = run_with_stdin(renderer, "accomplishment", ACCOMPLISHMENT_INPUT, monkeypatch, capsys)

        assert code == 0
        assert out.splitlines()[0] == "# Accomplishment: Demo"
        assert "**Archived**: 2026-11-22" in out
        assert "**Convergence**: converged" in out
        assert "The slice." in out
        assert [line for line in out.splitlines() if line.startswith("## ")] == [
            "## Spec Slice",
            "## What Got Done",
            "## Deferred or Dropped",
            "## Notable Decisions",
            "## Files Touched",
            "## Lessons Cross-Reference",
        ]

    def test_list_fields_render_one_bullet_per_item(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        _, out, _ = run_with_stdin(renderer, "accomplishment", ACCOMPLISHMENT_INPUT, monkeypatch, capsys)

        assert "- Built it\n- Shipped it\n" in out
        assert "- a.py\n- b.py\n" in out

    def test_absent_optional_lists_render_none(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        payload = {key: value for key, value in ACCOMPLISHMENT_INPUT.items() if key not in {"deferred", "decisions"}}

        _, out, _ = run_with_stdin(renderer, "accomplishment", payload, monkeypatch, capsys)

        assert "## Deferred or Dropped\n\n- none\n" in out
        assert "## Notable Decisions\n\n- none\n" in out

    def test_missing_required_field_exits_1_naming_it(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        payload = {key: value for key, value in ACCOMPLISHMENT_INPUT.items() if key != "convergence"}

        code, out, err = run_with_stdin(renderer, "accomplishment", payload, monkeypatch, capsys)

        assert code == 1
        assert out == ""
        assert "convergence" in err

    def test_template_headings_match_the_session_management_reference(self) -> None:
        reference = SESSION_MANAGEMENT_PATH.read_text()
        block = re.search(r"### accomplishment\.md Template\n\n```markdown\n(.*?)\n```", reference, re.DOTALL)
        assert block is not None

        def headings(text: str) -> list[str]:
            return [line.split(":")[0] for line in text.splitlines() if line.startswith("#")]

        template = (TEMPLATES_DIR / "accomplishment.md.tmpl").read_text()

        assert headings(template) == headings(block[1])


class TestIssue:
    SECTION_ORDER = [
        "What Is Wanted",
        "What We Already Know",
        "Prior Research and Thoughts",
        "Changes, File by File",
        "Out of Scope",
        "Acceptance Criteria",
    ]
    REQUIRED = {
        "What Is Wanted": "Retry binds.",
        "What We Already Know": "It loops.",
        "Acceptance Criteria": "- [ ] Exits 1.",
    }

    def test_sections_come_out_in_format_order_and_absent_optionals_are_skipped(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        sections = {"Out of Scope": "Ports.", **self.REQUIRED}
        payload = {"title": "Add a retry limit", "sections": sections}

        code, out, _ = run_with_stdin(renderer, "issue", payload, monkeypatch, capsys)

        assert code == 0
        assert out.splitlines()[0] == "Add a retry limit"
        headings = [line.removeprefix("## ") for line in out.splitlines() if line.startswith("## ")]
        assert headings == ["What Is Wanted", "What We Already Know", "Out of Scope", "Acceptance Criteria"]
        assert "Retry binds." in out

    def test_missing_required_section_exits_1_naming_it(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        sections = {key: value for key, value in self.REQUIRED.items() if key != "Acceptance Criteria"}

        code, out, err = run_with_stdin(renderer, "issue", {"title": "T", "sections": sections}, monkeypatch, capsys)

        assert code == 1
        assert out == ""
        assert "Acceptance Criteria" in err

    def test_unknown_section_exits_1_naming_it(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        sections = {**self.REQUIRED, "Motivation": "Why."}

        code, out, err = run_with_stdin(renderer, "issue", {"title": "T", "sections": sections}, monkeypatch, capsys)

        assert code == 1
        assert out == ""
        assert "Motivation" in err

    def test_rendered_headings_follow_the_reference_order(
        self, renderer: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        reference = ISSUE_FORMAT_PATH.read_text()
        order = [match[1] for match in re.finditer(r"^\d+\. (.+?) \((?:required|optional)\)$", reference, re.MULTILINE)]
        sections = dict.fromkeys(reversed(order), "Text.")

        _, out, _ = run_with_stdin(renderer, "issue", {"title": "T", "sections": sections}, monkeypatch, capsys)

        headings = [line.removeprefix("## ") for line in out.splitlines() if line.startswith("## ")]
        assert headings == order == self.SECTION_ORDER

    @pytest.mark.parametrize("title", ["", "  ", "Two\nlines", ["a"]])
    def test_bad_title_exits_1(
        self,
        renderer: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        title: object,
    ) -> None:
        code, out, err = run_with_stdin(
            renderer, "issue", {"title": title, "sections": self.REQUIRED}, monkeypatch, capsys
        )

        assert code == 1
        assert out == ""
        assert "title" in err

    @pytest.mark.parametrize("body", ["", "   ", ["a", "b"]])
    def test_bad_section_body_exits_1_naming_the_section(
        self,
        renderer: ModuleType,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        body: object,
    ) -> None:
        sections = {**self.REQUIRED, "What Is Wanted": body}

        code, out, err = run_with_stdin(renderer, "issue", {"title": "T", "sections": sections}, monkeypatch, capsys)

        assert code == 1
        assert out == ""
        assert "What Is Wanted" in err
