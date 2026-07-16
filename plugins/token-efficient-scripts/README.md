# token-efficient-scripts (Claude Code plugin)

Write throwaway bash/python for one-off file & data tasks so they cost minimal tokens and run fast — and let the skill improve itself from its own benchmark runs.

## What's inside

```
token-efficient-scripts/
├── .claude-plugin/plugin.json
├── skills/token-efficient-scripts/
│   ├── SKILL.md                        # the skill (3-tier decision rule + guardrails)
│   └── references/
│       ├── benchmark-findings.md       # shipped read-only baseline findings
│       └── log-run.py                  # append helper (standalone use)
├── commands/bench.md                   # /token-efficient-scripts:bench
├── hooks/hooks.json                    # Stop hook -> scripts/on-stop.sh
└── scripts/
    ├── bench.py                        # portable benchmark (tiktoken optional)
    ├── run-bench.sh                    # runs bench.py, logs to $CLAUDE_PLUGIN_DATA
    └── on-stop.sh                      # cheap deduped datapoint on session stop
```

## Install

From GitHub:

```
/plugin marketplace add MaceTenth/token-efficient-scripts
/plugin install token-efficient-scripts@macetenth-plugins
```

Or from a local clone:

```
/plugin marketplace add /path/to/token-efficient-scripts
/plugin install token-efficient-scripts@macetenth-plugins
```

## Use

- The **skill** activates automatically when you write a disposable script for a file/data question.
- Run **`/token-efficient-scripts:bench`** to re-benchmark and log any new finding.

## Self-improvement model

- Runtime findings accumulate in `${CLAUDE_PLUGIN_DATA}/findings-log.md` — this **survives plugin updates**; the bundled `benchmark-findings.md` is the read-only baseline.
- A finding is promoted into `SKILL.md` only when **replicated (≥2 runs) and material** (new guardrail, corrected range, changed priority). New correctness traps go in immediately.
- Promotion is a maintainer step: edit the source `SKILL.md`, bump `version` in `plugin.json`, then `/plugin marketplace update macetenth-plugins`.

## Unattended cadence (optional)

The Stop hook logs a cheap datapoint per session. For scheduled re-benchmarking with no one present, pair `/bench` with a scheduled cloud agent (routine) that runs `scripts/run-bench.sh`.

## Notes

- Token counts use `cl100k` (tiktoken) if installed, else a `chars/4` proxy — figures are approximate; percentages are the robust part.
- The plugin cache is read-only after install; never write into the plugin tree at runtime — use `${CLAUDE_PLUGIN_DATA}`.
