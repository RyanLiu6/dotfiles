# Dotfiles

Cross-platform development environment configuration for macOS and Linux.

## Docs

- [docs/architecture.md](docs/architecture.md): repo structure, AI tools pipeline, component layout
- [docs/ai-tools.md](docs/ai-tools.md): tools.json schema, skills, agents, templates, setup flow

## Commands

All commands use [Invoke](https://www.pyinvoke.org/) via `inv`. Prefix with `uv run` if the virtualenv is not activated.

| Task | Command |
|------|---------|
| Full setup | `inv setup` |
| Reset (teardown + setup) | `inv reset` |
| Reset (preserve tool lines in .zshrc) | `inv reset --keep` |
| Tests | `inv test` |
| Lint | `inv lint` |
| Lint fix | `inv lint --fix` |
| Format | `inv format` |
| Format check | `inv format --check` |
| Type check | `inv typecheck` |
| Cleanup backup files | `inv cleanup` |

Run `inv format` and `inv lint --fix` before committing.

## Structure

```
.
├── ai/                     AI CLI tool configurations
│   ├── memory/             Shared memory files (@-imported by CLAUDE.md)
│   ├── modules/            Per-tool configs (claude, gemini, opencode, cursor, etc.)
│   ├── skills/             Shared skill definitions (symlinked or generated per tool)
│   ├── templates/          Reusable templates (AGENTS.reviews.md, .claude/rules/)
│   ├── tools.json          Tool registry — drives scripts/setup.py
│   └── work/               Work-specific configs (gitignored)
├── direnv/                 direnv setup
├── git/                    Git config and global gitignore
├── lazygit/                Lazygit config
├── lib/                    Shared shell helpers (platform detection, symlink utils)
├── rectangle/              Rectangle window manager config (macOS)
├── scripts/                Bootstrap, setup, and reset entry points
│   └── setup.py            AI tools setup — reads tools.json, creates symlinks/generates files
├── shell/                  ZSH configuration (.zshrc, .zprofile, plugins)
├── tasks.py                Invoke task definitions (setup, reset, test, lint, etc.)
├── terminal/               Terminal emulator configs (Ghostty)
└── tests/                  Pytest suite for tasks.py and scripts/setup.py
```

## Rules

- Shell scripts use `lib/platform.sh` for cross-platform helpers (`detect_os`, `ensure_symlink`, etc.)
- AI tool configs live in `ai/modules/<tool>/` — never edit deployed configs in `~/.claude/`, `~/.gemini/`, etc. directly
- `ai/work/` is gitignored — put work-specific (non-public) configs there
- `ai/skills/` contains shared skills consumed by all tools that support them
- `scripts/setup.py` is the single source of truth for AI tool deployment — it reads `ai/tools.json`
- Tests must pass before committing: `inv test && inv lint && inv typecheck`
- Python code follows the patterns in `ai/memory/python.md`

## Pitfalls

| Issue | Fix |
|-------|-----|
| AI tool config not updating | Run `python scripts/setup.py <tool>` to re-deploy symlinks |
| ~/.zshrc missing tool lines after reset | Use `inv reset --keep` to preserve tool-installed lines |
| Setup fails on fresh machine | Run `scripts/bootstrap` first to install uv and Python |
| Backup files piling up | Run `inv cleanup` to remove stale `.backup.*` files |
