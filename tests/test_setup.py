from pathlib import Path
from textwrap import dedent
from typing import cast
from unittest.mock import MagicMock

import pytest

from scripts.setup import (
    ToolConfig,
    apply_work_overlay,
    convert_md_to_toml,
    ensure_settings_from_template,
    find_skill_files,
    generate_memory,
    parse_frontmatter,
    run_bootstrap,
    setup_tool,
)


def test_parse_frontmatter() -> None:
    content = dedent("""\
        ---
        name: test-skill
        description: A test skill
        ---

        # Body content
    """)
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["name"] == "test-skill"
    assert frontmatter["description"] == "A test skill"
    assert "# Body content" in body


def test_parse_frontmatter_no_frontmatter() -> None:
    content = "# Just a heading\n\nSome content."
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter == {}
    assert body == content


def test_parse_frontmatter_empty_values() -> None:
    content = dedent("""\
        ---
        name: my-skill
        description:
        ---

        Body here.
    """)
    frontmatter, body = parse_frontmatter(content)

    assert frontmatter["name"] == "my-skill"
    assert frontmatter["description"] == ""
    assert "Body here." in body


def test_convert_md_to_toml(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        dedent("""\
        ---
        name: test-skill
        description: A test skill for conversion
        ---

        # Test Skill

        Do the thing.
    """)
    )

    result = convert_md_to_toml(skill_file)

    assert 'description = "A test skill for conversion"' in result
    assert 'prompt = """' in result
    assert "# Test Skill" in result
    assert "Do the thing." in result
    assert result.rstrip().endswith('"""')


def test_convert_md_to_toml_no_frontmatter(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# Just content\n\nNo frontmatter here.")

    result = convert_md_to_toml(skill_file)

    assert 'description = "' not in result
    assert 'prompt = """' in result
    assert "# Just content" in result


def test_find_skill_files(tmp_path: Path) -> None:
    skill_a = tmp_path / "skill-a"
    skill_a.mkdir()
    (skill_a / "SKILL.md").write_text("---\nname: skill-a\n---\n# A")

    skill_b = tmp_path / "skill-b"
    skill_b.mkdir()
    (skill_b / "SKILL.md").write_text("---\nname: skill-b\n---\n# B")

    (tmp_path / "not-a-skill").mkdir()

    skills = find_skill_files(tmp_path)
    names = sorted([name for name, _ in skills])

    assert names == ["skill-a", "skill-b"]


def test_find_skill_files_ignores_readme(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Skills readme")
    skill = tmp_path / "my-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("---\nname: my-skill\n---\n# Skill")

    skills = find_skill_files(tmp_path)
    names = [name for name, _ in skills]

    assert "README" not in names
    assert "my-skill" in names


def test_generate_memory_single_file(tmp_path: Path) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "base.md").write_text("# Base Rules\n\nRule one.")
    (memory_dir / "python.md").write_text("# Python Rules\n\nUse type hints.")

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    result = generate_memory(memory_dir, config_dir, "global_rules.md", "single_file")

    assert result is True
    output = (config_dir / "global_rules.md").read_text()
    assert "# Base Rules" in output
    assert "# Python Rules" in output
    assert "Rule one." in output
    assert "Use type hints." in output


def test_generate_memory_directory(tmp_path: Path) -> None:
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "base.md").write_text("# Base Rules\n\nRule one.")
    (memory_dir / "python.md").write_text("# Python Rules\n\nUse type hints.")

    config_dir = tmp_path / "config"
    config_dir.mkdir()

    result = generate_memory(memory_dir, config_dir, "rules", "directory")

    assert result is True
    rules_dir = config_dir / "rules"
    assert rules_dir.is_dir()
    assert (rules_dir / "base.md").read_text() == "# Base Rules\n\nRule one."
    assert (rules_dir / "python.md").read_text() == "# Python Rules\n\nUse type hints."


