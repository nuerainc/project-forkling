#!/usr/bin/env bash
# bootstrap.sh — install dogfood on any device with python + git.
#
# Usage:
#   curl -fsSL <raw-url>/scripts/bootstrap.sh | bash
#   # or, after clone:
#   ./scripts/bootstrap.sh
#
# What this does:
#   1. Verifies python >= 3.9 and git are present
#   2. Optionally installs Ollama if it isn't already there
#   3. Installs the package in editable mode (no deps — stdlib only)
#   4. Runs `python -m dogfood doctor` so you can see the runtime state

set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ dogfood bootstrap"

if ! command -v python >/dev/null 2>&1; then
  echo "✗ python not found on PATH. Install python 3.9+ first." >&2
  exit 1
fi
if ! command -v git >/dev/null 2>&1; then
  echo "✗ git not found on PATH. Install git first." >&2
  exit 1
fi

PY="$(command -v python)"
PYVER="$("$PY" -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
MAJOR="${PYVER%%.*}"
MINOR="${PYVER#*.}"
if [ "$MAJOR" -lt 3 ] || { [ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]; }; then
  echo "✗ python >= 3.9 required (have $PYVER)." >&2
  exit 1
fi
echo "✓ python $PYVER"

# Install package — no deps, stdlib only.
"$PY" -m pip install -e . >/dev/null
echo "✓ installed"

# Ollama is optional; if it's already there, we'll see it in `doctor`.
if command -v ollama >/dev/null 2>&1; then
  echo "✓ ollama already installed"
else
  echo "ℹ ollama not detected — agent will use the rule-based fallback."
  echo "  (Optional) Install from https://ollama.com/download to enable local LLMs."
fi

echo
echo "→ doctor:"
"$PY" -m dogfood doctor
echo
echo "✅ dogfood ready. Try:"
echo "   $PY -m dogfood plan \"list dogfood\""
echo "   $PY -m dogfood self-improve"