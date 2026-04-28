import re
from pathlib import Path

import pytest

AGENTS_DIR = Path(__file__).resolve().parent.parent / "ai" / "modules" / "opencode" / "agents"


def _get_agent_files() -> list[str]:
    if not AGENTS_DIR.exists():
        return []
    return [f.stem for f in AGENTS_DIR.glob("*.md")]


@pytest.mark.parametrize("agent_name", _get_agent_files())
def test_agent_has_valid_frontmatter(agent_name: str) -> None:
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    content = agent_path.read_text()

    assert content.startswith("---"), f"{agent_path}: missing YAML frontmatter delimiter"

    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{agent_path}: malformed frontmatter (missing closing ---)"

    yaml_content = parts[1].strip()
    frontmatter: dict[str, str] = {}
    for line in yaml_content.split("\n"):
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    assert "description" in frontmatter, f"{agent_path}: missing 'description' in frontmatter"
    assert len(frontmatter["description"]) > 0, f"{agent_path}: empty description"


@pytest.mark.parametrize("agent_name", _get_agent_files())
def test_agent_has_body(agent_name: str) -> None:
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    content = agent_path.read_text()

    parts = content.split("---", 2)
    body = parts[2].strip() if len(parts) >= 3 else ""
    assert len(body) > 0, f"{agent_path}: empty body"


@pytest.mark.parametrize("agent_name", _get_agent_files())
def test_agent_color_is_valid_hex(agent_name: str) -> None:
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    content = agent_path.read_text()

    parts = content.split("---", 2)
    yaml_content = parts[1] if len(parts) >= 3 else ""

    color_match = re.search(r'^color:\s*["\']?(#[0-9A-Fa-f]+)["\']?', yaml_content, re.MULTILINE)
    if color_match is None:
        pytest.skip(f"Agent '{agent_name}' has no color field")

    color = color_match.group(1)
    assert re.fullmatch(r"#[0-9A-Fa-f]{6}", color), (
        f"{agent_path}: invalid hex color '{color}' (expected #RRGGBB)"
    )


@pytest.mark.parametrize("agent_name", _get_agent_files())
def test_agent_tools_is_mapping(agent_name: str) -> None:
    agent_path = AGENTS_DIR / f"{agent_name}.md"
    content = agent_path.read_text()

    parts = content.split("---", 2)
    yaml_content = parts[1] if len(parts) >= 3 else ""

    tools_match = re.search(r"^tools:\s*$", yaml_content, re.MULTILINE)
    if tools_match is None:
        pytest.skip(f"Agent '{agent_name}' has no tools field")

    block_start = tools_match.end()
    block_lines: list[str] = []
    for line in yaml_content[block_start:].splitlines():
        if line and not line.startswith((" ", "\t")):
            break
        if line.strip():
            block_lines.append(line)

    assert block_lines, f"{agent_path}: 'tools:' block is empty"

    for line in block_lines:
        stripped = line.strip()
        assert not stripped.startswith("-"), (
            f"{agent_path}: 'tools' must be a mapping (key: true), not a list. "
            f"Offending line: {line!r}"
        )
        assert re.match(r"^\s+[A-Za-z_][A-Za-z0-9_]*:\s*(true|false)\s*$", line), (
            f"{agent_path}: invalid tools entry {line!r} "
            "(expected '  <tool>: true' or '  <tool>: false')"
        )
