#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Validate a bpe:validator findings JSON block against the canonical schema.

Usage:
    validate-findings.py            # read JSON from stdin
    validate-findings.py FILE       # read JSON from FILE
    validate-findings.py -          # read JSON from stdin (explicit)

Caps (a longer value is malformed, exit 1):
    finding message  at most 240 characters (MAX_MESSAGE_CHARS)
    top-level notes  at most 80 words (MAX_NOTES_WORDS)

Exit codes:
    0  Input is well-formed; canonical JSON is written to stdout.
    1  Input is malformed; a human-readable error is written to stderr.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NoReturn

SEVERITIES = frozenset({"block", "warn", "info"})
VERDICTS = frozenset({"block", "warn", "clean"})
REQUIRED_TOP = frozenset({"validator", "verdict", "findings", "iter"})
OPTIONAL_TOP = frozenset({"notes"})
REQUIRED_FINDING = frozenset({"severity", "file", "message"})
OPTIONAL_FINDING = frozenset({"line", "rule", "suggested_fix", "reference"})
MAX_MESSAGE_CHARS = 240
MAX_NOTES_WORDS = 80


def fail(msg: str) -> NoReturn:
    """Write an error to stderr and exit 1.

    Args:
        msg: Human-readable description of the schema violation.
    """
    sys.stderr.write(f"validate-findings: {msg}\n")
    sys.exit(1)


def check_top(data: object) -> dict[str, object]:
    """Check the top-level object of a findings block.

    Args:
        data: The parsed JSON value.

    Returns:
        The same object, narrowed to a dict, when it is well-formed.
        Exits 1 through `fail` otherwise, including when `notes` exceeds
        `MAX_NOTES_WORDS` words.
    """
    if not isinstance(data, dict):
        fail(f"top-level value must be a JSON object, got {type(data).__name__}")
    keys = set(data.keys())
    missing = REQUIRED_TOP - keys
    if missing:
        fail(f"missing required top-level keys: {sorted(missing)}")
    unknown = keys - REQUIRED_TOP - OPTIONAL_TOP
    if unknown:
        fail(f"unknown top-level keys: {sorted(unknown)}")
    if not isinstance(data["validator"], str) or not data["validator"]:
        fail("validator: must be a non-empty string")
    if data["verdict"] not in VERDICTS:
        fail(f"verdict: expected one of {sorted(VERDICTS)}, got {data['verdict']!r}")
    if not isinstance(data["iter"], int) or isinstance(data["iter"], bool) or data["iter"] < 1:
        fail(f"iter: must be a positive integer, got {data['iter']!r}")
    if not isinstance(data["findings"], list):
        fail(f"findings: must be a list, got {type(data['findings']).__name__}")
    if "notes" in data and not isinstance(data["notes"], str):
        fail(f"notes: must be a string, got {type(data['notes']).__name__}")
    if "notes" in data:
        words = len(data["notes"].split())
        if words > MAX_NOTES_WORDS:
            fail(f"notes: {words} words exceeds the {MAX_NOTES_WORDS}-word cap")
    return data


def check_finding(idx: int, f: object) -> None:
    """Check one finding object.

    Args:
        idx: Position of the finding in the `findings` list, used in errors.
        f: The parsed finding value.

    Returns:
        None when the finding is well-formed. Exits 1 through `fail`
        otherwise, including when `message` exceeds `MAX_MESSAGE_CHARS`
        characters.
    """
    prefix = f"findings[{idx}]"
    if not isinstance(f, dict):
        fail(f"{prefix}: must be an object, got {type(f).__name__}")
    keys = set(f.keys())
    missing = REQUIRED_FINDING - keys
    if missing:
        fail(f"{prefix}: missing required keys: {sorted(missing)}")
    unknown = keys - REQUIRED_FINDING - OPTIONAL_FINDING
    if unknown:
        fail(f"{prefix}: unknown keys: {sorted(unknown)}")
    if f["severity"] not in SEVERITIES:
        fail(
            f"{prefix}.severity: expected one of {sorted(SEVERITIES)}, "
            f"got {f['severity']!r}"
        )
    if not isinstance(f["file"], str) or not f["file"]:
        fail(f"{prefix}.file: must be a non-empty string")
    if not isinstance(f["message"], str) or not f["message"]:
        fail(f"{prefix}.message: must be a non-empty string")
    if len(f["message"]) > MAX_MESSAGE_CHARS:
        fail(
            f"{prefix}.message: {len(f['message'])} characters exceeds the "
            f"{MAX_MESSAGE_CHARS}-character cap"
        )
    if "line" in f and (
        not isinstance(f["line"], int) or isinstance(f["line"], bool) or f["line"] < 1
    ):
        fail(f"{prefix}.line: must be a positive integer, got {f['line']!r}")
    for opt in ("rule", "suggested_fix", "reference"):
        if opt in f and not isinstance(f[opt], str):
            fail(f"{prefix}.{opt}: must be a string, got {type(f[opt]).__name__}")


