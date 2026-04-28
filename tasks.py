import json
import os
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

from invoke.context import Context
from invoke.tasks import task

REPO_DIR = Path(__file__).parent

ZSHRC_TOOL_MARKER = "# Tools install themselves below this line"

COMPONENTS = ["terminal", "direnv", "git", "lazygit", "rectangle", "shell"]


def _load_ai_tool_paths() -> list[str]:
    """Derive all managed AI tool paths from ai/tools.json.

    Reads the tools configuration and collects every target path (symlinks,
    skills, generated commands/memory) so teardown knows what to remove.

    Returns:
        List of paths relative to $HOME (e.g. ".claude/CLAUDE.md").
    """
    config_path = REPO_DIR / "ai" / "tools.json"
    with open(config_path) as f:
        config = json.load(f)

    paths: list[str] = []
    for tool in config.get("tools", {}).values():
        config_dir = tool["config_dir"]
        # Strip ~/ prefix to get path relative to $HOME
        rel_dir = config_dir.removeprefix("~/")

        for symlink in tool.get("symlinks", []):
            paths.append(f"{rel_dir}/{symlink['target']}")

        if "skills_symlink" in tool:
            paths.append(f"{rel_dir}/{tool['skills_symlink']['target']}")

        if "agents_symlink" in tool:
            paths.append(f"{rel_dir}/{tool['agents_symlink']['target']}")

        if "skills_generate" in tool:
            paths.append(f"{rel_dir}/{tool['skills_generate']['target']}")

        if "memory_generate" in tool:
            paths.append(f"{rel_dir}/{tool['memory_generate']['target']}")

    return paths


def _load_overlay_paths() -> list[str]:
    """Derive overlay-deployed paths from ai/work/modules/<tool_id>/.

    For each tool in tools.json, walk the matching overlay directory and
    emit target paths for every file that setup.py would symlink. `.sh`
    files are skipped: they execute arbitrary side effects whose outputs
    aren't knowable from the filename alone, so teardown can't track them.

    Returns:
        List of paths relative to $HOME (e.g. ".codex/config.toml").
    """
    config_path = REPO_DIR / "ai" / "tools.json"
    with open(config_path) as f:
        config = json.load(f)

    overlay_root = REPO_DIR / "ai" / "work" / "modules"
    paths: list[str] = []
    for tool_id, tool in config.get("tools", {}).items():
        overlay_dir = overlay_root / tool_id
        if not overlay_dir.exists():
            continue

        rel_dir = tool["config_dir"].removeprefix("~/")
        for entry in sorted(overlay_dir.iterdir()):
            if not entry.is_file() or entry.suffix == ".sh":
                continue
            paths.append(f"{rel_dir}/{entry.name}")

    return paths


def _extract_zshrc_tool_content() -> Optional[str]:
    """Extract tool-installed content from ~/.zshrc (everything from the marker onward).

    Reads the current ~/.zshrc (if it exists and is a real file, not a symlink),
    finds the ZSHRC_TOOL_MARKER line, and returns everything from that line onward.

    Returns:
        The marker line and all content below it, or None if the file is missing,
        is a symlink, has no marker, or has only whitespace after the marker.
    """
    zshrc = Path.home() / ".zshrc"
    if not zshrc.is_file() or zshrc.is_symlink():
        return None

    content = zshrc.read_text()
    marker_idx = content.find(ZSHRC_TOOL_MARKER)
    if marker_idx == -1:
        return None

    preserved = content[marker_idx:]
    after_marker = preserved[len(ZSHRC_TOOL_MARKER) :]
    if not after_marker.strip():
        return None

    return preserved


def _restore_zshrc_tool_content(content: str) -> None:
    """Replace the marker block in the freshly-created ~/.zshrc with preserved content.

    Reads the new ~/.zshrc, finds the ZSHRC_TOOL_MARKER line, and replaces
    everything from that line onward with the previously saved content.

    Args:
        content: The preserved block (marker line + tool-installed lines).
    """
    zshrc = Path.home() / ".zshrc"
    current = zshrc.read_text()
    marker_idx = current.find(ZSHRC_TOOL_MARKER)
    if marker_idx == -1:
        return

    new_content = current[:marker_idx] + content
    zshrc.write_text(new_content)
    print("  ✓ Restored tool-installed content in ~/.zshrc")


