import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from invoke.context import Context

from tasks import (
    ZSHRC_TOOL_MARKER,
    _extract_zshrc_tool_content,
    _restore_zshrc_tool_content,
    _setup_platform,
    _teardown,
    cleanup,
)


@pytest.fixture
def fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


LOADER_TEMPLATE = """\
# ~/.zshrc loader
source /some/path/shell/.zshrc

# Tools install themselves below this line
"""

TOOL_CONTENT = """\
# Added by some-tool
source ~/.some_tool_profile

# another-tool completions
eval "$(another-tool completions zsh)"
"""

ZSHRC_WITH_TOOLS = LOADER_TEMPLATE + TOOL_CONTENT


class TestExtractZshrcToolContent:
    def test_extract_zshrc_tool_content(self, fake_home: Path) -> None:
        zshrc = fake_home / ".zshrc"
        zshrc.write_text(ZSHRC_WITH_TOOLS)

        result = _extract_zshrc_tool_content()
        assert result is not None
        assert result.startswith(ZSHRC_TOOL_MARKER)
        assert "some_tool_profile" in result
        assert "another-tool completions" in result

    def test_extract_zshrc_tool_content_no_marker(self, fake_home: Path) -> None:
        zshrc = fake_home / ".zshrc"
        zshrc.write_text("# just some zshrc\nexport FOO=bar\n")

        assert _extract_zshrc_tool_content() is None

    def test_extract_zshrc_tool_content_no_file(self, fake_home: Path) -> None:
        assert _extract_zshrc_tool_content() is None

    def test_extract_zshrc_tool_content_empty_after_marker(self, fake_home: Path) -> None:
        zshrc = fake_home / ".zshrc"
        zshrc.write_text(LOADER_TEMPLATE + "\n  \n")

        assert _extract_zshrc_tool_content() is None

    def test_extract_zshrc_tool_content_symlink(self, fake_home: Path) -> None:
        real_file = fake_home / ".zshrc.real"
        real_file.write_text(ZSHRC_WITH_TOOLS)
        zshrc = fake_home / ".zshrc"
        zshrc.symlink_to(real_file)

        assert _extract_zshrc_tool_content() is None


class TestRestoreZshrcToolContent:
    def test_restore_zshrc_tool_content(self, fake_home: Path) -> None:
        zshrc = fake_home / ".zshrc"
        zshrc.write_text(LOADER_TEMPLATE)

        preserved = ZSHRC_TOOL_MARKER + "\n" + TOOL_CONTENT
        _restore_zshrc_tool_content(preserved)

        result = zshrc.read_text()
        assert "some_tool_profile" in result
        assert "another-tool completions" in result
        assert result.startswith("# ~/.zshrc loader")
        assert result.count(ZSHRC_TOOL_MARKER) == 1

    def test_restore_zshrc_tool_content_no_marker(self, fake_home: Path) -> None:
        zshrc = fake_home / ".zshrc"
        zshrc.write_text("# no marker here\n")

        preserved = ZSHRC_TOOL_MARKER + "\n" + TOOL_CONTENT
        _restore_zshrc_tool_content(preserved)

        result = zshrc.read_text()
        assert result == "# no marker here\n"


