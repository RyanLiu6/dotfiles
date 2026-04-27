#!/usr/bin/env python3
"""
AI CLI Tools Setup Script

Sets up symlinks for multiple AI CLI tools (Claude Code, Gemini CLI, etc.)
by reading configuration from tools.json.

Usage:
    python setup.py              # Setup all tools
    python setup.py claude       # Setup only Claude Code
    python setup.py gemini       # Setup only Gemini CLI
    python setup.py --list       # List available tools
"""

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TypedDict


class Symlink(TypedDict):
    source: str
    target: str


class SkillsSymlink(TypedDict):
    source: str
    target: str


class AgentsSymlink(TypedDict):
    source: str
    target: str


class SkillsGenerate(TypedDict):
    source: str
    target: str
    format: str


class MemoryGenerate(TypedDict):
    source: str
    target: str
    mode: str


class SettingsTemplate(TypedDict):
    template: str
    target: str


class ToolConfig(TypedDict, total=False):
    name: str
    config_dir: str
    tool_dir: str
    symlinks: list[Symlink]
    settings_template: SettingsTemplate
    skills_symlink: SkillsSymlink
    agents_symlink: AgentsSymlink
    skills_generate: SkillsGenerate
    memory_generate: MemoryGenerate
    extra_skills_dirs: list[str]
    bootstrap: str


class ToolsConfig(TypedDict):
    tools: dict[str, ToolConfig]


class Colors:
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BLUE = "\033[0;34m"
    BOLD = "\033[1m"
    NC = "\033[0m"  # No Color


def print_colored(message: str, color: str = Colors.NC) -> None:
    print(f"{color}{message}{Colors.NC}")


AI_DIR = "ai"


def get_repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_ai_root(repo_root: Path) -> Path:
    return repo_root / AI_DIR


def load_tools_config(ai_root: Path) -> ToolsConfig:
    config_path = ai_root / "tools.json"
    if not config_path.exists():
        print_colored(f"Error: tools.json not found at {config_path}", Colors.RED)
        sys.exit(1)

    with open(config_path) as f:
        config: ToolsConfig = json.load(f)
    return config


SHELL_ALIASES = {
    "gemini": {
        "alias": "alias gemini='gemini --yolo'",
        "comment": "# Gemini CLI: run in yolo mode (auto-approve all tools)",
    },
}


def setup_shell_alias(tool_id: str) -> bool:
    if tool_id not in SHELL_ALIASES:
        return True

    alias_config = SHELL_ALIASES[tool_id]
    alias_line = alias_config["alias"]
    comment_line = alias_config["comment"]

    zshrc_path = Path.home() / ".zshrc"

    if not zshrc_path.exists():
        print_colored("  Warning: ~/.zshrc not found, skipping alias setup", Colors.YELLOW)
        return False

    with open(zshrc_path) as f:
        content = f.read()

    if alias_line in content:
        print_colored("  Alias already exists in ~/.zshrc", Colors.GREEN)
        return True

    print_colored("  Adding alias to ~/.zshrc", Colors.GREEN)
    with open(zshrc_path, "a") as f:
        f.write(f"\n{comment_line}\n{alias_line}\n")

    print(f"    Added: {alias_line}")
    print_colored("  Run 'source ~/.zshrc' or restart your shell to apply", Colors.YELLOW)
    return True


def backup_if_exists(path: Path) -> None:
    if path.exists() and not path.is_symlink():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = path.with_suffix(f"{path.suffix}.backup.{timestamp}")
        print_colored(f"  Backing up existing {path.name} to {backup_path.name}", Colors.YELLOW)
        path.rename(backup_path)
    elif path.is_symlink():
        print_colored(f"  Removing existing symlink: {path}", Colors.YELLOW)
        path.unlink()


def create_symlink(source: Path, target: Path, name: str) -> bool:
    if not source.exists():
        print_colored(f"  Warning: Source {name} not found at {source}", Colors.RED)
        return False

    backup_if_exists(target)

    print_colored(f"  Creating symlink for {name}", Colors.GREEN)
    target.symlink_to(source)
    print(f"    {target} -> {source}")
    return True


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter delimited by --- from markdown content.

    Args:
        content: Raw markdown string, optionally starting with --- delimited frontmatter.

    Returns:
        Tuple of (frontmatter dict, body string). If no frontmatter is found,
        returns an empty dict and the original content.
    """
    frontmatter: dict[str, str] = {}
    body = content

    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            body = parts[2].strip()

            for line in yaml_content.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    frontmatter[key.strip()] = value.strip()

    return frontmatter, body


def convert_md_to_toml(md_path: Path) -> str:
    """Convert a markdown skill file to Gemini CLI's TOML command format.

    Extracts the description from YAML frontmatter and wraps the markdown body
    in a triple-quoted prompt field.

    Args:
        md_path: Path to the markdown skill file (e.g., SKILL.md).

    Returns:
        TOML-formatted string with description and prompt fields.
    """
    content = md_path.read_text()
    frontmatter, body = parse_frontmatter(content)
    description = frontmatter.get("description", "")

    lines = []
    if description:
        lines.append(f'description = "{description}"')
    lines.append('prompt = """')
    lines.append(body)
    lines.append('"""')

    return "\n".join(lines)


