# ABOUTME: Tests that the newest Recommended Tier Map entry carries a machine-readable YAML profile block.
# ABOUTME: /bpe:init reads that block at run time, so it must parse and name only shipped skills and agents.
"""Schema check for the YAML profile block in bpe/references/model-profiles.md."""

import re
from pathlib import Path
from typing import TypedDict

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PROFILES_PATH = REPO_ROOT / "bpe" / "references" / "model-profiles.md"
SKILLS_DIR = REPO_ROOT / "bpe" / "skills"
AGENTS_DIR = REPO_ROOT / "bpe" / "agents"

ALIASES = {"opus", "sonnet", "haiku"}
PINNED_ID = re.compile(r"claude-[a-z]+-[0-9]+(-[0-9]+)*")
DATED_HEADING = re.compile(r"^### (\d{4}-\d{2}-\d{2})\b")
FENCE_OPEN = "```yaml"
FENCE_CLOSE = "```"


def newest_entry_lines() -> list[str]:
    """Return the lines under the newest dated heading of "## Recommended Tier Map", heading excluded."""
    lines = PROFILES_PATH.read_text().splitlines()
    start = lines.index("## Recommended Tier Map")
    dated = [
        (line_index, heading_match[1])
        for line_index, line in enumerate(lines[start:], start)
        if (heading_match := DATED_HEADING.match(line))
    ]
    newest_index, _ = max(dated, key=lambda pair: pair[1])
    end = next(
        (line_index for line_index in range(newest_index + 1, len(lines)) if lines[line_index].startswith("#")),
        len(lines),
    )
    return lines[newest_index + 1 : end]


def yaml_blocks(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current: list[str] | None = None
    for line in lines:
        if current is None:
            if line.strip() == FENCE_OPEN:
                current = []
        elif line.strip() == FENCE_CLOSE:
            blocks.append("\n".join(current))
            current = None
        else:
            current.append(line)
    return blocks


class ProfileBlock(TypedDict):
    active_profile: str
    profiles: dict[str, dict[str, dict[str, str]]]


def string_map(value: object, where: str) -> dict[str, str]:
    assert isinstance(value, dict), f"{where} is not a mapping"
    result: dict[str, str] = {}
    for key, item in value.items():
        assert isinstance(key, str), f"{where} has a non-string key {key!r}"
        assert isinstance(item, str), f"{where}.{key} is not a string"
        result[key] = item
    return result


def parse_profile_block(text: str) -> ProfileBlock:
    parsed: object = yaml.safe_load(text)
    assert isinstance(parsed, dict)
    active_profile = parsed.get("active_profile")
    assert isinstance(active_profile, str), "active_profile is not a string"
    raw_profiles = parsed.get("profiles")
    assert isinstance(raw_profiles, dict), "profiles is not a mapping"
    profiles: dict[str, dict[str, dict[str, str]]] = {}
    for name, raw_profile in raw_profiles.items():
        assert isinstance(name, str), f"profile name {name!r} is not a string"
        assert isinstance(raw_profile, dict), f"profile {name} is not a mapping"
        profiles[name] = {group: string_map(members, f"{name}.{group}") for group, members in raw_profile.items()}
    return {"active_profile": active_profile, "profiles": profiles}


@pytest.fixture
def profile_block() -> ProfileBlock:
    blocks = yaml_blocks(newest_entry_lines())
    assert len(blocks) == 1, f"expected exactly one yaml block under the newest heading, found {len(blocks)}"
    return parse_profile_block(blocks[0])


def test_block_has_active_profile_naming_a_profile(profile_block: ProfileBlock) -> None:
    assert profile_block["active_profile"] in profile_block["profiles"]


def test_every_skill_key_names_a_shipped_skill(profile_block: ProfileBlock) -> None:
    shipped = {path.name for path in SKILLS_DIR.iterdir() if path.is_dir()}
    for name, profile in profile_block["profiles"].items():
        unknown = set(profile.get("skills", {})) - shipped
        assert not unknown, f"profile {name} names skills that do not ship: {sorted(unknown)}"


def test_every_agent_key_names_a_shipped_agent(profile_block: ProfileBlock) -> None:
    shipped = {path.stem for path in AGENTS_DIR.glob("*.md")}
    for name, profile in profile_block["profiles"].items():
        unknown = set(profile.get("agents", {})) - shipped
        assert not unknown, f"profile {name} names agents that do not ship: {sorted(unknown)}"


def test_every_value_is_an_alias_or_a_pinned_id(profile_block: ProfileBlock) -> None:
    for name, profile in profile_block["profiles"].items():
        for group in ("skills", "agents"):
            for key, value in profile.get(group, {}).items():
                assert value in ALIASES or PINNED_ID.fullmatch(value), f"{name}.{group}.{key}: {value!r}"
