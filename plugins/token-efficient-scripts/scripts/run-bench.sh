#!/usr/bin/env bash
# Run the portable benchmark and append a dated summary to the persistent data dir.
set -euo pipefail
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
DATA="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/te-scripts-data}"
mkdir -p "$DATA"
python3 "$ROOT/scripts/bench.py" "$DATA/findings-log.md"