def _setup_platform(ctx: Context) -> None:
    system = platform.system()
    if system == "Darwin":
        print("🖥️  Detected OS: macos")
        if not shutil.which("brew"):
            print("📦 Installing Homebrew...")
            ctx.run(
                '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                env={"NONINTERACTIVE": "1"},
                pty=True,
            )
            # Add brew to PATH so child processes (component setup scripts) can find it
            if Path("/opt/homebrew/bin/brew").exists():
                brew_prefix = "/opt/homebrew"
            elif Path("/usr/local/bin/brew").exists():
                brew_prefix = "/usr/local"
            else:
                raise SystemExit("⚠️  Homebrew installed but binary not found")
            os.environ["PATH"] = (
                f"{brew_prefix}/bin:{brew_prefix}/sbin:{os.environ.get('PATH', '')}"
            )
        else:
            print("✓ Homebrew already installed")
    elif system == "Linux":
        print("🖥️  Detected OS: linux")
        if not shutil.which("sudo"):
            raise SystemExit("⚠️  sudo is required for package installation on Linux")
    else:
        raise SystemExit(f"⚠️  Unsupported operating system: {system}")
    print()


def _run_component(ctx: Context, component: str) -> None:
    script = REPO_DIR / component / "setup"
    if not script.exists():
        print(f"Warning: {script} not found, skipping")
        return
    ctx.run(str(script), env={"REPO_DIR": str(REPO_DIR)}, pty=True)


def _teardown() -> None:
    home = Path.home()

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("Removing existing configurations")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

    zprofile = home / ".zprofile"
    if zprofile.exists() or zprofile.is_symlink():
        print(f"  → Removing {zprofile}")
        zprofile.unlink()

    zshrc = home / ".zshrc"
    if zshrc.is_file() and not zshrc.is_symlink():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = home / f".zshrc.backup.{timestamp}"
        print(f"  → Backing up {zshrc} to {backup}")
        shutil.copy2(zshrc, backup)
    if zshrc.exists() or zshrc.is_symlink():
        zshrc.unlink()

    direnvrc = home / ".config" / "direnv" / "direnvrc"
    if direnvrc.exists() or direnvrc.is_symlink():
        print(f"  → Removing {direnvrc}")
        direnvrc.unlink()

    gitignore = home / ".gitignore_global"
    if gitignore.exists() or gitignore.is_symlink():
        print(f"  → Removing {gitignore}")
        gitignore.unlink()

    print("  → Resetting git global config")
    subprocess.run(
        ["git", "config", "--global", "--unset", "core.excludesfile"],
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "--global", "--unset", "include.path"],
        capture_output=True,
    )

    ghostty = home / ".config" / "ghostty"
    if ghostty.is_symlink():
        print(f"  → Removing {ghostty} symlink")
        ghostty.unlink()
    elif ghostty.is_dir():
        print(f"  → Removing {ghostty} directory")
        shutil.rmtree(ghostty)

    starship = home / ".config" / "starship.toml"
    if starship.exists() or starship.is_symlink():
        print(f"  → Removing {starship}")
        starship.unlink()

    for rel_path in _load_ai_tool_paths() + _load_overlay_paths():
        path = home / rel_path
        if path.is_symlink():
            print(f"  → Removing AI symlink: {path}")
            path.unlink()
        elif path.is_dir():
            print(f"  → Removing AI config: {path}")
            shutil.rmtree(path)
        elif path.is_file():
            print(f"  → Removing AI config: {path}")
            path.unlink()

    print("  ✓ All configurations removed")
    print()


@task
def setup(ctx: Context) -> None:
    """Run full development environment setup.

    Detects the platform, runs each component setup script (terminal, direnv,
    git, lazygit, shell), then configures AI CLI tools via scripts/setup.py.

    Args:
        ctx: Invoke context for running shell commands.
    """
    print("======================================")
    print("Development Environment Setup")
    print("======================================")
    print()

    _setup_platform(ctx)

    for component in COMPONENTS:
        _run_component(ctx, component)

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("AI CLI Tools Setup")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()
    ctx.run("python scripts/setup.py", pty=True)

    print()
    print("======================================")
    print("✓ Setup complete!")
    print("======================================")
    print()
    print("Please restart your terminal or run: source ~/.zshrc")


