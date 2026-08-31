# Changelog

All notable changes to the `token-efficient-scripts` plugin. Earlier history is in the git log.

## 0.5.0 — 2026-08-31

### Added — failed-command recovery

The skill covered writing a good command; it said nothing about the moment a command **fails**,
where the default reflex (read the man page) is the most expensive documentation habit available.

- **New skill section: "When a command fails — recover in this order."** A cheapest-first
  escalation ladder: the error text you already have → `cmd --help` → a tight `man | grep` →
  the web, and only for what local docs structurally cannot say.
- **New platform table** in the cheat sheet: the eight measured GNU→BSD/macOS fixes
  (`date -v`, `stat -f %z`, `du -d`, `grep -E`, `xargs -0`, `sed -i ''`, `-exec basename`,
  `gtimeout`), so an agent with the skill loaded pays **zero** tokens for these.
- **New benchmark** `scripts/bench-recovery.py` + `scripts/run-bench-recovery.sh`, measuring
  every recovery strategy on three axes: tokens returned, whether that text **actually contains
  the answer**, and wall clock. Every replacement command is verified correct in the same run.
  Scenarios are **prechecked** — on GNU userland the benchmark reports *not applicable* instead
  of producing meaningless numbers. `BENCH_NET=0` skips the network leg.
- **New command** `/token-efficient-scripts:bench-recovery`.
- **New reference** `references/cli-failure-recovery.md` — method, per-scenario table, traps,
  limitations.
- **Two new correctness guardrails:** a man page you got may not be the tool you meant
  (`man timeout` returns ncurses `curs_inopts(3X)`); GNU flags are not BSD flags.
- Skill `description` now also triggers on a **just-failed** command, not only on writing one.

### Measured (Darwin 25.5 arm64, cl100k_base, all fixes verified correct)

| | tokens | solved | tool calls | wall clock |
|---|---:|:---:|:---:|---:|
| straight to `man` | 26,316 | 6/8 | 8 | 0.85s |
| error → `--help` → tight `man\|grep` → web | **3,166** | **8/8** | 11 | 0.90s |

**8.3× fewer tokens, two more scenarios solved.** The man-page leg alone drops 30×
(26,316 → 870) for the same 6/8 answers.

### Explicitly not claimed

- **No speed saving.** Every ladder measured within 0.43–0.90s; the benchmark does not
  demonstrate a wall-clock win and the docs say so.
- **Costs round trips.** Per failure the naive path is 1 tool call; the ladder is 0–3.
- **Platform-specific.** These are BSD-userland failures; on GNU userland they do not occur.
- Single host, `cl100k_base` proxy. Token counts are directional; the ordering of strategies
  is the robust finding.

## 0.4.0 and earlier

Three-tier skill (output control, predicate pushdown, code trimming), correctness guardrails,
`/bench` benchmark with an append-only findings log, stop hook, and a weekly unattended
re-benchmark. See the git log and `references/benchmark-findings.md`.
