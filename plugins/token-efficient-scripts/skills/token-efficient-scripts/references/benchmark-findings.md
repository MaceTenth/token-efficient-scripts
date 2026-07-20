# Benchmark findings: token-efficient throwaway scripts

## Executive summary

The skill's primary recommendation is supported: for disposable commands emitted by an agent harness, returning the answer instead of raw records can reduce context dramatically without changing the task result.

Ten deterministic experiments were run on 2026-07-15. All ten optimized commands produced the same task answer as their baselines. Across the seven output-focused experiments, the mean output-token reduction was 90.4% and the median was 99.97%. The experiment does not establish a universal monthly cost saving because task mix, tokenizer, caching, compaction, truncation, pricing, and retained context vary by harness.

## Scope and environment

- Purpose: test one-off commands a Codex- or Claude-style agent writes while inspecting files or data.
- Platform: Darwin arm64.
- Token counter: `tiktoken` with `cl100k_base`, matching the original skill's method. This is a proxy, not a claim about any current model's private tokenizer.
- Data: deterministic synthetic logs, JSON, simple CSV, TSV, and a 2,000-file directory tree.
- Timing: median wall time over repeated runs—three repetitions for most output tests, five for filter/code tests, and nine for `grep` versus `rg`.
- Correctness rule: compare the task answer, not presentation differences. An optimization fails if it changes the requested IDs, count, sum, JSON value, preview, stored records, or unique set.

## Results

| # | Task and transformation | Same answer | Baseline tokens | Optimized tokens | Reduction | Speedup |
|---:|---|:---:|---:|---:|---:|---:|
| 1 | Print ERROR records → `rg -c` | Yes | 370,940 | 3 | 99.999% | 1.39× |
| 2 | Full active-user JSON → project `.id` | Yes | 179,244 | 11,666 | 93.49% | 1.40× |
| 3 | Red-team JSON records → `jq` count | Yes | 134,482 | 3 | 99.998% | 1.27× |
| 4 | Matching EU CSV rows → `awk` sum | Yes | 366,340 | 6 | 99.998% | 1.03× |
| 5 | Pretty complete JSON → compact JSON | Yes | 885,827 | 525,827 | 40.64% | 1.21× |
| 6 | Unbounded `find` → first 20 paths | Yes | 88,000 | 880 | 99.00% | 1.33× |
| 7 | Full ERROR stdout → file + count + preview | Yes | 370,940 | 107 | 99.97% | 0.61× |
| 8 | Sort all TSV rows → filter before sort | Yes | 34,187 | 34,187 | 0% | 1.68× |
| 9 | `grep -c` → `rg -c` | Yes | 3 | 3 | 0% | 6.99× |
| 10 | Ceremony-heavy Python → short `awk` count | Yes | 3 | 3 | 0% | 0.30× |

In experiment 10, the command itself fell from 80 to 48 `cl100k_base` tokens, a 40% reduction, while runtime became 3.29× slower.

## Aggregate findings

### Output control

- Mean reduction across seven output experiments: **90.4%**.
- Median reduction across those experiments: **99.97%**.
- Combined reduction across all seven: **77.52%**. The complete-JSON experiment dominates this weighted figure because the full data genuinely had to be returned.
- Combined reduction across answer/preview/spill tasks, excluding complete JSON: **99.16%**.
- Observed range: **40.64–99.999%**.

This verifies the mechanism behind Tier 1. It does not guarantee the same average for an arbitrary workload.

### Predicate pushdown and tool choice

Filtering a 300,000-row TSV before sorting produced a 1.68× speedup, supporting the low end of the skill's earlier 1.5–2.5× estimate. `rg -c` was 6.99× faster than `grep -c` for the tested literal search on this machine. Both measurements are workload- and platform-specific.

### Code trimming

Removing Python ceremony reduced command tokens by 40%, but the resulting `awk` command was slower. Code brevity is therefore a context optimization, not a runtime guarantee. It should remain the last tier, after answer correctness and output control.

### Spilling results

Writing full matches to a file and returning only a count plus three-row preview reduced returned output by 99.97%. It was 1.64× slower because it added file I/O and a second read. This is a valid trade when later work needs the full artifact but the model does not need every row in context.

## Claim assessment

| Skill claim | Assessment | Evidence |
|---|---|---|
| Returning the answer instead of records is the dominant lever | Verified for this benchmark | Four aggregation/projection tests saved 93.49–99.999% |
| Capping exploratory output is effective | Verified | First-20 preview saved 99.00% |
| Compact JSON saves 50–79% | Not reproduced as stated | Observed 40.64%; structure and whitespace density matter |
| Filter-before-sort can improve runtime by 1.5–2.5× | Supported, not universal | Observed 1.68× |
| `rg` is faster than `grep` | Supported on tested workload only | Observed 6.99× |
| Trimming code saves roughly 25% of code tokens | Supported by one test | Observed 40%, but runtime worsened |
| The skill saves roughly 94% of monthly cost | Not established | Requires a representative task mix and harness-specific billing model |

## Limitations

1. The workloads were synthetic and selected to exercise the skill's recommendations; this was not a randomized sample of real agent sessions.
2. Output token counts used `cl100k_base`. Current Codex and Claude tokenization may differ.
3. Tool output may be truncated, compacted, cached, or billed differently across harnesses.
4. Timing results reflect one Darwin arm64 machine and installed tool versions.
5. The CSV experiment intentionally used a simple format without quoted commas; generic CSV requires a real CSV parser.
6. `grep -c` and `rg -c` count matching lines, not arbitrary match occurrences.
7. A short command can be less robust, less portable, or slower. Correctness remains the hard constraint.

