# ABOUTME: Tests for dispatch usage attribution in bpe/scripts/goal-run-report.py.
# ABOUTME: Loads the script by path because its hyphenated filename cannot be imported by name.
"""Tests for how goal-run-report.py attributes subagent usage to Agent and SendMessage dispatches."""

import importlib.util
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pytest

REPORT_PATH = Path(__file__).resolve().parent.parent / "bpe" / "scripts" / "goal-run-report.py"
AGENT_ID = "aaaa1111"
BASE_HOUR = 10


@pytest.fixture(scope="module")
def report() -> ModuleType:
    """Load goal-run-report.py as a module.

    Returns:
        The executed module object.

    Raises:
        ImportError: When the script cannot be located for loading.
    """
    spec = importlib.util.spec_from_file_location("goal_run_report", REPORT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {REPORT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stamp(minute: int, second: int = 0) -> str:
    """Build a UTC timestamp string inside the fixture hour.

    Args:
        minute: Minute of the hour.
        second: Second of the minute.

    Returns:
        An ISO 8601 timestamp ending in Z.
    """
    return f"2026-11-11T{BASE_HOUR:02d}:{minute:02d}:{second:02d}.000Z"


def agent_call(minute: int, call_id: str, description: str) -> dict[str, object]:
    """Build a parent assistant entry holding an Agent tool_use.

    Args:
        minute: Minute of the fixture hour.
        call_id: The tool_use id.
        description: The dispatch description.

    Returns:
        A transcript entry.
    """
    block = {
        "type": "tool_use",
        "id": call_id,
        "name": "Agent",
        "input": {"description": description, "subagent_type": "bpe:step-executor"},
    }
    return {"type": "assistant", "timestamp": stamp(minute), "message": {"id": f"m-{call_id}", "content": [block]}}


def agent_result(minute: int, call_id: str) -> dict[str, object]:
    """Build the immediate async tool_result that carries the agent id.

    Args:
        minute: Minute of the fixture hour.
        call_id: The tool_use id being answered.

    Returns:
        A transcript entry.
    """
    return {
        "type": "user",
        "timestamp": stamp(minute, 1),
        "toolUseResult": {"agentId": AGENT_ID, "resolvedModel": "test-model"},
        "message": {"content": [{"type": "tool_result", "tool_use_id": call_id}]},
    }


def send_call(minute: int, call_id: str, summary: str) -> dict[str, object]:
    """Build a parent assistant entry holding a SendMessage tool_use.

    Args:
        minute: Minute of the fixture hour.
        call_id: The tool_use id.
        summary: The continuation summary.

    Returns:
        A transcript entry.
    """
    block = {
        "type": "tool_use",
        "id": call_id,
        "name": "SendMessage",
        "input": {"to": AGENT_ID, "summary": summary, "message": "Mode: fix"},
    }
    return {"type": "assistant", "timestamp": stamp(minute), "message": {"id": f"m-{call_id}", "content": [block]}}


def sub_turn(minute: int, second: int, cache_read: int = 100, output: int = 10) -> dict[str, object]:
    """Build one subagent assistant entry with usage.

    Args:
        minute: Minute of the fixture hour.
        second: Second of the minute.
        cache_read: Cache-read tokens to record.
        output: Output tokens to record.

    Returns:
        A transcript entry.
    """
    usage = {"cache_read_input_tokens": cache_read, "output_tokens": output}
    return {
        "type": "assistant",
        "timestamp": stamp(minute, second),
        "message": {"id": f"s-{minute}-{second}", "usage": usage, "content": [{"type": "text", "text": "x"}]},
    }


def write_lines(path: Path, entries: Sequence[dict[str, object]]) -> None:
    """Write entries as JSON lines, creating parent directories.

    Args:
        path: File to write.
        entries: Entries to serialize, one per line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8")


def build_session(tmp_path: Path, parent: Sequence[dict[str, object]], sub: Sequence[dict[str, object]]) -> Path:
    """Write a parent transcript and the subagent transcript beside it.

    Args:
        tmp_path: Test directory.
        parent: Parent transcript entries.
        sub: Entries for the subagent transcript of AGENT_ID.

    Returns:
        The parent transcript path.
    """
    session = tmp_path / "session.jsonl"
    write_lines(session, parent)
    write_lines(tmp_path / "session" / "subagents" / f"agent-{AGENT_ID}.jsonl", sub)
    return session


def warm_batch() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Build an implement dispatch with two SendMessage continuations.

    Returns:
        The parent entries and the subagent entries.
    """
    parent = [
        agent_call(0, "t1", "Implement batch x"),
        agent_result(0, "t1"),
        send_call(10, "t2", "Fix pass 1"),
        send_call(20, "t3", "Finalize batch x"),
    ]
    sub = [
        sub_turn(1, 0, cache_read=100),
        sub_turn(2, 0, cache_read=200),
        sub_turn(11, 0, cache_read=300),
        sub_turn(21, 0, cache_read=400),
        sub_turn(23, 0, cache_read=500),
    ]
    return parent, sub


class TestContinuationAttribution:
    """A SendMessage continuation owns the entries between its start and the next dispatch."""

    def test_three_rows_sum_to_the_file_total(self, report: ModuleType, tmp_path: Path) -> None:
        parent, sub = warm_batch()
        session = build_session(tmp_path, parent, sub)

        dispatches, _ = report.scan_parent(session, None, None)
        report.resolve_continuations(dispatches)
        report.attribute_usage(session, dispatches, None)

        assert [dispatch.usage.cache_read for dispatch in dispatches] == [300, 300, 900]
        assert sum(dispatch.usage.cache_read for dispatch in dispatches) == 1500
        assert sum(dispatch.usage.turns for dispatch in dispatches) == 5

    def test_each_entry_goes_to_the_window_that_contains_it(self, report: ModuleType, tmp_path: Path) -> None:
        parent, sub = warm_batch()
        session = build_session(tmp_path, parent, sub)

        dispatches, _ = report.scan_parent(session, None, None)
        report.resolve_continuations(dispatches)
        report.attribute_usage(session, dispatches, None)

        assert [dispatch.usage.turns for dispatch in dispatches] == [2, 1, 2]
        assert dispatches[2].usage.minutes == pytest.approx(2.0)

    def test_entry_outside_every_window_is_not_attributed(self, report: ModuleType, tmp_path: Path) -> None:
        parent, sub = warm_batch()
        sub = [*sub, sub_turn(25, 0, cache_read=7000)]
        later = datetime(2026, 11, 11, BASE_HOUR, 22, tzinfo=UTC)
        session = build_session(tmp_path, parent, sub)

        dispatches, _ = report.scan_parent(session, None, None)
        report.resolve_continuations(dispatches)
        report.attribute_usage(session, dispatches, later)

        assert sum(dispatch.usage.cache_read for dispatch in dispatches) == 100 + 200 + 300 + 400
        assert dispatches[0].usage.cache_read == 300

    def test_cold_dispatch_without_continuations_keeps_the_whole_file(self, report: ModuleType, tmp_path: Path) -> None:
        parent = [agent_call(0, "t1", "Implement batch x"), agent_result(0, "t1")]
        sub = [sub_turn(1, 0, cache_read=100), sub_turn(2, 0, cache_read=200), sub_turn(40, 0, cache_read=50)]
        session = build_session(tmp_path, parent, sub)

        dispatches, _ = report.scan_parent(session, None, None)
        report.resolve_continuations(dispatches)
        report.attribute_usage(session, dispatches, None)

        assert len(dispatches) == 1
        assert dispatches[0].usage.cache_read == 350
        assert dispatches[0].usage.turns == 3

    def test_cold_dispatch_drops_entries_after_until(self, report: ModuleType, tmp_path: Path) -> None:
        parent = [agent_call(0, "t1", "Implement batch x"), agent_result(0, "t1")]
        sub = [sub_turn(1, 0, cache_read=100), sub_turn(40, 0, cache_read=50)]
        session = build_session(tmp_path, parent, sub)
        until = datetime(2026, 11, 11, BASE_HOUR, 30, tzinfo=UTC)

        dispatches, _ = report.scan_parent(session, None, None)
        report.resolve_continuations(dispatches)
        report.attribute_usage(session, dispatches, until)

        assert dispatches[0].usage.cache_read == 100
        assert dispatches[0].usage.turns == 1


class TestMain:
    """main() prints continuation rows with their own usage."""

    def test_continuation_rows_show_minutes_and_cache_read(
        self, report: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        parent, sub = warm_batch()
        session = build_session(tmp_path, parent, sub)

        assert report.main([str(session)]) == 0

        rows = [line for line in capsys.readouterr().out.splitlines() if "(continuation)" in line]
        assert len(rows) == 2
        finalize_cells = [cell.strip() for cell in rows[1].strip("|").split("|")]
        assert finalize_cells[5] == "2.0"
        assert finalize_cells[9] == "900"
