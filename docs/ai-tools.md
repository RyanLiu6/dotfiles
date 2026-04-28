# AI Tools

The `ai/` directory manages configurations for multiple AI CLI tools from a single source of truth.

## Overview

```
ai/
├── memory/             Shared memory files (@-imported by tool-specific CLAUDE.md)
├── modules/            Per-tool configs deployed via symlink
│   ├── claude/         Claude Code: CLAUDE.md, hooks/, settings.json, statusline.sh
│   ├── codex/          Codex CLI + oh-my-codex: AGENTS.md, bootstrap.sh
│   ├── gemini/         Gemini CLI: GEMINI.md
│   ├── opencode/       OpenCode: AGENTS.md, opencode.json, agents/
│   ├── cursor/         Cursor
│   ├── antigravity/    Antigravity
│   └── vscode/         VS Code
├── skills/             Shared skill definitions (consumed by all supporting tools)
├── templates/          Reusable templates for repo-level files
├── tools.json          Tool registry — schema below
└── work/               Work-specific overrides (gitignored, not committed)
    ├── modules/        Per-tool overlays, mirrors modules/ layout
    └── skills/         Work-specific skills (picked up via extra_skills_dirs)
```

## tools.json Schema

Each tool entry in `tools.json` defines how `scripts/setup.py` deploys it:

```jsonc
{
  "name": "Claude Code",          // Display name
  "config_dir": "~/.claude",      // Where configs are deployed
  "tool_dir": "modules/claude",   // Source directory (relative to ai/)
  "symlinks": [                   // Files/dirs symlinked into config_dir
    {"source": "CLAUDE.md", "target": "CLAUDE.md"}
  ],
  "settings_template": {          // Copy template if target doesn't exist
    "template": "settings.template.json",
    "target": "settings.json"
  },
  "skills_symlink": {             // Symlink individual skills into config_dir/target/
    "source": "skills",
    "target": "skills"
  },
  "agents_symlink": {             // Symlink agent .md files (OpenCode)
    "source": "modules/opencode/agents",
    "target": "agents"
  },
  "skills_generate": {            // Generate skill files (Gemini TOML, Cursor MD)
    "source": "skills",
    "target": "commands",
    "format": "toml"
  },
  "bootstrap": "bootstrap.sh",    // Script run from tool_dir before symlinks (e.g., npm install)
  "extra_skills_dirs": ["work/skills"]  // Additional skills dirs (e.g., gitignored work skills)
}
```

## Skills

Skills live in `ai/skills/<skill-name>/SKILL.md`. Each skill is a markdown file with YAML frontmatter:

```yaml
---
name: rreview
description: Code review orchestrator with scout, review, and confidence filter phases
argument-hint: "[PR-number]"
user-invocable: true
allowed-tools: Read, Glob, Grep, Bash, Agent, Task
---
```

Skills are deployed differently per tool:
- **Claude Code / OpenCode / Antigravity**: Symlinked as directories into the tool's skills folder
- **Gemini CLI**: Converted to TOML format and written to `~/.gemini/commands/`
- **Cursor**: Copied as markdown to `~/.cursor/commands/`

## Agents (OpenCode)

OpenCode agents live in `ai/modules/opencode/agents/*.md` with frontmatter:

```yaml
---
description: Read-only codebase cartographer
color: "#4169E1"
tools:
  read: true
  glob: true
  grep: true
---
```

These are symlinked individually into `~/.config/opencode/agents/`.

## Templates

`ai/templates/` contains reusable templates meant to be copied into repo roots:

- `agents-reviews.md` — Review standards (copy as `AGENTS.reviews.md`)
- `rules/python-patterns.md` — Python code patterns (copy to `.claude/rules/`)
- `rules/react-patterns.md` — React patterns
- `rules/typescript-patterns.md` — TypeScript patterns

Templates have a `description` in frontmatter explaining their purpose and where to place them.

## Work Directory

`ai/work/` is gitignored. Its layout mirrors `ai/modules/` so work-specific
overrides are per-tool:

```
ai/work/
├── modules/
│   ├── codex/          # e.g., config.toml with IC AI Gateway provider
│   └── opencode/       # e.g., setup-providers.sh, overlay JSON
└── skills/             # work-specific skills (symlinked via extra_skills_dirs)
```

### How overlays are applied

For each tool, after the public module is deployed, `setup.py` checks for
`ai/work/modules/<tool_id>/`. If present, each file is handled by extension:

| Overlay file | Action |
|---|---|
| `*.sh` | Made executable and run. Intended for idempotent setup scripts (e.g., generating provider URLs from env/email). |
| any other file | Symlinked into the config directory with the same name, fully replacing any public file of that name. |

The overlay phase is opt-in by presence: no flags, no profile system. If
`ai/work/modules/<tool_id>/` is absent or empty, the public module ships
untouched. To reset cleanly after changing overlays, run `inv reset && inv setup`.

### Backporting settings changes

When you edit a file in `ai/modules/<tool>/` that also has a work overlay
counterpart in `ai/work/modules/<tool>/`, the overlay copy must be
hand-updated. Overlays fully replace the public file — they do not
merge. Nothing detects drift automatically.

### Bootstrap

Tools with `"bootstrap": "<script>.sh"` run the named script from their
`tool_dir` before any symlinks are laid down. This is where package
installs happen — for example, `modules/codex/bootstrap.sh` runs
`npm install -g @openai/codex oh-my-codex` and `omx setup`. Bootstrap
scripts must be idempotent.

Bootstrap requires a TTY on first run — `omx setup` may prompt
interactively. `inv setup` already uses `pty=True`, so this is only
relevant if someone calls `scripts/setup.py` directly in CI.

## Setup Flow

```bash
# Deploy all tools
python scripts/setup.py

# Deploy a specific tool
python scripts/setup.py claude

# List available tools
python scripts/setup.py --list
```

The setup script:
1. Reads `ai/tools.json`
2. For each tool: creates config dir, symlinks files, generates skills, copies templates
3. Handles backups of existing non-symlink configs