def test_generate_memory_missing_source(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    missing_dir = tmp_path / "nonexistent"

    result = generate_memory(missing_dir, config_dir, "rules.md", "single_file")

    assert result is False


def test_ensure_settings_from_template_target_exists(tmp_path: Path) -> None:
    (tmp_path / "settings.template.json").write_text('{"key": "value"}')
    (tmp_path / "settings.json").write_text('{"existing": true}')

    result = ensure_settings_from_template(
        tmp_path, {"template": "settings.template.json", "target": "settings.json"}
    )

    assert result is True
    assert '"existing": true' in (tmp_path / "settings.json").read_text()


def test_ensure_settings_from_template_missing_template(tmp_path: Path) -> None:
    result = ensure_settings_from_template(
        tmp_path, {"template": "missing.json", "target": "settings.json"}
    )

    assert result is False
    assert not (tmp_path / "settings.json").exists()


def test_ensure_settings_from_template_creates_from_template(tmp_path: Path) -> None:
    (tmp_path / "settings.template.json").write_text('{"from": "template"}')

    result = ensure_settings_from_template(
        tmp_path, {"template": "settings.template.json", "target": "settings.json"}
    )

    assert result is True
    assert '"from": "template"' in (tmp_path / "settings.json").read_text()


def test_apply_work_overlay_no_overlay(tmp_path: Path) -> None:
    ai_root = tmp_path / "ai"
    ai_root.mkdir()
    config_dir = tmp_path / "cfg"
    config_dir.mkdir()

    assert apply_work_overlay("ghost", config_dir, ai_root) is True


def test_apply_work_overlay_runs_scripts(tmp_path: Path) -> None:
    ai_root = tmp_path / "ai"
    overlay = ai_root / "work" / "modules" / "mytool"
    overlay.mkdir(parents=True)
    marker = tmp_path / "ran.txt"
    (overlay / "setup.sh").write_text(f"#!/usr/bin/env bash\necho ok > {marker}\n")

    config_dir = tmp_path / "cfg"
    config_dir.mkdir()

    assert apply_work_overlay("mytool", config_dir, ai_root) is True
    assert marker.read_text().strip() == "ok"


def test_apply_work_overlay_symlinks_other_files(tmp_path: Path) -> None:
    ai_root = tmp_path / "ai"
    overlay = ai_root / "work" / "modules" / "mytool"
    overlay.mkdir(parents=True)
    (overlay / "config.toml").write_text("[profiles.work]\nmodel = 'x'\n")

    config_dir = tmp_path / "cfg"
    config_dir.mkdir()

    assert apply_work_overlay("mytool", config_dir, ai_root) is True

    target = config_dir / "config.toml"
    assert target.is_symlink()
    assert target.resolve() == (overlay / "config.toml").resolve()


def test_apply_work_overlay_symlinks_json(tmp_path: Path) -> None:
    ai_root = tmp_path / "ai"
    overlay = ai_root / "work" / "modules" / "mytool"
    overlay.mkdir(parents=True)
    (overlay / "opencode.json").write_text('{"providers": {"ic": {}}}')

    config_dir = tmp_path / "cfg"
    config_dir.mkdir()

    assert apply_work_overlay("mytool", config_dir, ai_root) is True

    target = config_dir / "opencode.json"
    assert target.is_symlink()
    assert target.resolve() == (overlay / "opencode.json").resolve()


def test_run_bootstrap_success(tmp_path: Path) -> None:
    marker = tmp_path / "ran.txt"
    script = tmp_path / "bootstrap.sh"
    script.write_text(f"#!/usr/bin/env bash\necho ok > {marker}\n")

    assert run_bootstrap(tmp_path, "bootstrap.sh") is True
    assert marker.read_text().strip() == "ok"


def test_run_bootstrap_missing(tmp_path: Path) -> None:
    assert run_bootstrap(tmp_path, "missing.sh") is False


def test_run_bootstrap_nonzero_exit(tmp_path: Path) -> None:
    script = tmp_path / "bootstrap.sh"
    script.write_text("#!/usr/bin/env bash\nexit 3\n")

    assert run_bootstrap(tmp_path, "bootstrap.sh") is False


def test_setup_tool_skips_config_on_bootstrap_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ai_root = tmp_path / "ai"
    tool_dir = ai_root / "modules" / "mytool"
    tool_dir.mkdir(parents=True)
    (tool_dir / "CONFIG.md").write_text("config")

    config_dir = tmp_path / "cfg"

    tool_config = cast(
        ToolConfig,
        {
            "name": "MyTool",
            "config_dir": str(config_dir),
            "tool_dir": "modules/mytool",
            "symlinks": [{"source": "CONFIG.md", "target": "CONFIG.md"}],
            "bootstrap": "bootstrap.sh",
        },
    )

    monkeypatch.setattr("scripts.setup.run_bootstrap", lambda *_: False)
    mock_symlink = MagicMock()
    mock_alias = MagicMock()
    monkeypatch.setattr("scripts.setup.create_symlink", mock_symlink)
    monkeypatch.setattr("scripts.setup.setup_shell_alias", mock_alias)

    result = setup_tool("mytool", tool_config, ai_root)

    assert result is False
    assert mock_symlink.called is False
    assert not (config_dir / "CONFIG.md").exists()
    mock_alias.assert_called_once_with("mytool")


def test_setup_tool_codex_symlinks_agents_without_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end codex flow with bootstrap mocked: no real npm/omx invocation.

    Simulates `omx setup` writing a regular `AGENTS.md` into the config dir,
    followed by the bootstrap script's cleanup of that regular file. Then lets
    the real symlink step run. The target must end up as a symlink to the
    source, with no `.backup.*` residue from earlier runs.
    """
    ai_root = tmp_path / "ai"
    tool_dir = ai_root / "modules" / "codex"
    tool_dir.mkdir(parents=True)
    source_agents = tool_dir / "AGENTS.md"
    source_agents.write_text("source agents")
    (tool_dir / "bootstrap.sh").write_text("#!/usr/bin/env bash\n")

    config_dir = tmp_path / "dot-codex"

    tool_config = cast(
        ToolConfig,
        {
            "name": "Codex CLI",
            "config_dir": str(config_dir),
            "tool_dir": "modules/codex",
            "symlinks": [{"source": "AGENTS.md", "target": "AGENTS.md"}],
            "bootstrap": "bootstrap.sh",
        },
    )

    def fake_bootstrap(_tool_dir: Path, _script: str) -> bool:
        config_dir.mkdir(parents=True, exist_ok=True)
        agents = config_dir / "AGENTS.md"
        agents.write_text("omx default")
        if agents.exists() and not agents.is_symlink():
            agents.unlink()
        return True

    monkeypatch.setattr("scripts.setup.run_bootstrap", fake_bootstrap)

    assert setup_tool("codex", tool_config, ai_root) is True

    deployed = config_dir / "AGENTS.md"
    assert deployed.is_symlink()
    assert deployed.resolve() == source_agents.resolve()
    assert list(config_dir.glob("*.backup.*")) == []
