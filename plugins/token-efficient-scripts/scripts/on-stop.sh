#!/usr/bin/env bash
# Stop hook: cheap, dependency-free output-control datapoint, deduped so the log stays quiet.
# Demonstration of continuous self-logging — remove this hook from hooks.json if unwanted.
set -euo pipefail
DATA="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/te-scripts-data}"
mkdir -p "$DATA"; log="$DATA/findings-log.md"
tmp="$(mktemp)"; i=0; while [ $i -lt 20000 ]; do echo "10.0.0.1 - - 404 /x"; i=$((i+1)); done > "$tmp"
dump=$(grep ' 404 ' "$tmp" | wc -c | tr -d ' ')
cnt=$(grep -c ' 404 ' "$tmp" | wc -c | tr -d ' ')
rm -f "$tmp"
red=$(( (dump - cnt) * 100 / dump ))
line="stop-hook output-control proxy: dump=${dump}B vs count=${cnt}B (${red}% less)"
# dedupe: only append if the measurement changed since last time
[ -f "$log" ] && grep -qF "$line" "$log" && exit 0
printf -- '- %s %s\n' "$(date +%F)" "$line" >> "$log"