class TestCleanup:
    @pytest.fixture
    def fake_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_cleanup(self, fake_home: Path) -> None:
        backup_files: list[Path] = []
        backup_dirs: list[Path] = []

        for rel in [
            ".zprofile.backup",
            ".gitignore_global.backup",
            ".config/starship.toml.backup",
            ".config/direnv/direnvrc.backup",
        ]:
            p = fake_home / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("backup")
            backup_files.append(p)

        ghostty_backup = fake_home / ".config" / "ghostty.backup"
        ghostty_backup.mkdir(parents=True)
        (ghostty_backup / "config").write_text("backup")
        backup_dirs.append(ghostty_backup)

        for ts in ["20240101_120000", "20240615_090000"]:
            p = fake_home / f".zshrc.backup.{ts}"
            p.write_text("backup")
            backup_files.append(p)

        claude_dir = fake_home / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        for name in [
            "CLAUDE.md.backup.20240101_120000",
            "settings.json.backup.20240101_120000",
        ]:
            p = claude_dir / name
            p.write_text("backup")
            backup_files.append(p)

        skills_backup = claude_dir / "skills.backup.20240101_120000"
        skills_backup.mkdir()
        (skills_backup / "some-skill").mkdir()
        backup_dirs.append(skills_backup)

        gemini_dir = fake_home / ".gemini"
        gemini_dir.mkdir(parents=True, exist_ok=True)
        p = gemini_dir / "GEMINI.md.backup.20240101_120000"
        p.write_text("backup")
        backup_files.append(p)

        commands_backup = gemini_dir / "commands.backup.20240101_120000"
        commands_backup.mkdir()
        backup_dirs.append(commands_backup)

        preserved = []
        for rel in [".zprofile", ".zshrc"]:
            p = fake_home / rel
            p.write_text("real config")
            preserved.append(p)
        for name, parent in [("CLAUDE.md", claude_dir), ("GEMINI.md", gemini_dir)]:
            p = parent / name
            p.write_text("real config")
            preserved.append(p)

        all_backups = backup_files + backup_dirs
        for p in all_backups:
            assert p.exists()

        cleanup(MagicMock(spec=Context))

        for p in all_backups:
            assert not p.exists(), f"Cleanup missed: {p}"
        for p in preserved:
            assert p.exists(), f"Cleanup wrongly removed: {p}"

    def test_cleanup_no_backups(self, fake_home: Path) -> None:
        cleanup(MagicMock(spec=Context))


