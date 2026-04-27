#!/usr/bin/env bash
#
# Bootstrap Codex CLI with oh-my-codex (OMX).
#
# Installs @openai/codex and oh-my-codex globally via npm, then runs
# `omx setup` to scaffold ~/.codex/ (prompts, hooks, AGENTS scaffolding,
# native codex config.toml). Safe to re-run — npm will no-op if the
# latest versions are already installed.

set -euo pipefail

if ! command -v npm >/dev/null 2>&1; then
  echo "bootstrap: npm not found. Install Node.js 20+ first." >&2
  exit 1
fi

echo "bootstrap: ensuring @openai/codex and oh-my-codex are installed..."
npm install -g @openai/codex oh-my-codex

if ! command -v omx >/dev/null 2>&1; then
  echo "bootstrap: omx not on PATH after install. Check your npm global prefix." >&2
  exit 1
fi

echo "bootstrap: running omx setup..."
omx setup

echo "bootstrap: codex + oh-my-codex ready."