def finding_items(data: dict[str, object]) -> list[dict[str, object]]:
    """Return the findings of a validated block as a typed list.

    Args:
        data: A top-level object already accepted by `check_top` and whose
            findings all passed `check_finding`.

    Returns:
        The `findings` list, narrowed to a list of dicts.
    """
    findings = data["findings"]
    if not isinstance(findings, list):
        fail("findings: must be a list")
    return [f for f in findings if isinstance(f, dict)]


def check_consistency(data: dict[str, object]) -> None:
    """Check that the verdict matches the worst finding severity.

    Args:
        data: A top-level object already accepted by `check_top`.
    """
    severities = [f["severity"] for f in finding_items(data)]
    has_block = "block" in severities
    has_warn = "warn" in severities
    verdict = data["verdict"]
    if has_block and verdict != "block":
        fail(
            f"verdict mismatch: findings contain a 'block' severity but verdict is "
            f"{verdict!r}; expected 'block'"
        )
    if not has_block and has_warn and verdict != "warn":
        fail(
            f"verdict mismatch: findings contain 'warn' but no 'block', so verdict "
            f"must be 'warn'; got {verdict!r}"
        )
    if not has_block and not has_warn and verdict != "clean":
        fail(
            f"verdict mismatch: no 'block' or 'warn' findings, so verdict must be "
            f"'clean'; got {verdict!r}"
        )


def canonicalize(data: dict[str, object]) -> dict[str, object]:
    """Rebuild a validated block with keys in canonical order.

    Args:
        data: A block that passed every check.

    Returns:
        A new dict with top-level and finding keys in schema order.
    """
    canon_findings: list[dict[str, object]] = []
    canon: dict[str, object] = {
        "validator": data["validator"],
        "verdict": data["verdict"],
        "iter": data["iter"],
        "findings": canon_findings,
    }
    for f in finding_items(data):
        cf: dict[str, object] = {"severity": f["severity"], "file": f["file"]}
        if "line" in f:
            cf["line"] = f["line"]
        if "rule" in f:
            cf["rule"] = f["rule"]
        cf["message"] = f["message"]
        if "suggested_fix" in f:
            cf["suggested_fix"] = f["suggested_fix"]
        if "reference" in f:
            cf["reference"] = f["reference"]
        canon_findings.append(cf)
    if "notes" in data:
        canon["notes"] = data["notes"]
    return canon


def main() -> None:
    if len(sys.argv) > 2:
        fail("usage: validate-findings.py [PATH | -]   (default: stdin)")
    source = sys.argv[1] if len(sys.argv) == 2 else "-"
    try:
        raw = sys.stdin.read() if source == "-" else Path(source).read_text()
    except OSError as e:
        fail(f"cannot read {source!r}: {e}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        fail(f"input is not valid JSON: {e}")
    data = check_top(data)
    for i, f in enumerate(data["findings"]):
        check_finding(i, f)
    check_consistency(data)
    canon = canonicalize(data)
    sys.stdout.write(json.dumps(canon, indent=2, sort_keys=False) + "\n")


if __name__ == "__main__":
    main()
