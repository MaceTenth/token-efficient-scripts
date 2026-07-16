<div align="center">

# ⚡ token-efficient-scripts

**A Claude Code plugin for throwaway bash/python that costs almost nothing.**

![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-plugin-8A63D2)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Self-benchmarking](https://img.shields.io/badge/self--benchmarking-weekly-brightgreen)

**[🎞️ View the interactive slide →](https://macetenth.github.io/token-efficient-scripts/slide.html)**

</div>

> For one-off shell/python that searches, counts, filters, or aggregates data, the token bill is dominated by **what the command prints back into context** — not the code. Optimize output first, data flow second, code last.

---

## The one number that matters

Same answer — *"count the 404s in a 60k-line log"* — measured as tokens returned to context:

| | command | tokens into context |
|---|---|---|
| ❌ | `grep ' 404 ' log` | **137,136** |
| ✅ | `grep -c ' 404 ' log` | **3** |

Every token a command prints is injected into context **and re-billed every turn it lingers** in an agent loop. Controlling output is the whole game.

---

## How it works — three tiers, by impact

| Tier | Lever | Billed as | Measured |
|---|---|---|---|
| **1** | **Control output** — return the answer, cap rows, project fields, spill big results to a file | input tokens | up to **~100%** |
| **2** | **Push filters early & use fast tools** — predicate pushdown, `rg`/`fd`, filter inside `jq` | runtime | **1.5–2.5×** |
| **3** | **Trim the code** — no argparse/`main()`/docstrings/try-except; shell over python | output tokens | **~25–40%** |

…all gated by correctness guardrails: `wc -l` counts newlines not lines; `cat` glues newline-less file boundaries; `sort` before `uniq`; ties ≠ bug; judge equivalence on the data, not the formatting.

---

## Benchmarks

All optimized commands were verified to return the **same answer** as their baseline. Token counts use `cl100k` (tiktoken) as a proxy — the **percentages are the robust part; absolute dollars are ±20%**.

<details open>
<summary><b>Output-token reduction across 6 tasks (99.5% combined)</b></summary>

| Task | Technique | Output naive | Output opt | Saved | Speedup |
|---|---|---:|---:|---:|---:|
| Count 404s | dump matches → return the count | 137,136 | 3 | 100% | 1.1× |
| Unique IPs w/ 500 | sort-all → **filter-then-sort** | 4 | 4 | — | **1.7×** |
| Largest files | dump all → `head -10` | 16,181 | 515 | 97% | 1.0× |
| Return 100 records | pretty JSON → **TSV rows** | 2,402 | 500 | 79% | 1.0× |
| Return 100 records | pretty JSON → compact JSON | 2,402 | 1,202 | 50% | 1.0× |
| Category summary | dump rows → aggregate to 2 lines | 299,500 | 22 | 100% | 0.9× |
| **Total** | | **457,625** | **2,246** | **99.5%** | 1.2× |

</details>

<details>
<summary><b>Refinement levers (spill-to-file, projection, tool choice)</b></summary>

| # | Technique | Metric | Result | Verdict |
|---|---|---|---|---|
| 1 | **Spill big result to file** + print summary | output tokens | 137,136 → 84 | ✅ Huge (100%) |
| 3 | **Return only needed fields** (ids vs whole objects) | output tokens | 2,402 → 400 | ✅ Strong (83%) |
| 4 | **`rg` instead of `grep`** | runtime | 2.5× faster | ✅ Strong (if `rg` installed) |
| 5 | **Pushdown into `jq`** (vs `dump\|grep\|wc`) | runtime | 1.5× faster | ✅ Good |
| 6 | **Project + filter early**, drop useless `cat`/stages | runtime | 1.2× faster | ✅ Modest but free |
| 2 | **Early `head` short-circuit** | runtime | 1.1× | ⚠️ Marginal at small scale |

</details>

<details>
<summary><b>Independent verification run — 10 experiments</b></summary>

| # | Experiment | Correct? | Output reduction | Runtime effect |
|---|---|:---:|---:|---|
| 1 | Count ERROR lines with `rg -c` | Yes | 99.999% | 1.39× faster |
| 2 | Project JSON IDs instead of records | Yes | 93.49% | 1.40× faster |
| 3 | Count JSON matches inside `jq` | Yes | 99.998% | 1.27× faster |
| 4 | Sum CSV values inside `awk` | Yes | 99.998% | 1.03× faster |
| 5 | Compact instead of pretty JSON | Yes | 40.64% | 1.21× faster |
| 6 | Cap exploratory `find` with `head` | Yes | 99.00% | 1.33× faster |
| 7 | Spill full results to a file | Yes | 99.97% | 0.61× as fast |
| 8 | Filter before sorting | Yes | no change | 1.68× faster |
| 9 | `rg -c` vs `grep -c` | Yes | no change | 6.99× faster |
| 10 | Short `awk` vs verbose Python | Yes | no change | 40% fewer code tokens, 3.29× slower |

</details>

> 📊 Full run log (append-only, updated weekly): [`benchmark-findings.md`](plugins/token-efficient-scripts/skills/token-efficient-scripts/references/benchmark-findings.md) · one-slide explainer: **[live slide](https://macetenth.github.io/token-efficient-scripts/slide.html)** ([source](slide.html))

---

## What it saves (illustrative)

An active user (~3,000 throwaway scripts/month, single-read baseline; not a universal guarantee — depends on task mix, tokenizer, caching):

| Model | Without | With | Saved |
|---|---|---|---|
| Sonnet 5 ($3/$15) | ~$54/mo | ~$3.45/mo | **~94%** |
| Opus 4.8 ($5/$25) | ~$91/mo | ~$5.75/mo | **~94%** |

In agent sessions where output lingers, the Opus saving is closer to **~$250/mo** (input re-billed each turn).

---

## Install

```
/plugin marketplace add MaceTenth/token-efficient-scripts
/plugin install token-efficient-scripts@macetenth-plugins
```

## Use

- The **skill** activates automatically when you write a disposable script for a file/data question.
- **`/token-efficient-scripts:bench`** — re-runs the benchmark locally and appends the result to your own `${CLAUDE_PLUGIN_DATA}/findings-log.md`. It runs entirely on your machine and does **not** push anywhere.

## Self-improvement model

- Runtime findings accumulate in `${CLAUDE_PLUGIN_DATA}` (survives plugin updates).
- A finding is promoted into `SKILL.md` only when **replicated (≥2 runs) and material**; new correctness traps go in immediately.
- **Publishing to this repo is a maintainer action** — a weekly scheduled task on the maintainer's machine re-benchmarks, appends to the findings file, and pushes. Contributors benchmark locally; they don't publish here.

## Repo layout

```
.claude-plugin/marketplace.json      # marketplace manifest (macetenth-plugins)
plugins/token-efficient-scripts/     # the plugin: skill + /bench command + stop hook + benchmark
slide.html                           # one-slide explainer
```

## Notes

- **Platform:** the bash one-liners need a POSIX shell + coreutils — macOS, Linux, WSL, or Windows with Git Bash. On native Windows without Git Bash (where Claude Code falls back to the PowerShell tool) they won't run — use Python or PowerShell equivalents there. The token-efficiency *principles* (return the answer, cap output, filter early) apply on any shell.
- Token counts use `cl100k` (tiktoken) if installed, else a `chars/4` proxy — figures are approximate; the percentages and the ordering of levers are the robust findings.
- The plugin cache is read-only after install; runtime writes go to `${CLAUDE_PLUGIN_DATA}`, never into the plugin tree.

<div align="center"><sub>Built with Claude Code · MIT</sub></div>
