# ABOUTME: Tests for bpe/scripts/check-artifacts.py, the deterministic checker for plan.md, todo.md, and spec.md.
# ABOUTME: Loads the script by path because its hyphenated filename cannot be imported by name.
"""Tests for the rules check-artifacts.py applies to plan.md, todo.md, and spec.md."""

import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSION_MANAGEMENT_PATH = REPO_ROOT / "bpe" / "references" / "session-management.md"
CHECKER_PATH = REPO_ROOT / "bpe" / "scripts" / "check-artifacts.py"

CLEAN_PLAN = """# Plan: Demo

## How This Plan Runs

Not a section, because it has no step headings.

## Section 1: First

**Tools:** none

**Batch:** one

### Step 1: Build the thing

1. Do it.

### Step 2: Document the thing (task)

1. Write it.

## Section 2: Second

**Tools:**
- Skills: python:python

**Batch:** two

### Step 1: Ship the thing
"""

CLEAN_TODO = """# Todo: Demo

Mirrors plan.md.

## Section 1: First

- [x] Step 1: Build the thing
- [ ] Step 2: Document the thing

## Section 2: Second

- [ ] Step 1: Ship the thing
"""


@pytest.fixture(scope="module")
def checker() -> ModuleType:
    """Load check-artifacts.py as a module.

    Returns:
        The executed module object.

    Raises:
        ImportError: When the script cannot be located for loading.
    """
    spec = importlib.util.spec_from_file_location("check_artifacts", CHECKER_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {CHECKER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_checker(
    checker: ModuleType,
    capsys: pytest.CaptureFixture[str],
    paths: list[Path],
) -> tuple[int, list[str]]:
    """Run main() on the given paths and capture its output.

    Args:
        checker: The loaded check-artifacts module.
        capsys: The pytest stdout capture fixture.
        paths: Artifact paths to hand to the checker.

    Returns:
        The exit code and the printed problem lines.
    """
    exit_code = checker.main([str(path) for path in paths])
    printed = capsys.readouterr().out.splitlines()
    return exit_code, printed


def rules_of(lines: list[str]) -> list[str]:
    """Pull the rule name out of each `path:line: rule: message` line.

    Args:
        lines: Printed problem lines.

    Returns:
        The rule names, in print order.
    """
    return [line.split(": ", 2)[1] for line in lines]


@pytest.fixture
def workdir(tmp_path: Path) -> Path:
    """Write a clean plan.md and todo.md pair into a temp directory.

    Args:
        tmp_path: The pytest temp directory.

    Returns:
        The directory holding the pair.
    """
    (tmp_path / "plan.md").write_text(CLEAN_PLAN)
    (tmp_path / "todo.md").write_text(CLEAN_TODO)
    return tmp_path


class TestPlanRules:
    """Rules that apply to plan.md alone."""

    def test_clean_pair_passes(self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path) -> None:
        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md", workdir / "todo.md"])

        assert exit_code == 0
        assert printed == []

    @pytest.mark.parametrize(
        "bad_heading",
        ["### Step 2 - Document the thing", "### Step: Document the thing", "### Step 2: ", "### Step X: Title"],
    )
    def test_malformed_step_heading_fails(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path, bad_heading: str
    ) -> None:
        plan = CLEAN_PLAN.replace("### Step 2: Document the thing (task)", bad_heading)
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["plan-step-heading"]

    def test_step_headings_inside_code_fences_are_ignored(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        plan = CLEAN_PLAN.replace("1. Do it.", "```text\n### Step X: [Title]\n```")
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 0
        assert printed == []

    def test_gap_in_step_numbers_fails(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        plan = CLEAN_PLAN.replace("### Step 2: Document", "### Step 4: Document")
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["plan-step-order"]

    def test_numbering_restarts_in_each_section(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 0
        assert printed == []

    def test_continuing_numbers_into_the_next_section_fails(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        plan = CLEAN_PLAN.replace("### Step 1: Ship the thing", "### Step 3: Ship the thing")
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["plan-step-order"]

    def test_missing_tools_line_fails(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        plan = CLEAN_PLAN.replace("**Tools:** none\n\n", "")
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["plan-tools-missing"]

    def test_tools_none_passes(self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path) -> None:
        exit_code, _ = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 0

    def test_missing_batch_line_fails(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        plan = CLEAN_PLAN.replace("**Batch:** one\n\n", "")
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["plan-batch-missing"]

    def test_per_step_batch_lines_replace_the_section_line(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        plan = (
            CLEAN_PLAN.replace("**Batch:** one\n\n", "")
            .replace("### Step 1: Build the thing\n", "### Step 1: Build the thing\n\n**Batch:** one-a\n")
            .replace(
                "### Step 2: Document the thing (task)\n", "### Step 2: Document the thing (task)\n\n**Batch:** one-b\n"
            )
        )
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 0
        assert printed == []

    def test_batch_line_on_only_some_steps_fails(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        plan = CLEAN_PLAN.replace("**Batch:** one\n\n", "").replace(
            "### Step 1: Build the thing\n", "### Step 1: Build the thing\n\n**Batch:** one-a\n"
        )
        (workdir / "plan.md").write_text(plan)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["plan-batch-missing"]


class TestTodoRules:
    """Rules that apply to todo.md, alone or against plan.md."""

    def test_bad_checkbox_fails(self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path) -> None:
        todo = CLEAN_TODO.replace("- [ ] Step 2: Document the thing", "- Step 2: Document the thing")
        (workdir / "todo.md").write_text(todo)

        exit_code, printed = run_checker(checker, capsys, [workdir / "todo.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["todo-checkbox"]

    def test_uppercase_x_checkbox_fails(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        todo = CLEAN_TODO.replace("- [x] Step 1", "- [X] Step 1")
        (workdir / "todo.md").write_text(todo)

        exit_code, printed = run_checker(checker, capsys, [workdir / "todo.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["todo-checkbox"]

    def test_todo_beside_a_plan_is_compared_without_naming_the_plan(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        todo = CLEAN_TODO.replace("- [ ] Step 1: Ship the thing\n", "")
        (workdir / "todo.md").write_text(todo)

        exit_code, printed = run_checker(checker, capsys, [workdir / "todo.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["todo-plan-mismatch"]

    @pytest.mark.parametrize(
        ("old", "new", "expected_text"),
        [
            ("- [ ] Step 1: Ship the thing\n", "", "Step 1: Ship the thing"),
            ("- [ ] Step 1: Ship the thing\n", "- [ ] Step 1: Ship the thing\n- [ ] Step 2: Extra\n", "Step 2: Extra"),
            ("Step 2: Document the thing", "Step 2: Document the other thing", "Step 2: Document the other thing"),
        ],
        ids=["missing", "extra", "retitled"],
    )
    def test_drift_from_the_plan_fails_and_names_the_first_difference(
        self,
        checker: ModuleType,
        capsys: pytest.CaptureFixture[str],
        workdir: Path,
        old: str,
        new: str,
        expected_text: str,
    ) -> None:
        (workdir / "todo.md").write_text(CLEAN_TODO.replace(old, new))

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md", workdir / "todo.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["todo-plan-mismatch"]
        assert expected_text in printed[0]

    def test_renamed_section_heading_is_named_in_the_message(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        (workdir / "todo.md").write_text(CLEAN_TODO.replace("## Section 2: Second", "## Section 2: Renamed"))

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md", workdir / "todo.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["todo-plan-mismatch"]
        assert "## Section 2: Second" in printed[0]
        assert "## Section 2: Renamed" in printed[0]

    def test_reordered_items_fail(self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path) -> None:
        todo = CLEAN_TODO.replace(
            "- [x] Step 1: Build the thing\n- [ ] Step 2: Document the thing\n",
            "- [ ] Step 2: Document the thing\n- [x] Step 1: Build the thing\n",
        )
        (workdir / "todo.md").write_text(todo)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md", workdir / "todo.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["todo-plan-mismatch"]
        assert "Step 1: Build the thing" in printed[0]

    def test_task_suffix_is_dropped_from_the_expected_title(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        todo = CLEAN_TODO.replace("Step 2: Document the thing", "Step 2: Document the thing (task)")
        (workdir / "todo.md").write_text(todo)

        exit_code, printed = run_checker(checker, capsys, [workdir / "plan.md", workdir / "todo.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["todo-plan-mismatch"]


class TestOutputAndExit:
    """The output line format, exit codes, and artifact detection."""

    def test_output_line_format(self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path) -> None:
        plan = CLEAN_PLAN.replace("**Tools:** none\n\n", "")
        (workdir / "plan.md").write_text(plan)
        plan_path = workdir / "plan.md"

        _, printed = run_checker(checker, capsys, [plan_path])

        heading_line = plan.splitlines().index("## Section 1: First") + 1
        assert printed == [f"{plan_path}:{heading_line}: plan-tools-missing: {printed[0].split(': ', 2)[2]}"]
        assert printed[0].split(": ", 2)[2] != ""

    def test_exit_one_on_hard_failure_and_zero_on_nothing(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], workdir: Path
    ) -> None:
        clean_code, _ = run_checker(checker, capsys, [workdir / "plan.md"])
        (workdir / "plan.md").write_text(CLEAN_PLAN.replace("**Batch:** two\n\n", ""))
        broken_code, _ = run_checker(checker, capsys, [workdir / "plan.md"])

        assert clean_code == 0
        assert broken_code == 1

    def test_unrecognized_filename_is_an_error(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        stray = tmp_path / "notes.md"
        stray.write_text("# Notes\n")

        exit_code, printed = run_checker(checker, capsys, [stray])

        assert exit_code == 1
        assert rules_of(printed) == ["artifact-type"]

    def test_missing_file_is_an_error(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        exit_code, printed = run_checker(checker, capsys, [tmp_path / "plan.md"])

        assert exit_code == 1
        assert rules_of(printed) == ["artifact-missing"]


class TestThisRepo:
    """The checker accepts the plan and todo this repo is developed with."""

    def test_own_plan_and_todo_pass(self, checker: ModuleType, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code, printed = run_checker(checker, capsys, [REPO_ROOT / "plan.md", REPO_ROOT / "todo.md"])

        assert printed == []
        assert exit_code == 0


CLEAN_SPEC = """# Demo

## Starting context

Familiar with the stack.

## Project overview

A demo.

## Invariants

- deps: frozen

## Available tooling

**MCPs:** none

## Roadmap / phase log

**Upcoming:** none

## Goals

### Feature Status

| Feature | State | Open Work | Docs | Code |
|---|---|---|---|---|
| Login | shipped | none | yes | yes |

### Login

Users sign in with a password.

## Non-goals

- Never SSO.

## Component boundaries

Auth is one module.

## Success criteria

Tests pass.
"""


def write_spec(directory: Path, text: str) -> Path:
    """Write text as spec.md in a directory.

    Args:
        directory: Where to write the file.
        text: The spec contents.

    Returns:
        The path of the written file.
    """
    spec_path = directory / "spec.md"
    spec_path.write_text(text)
    return spec_path


class TestSpecRules:
    """Rules that apply to spec.md."""

    def test_clean_spec_passes(self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, CLEAN_SPEC)])

        assert exit_code == 0
        assert printed == []

    def test_pre_07_layout_warns_once_and_skips_every_section_check(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        old_spec = "# Old\n\n## Goals\n\n### 0.4.0 Material parity\n\n## Starting context\n\nPlanned(x): oops\n"

        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, old_spec)])

        assert exit_code == 0
        assert rules_of(printed) == ["spec-pre-0.7"]

    def test_this_repos_spec_exits_zero_with_only_the_pre_07_warning(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code, printed = run_checker(checker, capsys, [REPO_ROOT / "spec.md"])

        assert exit_code == 0
        assert rules_of(printed) == ["spec-pre-0.7"]

    def test_sections_out_of_order_fail(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        swapped = (
            CLEAN_SPEC.replace("## Non-goals", "## TMP")
            .replace("## Goals", "## Non-goals")
            .replace("## TMP", "## Goals")
        )

        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, swapped)])

        assert exit_code == 1
        assert "spec-section-order" in rules_of(printed)

    def test_external_tool_candidates_after_available_tooling_is_allowed(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        spec = CLEAN_SPEC.replace(
            "## Roadmap / phase log", "## External tool candidates\n\nNone.\n\n## Roadmap / phase log"
        )

        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, spec)])

        assert exit_code == 0
        assert printed == []

    def test_missing_status_table_warns_and_exits_zero(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        start = CLEAN_SPEC.index("### Feature Status")
        end = CLEAN_SPEC.index("### Login")
        spec = CLEAN_SPEC[:start] + CLEAN_SPEC[end:]

        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, spec)])

        assert exit_code == 0
        assert rules_of(printed) == ["goals-status-table"]

    def test_wrong_status_columns_warn(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path
    ) -> None:
        spec = CLEAN_SPEC.replace("| Feature | State | Open Work | Docs | Code |", "| Feature | State | Docs | Code |")

        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, spec)])

        assert exit_code == 0
        assert rules_of(printed) == ["goals-status-columns"]

    @pytest.mark.parametrize(
        "heading",
        ["### 0.4.0 Material parity", "### Login (Issue #30)", "### Phase 2 work", "### OAuth 2.0 Login"],
    )
    def test_phase_named_goals_heading_warns(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path, heading: str
    ) -> None:
        exit_code, printed = run_checker(
            checker, capsys, [write_spec(tmp_path, CLEAN_SPEC.replace("### Login", heading))]
        )

        assert exit_code == 0
        assert rules_of(printed) == ["goals-phase-heading"]

    @pytest.mark.parametrize("marker", ["Planned(x): a thing.", "Planned (): a thing.", "Known gap with no colon."])
    def test_malformed_marker_warns(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path, marker: str
    ) -> None:
        spec = CLEAN_SPEC.replace("Users sign in with a password.", marker)

        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, spec)])

        assert exit_code == 0
        assert rules_of(printed) == ["goals-marker"]

    @pytest.mark.parametrize("marker", ["Planned (containers fixes): a thing.", "Known gap: docs lag, see #12."])
    def test_well_formed_marker_passes(
        self, checker: ModuleType, capsys: pytest.CaptureFixture[str], tmp_path: Path, marker: str
    ) -> None:
        spec = CLEAN_SPEC.replace("Users sign in with a password.", marker)

        exit_code, printed = run_checker(checker, capsys, [write_spec(tmp_path, spec)])

        assert exit_code == 0
        assert printed == []


class TestCanonicalOrderDrift:
    """The checker's section order cannot drift from the reference that defines it."""

    def test_constant_matches_session_management_list(self, checker: ModuleType) -> None:
        reference = SESSION_MANAGEMENT_PATH.read_text()
        section = reference.split("## Spec Section Order (spec.md)", 1)[1].split("\n## ", 1)[0]

        documented = re.findall(r"^\d+\. `(## [^`]+)`$", section, flags=re.MULTILINE)

        assert documented
        assert list(checker.SPEC_SECTION_ORDER) == documented
