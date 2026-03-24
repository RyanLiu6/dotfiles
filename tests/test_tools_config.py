import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def tools_config(ai_root: Path) -> dict[str, Any]:
    config_path = ai_root / "tools.json"
    assert config_path.exists(), "tools.json not found"
    with open(config_path) as f:
        config: dict[str, Any] = json.load(f)
    return config


REQUIRED_TOOL_FIELDS = ["name", "config_dir", "tool_dir"]


def _get_tool_ids() -> list[str]:
    config_path = Path(__file__).resolve().parent.parent / "ai" / "tools.json"
    with open(config_path) as f:
        config: dict[str, Any] = json.load(f)
    return list(config["tools"].keys())


def test_tools_config(tools_config: dict[str, Any]) -> None:
    assert "tools" in tools_config
    assert len(tools_config["tools"]) > 0


@pytest.mark.parametrize("tool_id", _get_tool_ids())
def test_tool_has_required_fields(tool_id: str, tools_config: dict[str, Any]) -> None:
    assert tool_id in tools_config["tools"], f"Tool '{tool_id}' not in tools.json"

    tool = tools_config["tools"][tool_id]
    for field in REQUIRED_TOOL_FIELDS:
        assert field in tool, f"Tool '{tool_id}' missing required field '{field}'"


@pytest.mark.parametrize("tool_id", _get_tool_ids())
def test_tool_dir_exists(tool_id: str, tools_config: dict[str, Any], ai_root: Path) -> None:
    tool = tools_config["tools"][tool_id]
    tool_dir = ai_root / tool["tool_dir"]
    assert tool_dir.exists(), f"Tool '{tool_id}' tool_dir does not exist: {tool_dir}"


@pytest.mark.parametrize("tool_id", _get_tool_ids())
def test_tool_symlink_sources_exist(
    tool_id: str, tools_config: dict[str, Any], ai_root: Path
) -> None:
    tool = tools_config["tools"][tool_id]
    tool_dir = ai_root / tool["tool_dir"]

    template_targets = set()
    if "settings_template" in tool:
        template_targets.add(tool["settings_template"]["target"])

    for symlink in tool.get("symlinks", []):
        if symlink["source"] in template_targets:
            continue
        source = tool_dir / symlink["source"]
        assert source.exists(), f"Tool '{tool_id}' symlink source does not exist: {source}"


def test_tool_skills_source_exists(tools_config: dict[str, Any], ai_root: Path) -> None:
    for tool_id, tool in tools_config["tools"].items():
        if "skills_symlink" in tool:
            source = ai_root / tool["skills_symlink"]["source"]
            assert source.exists(), (
                f"Tool '{tool_id}' skills_symlink source does not exist: {source}"
            )

        if "skills_generate" in tool:
            source = ai_root / tool["skills_generate"]["source"]
            assert source.exists(), (
                f"Tool '{tool_id}' skills_generate source does not exist: {source}"
            )


def test_memory_generate_source_exists(tools_config: dict[str, Any], ai_root: Path) -> None:
    for tool_id, tool in tools_config["tools"].items():
        if "memory_generate" in tool:
            source = ai_root / tool["memory_generate"]["source"]
            assert source.exists(), (
                f"Tool '{tool_id}' memory_generate source does not exist: {source}"
            )
            mode = tool["memory_generate"]["mode"]
            assert mode in ("single_file", "directory"), (
                f"Tool '{tool_id}' memory_generate has invalid mode: {mode}"
            )


def test_agents_symlink_source_exists(tools_config: dict[str, Any], ai_root: Path) -> None:
    for tool_id, tool in tools_config["tools"].items():
        if "agents_symlink" in tool:
            source = ai_root / tool["agents_symlink"]["source"]
            assert source.exists(), (
                f"Tool '{tool_id}' agents_symlink source does not exist: {source}"
            )
            assert source.is_dir(), (
                f"Tool '{tool_id}' agents_symlink source is not a directory: {source}"
            )


def test_extra_skills_dirs_exist(tools_config: dict[str, Any], ai_root: Path) -> None:
    for _tool_id, tool in tools_config["tools"].items():
        for extra_dir in tool.get("extra_skills_dirs", []):
            path = ai_root / extra_dir
            if not path.exists():
                pytest.skip(f"Optional extra_skills_dir '{extra_dir}' not present (local-only)")
            assert path.is_dir()


@pytest.mark.parametrize("tool_id", _get_tool_ids())
def test_settings_template_exists(
    tool_id: str, tools_config: dict[str, Any], ai_root: Path
) -> None:
    tool = tools_config["tools"][tool_id]
    if "settings_template" not in tool:
        pytest.skip(f"Tool '{tool_id}' has no settings_template")

    template_path = ai_root / tool["tool_dir"] / tool["settings_template"]["template"]
    assert template_path.exists(), f"Template not found: {template_path}"

    with open(template_path) as f:
        content = json.load(f)
    assert isinstance(content, dict)


def test_claude_template_has_no_work_config(ai_root: Path) -> None:
    template_path = ai_root / "modules" / "claude" / "settings.template.json"
    parsed = json.loads(template_path.read_text())

    assert "env" not in parsed, "Template should not contain env vars"


def test_claude_template_only_official_plugins(ai_root: Path) -> None:
    template_path = ai_root / "modules" / "claude" / "settings.template.json"
    config = json.loads(template_path.read_text())

    for plugin_key in config.get("enabledPlugins", {}):
        assert plugin_key.endswith("@claude-plugins-official"), (
            f"Non-official plugin in template: {plugin_key}"
        )
