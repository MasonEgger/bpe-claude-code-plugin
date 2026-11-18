#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
# ABOUTME: Measures a /bpe:goal run from its session transcript and the subagent transcripts beside it.
# ABOUTME: Prints per-dispatch, by-kind, and orchestrator tables so before and after runs share one arithmetic.
"""Report dispatch counts, subagent cost, and orchestrator cost for a goal run.

Usage:
    goal-run-report.py SESSION_JSONL [--since ISO] [--until ISO]

SESSION_JSONL is the parent transcript at ~/.claude/projects/<project>/<session>.jsonl.
The subagent transcripts are read from <session>/subagents/agent-<agentId>.jsonl
next to it.
--since and --until are inclusive ISO 8601 UTC bounds (for example
2026-11-09T22:40:00Z) applied to dispatch and orchestrator timestamps. A bound
with no offset (2026-11-09T22:40:00) is read as UTC.
Only counts, token totals, times, agent types, models, and dispatch descriptions
are printed; message bodies never are.

Turns counts assistant transcript entries. Claude Code can split one API response
across several entries that share a message id, so the API responses column counts
the unique message ids among the same entries. Every other figure is summed per
entry, with no deduplication.

Continuations (SendMessage) add a dispatch count and no second copy of the usage,
because each subagent transcript is summed once, under its Agent dispatch.
A continuation's kind is the first word of its summary when that names a known
kind (implement, validate, re-validate, fix, finalize, sweep). Otherwise it is the
word on a "Mode: <word>" line in the message, then the first word of the message's
first non-empty line, then other. The message is read only to pick the kind and is
never printed or stored. The printed label is the summary, or the placeholder
"continuation". The "to" field may be an agentId or an agent name; a name is
resolved through the "name" input of the Agent dispatches. A continuation whose
target resolves to neither is kept, counted, and shown with its raw "to" value.

Exit codes:
    0  Report written to stdout.
    1  The transcript path does not exist, or a bound is not a valid timestamp.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

JsonObject = dict[str, object]

KIND_BY_FIRST_WORD = {
    "implement": "implement",
    "validate": "validator",
    "re-validate": "validator",
    "fix": "fix",
    "finalize": "finalize",
    "sweep": "sweep",
}
MODE_LINE = re.compile(r"^\s*Mode:\s*(\S+)", re.IGNORECASE | re.MULTILINE)
KIND_ORDER = ("implement", "validator", "fix", "finalize", "sweep", "other")
USAGE_FIELDS = (
    "input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "output_tokens",
)


@dataclass
class Usage:
    """Token and activity totals for one transcript or one span of it."""

    turns: int = 0
    tools: int = 0
    input_tokens: int = 0
    cache_read: int = 0
    cache_create: int = 0
    output: int = 0
    message_ids: set[str] = field(default_factory=set)
    first: datetime | None = None
    last: datetime | None = None

    @property
    def responses(self) -> int:
        """Unique API responses among the entries summed so far."""
        return len(self.message_ids)

    @property
    def minutes(self) -> float:
        """Wall-clock minutes from the first to the last timestamp seen."""
        if self.first is None or self.last is None:
            return 0.0
        return (self.last - self.first).total_seconds() / 60


@dataclass
class Dispatch:
    """One Agent or SendMessage tool_use in the parent transcript."""

    start: datetime
    tool_use_id: str
    description: str
    subagent_type: str = "unknown"
    model: str = "unknown"
    agent_id: str | None = None
    name: str | None = None
    target: str | None = None
    continuation: bool = False
    kind: str = "other"
    usage: Usage = field(default_factory=Usage)


def parse_timestamp(text: str) -> datetime:
    """Parse an ISO 8601 timestamp, accepting a trailing Z.

    Args:
        text: Timestamp such as 2026-11-09T22:40:00Z or one with milliseconds.
            A value with no offset is read as UTC.

    Returns:
        A timezone-aware datetime.

    Raises:
        ValueError: If the text is not an ISO 8601 timestamp.
    """
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def parse_entry_timestamp(value: object) -> datetime | None:
    """Parse a transcript entry's timestamp field without raising.

    Args:
        value: The raw timestamp field of an entry.

    Returns:
        A timezone-aware datetime, or None when the field is missing or will not parse.
    """
    if not isinstance(value, str):
        return None
    try:
        return parse_timestamp(value)
    except ValueError:
        return None


def get_str(mapping: JsonObject, key: str) -> str | None:
    """Read a string field.

    Args:
        mapping: Parsed JSON object.
        key: Field name.

    Returns:
        The value when it is a string, otherwise None.
    """
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def get_dict(mapping: JsonObject, key: str) -> JsonObject:
    """Read an object field.

    Args:
        mapping: Parsed JSON object.
        key: Field name.

    Returns:
        The value when it is an object, otherwise an empty object.
    """
    value = mapping.get(key)
    return value if isinstance(value, dict) else {}


def get_int(mapping: JsonObject, key: str) -> int:
    """Read an integer field.

    Args:
        mapping: Parsed JSON object.
        key: Field name.

    Returns:
        The value when it is an integer, otherwise 0.
    """
    value = mapping.get(key)
    return value if isinstance(value, int) else 0


def read_entries(path: Path) -> Iterator[JsonObject]:
    """Stream the JSON object on each line of a transcript, skipping other lines.

    Args:
        path: Transcript file to read line by line.

    Yields:
        Each line that parses as a JSON object.
    """
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(entry, dict):
                yield entry


def content_blocks(entry: JsonObject) -> list[JsonObject]:
    """Return the content blocks of an entry's message, or an empty list.

    Args:
        entry: One transcript entry.

    Returns:
        The message content blocks when content is a list of objects.
    """
    content = get_dict(entry, "message").get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def add_assistant_entry(usage: Usage, entry: JsonObject, stamp: datetime) -> None:
    """Add one assistant entry's turn, tool_use blocks, and usage to a total.

    Args:
        usage: Running total to update in place.
        entry: An assistant transcript entry.
        stamp: The entry's parsed timestamp.
    """
    message = get_dict(entry, "message")
    raw_usage = get_dict(message, "usage")

    usage.turns += 1
    message_id = get_str(message, "id")
    if message_id:
        usage.message_ids.add(message_id)
    usage.tools += sum(1 for block in content_blocks(entry) if block.get("type") == "tool_use")
    usage.input_tokens += get_int(raw_usage, "input_tokens")
    usage.cache_read += get_int(raw_usage, "cache_read_input_tokens")
    usage.cache_create += get_int(raw_usage, "cache_creation_input_tokens")
    usage.output += get_int(raw_usage, "output_tokens")

    # Track the first and last timestamps for the minutes column.
    if usage.first is None or stamp < usage.first:
        usage.first = stamp
    if usage.last is None or stamp > usage.last:
        usage.last = stamp


def classify(description: str) -> str:
    """Classify a dispatch by the first word of its description.

    Args:
        description: The Agent tool_use description.

    Returns:
        implement, validator, fix, finalize, sweep, or other.
    """
    return kind_of_first_word(description) or "other"


def kind_of_first_word(text: str) -> str | None:
    """Map the first word of a text to a known dispatch kind.

    Args:
        text: A description, summary, or message line.

    Returns:
        The kind, or None when the text is empty or its first word is not a known kind.
    """
    words = text.split()
    if not words:
        return None
    return KIND_BY_FIRST_WORD.get(words[0].lower())


def classify_continuation(summary: str, message: str) -> str:
    """Classify a SendMessage continuation without keeping the message.

    Args:
        summary: The SendMessage summary, possibly empty.
        message: The SendMessage body, read only to pick a kind.

    Returns:
        The kind from the summary's first word, else a "Mode: <word>" line in the
        message, else the first word of the message's first non-empty line, else other.
    """
    kind = kind_of_first_word(summary)
    if kind:
        return kind
    mode_match = MODE_LINE.search(message)
    if mode_match:
        kind = KIND_BY_FIRST_WORD.get(mode_match.group(1).lower())
        if kind:
            return kind
    for line in message.splitlines():
        if line.strip():
            return kind_of_first_word(line) or "other"
    return "other"


def subagent_usage(session: Path, agent_id: str) -> Usage:
    """Sum assistant usage over one subagent transcript.

    Args:
        session: Parent transcript path; subagents live in <stem>/subagents/.
        agent_id: The agentId from the Agent tool_result.

    Returns:
        Totals for the subagent, all zero when its transcript is missing.
    """
    usage = Usage()
    path = session.with_suffix("") / "subagents" / f"agent-{agent_id}.jsonl"
    if not path.is_file():
        return usage
    for entry in read_entries(path):
        stamp = parse_entry_timestamp(entry.get("timestamp"))
        if get_str(entry, "type") != "assistant" or stamp is None:
            continue
        add_assistant_entry(usage, entry, stamp)
    return usage


def scan_parent(
    session: Path, since: datetime | None, until: datetime | None
) -> tuple[list[Dispatch], Usage]:
    """Stream the parent transcript once for dispatches and orchestrator usage.

    Args:
        session: Parent transcript path.
        since: Inclusive lower bound, or None for no lower bound.
        until: Inclusive upper bound, or None for no upper bound.

    Returns:
        The in-span dispatches (Agent first, then continuations, in file order)
        with agent ids and models filled in, and the orchestrator usage in span.
    """
    dispatches: list[Dispatch] = []
    by_tool_use: dict[str, Dispatch] = {}
    orchestrator = Usage()

    for entry in read_entries(session):
        stamp = parse_entry_timestamp(entry.get("timestamp"))
        if stamp is None:
            continue
        in_span = (since is None or stamp >= since) and (until is None or stamp <= until)

        entry_type = get_str(entry, "type")
        if entry_type == "assistant":
            if not in_span:
                continue
            add_assistant_entry(orchestrator, entry, stamp)
            for block in content_blocks(entry):
                if block.get("type") != "tool_use":
                    continue
                name = get_str(block, "name")
                tool_input = get_dict(block, "input")
                if name == "Agent":
                    dispatch = Dispatch(
                        start=stamp,
                        tool_use_id=get_str(block, "id") or "",
                        description=get_str(tool_input, "description") or "",
                        subagent_type=get_str(tool_input, "subagent_type") or "general-purpose",
                        name=get_str(tool_input, "name"),
                    )
                    dispatch.kind = classify(dispatch.description)
                elif name == "SendMessage":
                    summary = get_str(tool_input, "summary") or ""
                    dispatch = Dispatch(
                        start=stamp,
                        tool_use_id=get_str(block, "id") or "",
                        description=summary or "continuation",
                        target=get_str(tool_input, "to"),
                        continuation=True,
                    )
                    dispatch.kind = classify_continuation(
                        summary, get_str(tool_input, "message") or ""
                    )
                else:
                    continue
                dispatches.append(dispatch)
                by_tool_use[dispatch.tool_use_id] = dispatch

        elif entry_type == "user":
            result = get_dict(entry, "toolUseResult")
            result_agent_id = get_str(result, "agentId")
            if not result_agent_id:
                continue
            for block in content_blocks(entry):
                if get_str(block, "type") != "tool_result":
                    continue
                dispatch = by_tool_use.get(get_str(block, "tool_use_id") or "")
                if dispatch is not None and not dispatch.continuation:
                    dispatch.agent_id = result_agent_id
                    dispatch.model = get_str(result, "resolvedModel") or "unknown"

    return dispatches, orchestrator


def resolve_continuations(dispatches: list[Dispatch]) -> int:
    """Point each continuation at the agentId it addresses.

    The "to" value may be an agentId of a dispatch in the span or an agent name
    from an Agent dispatch's "name" input.

    Args:
        dispatches: The in-span dispatches, updated in place.

    Returns:
        The number of continuations whose target resolved to neither.
    """
    known_ids: set[str] = set()
    ids_by_name: dict[str, str] = {}
    for dispatch in dispatches:
        if dispatch.continuation or not dispatch.agent_id:
            continue
        known_ids.add(dispatch.agent_id)
        if dispatch.name:
            ids_by_name[dispatch.name] = dispatch.agent_id

    unresolved = 0
    for dispatch in dispatches:
        if not dispatch.continuation:
            continue
        target = dispatch.target or ""
        if target in known_ids:
            dispatch.agent_id = target
        elif target in ids_by_name:
            dispatch.agent_id = ids_by_name[target]
        else:
            unresolved += 1
    return unresolved


def format_row(cells: list[str]) -> str:
    """Join cells into one Markdown table row.

    Args:
        cells: Already formatted cell text.

    Returns:
        A pipe-delimited row.
    """
    return "| " + " | ".join(cells) + " |"


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """Print a Markdown table.

    Args:
        headers: Column titles.
        rows: Cell text per row.
    """
    print(format_row(headers))
    print(format_row(["---"] * len(headers)))
    for row in rows:
        print(format_row(row))


def main(argv: list[str] | None = None) -> int:
    """Run the report.

    Args:
        argv: Command-line arguments, or None to use sys.argv.

    Returns:
        The process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Report dispatch counts and token cost for a /bpe:goal run."
    )
    parser.add_argument("session", type=Path, help="parent session transcript (.jsonl)")
    parser.add_argument(
        "--since",
        help="inclusive lower bound, ISO 8601 UTC such as 2026-11-09T22:40:00Z "
        "(no offset is read as UTC)",
    )
    parser.add_argument(
        "--until",
        help="inclusive upper bound, ISO 8601 UTC such as 2026-11-10T01:00:00Z "
        "(no offset is read as UTC)",
    )
    args = parser.parse_args(argv)

    if not args.session.is_file():
        sys.stderr.write(f"goal-run-report: transcript not found: {args.session}\n")
        return 1

    try:
        since = parse_timestamp(args.since) if args.since else None
        until = parse_timestamp(args.until) if args.until else None
    except ValueError as error:
        sys.stderr.write(f"goal-run-report: invalid timestamp: {error}\n")
        return 1

    dispatches, orchestrator = scan_parent(args.session, since, until)
    unresolved = resolve_continuations(dispatches)

    # Cost is per agent id, so a continuation adds a dispatch but no second cost.
    costs: dict[str, Usage] = {}
    for dispatch in dispatches:
        if dispatch.agent_id and dispatch.agent_id not in costs:
            costs[dispatch.agent_id] = subagent_usage(args.session, dispatch.agent_id)
        if dispatch.agent_id and not dispatch.continuation:
            dispatch.usage = costs[dispatch.agent_id]

    print("## Per-Dispatch")
    print()
    rows = [
        [
            dispatch.start.strftime("%H:%M"),
            dispatch.subagent_type + continuation_label(dispatch),
            dispatch.model,
            dispatch.kind,
            dispatch.description,
            f"{dispatch.usage.minutes:.1f}",
            f"{dispatch.usage.turns:,}",
            f"{dispatch.usage.responses:,}",
            f"{dispatch.usage.tools:,}",
            f"{dispatch.usage.cache_read:,}",
            f"{dispatch.usage.cache_create:,}",
            f"{dispatch.usage.output:,}",
        ]
        for dispatch in dispatches
    ]
    print_table(
        [
            "Start (UTC)", "Agent", "Model", "Kind", "Dispatch", "Min",
            "Turns", "API responses", "Tools", "Cache-read", "Cache-create", "Output",
        ],
        rows,
    )

    print()
    print("## By Kind")
    print()
    kind_rows: list[list[str]] = []
    total = Usage()
    total_count = 0
    for kind in KIND_ORDER:
        members = [dispatch for dispatch in dispatches if dispatch.kind == kind]
        if not members:
            continue
        # Minutes, tokens, and tools count each dispatch once; continuations add none.
        own = [dispatch for dispatch in members if not dispatch.continuation]
        minutes = sum(dispatch.usage.minutes for dispatch in own)
        cache_read = sum(dispatch.usage.cache_read for dispatch in own)
        cache_create = sum(dispatch.usage.cache_create for dispatch in own)
        output = sum(dispatch.usage.output for dispatch in own)
        total.cache_read += cache_read
        total.cache_create += cache_create
        total.output += output
        total_count += len(members)
        kind_rows.append(
            [
                kind, f"{len(members):,}", f"{minutes:.1f}",
                f"{cache_read:,}", f"{cache_create:,}", f"{output:,}",
            ]
        )
    kind_rows.append(
        [
            "all subagents", f"{total_count:,}",
            f"{sum(row_minutes(dispatch) for dispatch in dispatches):.1f}",
            f"{total.cache_read:,}", f"{total.cache_create:,}", f"{total.output:,}",
        ]
    )
    print_table(
        ["Kind", "Dispatches", "Minutes", "Cache-read", "Cache-create", "Output"],
        kind_rows,
    )

    print()
    print("## Orchestrator")
    print()
    print_table(
        ["Assistant turns", "API responses", "Cache-read", "Cache-create", "Output"],
        [
            [
                f"{orchestrator.turns:,}",
                f"{orchestrator.responses:,}",
                f"{orchestrator.cache_read:,}",
                f"{orchestrator.cache_create:,}",
                f"{orchestrator.output:,}",
            ]
        ],
    )
    if unresolved:
        print()
        print(f"Continuations with an unresolved target: {unresolved}")
    return 0


def continuation_label(dispatch: Dispatch) -> str:
    """Return the Agent column suffix for a dispatch.

    Args:
        dispatch: One dispatch.

    Returns:
        An empty string for an Agent dispatch, otherwise the continuation marker,
        with the raw "to" value when the target did not resolve.
    """
    if not dispatch.continuation:
        return ""
    if dispatch.agent_id is None:
        return f" (continuation, unresolved to={dispatch.target})"
    return " (continuation)"


def row_minutes(dispatch: Dispatch) -> float:
    """Return the minutes a dispatch adds to the subagent total.

    Args:
        dispatch: One dispatch.

    Returns:
        Zero for a continuation, otherwise the subagent transcript minutes.
    """
    return 0.0 if dispatch.continuation else dispatch.usage.minutes


if __name__ == "__main__":
    sys.exit(main())
