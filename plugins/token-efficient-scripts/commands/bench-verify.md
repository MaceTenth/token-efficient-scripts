---
description: Re-run the verification-output benchmark (tests, builds, git, archives) and log loud vs quiet tokens, whether the answer survived, and wall clock.
---

# /bench-verify — measure the cost of commands run only to check something

Run the bundled benchmark and record what it finds:

1. Run it:
   ```
   bash "${CLAUDE_PLUGIN_ROOT}/scripts/run-bench-verify.sh"
   ```
   It generates hermetic fixtures in a temp dir (a pytest suite, a C++ template error, a cargo
   crate with type errors, a git repo, a zip and a tar of 400 files), then for each scenario
   measures the habitual loud form against the recommended quiet form on three axes:
   **tokens returned**, **whether that text still contains the answer**, and **wall clock**
   (median of 5). A dated summary is appended to `${CLAUDE_PLUGIN_DATA}/verify-log.md`.

2. **Check applicability first.** A scenario whose tool (`pytest`, `clang++`, `cargo`, `git`,
   `zip`/`unzip`, `tar`) is not installed is reported not-applicable. That is a valid result,
   not a broken run. Report which scenarios applied.

3. Read the new log entry and compare it to the shipped baseline in
   `skills/token-efficient-scripts/references/verification-output.md`. Report the
   habit -> recommended tokens per scenario and the total.

4. Apply the skill's **Self-improvement protocol**:
   - Always keep the raw datapoint in the log.
   - **`all recommended forms kept the answer: False` is the most important result** — a quiet
     form in `SKILL.md` no longer answers the question on this host. Flag it; do not loosen the
     check to make it pass. The script also exits 1.
   - The `| head -20` / `| tail -20` rows on the compiler scenario are **expected** to lose the
     answer: they demonstrate the trap. If one keeps it, report "trap did not reproduce".
   - Only propose an edit to `SKILL.md` when a finding is **replicated across ≥2 runs and
     material**.
   - Never inflate a claim. This benchmark measures **tokens and answer retention**, not speed:
     the loud and quiet forms do the same work, and wall clock lands within noise. Do not report
     a time saving.