@task
def reset(ctx: Context, yes: bool = False, keep: bool = False) -> None:
    """Remove all managed configs and symlinks, then re-run setup from scratch.

    Args:
        ctx: Invoke context for running shell commands.
        yes: Skip the interactive confirmation prompt.
        keep: Preserve tool-installed lines in ~/.zshrc across the reset.
    """
    print("======================================")
    print("Development Environment Reset")
    print("======================================")
    print()

    if not yes:
        print("⚠️  This will:")
        print("  - Remove all config symlinks and files")
        print("  - Reset git global configuration")
        print("  - Re-run full setup from scratch")
        if keep:
            print("  - PRESERVE tool-installed lines in ~/.zshrc")
        print()
        reply = input("Continue? [y/N] ")
        if reply.lower() != "y":
            print("Aborted.")
            return

    preserved_content = None
    if keep:
        preserved_content = _extract_zshrc_tool_content()
        if preserved_content:
            print("  → Extracted tool-installed content from ~/.zshrc")
        else:
            print("  → No tool-installed content found to preserve")

    print()
    _teardown()
    setup(ctx)

    if preserved_content:
        _restore_zshrc_tool_content(preserved_content)


@task
def test(ctx: Context, verbose: bool = False) -> None:
    """Run the pytest test suite.

    Args:
        ctx: Invoke context for running shell commands.
        verbose: Enable verbose output (-v flag).
    """
    cmd = "uv run pytest"
    if verbose:
        cmd += " -v"
    ctx.run(cmd, pty=True)


@task(name="format")
def format_(ctx: Context, check: bool = False) -> None:
    """Run ruff code formatter.

    Args:
        ctx: Invoke context for running shell commands.
        check: Only check formatting without modifying files.
    """
    cmd = "uv run ruff format"
    if check:
        cmd += " --check"
    ctx.run(cmd, pty=True)


@task
def lint(ctx: Context, fix: bool = False) -> None:
    """Run ruff linter.

    Args:
        ctx: Invoke context for running shell commands.
        fix: Automatically fix fixable lint violations.
    """
    cmd = "uv run ruff check"
    if fix:
        cmd += " --fix"
    ctx.run(cmd, pty=True)


def _find_ai_backup_files() -> list[Path]:
    """Find timestamped backup files in AI tool config directories.

    Reads tools.json to discover config directories, then searches each for
    backup files created by scripts/setup.py's backup_if_exists() function.
    These follow the pattern: {name}.backup.{YYYYMMDD_HHMMSS}

    Returns:
        List of paths to backup files/directories found in AI config dirs.
    """
    config_path = REPO_DIR / "ai" / "tools.json"
    with open(config_path) as f:
        config = json.load(f)

    backups: list[Path] = []
    for tool in config.get("tools", {}).values():
        config_dir = Path(os.path.expanduser(tool["config_dir"]))
        if not config_dir.exists():
            continue

        backups.extend(config_dir.glob("*.backup.*"))

        for child in config_dir.iterdir():
            if child.is_dir() and not child.is_symlink():
                backups.extend(child.glob("*.backup.*"))

    return backups


@task
def cleanup(ctx: Context) -> None:
    """Remove backup files left behind by setup scripts.

    Setup scripts create .backup files when replacing existing configs with
    symlinks. This task finds and removes those stale backups from three sources:
    shell scripts (lib/platform.sh), the reset task (_teardown), and the AI
    tools setup script (scripts/setup.py).

    Args:
        ctx: Invoke context for running shell commands.
    """
    home = Path.home()

    shell_backups = [
        home / ".zprofile.backup",
        home / ".gitignore_global.backup",
        home / ".config" / "starship.toml.backup",
        home / ".config" / "ghostty.backup",
        home / ".config" / "direnv" / "direnvrc.backup",
    ]

    zshrc_backups = list(home.glob(".zshrc.backup.*"))

    ai_backups = _find_ai_backup_files()

    all_backups = shell_backups + zshrc_backups + ai_backups
    found = [p for p in all_backups if p.exists() or p.is_dir()]

    if not found:
        print("✓ No backup files found — nothing to clean up.")
        return

    for path in found:
        if path.is_dir():
            print(f"  → Removing {path}/")
            shutil.rmtree(path)
        else:
            print(f"  → Removing {path}")
            path.unlink()

    print(f"  ✓ Removed {len(found)} backup file(s)")


@task
def typecheck(ctx: Context) -> None:
    """Run mypy type checker against scripts/, tasks.py, and tests/.

    Args:
        ctx: Invoke context for running shell commands.
    """
    ctx.run("uv run mypy scripts/ tasks.py tests/", pty=True)