class TestSetupPlatform:
    @pytest.fixture
    def mock_ctx(self) -> MagicMock:
        return MagicMock(spec=Context)

    def test_setup_platform_macos_apple_silicon(
        self, mock_ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tasks.platform.system", lambda: "Darwin")
        monkeypatch.setattr("tasks.shutil.which", lambda _cmd: None)
        monkeypatch.setattr(
            "tasks.Path.exists",
            lambda self: str(self) == "/opt/homebrew/bin/brew",
        )
        original_path = os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", original_path)

        _setup_platform(mock_ctx)

        mock_ctx.run.assert_called_once()
        _args, kwargs = mock_ctx.run.call_args
        assert kwargs["env"] == {"NONINTERACTIVE": "1"}
        assert "/opt/homebrew/bin" in os.environ["PATH"]
        assert "/opt/homebrew/sbin" in os.environ["PATH"]

    def test_setup_platform_macos_intel(
        self, mock_ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tasks.platform.system", lambda: "Darwin")
        monkeypatch.setattr("tasks.shutil.which", lambda _cmd: None)
        monkeypatch.setattr(
            "tasks.Path.exists",
            lambda self: str(self) == "/usr/local/bin/brew",
        )
        original_path = os.environ.get("PATH", "")
        monkeypatch.setenv("PATH", original_path)

        _setup_platform(mock_ctx)

        assert "/usr/local/bin" in os.environ["PATH"]
        assert "/usr/local/sbin" in os.environ["PATH"]

    def test_setup_platform_macos_brew_already_installed(
        self, mock_ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tasks.platform.system", lambda: "Darwin")
        monkeypatch.setattr("tasks.shutil.which", lambda _cmd: "/opt/homebrew/bin/brew")

        _setup_platform(mock_ctx)

        mock_ctx.run.assert_not_called()

    def test_setup_platform_macos_brew_not_found_after_install(
        self, mock_ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tasks.platform.system", lambda: "Darwin")
        monkeypatch.setattr("tasks.shutil.which", lambda _cmd: None)
        monkeypatch.setattr("tasks.Path.exists", lambda self: False)

        with pytest.raises(SystemExit):
            _setup_platform(mock_ctx)

    def test_setup_platform_linux(
        self, mock_ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tasks.platform.system", lambda: "Linux")
        monkeypatch.setattr("tasks.shutil.which", lambda _cmd: "/usr/bin/sudo")

        _setup_platform(mock_ctx)

        mock_ctx.run.assert_not_called()

    def test_setup_platform_linux_no_sudo(
        self, mock_ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tasks.platform.system", lambda: "Linux")
        monkeypatch.setattr("tasks.shutil.which", lambda _cmd: None)

        with pytest.raises(SystemExit):
            _setup_platform(mock_ctx)

    def test_setup_platform_unsupported_os(
        self, mock_ctx: MagicMock, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr("tasks.platform.system", lambda: "FreeBSD")

        with pytest.raises(SystemExit):
            _setup_platform(mock_ctx)


class TestTeardown:
    @pytest.fixture
    def fake_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("HOME", str(tmp_path))
        return tmp_path

    def test_teardown(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_run = MagicMock()
        monkeypatch.setattr("tasks.subprocess.run", mock_run)

        ai_symlink = fake_home / ".claude" / "CLAUDE.md"
        ai_dir = fake_home / ".gemini" / "commands"
        ai_file = fake_home / ".claude" / "settings.json"
        monkeypatch.setattr(
            "tasks._load_ai_tool_paths",
            lambda: [
                ".claude/CLAUDE.md",
                ".gemini/commands",
                ".claude/settings.json",
            ],
        )
        monkeypatch.setattr("tasks._load_overlay_paths", lambda: [])

        configs = {
            ".zprofile": fake_home / ".zprofile",
            ".zshrc": fake_home / ".zshrc",
            "direnvrc": fake_home / ".config" / "direnv" / "direnvrc",
            "gitignore": fake_home / ".gitignore_global",
            "starship": fake_home / ".config" / "starship.toml",
        }
        for p in configs.values():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("config")

        ghostty = fake_home / ".config" / "ghostty"
        ghostty.mkdir(parents=True)
        (ghostty / "config").write_text("font-size = 14")

        ai_symlink.parent.mkdir(parents=True, exist_ok=True)
        real_target = fake_home / "real_claude_md"
        real_target.write_text("real")
        ai_symlink.symlink_to(real_target)

        ai_dir.parent.mkdir(parents=True, exist_ok=True)
        ai_dir.mkdir()
        (ai_dir / "cmd").write_text("x")

        ai_file.write_text("settings")

        _teardown()

        for name, p in configs.items():
            assert not p.exists(), f"{name} should be removed"
        assert not ghostty.exists(), "ghostty dir should be removed"

        zshrc_backups = list(fake_home.glob(".zshrc.backup.*"))
        assert len(zshrc_backups) == 1

        assert not ai_symlink.exists() and not ai_symlink.is_symlink()
        assert not ai_dir.exists()
        assert not ai_file.exists()

        git_unset_calls = [args[0][0] for args in mock_run.call_args_list]
        assert any("core.excludesfile" in cmd for cmd in git_unset_calls)
        assert any("include.path" in cmd for cmd in git_unset_calls)

    def test_teardown_symlinks(self, fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_run = MagicMock()
        monkeypatch.setattr("tasks.subprocess.run", mock_run)
        monkeypatch.setattr("tasks._load_ai_tool_paths", lambda: [])
        monkeypatch.setattr("tasks._load_overlay_paths", lambda: [])

        real_file = fake_home / "real_zprofile"
        real_file.write_text("real")

        zprofile = fake_home / ".zprofile"
        zprofile.symlink_to(real_file)

        real_zshrc = fake_home / "real_zshrc"
        real_zshrc.write_text("real")
        zshrc = fake_home / ".zshrc"
        zshrc.symlink_to(real_zshrc)

        ghostty_real = fake_home / "real_ghostty"
        ghostty_real.mkdir()
        ghostty = fake_home / ".config" / "ghostty"
        ghostty.parent.mkdir(parents=True, exist_ok=True)
        ghostty.symlink_to(ghostty_real)

        _teardown()

        assert not zprofile.exists() and not zprofile.is_symlink()
        assert not zshrc.exists() and not zshrc.is_symlink()
        assert not ghostty.exists() and not ghostty.is_symlink()

        zshrc_backups = list(fake_home.glob(".zshrc.backup.*"))
        assert len(zshrc_backups) == 0

    def test_teardown_nothing_exists(
        self, fake_home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_run = MagicMock()
        monkeypatch.setattr("tasks.subprocess.run", mock_run)
        monkeypatch.setattr("tasks._load_ai_tool_paths", lambda: [])
        monkeypatch.setattr("tasks._load_overlay_paths", lambda: [])

        _teardown()
