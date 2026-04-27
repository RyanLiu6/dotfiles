# Architecture

## Component Layout

Each top-level directory is a self-contained component with its own `setup` script:

| Component | What it does |
|-----------|-------------|
| `shell/` | ZSH config: `.zshrc`, `.zprofile`, plugins, performance tracking |
| `terminal/` | Ghostty terminal emulator config |
| `git/` | Git global config, aliases, global gitignore |
| `direnv/` | direnv shell hook and direnvrc |
| `lazygit/` | Lazygit TUI config |
| `rectangle/` | Rectangle window manager plist (macOS only) |

### Component Setup Contract

Every component has a `setup` script that:
1. Receives `REPO_DIR` as an environment variable
2. Sources `lib/platform.sh` for cross-platform helpers
3. Creates symlinks from the repo into `$HOME` or `~/.config/`
4. Is idempotent — safe to run repeatedly

### Shared Library (`lib/platform.sh`)

Provides:
- `detect_os` — returns `macos` or `linux`
- `ensure_symlink <source> <target> <label>` — creates a symlink with backup
- `ensure_zsh` — installs zsh if missing (Linux)
- `get_zsh_path` — finds the zsh binary

## Setup Pipeline

```
scripts/bootstrap          Install uv + Python
    ↓
inv setup                  Entry point (tasks.py)
    ↓
_setup_platform()          Install Homebrew (macOS) or verify sudo (Linux)
    ↓
_run_component()           Run each component's setup script in order:
    ├── terminal/setup         Ghostty config symlink
    ├── direnv/setup           direnvrc symlink
    ├── git/setup              Git config, aliases, global gitignore
    ├── lazygit/setup          Lazygit config
    ├── rectangle/setup        Rectangle plist import (macOS)
    └── shell/setup            .zprofile symlink, .zshrc loader creation
    ↓
scripts/setup.py           AI tools setup (reads ai/tools.json)
```

## Shell Configuration

The shell setup uses a **loader pattern** to avoid conflicts with tools that modify `~/.zshrc`:

1. `shell/.zshrc.loader` is a template with `__REPO_DIR__` placeholder
2. `shell/setup` renders it into `~/.zshrc`, replacing the placeholder
3. The loader sources `shell/.zshrc` (the real config)
4. Everything below the `# Tools install themselves below this line` marker is preserved across re-runs

This means:
- The repo owns everything above the marker (shell config)
- Tools own everything below the marker (their auto-installed lines)
- `inv reset --keep` preserves the tool section during a full reset

## Reset and Teardown

`inv reset` calls `_teardown()` which:
1. Removes all config symlinks and files
2. Backs up `~/.zshrc` with a timestamp
3. Resets git global config (`core.excludesfile`, `include.path`)
4. Removes AI tool symlinks/configs (driven by `ai/tools.json`)
5. Re-runs the full setup pipeline
