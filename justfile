# ABOUTME: Task runner recipes; `just check` is the local gate (no pre-commit).
# ABOUTME: `just test-all` runs the supported Python version matrix locally.

default:
    @just --list

check:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy .
    uv run pytest

fmt:
    uv run ruff format .
    uv run ruff check --fix .

test:
    uv run pytest

test-all:
    #!/usr/bin/env bash
    set -euo pipefail
    for python_version in 3.11 3.12 3.13 3.14; do
        uv run --python "$python_version" -m pytest
    done