## Recommendation

Retain the skill with this priority order:

1. Preserve the exact task answer.
2. Return only the fields or aggregate the harness needs.
3. Cap previews or spill complete data to an artifact when appropriate.
4. Push selective filters before expensive transforms such as sorting.
5. Shorten command code only when doing so does not compromise clarity, error behavior, portability, or correctness.

Quote the measured ranges and environment rather than presenting a universal cost-saving percentage.

---

# Run 2 — 2026-07-15 (interactive session)

A second, independent run on the same day, four batches (36 experiments total). Same environment class (Darwin arm64, `cl100k_base` token proxy, `jq`/`rg`/`awk`/`md5` present, `gawk`/`fd` absent). Dataset: 200 text files (+30 exact duplicates), a 60,000-line access log, a 100,000-row CSV, 5,000 JSON records, and a small code tree. This run **agrees with Run 1 on every overlapping claim** and adds reproducible correctness-trap evidence plus a per-turn cost note.

## Batch A — code tokens + runtime, 10 complex tasks

Code Claude writes fell 901 → 665 `cl100k` tokens (**26%**); median runtime 266 → 195 ms (**1.4×**). Three results were flagged DIFF and all three were instructive, not capability failures:

- `wc -l` counted 1,960 vs Python's 2,000 — off by one per file because files lacked a trailing newline (**`wc -l` counts newlines, not lines**).
- "Top-5 words" reordered under ties — the task was underspecified, not wrong.
- Status-code counts were identical data (25,716 / 8,571×4) in dict vs columnar form — a presentation diff, not a data diff.

## Batch B — 10 further complex tasks

901-class result reproduced: 914 → 683 tokens (**25%**), 310 → 228 ms (**26%**). One DIFF: `cat *.txt | …` glued the last token of one file to the first of the next (files had no trailing newline), losing counts (2,565 → 2,541 for the word `error`); processing files separately with `awk` restored 2,565. **`cat`-concatenation across newline-less files corrupts boundary tokens** — a second member of the same trailing-newline trap family as `wc -l`.

## Batch C — output tokens returned to context, 6 experiments

Combined 457,625 → 2,246 output tokens (**99.5%**), consistent with Run 1's output-control finding. Highlights: `grep` matches → `grep -c` 137,136 → 3; dump matching rows → `awk` aggregate 299,500 → 22; full listing → `head -10` 16,181 → 515; pretty JSON → TSV rows 2,402 → 500 (**79%**); pretty JSON → compact JSON 2,402 → 1,202 (**50%**). Predicate pushdown (filter before sort; identical tiny output) ran **1.7×** faster.

## Batch D — refinements, 6 experiments

- **Spill-to-file** (`cmd > file; echo count+path; head -2`): 137,136 → 84 output tokens (**~100%**) while preserving the full data on disk. Confirms the Tier-1 "need it all → spill" pattern.
- **Field projection** (return `.id` only, not whole objects): 2,402 → 400 (**83%**).
- **`rg -c` vs `grep -c`**: **2.5×** faster here (Run 1 measured 6.99× — both confirm the direction; the magnitude is workload/platform-specific, not universal).
- **Filter inside `jq`** vs dump-then-`grep`: **1.5×**.
- **Drop useless `cat` / extra pipe stage**: **1.2×**.
- **Early `head` short-circuit**: only **1.1×** on this 2,000-file tree — marginal at small scale; the payoff grows with source size / per-item cost. Report it as conditional, not universal.

## Illustrative cost model (not established as universal)

Per Run 1's claim assessment, a fixed monthly cost-saving percentage is **not established** — it depends on task mix, tokenizer, caching, compaction, and harness billing. As an *illustration only*, for a hypothetical active user (~3,000 throwaway scripts/month; 70% light / 25% medium / 5% heavy output; single-read baseline; `cl100k` proxy prices Sonnet 5 $3/$15, Opus 4.8 $5/$25 per M): command output into context 5,600 → 48 input tokens/task and code 90 → 67 output tokens/task give Sonnet 5 ~$54 → ~$3.45/mo and Opus 4.8 ~$91 → ~$5.75/mo. In an agent loop the tool output is re-billed as input each turn it lingers, so the absolute gap widens (≈$250/mo Opus at ~3 turns). Treat as ±20% and workload-specific; the robust part is that output control (input tokens) dominates and code trimming (output tokens) is a rounding error.

## Net for Run 2

Reproduces Run 1's core: output control is the dominant lever; compact JSON lands ~50% (not the 50–79% the skill text once claimed); `rg`/pushdown help but by platform-specific margins; code trimming ~25–40% and last-priority. New contribution: two reproducible correctness traps (`wc -l` newlines, `cat` boundary-merge) and the per-turn input re-billing dynamic.

---
# /bench run — 2026-07-16

token counter: cl100k
- output-control: grep -> grep -c: 192000 -> 3 (100%), same_answer=True
- output-control: rows -> aggregate: 299500 -> 4 (100%), same_answer=True
- code: python walk -> find|wc: 60 -> 41 (32%), same_answer=True
- predicate pushdown: 1.52x faster

---
# /bench run — 2026-07-20

token counter: cl100k
- output-control: grep -> grep -c: 192000 -> 3 (100%), same_answer=True
- output-control: rows -> aggregate: 299500 -> 4 (100%), same_answer=True
- code: python walk -> find|wc: 58 -> 39 (33%), same_answer=True
- predicate pushdown: 1.68x faster
