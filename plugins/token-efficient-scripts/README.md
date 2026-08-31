# token-efficient-scripts (Claude Code plugin)

Write throwaway bash/python for one-off file & data tasks so they cost minimal tokens and run fast — and let the skill improve itself from its own benchmark runs.

## What's inside

```
token-efficient-scripts/
├── .claude-plugin/plugin.json
├── skills/token-efficient-scripts/
│   ├── SKILL.md                        # the skill (3 tiers + recovery ladder + guardrails)
│   └── references/
│       ├── benchmark-findings.md       # shipped read-only baseline findings
│       ├── cli-failure-recovery.md     # failed-command recovery findings
│       └── log-run.py                  # append helper (standalone use)
├── commands/
│   ├── bench.md                        # /token-efficient-scripts:bench
│   └── bench-recovery.md               # /token-efficient-scripts:bench-recovery
├── hooks/hooks.json                    # PreToolUse(Bash) -> pre-bash-man.py; Stop -> on-stop.sh
└── scripts/
    ├── bench.py                        # portable benchmark (tiktoken optional)
    ├── bench-recovery.py               # failed-command recovery benchmark
    ├── pre-bash-man.py                 # DENIES unfiltered `man`, returns the ladder
    ├── test-pre-bash-man.py             # 35 tests for that hook (--e2e drives real claude)
    ├── run-bench.sh                    # runs bench.py, logs to $CLAUDE_PLUGIN_DATA
    ├── run-bench-recovery.sh           # runs bench-recovery.py, logs to $CLAUDE_PLUGIN_DATA
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

### The `man` hook (enforcement, not suggestion)

A skill is injected text: it biases the model, it cannot stop a tool call. This plugin also
ships a **`PreToolUse` hook** that does stop one — an unfiltered `man` is **denied**, and the
denial hands back the ladder (`--help`, then a tight `grep`, then the web).

It is deliberately narrow, and **fails open** on anything unexpected:

| denied | allowed |
|---|---|
| `man find` | `man find \| col -b \| grep -nE -m3 -B2 -A3 'printf'` |
| `man 5 hosts` | `man -k compress`, `man -w find` (already tiny) |
| `man find \| col -b`, `man x \| less` (still the whole page) | `man find > /tmp/f` (never enters context) |
| `MANWIDTH=80 man date` | `TE_ALLOW_MAN=1 man find` (explicit override) |

No false positives on `human`, `command -v man`, `/usr/share/man`, or bare `man`.

The denial itself costs **229 tokens** — 93% less than the average man page it replaces, and it
is actionable rather than just a refusal. **To disable it**, delete the `PreToolUse` block from
`hooks/hooks.json`, or use the `TE_ALLOW_MAN=1` prefix per call.

**Tests.** A hook that misfires is worse than no hook, so it has its own suite:

```
python3 scripts/test-pre-bash-man.py          # 35 cases: fast, free, no API, no network
python3 scripts/test-pre-bash-man.py --e2e    # ALSO drives a real `claude -p` (costs money)
```

The unit matrix covers what must be denied (`man find`, `man 5 hosts`, `MANWIDTH=80 man date`,
and pipes that don't reduce — `| col -b`, `| cat`, `| less`), what must be allowed (a reducing
filter, `-k`/`-w`/`-f`/`--help`, redirects, the override), and what must never false-positive
(`human`, `command -v man`, `/usr/share/man`, `apropos`, bare `man`). Six cases assert it
**fails open** on malformed stdin, a missing field, or a non-Bash tool. Exits non-zero on any
failure.

`--e2e` spawns a real headless session via `--settings` and asserts both directions — that the
denial reaches the model, and that a filtered `man` still runs. It touches no config of yours.

## Self-improvement model

- Runtime findings accumulate in `${CLAUDE_PLUGIN_DATA}/findings-log.md` — this **survives plugin updates**; the bundled `benchmark-findings.md` is the read-only baseline.
- A finding is promoted into `SKILL.md` only when **replicated (≥2 runs) and material** (new guardrail, corrected range, changed priority). New correctness traps go in immediately.
- Promotion is a maintainer step: edit the source `SKILL.md`, bump `version` in `plugin.json`, then `/plugin marketplace update macetenth-plugins`.

## Unattended cadence (optional)

The Stop hook logs a cheap datapoint per session. For scheduled re-benchmarking with no one present, pair `/bench` with a scheduled cloud agent (routine) that runs `scripts/run-bench.sh`.

## Notes

- Token counts use `cl100k` (tiktoken) if installed, else a `chars/4` proxy — figures are approximate; percentages are the robust part.
- The plugin cache is read-only after install; never write into the plugin tree at runtime — use `${CLAUDE_PLUGIN_DATA}`.
