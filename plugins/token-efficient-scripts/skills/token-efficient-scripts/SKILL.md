---
name: token-efficient-scripts
description: Write throwaway bash/python commands used by Codex-, Claude-, or similar agent harnesses for one-off searching, counting, filtering, or aggregation over files, logs, simple CSV, or JSON. Use when a disposable command should answer a question while returning minimal tool output and avoiding unnecessary work. Prioritize correctness, output control, predicate pushdown, and only then code trimming. Do NOT use for production, library, or long-lived code where robustness and readability matter.
---

# Token-efficient throwaway scripts

For agent-written one-off scripts, context use is often dominated by **output tokens** (what the command returns to the harness), not the code. Optimize in this order. A 10-task validation found the same answer in every experiment, with a 90.4% mean output reduction across seven output-focused tasks. See [references/benchmark-findings.md](references/benchmark-findings.md) when evaluating the evidence or quoting results.

## Tier 1 — Control output (40.6–99.999% measured; the dominant lever)

Treat every printed token as context cost. Harnesses may truncate, compact, or cache tool output differently, but unbounded output can still dwarf a short command.

- **Return the answer, not the data.** Use `grep -c`/`rg -c` for matching-line counts; use `wc -l`, `uniq -c`, or `awk` sums/counts to aggregate instead of dumping rows.
- **Cap exploratory output:** `| head -N`, SQL `LIMIT`, `jq '.[:N]'`. Never let a listing run unbounded.
- **Project only needed fields**, not whole records: `jq -r '.[].id'` not `jq '.'`; `awk '{print $1}'` not the whole line. (~83% on record dumps.)
- **Prefer compact/tabular output when machine readability is enough:** use `jq -c` or `jq -r '…|@tsv'` instead of `jq '.'`. Complete compact JSON saved 40.64% in the validation; savings depend on structure.
- **Need the full data? Spill to a file, print a summary + path** — don't stream it through context:
  `cmd > /tmp/out.txt; echo "$(wc -l </tmp/out.txt) rows -> /tmp/out.txt"; head -3 /tmp/out.txt` (137k tokens → 84.)

## Tier 2 — Push predicates early & benchmark fast tools (1.68× measured for filter-before-sort)

- **Filter closest to the source.** `awk '$4==500{print $1}' log | sort -u` beats `sort log | awk …` — the filter shrinks what later stages process. This also fixes slow sort-heavy pipelines.
- **Filter inside the reader, not after:** `jq 'select(...)'` beats `jq '.[]' | grep`. (1.5×.)
- **Prefer `rg`/`fd` when installed**, but treat speed as workload-dependent; fall back to `grep`/`find` if absent. In the validation workload, `rg -c` was 6.99× faster than `grep -c`, not a universal ratio.
- **Short-circuit large sources:** `find … | head` stops early. Worth it only when the source is large or each item is expensive; negligible on small trees.
- Drop useless `cat` and redundant pipe stages.

## Tier 3 — Trim the code after correctness (40% fewer command tokens in one test)

- **Default to a bash command over Python.** For search/count/filter/aggregate, reach for `grep`/`rg`/`awk`/`jq`/`find`/`sort`/`uniq`/`wc` first — if a shell one-liner does the job while preserving semantics, use it. Only fall back to Python when the task genuinely needs it: complex parsing, multi-key grouping, quoted-CSV, or cross-platform behavior a one-liner can't handle safely.
- **For throwaway Python, skip the ceremony — readability is not a goal for one-off code.** No comments, no docstrings, no `argparse` (use `sys.argv`), no `main()`/`if __name__`, no try/except (a traceback is acceptable for a disposable script). Add any of these back only if the script will live on or if error handling actually protects correctness or prevents a flood of failure output.
- **Remove unnecessary intermediate variables**; keep variables that clarify semantics or prevent repeated work.
- **1-token names, not 1-char golf.** `count` and `c` both cost 1 token; keep normal spacing. Golfing saves characters, not tokens, and hurts correctness review.
- **Do not infer speed from brevity.** The validation's shorter `awk` command used 40% fewer command tokens but ran 3.29× slower than its Python baseline.

