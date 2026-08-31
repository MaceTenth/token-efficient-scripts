---
description: Re-run the failed-command recovery benchmark and log what it finds about man pages vs --help vs targeted grep vs web search.
---

# /bench-recovery — measure the cost of recovering from a failed command

Run the bundled recovery benchmark and record what it finds:

1. Run it:
   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/run-bench-recovery.sh"
   ```
   It replays real GNU-flag-on-BSD failures, then for each one measures every recovery
   strategy (the error text alone, `--help`, the full `man` page, a loose `man | grep`,
   a tight `man | grep`, and the web) on three axes: **tokens returned**, **whether that
   text actually contains the answer**, and **wall clock**. Every replacement command is
   verified to produce a correct result. A dated summary is appended to
   `${CLAUDE_PLUGIN_DATA}/recovery-log.md`.

   Set `BENCH_NET=0` to skip the network leg on an offline or sandboxed host.

2. **Check applicability first.** Each scenario is prechecked: if the command does not
   actually fail on this host, it is excluded and reported as not-applicable. On GNU
   userland all eight succeed and the benchmark correctly reports nothing to measure —
   that is a valid result, not a broken run. Report which scenarios applied.

3. Read the new log entry and compare it to the shipped baseline in
   `skills/token-efficient-scripts/references/cli-failure-recovery.md`. Report the deltas
   concisely: tokens per answer per strategy, and the ladder totals.

4. Apply the skill's **Self-improvement protocol**:
   - Always keep the raw datapoint in the log.
   - Only propose an edit to `SKILL.md` when a finding is **replicated across ≥2 runs and
     material**. New correctness traps are the exception — add them immediately.
   - A strategy that returns **0 tokens and no answer** is a *success* of the ladder, not a
     failure: it is the signal to escalate to the web. Do not "fix" it by widening the probe.
   - Never inflate a claim. In particular: this benchmark measures **tokens and answer
     rate**, not speed. Wall clock across all ladders lands within a second of itself —
     do not report a time saving.