def find_skill_files(source_dir: Path) -> list[tuple[str, Path]]:
    """Discover skill files in both subdirectory and flat-file formats.

    Searches for skills in two formats: subdirectories containing a SKILL.md file
    (preferred), and legacy flat .md files (excluding README.md).

    Args:
        source_dir: Root directory to search for skills.

    Returns:
        List of (skill_name, skill_path) tuples. skill_name is derived from
        the subdirectory name or the file stem.
    """
    skills = []

    for skill_dir in source_dir.iterdir():
        if skill_dir.is_dir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                skills.append((skill_dir.name, skill_file))

    for md_file in source_dir.glob("*.md"):
        if md_file.name.lower() != "readme.md":
            skills.append((md_file.stem, md_file))

    return skills


def generate_skills(source_dir: Path, target_dir: Path, fmt: str) -> bool:
    if not source_dir.exists():
        print_colored(f"  Warning: Skills directory not found at {source_dir}", Colors.RED)
        return False

    backup_if_exists(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    skills = find_skill_files(source_dir)
    if not skills:
        print_colored(f"  Warning: No skill files found in {source_dir}", Colors.YELLOW)
        return False

    print_colored(f"  Generating {fmt} files in {target_dir}", Colors.GREEN)
    for skill_name, skill_path in skills:
        if fmt == "toml":
            output = convert_md_to_toml(skill_path)
            target_path = target_dir / f"{skill_name}.toml"
        else:
            output = skill_path.read_text()
            target_path = target_dir / f"{skill_name}.md"

        target_path.write_text(output + "\n")
        print(f"    {skill_path.name} ({skill_name}) -> {target_path.name}")

    return True


def symlink_skills_to_config(
    skills_dirs: list[Path],
    target_dir: Path,
    label: str,
) -> bool:
    """Symlink individual skills from source directories into the config skills directory.

    Args:
        skills_dirs: List of directories containing skills (each subdir with SKILL.md).
        target_dir: The config skills directory (e.g., ~/.claude/skills/).
        label: Label for logging (e.g., "public skills" or "work skills").

    Returns:
        True if all symlinks were created successfully, False if any failed.
    """
    success = True

    for source_dir in skills_dirs:
        if not source_dir.exists():
            print_colored(f"  Info: {label} dir {source_dir} not found, skipping", Colors.YELLOW)
            continue

        print_colored(f"  Linking {label} from {source_dir}", Colors.GREEN)

        for skill_dir in source_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            target_link = target_dir / skill_dir.name

            if target_link.exists() or target_link.is_symlink():
                if target_link.is_symlink():
                    target_link.unlink()
                else:
                    shutil.rmtree(target_link)

            target_link.symlink_to(skill_dir)
            print(f"    {skill_dir.name} -> {skill_dir}")

    return success


def symlink_agents_to_config(source_dir: Path, target_dir: Path) -> bool:
    """Symlink individual agent .md files from source directory into the config agents directory.

    Args:
        source_dir: Directory containing agent .md files.
        target_dir: The config agents directory (e.g., ~/.config/opencode/agents/).

    Returns:
        True if all symlinks were created successfully, False if any failed.
    """
    if not source_dir.exists():
        print_colored(f"  Warning: Agents directory not found at {source_dir}", Colors.RED)
        return False

    backup_if_exists(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    md_files = list(source_dir.glob("*.md"))
    if not md_files:
        print_colored(f"  Warning: No agent files found in {source_dir}", Colors.YELLOW)
        return False

    print_colored(f"  Linking agents from {source_dir}", Colors.GREEN)

    for md_file in md_files:
        target_link = target_dir / md_file.name

        if target_link.exists() or target_link.is_symlink():
            target_link.unlink()

        target_link.symlink_to(md_file)
        print(f"    {md_file.name} -> {md_file}")

    return True


def generate_memory(source_dir: Path, config_dir: Path, target: str, mode: str) -> bool:
    """Concatenate or copy memory files for tools without @ import support.

    For tools that cannot use @-references to include shared memory files,
    this function either concatenates all memory files into a single output file
    or copies them individually into a target directory.

    Args:
        source_dir: Directory containing memory .md files (e.g., repo_root/memory).
        config_dir: The tool's config directory (e.g., ~/.windsurf).
        target: Target filename (single_file mode) or directory name (directory mode).
        mode: Either "single_file" (concatenate into one file) or "directory" (copy individually).

    Returns:
        True if memory was generated successfully, False otherwise.
    """
    if not source_dir.exists():
        print_colored(f"  Warning: Memory directory not found at {source_dir}", Colors.RED)
        return False

    memory_files = sorted(source_dir.glob("*.md"))
    if not memory_files:
        print_colored(f"  Warning: No memory files found in {source_dir}", Colors.YELLOW)
        return False

    target_path = config_dir / target

    if mode == "single_file":
        backup_if_exists(target_path)
        parts = []
        for mem_file in memory_files:
            parts.append(mem_file.read_text().strip())
        target_path.write_text("\n\n".join(parts) + "\n")
        print_colored(f"  Generated {target_path}", Colors.GREEN)
        for mem_file in memory_files:
            print(f"    Included: {mem_file.name}")
    elif mode == "directory":
        backup_if_exists(target_path)
        target_path.mkdir(parents=True, exist_ok=True)
        for mem_file in memory_files:
            dest = target_path / mem_file.name
            if dest.exists() or dest.is_symlink():
                dest.unlink()
            shutil.copy2(mem_file, dest)
            print(f"    {mem_file.name} -> {dest}")
        print_colored(f"  Copied memory files to {target_path}", Colors.GREEN)
    else:
        print_colored(f"  Warning: Unknown memory_generate mode '{mode}'", Colors.RED)
        return False

    return True


def ensure_settings_from_template(tool_dir: Path, template_cfg: SettingsTemplate) -> bool:
    """Create a settings file from a template if it doesn't exist.

    If the target settings file already exists in the tool directory, this is a
    no-op. Otherwise the template is automatically copied to the target path.

    Args:
        tool_dir: The tool's source directory (e.g. repo/ai/modules/claude).
        template_cfg: Dict with 'template' (source filename) and 'target' (output filename).

    Returns:
        True if the settings file exists (already or newly created), False otherwise.
    """
    template_path = tool_dir / template_cfg["template"]
    target_path = tool_dir / template_cfg["target"]

    if target_path.exists():
        print_colored(f"  Settings file already exists: {target_path.name}", Colors.GREEN)
        return True

    if not template_path.exists():
        print_colored(
            f"  Warning: Template {template_cfg['template']} not found at {template_path}",
            Colors.RED,
        )
        return False

    shutil.copy2(template_path, target_path)
    print_colored(f"  Created {target_path.name} from {template_path.name}", Colors.GREEN)
    print_colored(
        f"  Edit {target_path} to customise your settings",
        Colors.YELLOW,
    )
    return True


WORK_OVERLAY_ROOT = "work/modules"


def deep_merge(base: Mapping[str, object], overlay: Mapping[str, object]) -> dict[str, object]:
    """Recursively merge overlay into base. Overlay values win on leaves.

    Nested dicts are merged key-by-key. Any non-dict value in overlay
    replaces the corresponding value in base entirely (lists are not
    concatenated — replacement only).

    Args:
        base: The base dict (not mutated).
        overlay: The overlay dict whose values take precedence.

    Returns:
        A new merged dict.
    """
    result = dict(base)
    for key, overlay_value in overlay.items():
        base_value = result.get(key)
        if isinstance(base_value, dict) and isinstance(overlay_value, dict):
            result[key] = deep_merge(base_value, overlay_value)
        else:
            result[key] = overlay_value
    return result


def _merge_json_overlay(overlay_file: Path, target_file: Path) -> None:
    overlay_data = json.loads(overlay_file.read_text())
    if not isinstance(overlay_data, dict):
        print_colored(
            f"  Warning: overlay {overlay_file} is not a JSON object, skipping",
            Colors.RED,
        )
        return

    base_data: dict[str, object] = {}
    if target_file.exists():
        existing_text = target_file.read_text().strip()
        if existing_text:
            try:
                loaded = json.loads(existing_text)
                if isinstance(loaded, dict):
                    base_data = loaded
                else:
                    print_colored(
                        f"  Warning: {target_file} is not a JSON object; overwriting",
                        Colors.YELLOW,
                    )
            except json.JSONDecodeError:
                print_colored(
                    f"  Warning: {target_file} is not valid JSON; overwriting",
                    Colors.YELLOW,
                )

    merged = deep_merge(base_data, overlay_data)
    target_file.parent.mkdir(parents=True, exist_ok=True)
    if target_file.is_symlink():
        target_file.unlink()
    target_file.write_text(json.dumps(merged, indent=2) + "\n")
    print_colored(f"  Merged overlay {overlay_file.name} into {target_file}", Colors.GREEN)


def _run_overlay_script(script: Path) -> None:
    mode = script.stat().st_mode
    script.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print_colored(f"  Running overlay script {script.name}", Colors.GREEN)
    subprocess.run([str(script)], check=True)


def _symlink_overlay_file(overlay_file: Path, target: Path) -> None:
    backup_if_exists(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(overlay_file)
    print_colored(f"  Overlay symlink {overlay_file.name} -> {target}", Colors.GREEN)


def apply_work_overlay(tool_id: str, config_dir: Path, ai_root: Path) -> bool:
    """Apply work-profile overlay for a tool, if present.

    Looks for ai/work/modules/<tool_id>/. If found:
      - *.json: deep-merged into config_dir/<same-name>
      - *.sh: executed (user-managed, often idempotent provider setup)
      - any other file: symlinked into config_dir/<same-name>

    Args:
        tool_id: The tool identifier (e.g., "opencode", "codex").
        config_dir: The tool's deployed config directory (e.g., ~/.codex).
        ai_root: The ai/ directory root in the repo.

    Returns:
        True when overlay applied cleanly (or absent), False on script failure.
    """
    overlay_dir = ai_root / WORK_OVERLAY_ROOT / tool_id
    if not overlay_dir.exists():
        return True

    print_colored(f"  Applying work overlay from {overlay_dir}", Colors.BLUE)
    success = True

    for entry in sorted(overlay_dir.iterdir()):
        if not entry.is_file():
            continue

        if entry.suffix == ".json":
            _merge_json_overlay(entry, config_dir / entry.name)
        elif entry.suffix == ".sh":
            try:
                _run_overlay_script(entry)
            except subprocess.CalledProcessError as exc:
                print_colored(
                    f"  Warning: overlay script {entry.name} exited {exc.returncode}",
                    Colors.RED,
                )
                success = False
        else:
            _symlink_overlay_file(entry, config_dir / entry.name)

    return success


def run_bootstrap(tool_dir: Path, script_name: str) -> bool:
    """Run a tool's bootstrap script from its module directory.

    Args:
        tool_dir: The tool's source directory (e.g. ai/modules/codex).
        script_name: The bootstrap filename relative to tool_dir.

    Returns:
        True if the script exits zero or is absent; False if it fails.
    """
    script = tool_dir / script_name
    if not script.exists():
        print_colored(f"  Warning: bootstrap {script} not found, skipping", Colors.YELLOW)
        return False

    mode = script.stat().st_mode
    script.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print_colored(f"  Running bootstrap {script_name}", Colors.GREEN)
    try:
        subprocess.run([str(script)], check=True)
    except subprocess.CalledProcessError as exc:
        print_colored(
            f"  Warning: bootstrap exited {exc.returncode}",
            Colors.RED,
        )
        return False
    return True


def setup_tool(tool_id: str, tool_config: ToolConfig, ai_root: Path) -> bool:
    name = tool_config["name"]
    config_dir = Path(os.path.expanduser(tool_config["config_dir"]))
    tool_dir = ai_root / tool_config["tool_dir"]

    print_colored(f"\n{'=' * 50}", Colors.BLUE)
    print_colored(f"Setting up {name}", Colors.BOLD)
    print_colored(f"{'=' * 50}", Colors.BLUE)
    print(f"  Source directory: {tool_dir}")
    print(f"  Target directory: {config_dir}")

    if not tool_dir.exists():
        print_colored(f"  Warning: Tool directory {tool_dir} not found, skipping", Colors.YELLOW)
        return False

    if not config_dir.exists():
        print_colored(f"  Creating config directory: {config_dir}", Colors.YELLOW)
        config_dir.mkdir(parents=True)

    success = True

    # Bootstrap runs first so the tool is installed before we deploy config.
    if "bootstrap" in tool_config and not run_bootstrap(tool_dir, tool_config["bootstrap"]):
        success = False

    # Handle settings template (must run before symlinks so the source file exists)
    if "settings_template" in tool_config:
        ensure_settings_from_template(tool_dir, tool_config["settings_template"])

    for symlink in tool_config.get("symlinks", []):
        source = tool_dir / symlink["source"]
        target = config_dir / symlink["target"]

        if not create_symlink(source, target, symlink["source"]):
            success = False

    if "skills_symlink" in tool_config:
        skills_cfg = tool_config["skills_symlink"]
        source_dir = ai_root / skills_cfg["source"]
        target_dir = config_dir / skills_cfg["target"]

        backup_if_exists(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

        skills_dirs = [source_dir]
        for extra_dir_str in tool_config.get("extra_skills_dirs", []):
            if extra_dir_str.startswith("~"):
                skills_dirs.append(Path(os.path.expanduser(extra_dir_str)))
            else:
                skills_dirs.append(ai_root / extra_dir_str)

        if not symlink_skills_to_config(skills_dirs, target_dir, "skills"):
            success = False

    if "agents_symlink" in tool_config:
        agents_cfg = tool_config["agents_symlink"]
        source_dir = ai_root / agents_cfg["source"]
        target_dir = config_dir / agents_cfg["target"]

        if not symlink_agents_to_config(source_dir, target_dir):
            success = False

    if "skills_generate" in tool_config:
        skills_cfg = tool_config["skills_generate"]
        source = ai_root / skills_cfg["source"]
        target = config_dir / skills_cfg["target"]
        fmt = skills_cfg.get("format", "md")
        if not generate_skills(source, target, fmt):
            success = False

    if "memory_generate" in tool_config:
        mem_cfg = tool_config["memory_generate"]
        source = ai_root / mem_cfg["source"]
        if not generate_memory(source, config_dir, mem_cfg["target"], mem_cfg["mode"]):
            success = False

    setup_shell_alias(tool_id)

    if not apply_work_overlay(tool_id, config_dir, ai_root):
        success = False

    return success


def list_tools(config: ToolsConfig) -> None:
    print_colored("\nAvailable tools:", Colors.BOLD)
    print_colored("-" * 40, Colors.BLUE)

    for tool_id, tool_config in config.get("tools", {}).items():
        name = tool_config.get("name", tool_id)
        config_dir = tool_config.get("config_dir", "unknown")
        print(f"  {Colors.GREEN}{tool_id}{Colors.NC}: {name}")
        print(f"    Config dir: {config_dir}")
        symlinks = tool_config.get("symlinks", [])
        print(f"    Symlinks: {', '.join(s['source'] for s in symlinks)}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Setup symlinks for AI CLI tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python setup.py              # Setup all tools
  python setup.py claude       # Setup only Claude Code
  python setup.py gemini       # Setup only Gemini CLI
  python setup.py claude gemini  # Setup specific tools
  python setup.py --list       # List available tools
        """,
    )
    parser.add_argument(
        "tools",
        nargs="*",
        help="Specific tools to setup (default: all)",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available tools and exit",
    )

    args = parser.parse_args()

    repo_root = get_repo_root()
    ai_root = get_ai_root(repo_root)
    config = load_tools_config(ai_root)

    print_colored("=" * 50, Colors.BLUE)
    print_colored("AI CLI Tools Setup", Colors.BOLD)
    print_colored("=" * 50, Colors.BLUE)
    print(f"Repository root: {repo_root}")
    print(f"AI config root: {ai_root}")

    if args.list:
        list_tools(config)
        return

    tools_config = config.get("tools", {})

    if not tools_config:
        print_colored("Error: No tools defined in tools.json", Colors.RED)
        sys.exit(1)

    if args.tools:
        tools_to_setup = {}
        for tool_id in args.tools:
            if tool_id in tools_config:
                tools_to_setup[tool_id] = tools_config[tool_id]
            else:
                print_colored(f"Warning: Unknown tool '{tool_id}', skipping", Colors.YELLOW)
    else:
        tools_to_setup = tools_config

    if not tools_to_setup:
        print_colored("No valid tools to setup", Colors.RED)
        sys.exit(1)

    results = {}
    for tool_id, tool_config in tools_to_setup.items():
        results[tool_id] = setup_tool(tool_id, tool_config, ai_root)

    print_colored(f"\n{'=' * 50}", Colors.BLUE)
    print_colored("Setup Summary", Colors.BOLD)
    print_colored(f"{'=' * 50}", Colors.BLUE)

    for tool_id, success in results.items():
        name = tools_config[tool_id]["name"]
        status = f"{Colors.GREEN}OK{Colors.NC}" if success else f"{Colors.YELLOW}PARTIAL{Colors.NC}"
        print(f"  {name}: {status}")

    print_colored(f"\n{'=' * 50}", Colors.GREEN)
    print_colored("Setup complete!", Colors.GREEN)
    print_colored(f"{'=' * 50}", Colors.GREEN)


if __name__ == "__main__":
    main()