## Self-improvement protocol (run this when you benchmark or discover something new)

This skill is designed to learn from its own use. When a run produces a measurement or a failure mode not already recorded:

1. **Always append** the raw result to the findings log — an append-only log, cheap to grow. Standalone: `references/benchmark-findings.md` (helper: `python3 references/log-run.py "<title>" < body.md`). Installed as a plugin: the shipped file is a read-only cache, so runtime findings go to `${CLAUDE_PLUGIN_DATA}/findings-log.md` (the `/bench` command does this for you). Record the environment (machine, tools present, tokenizer used) and whether the optimized command gave the **same answer**.
2. **Only edit the tiers/guardrails in this file when a finding is (a) replicated across ≥2 runs and (b) material** — a new guardrail, a corrected range, or a technique that changes the priority order. Keep this file lean: every line here is re-loaded into context on each use, so unproven detail belongs in the reference log, not here.
3. **Never inflate a claim.** If a run contradicts a stated range (e.g. compact-JSON savings came in at ~50%, not 50–79%), correct the range here and cite the run. Prefer measured ranges + environment over universal percentages.
4. New correctness traps go straight into the guardrails list below (they are cheap and high-value); new speed/token magnitudes stay as ranges.

## Correctness guardrails (a smaller script must give the SAME answer)

- **`wc -l` counts newlines, not lines** — off by one per file lacking a trailing newline.
- **`cat file1 file2` glues the last token of one file to the first of the next** when files lack a trailing newline. Process files separately (`awk` over the file list, `grep -h`) when boundaries matter.
- **`sort` before `uniq`** — `uniq` only dedupes adjacent lines.
- **Ties make "top N" ambiguous** — a different tie-break order is not a bug.
- **Judge equivalence on the data, not the formatting** (dict vs columnar, quoting, trailing spaces).

## Validation summary

Ten deterministic throwaway tasks were tested on Darwin arm64. Every optimized command produced the same task answer as its baseline.

- Seven output-focused tasks averaged **90.4% fewer output tokens**; the median reduction was **99.97%**.
- Answer/preview/spill tasks, excluding a case that required the complete JSON value, produced a **99.16% combined reduction**.
- Compact JSON saved **40.64%**, below the earlier 50–79% estimate.
- Filter-before-sort ran **1.68× faster**; `rg -c` ran **6.99× faster** than `grep -c` on the tested workload.
- Spilling complete results to a file saved **99.97% of returned tokens** but ran **1.64× slower**.
- Shortening a Python command to `awk` cut command tokens **40%** but ran **3.29× slower**.

Interpret token counts as directional: the benchmark used `cl100k_base` for continuity with the original measurements, not the private tokenizer or billing behavior of every current agent harness. Do not turn these measurements into a universal monthly cost claim without a representative workload, current pricing, and harness-specific accounting. Read [references/benchmark-findings.md](references/benchmark-findings.md) for the full experiment table, methodology, and limitations.

## Cheat sheet

| Task | Instead of Python | Use |
|---|---|---|
| Count matching lines | print matches | `grep -c` / `rg -c` |
| Count files recursively | `os.walk` | `find root -type f \| wc -l` |
| Sum/avg a simple unquoted CSV column | `csv` module | `awk -F, '{s+=$2}END{print s}'` |
| Group-by aggregate | `defaultdict` | `awk '{s[$k]+=$v}END{...}'` |
| Filter JSON array | `json.load`+loop | `jq '.[] \| select(...)'` |
| Top-N frequency | `Counter` (small) | `sort\|uniq -c\|sort -rn\|head` |
| Files by mtime/size | `os.walk`+stat | `find -mtime/-size` |

Prior art: this generalizes Infracost's "predicate pushdown" (push filtering close to the data) to script authoring, adding the output-frugality and correctness dimensions.
