#!/usr/bin/env bash
# Run the failed-command recovery benchmark, append a dated summary to the persistent data dir.
# BENCH_NET=0 skips the network leg (offline / sandboxed hosts).
set -euo pipefail
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
DATA="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/te-scripts-data}"
mkdir -p "$DATA"
python3 "$ROOT/scripts/bench-recovery.py" "$DATA/recovery-log.md"
