---
description: Re-run the token-efficiency benchmark and log any new finding, then promote proven ones into the skill.
---

# /bench — re-benchmark and self-improve

Run the bundled benchmark and record what it finds:

1. Run the portable benchmark:
   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/run-bench.sh"
   ```
   It regenerates a small synthetic dataset, measures the three levers (output control, code trimming, predicate-pushdown timing), verifies each optimized command gives the **same answer**, and appends a dated summary to the persistent findings log at `${CLAUDE_PLUGIN_DATA}/findings-log.md` (this survives plugin updates; the shipped `skills/token-efficient-scripts/references/benchmark-findings.md` is the read-only baseline).

2. Read the new log entry and compare it to the baseline findings. Report the deltas concisely.

3. Apply the skill's **Self-improvement protocol**:
   - Always keep the raw datapoint in the log.
   - Only propose an edit to `SKILL.md` (tiers/guardrails/ranges) when a finding is **replicated across ≥2 runs and material**. New correctness traps are the exception — add them immediately.
   - Never inflate a claim; correct any range the run contradicts and cite the run.
   - Keep `SKILL.md` lean — unproven detail stays in the log.

Note: when installed as a plugin the skill files live in a read-only cache, so runtime findings accumulate in `${CLAUDE_PLUGIN_DATA}`. Folding proven findings back into the shipped `SKILL.md` and re-publishing is a maintainer step (edit the source in the marketplace repo, bump `version`, `/plugin marketplace update`).
