# Commands run only to check something — benchmark findings

The main findings file measures commands that ask a question of data; `cli-failure-recovery.md`
measures recovering from a command that failed. This one measures the commands an agent runs
**only to learn a verdict** — a test suite, a build, git history, an archive extraction. These
tools print a running log by default, while the agent needs one of: *did it pass*, *what broke*,
or *which files*. Most of them already have a quiet form that returns just that.

## Method

Ten scenarios. Every fixture is generated in a temp dir, so the run is hermetic and repeatable:

| scenario | fixture | answer the agent needs |
|---|---|---|
| pytest, all pass | 30 files × 10 tests | "300 passed" (or `ok`) |
| pytest, 1 fails | same + 1 failing test | the failing test id **and** `assert 6 == 7` |
| pytest, 1 fails + warnings | same, 30 tests raise a `DeprecationWarning` | the failing test id and assertion |
| clang++ template error | `std::sort` on a struct without `<`, `map::insert(42)` | **both** root-cause messages |
| cargo build | 3 type errors in `main.rs` | all three error locations |
| git log | 30-commit synthetic repo, fixed dates | the last 20 commit subjects |
| git show | same repo | the files one commit touched |
| git diff | same repo | the files 10 commits touched |
| unzip / tar | 400 files in 20 dirs | exit 0 and all 400 files on disk |

Each scenario compares the **habit** (the loud form an agent reaches for) with the
**recommended** quiet form, on three axes:

| axis | how |
|---|---|
| **tokens returned** | stdout + stderr, `cl100k_base` |
| **answer still present** | a per-scenario check against the known answer (table above) |
| **wall clock** | median of 5 runs |

The habit for pytest is plain `pytest`, not `pytest -v` — the conservative baseline. `-v` is
measured and shown, but no headline number uses it.

Run it with `/bench-verify`, or directly:

```
python3 scripts/bench-verify.py [log-path]
```

A scenario whose tool is not installed is reported not-applicable, never faked. The script exits
1 if a recommended form lost the answer or a loud baseline never contained it.

## Results — 2026-10-19, Darwin 25.5 arm64, cl100k_base

Apple clang 21.0.0, cargo 1.94.1, git 2.50.1, pytest 9.1.1. First of two runs.

| scenario | habit | tokens | recommended | tokens | saved |
|---|---|---:|---|---:|---:|
| pytest, all pass | `pytest` | 469 | `pytest -q >log 2>&1 && echo ok \|\| tail -5 log` | 2 | 99.5% |
| pytest, 1 fails | `pytest` | 571 | same wrapper | 49 | 91.4% |
| pytest, 1 fails + 30 warnings | `pytest` | 2,941 | same wrapper | 63 | 97.8% |
| clang++ template error | `clang++ -fsyntax-only` | 10,860 | `2>&1 \| grep -m5 'error:'` | 219 | 97.9% |
| cargo build, 3 errors | `cargo build` | 339 | `cargo build -q --message-format=short` | 102 | 69.9% |
| git log, 20 commits | `git log -20` | 1,383 | `git log --oneline -20` | 383 | 72.3% |
| git: files in one commit | `git show <rev>` | 850 | `git show --name-only --format= <rev>` | 15 | 98.2% |
| git: files in 10 commits | `git diff A B` | 6,143 | `git diff --name-only A B` | 60 | 99.0% |
| unzip 400 files | `unzip x.zip` | 4,172 | `unzip -q x.zip` | 0 | 100.0% |
| tar 400 files | `tar -xvf x.tar` | 3,303 | `tar -xf x.tar` | 0 | 100.0% |
| **total** | | **31,031** | | **893** | **97.1%** |

Every recommended form kept the answer, in both runs. The second run measured 30,963 → 893
(97.1%). Percentages are floored, never rounded up.

Other variants measured in the same run:

| variant | tokens | note |
|---|---:|---|
| `pytest -v`, all pass | 5,254 | 11× plain `pytest` — the expensive habit |
| `pytest -q`, all pass | 44 | most of the saving with no wrapper |
| `pytest -q`, 1 fails + 30 warnings | 2,518 | `-q` does not touch the warnings summary |
| `pytest -q --disable-warnings`, same | 152 | warnings were 93.9% of the `-q` output |
| `git show --stat` / `git diff --stat` | 47 / 177 | adds line counts per file for a few more tokens |

## What this saves, and what it does not

- **Context tokens: the win.** 31,031 → 893 across the ten scenarios.
- **Wall clock: no change.** 1.30s → 1.26s in total; per scenario the differences are within
  run-to-run noise. The tools do the same work either way, and writing to a pipe is cheap. Do not
  claim a speed saving from this benchmark.
- **Information: a narrower answer, on purpose.** `--name-only` says *which* files changed, not
  *what* changed. `--oneline` drops author, date and body. `--disable-warnings` hides warnings,
  which is right only when warnings are not the question. Use the quiet form when it answers the
  question asked, not as a blanket rule.
- **Not measured:** how much sooner the model replies when it reads less, and how often a model
  actually chooses the quiet form (adherence).

## Traps this run exposed

1. **A fixed `head`/`tail` cut loses compiler errors.** The template error printed 400 lines.
   `| head -20` (605 tokens) kept only the `insert` error; `| tail -20` (560 tokens) kept
   **neither** root cause — just a cascade error and "too many errors emitted". The `std::sort`
   root cause sits on line 31, then cascades into 17 more errors from inside the standard
   library before clang hits its error limit. `grep -m5 'error:'` kept both in 219 tokens. Test runners print their summary
   **last**; compilers print the root cause **first** and bury the next one in notes.
2. **Warnings, not verbosity, can dominate a test run.** 30 warnings across 301 tests made up
   93.9% of `pytest -q` output. `-q` alone barely helped (2,941 → 2,518).
3. **A 0-token answer is the exit status.** `unzip -q` and `tar -xf` print nothing on success.
   The harness reports the exit code; if one does not, append `; echo rc=$?` (about 4 tokens).

## Limitations

- **Single host; both runs on the same host.** Token counts reproduced (recommended total 893
  both times); wall clock will vary.
- **Habit totals drift by tens of tokens between runs** (31,031 vs 30,963): pytest and cargo
  print temp-dir paths and timings. The same result.
- **Synthetic fixtures of moderate size.** Real suites and repos are often larger, and loud
  output grows with them, so these totals are not an upper bound.
- **The compiler check is clang- and libc++-specific.** GCC/libstdc++ word the errors
  differently; the scenario is skipped without `clang++`.
- **`cl100k_base`**, for continuity with the other findings files — not the tokenizer or billing
  of any current harness. Treat token counts as directional.

---
# /bench-verify run — 2026-10-19

token counter: cl100k
applicable scenarios: 10/10
- pytest, 300 tests pass: 469 -> 2 tok (99.5%), answer kept: True, 0.275s -> 0.251s
- pytest, 1 of 301 fails: 571 -> 49 tok (91.4%), answer kept: True, 0.261s -> 0.258s
- pytest, 1 fails + 30 warnings: 2941 -> 63 tok (97.8%), answer kept: True, 0.262s -> 0.262s
- clang++ template error (2 errors): 10860 -> 219 tok (97.9%), answer kept: True, 0.188s -> 0.184s
- cargo build (3 type errors): 339 -> 102 tok (69.9%), answer kept: True, 0.043s -> 0.042s
- git log, last 20 commits: 1383 -> 383 tok (72.3%), answer kept: True, 0.009s -> 0.009s
- git: files in one commit: 850 -> 15 tok (98.2%), answer kept: True, 0.010s -> 0.011s
- git: files changed in 10 commits: 6143 -> 60 tok (99.0%), answer kept: True, 0.012s -> 0.010s
- unzip 400 files: 4172 -> 0 tok (100.0%), answer kept: True, 0.083s -> 0.076s
- tar -x 400 files: 3303 -> 0 tok (100.0%), answer kept: True, 0.153s -> 0.161s
- total habit -> recommended: 31031 -> 893 tok (97.1%), 1.30s -> 1.26s
- generic cuts that lost the answer (expected): clang++ template error (2 errors) ... | head -20; clang++ template error (2 errors) ... | tail -20
- all recommended forms kept the answer: True

---
# /bench-verify run — 2026-10-19

token counter: cl100k
applicable scenarios: 10/10
- pytest, 300 tests pass: 467 -> 2 tok (99.5%), answer kept: True, 0.274s -> 0.260s
- pytest, 1 of 301 fails: 569 -> 49 tok (91.3%), answer kept: True, 0.278s -> 0.273s
- pytest, 1 fails + 30 warnings: 2879 -> 63 tok (97.8%), answer kept: True, 0.276s -> 0.262s
- clang++ template error (2 errors): 10860 -> 219 tok (97.9%), answer kept: True, 0.196s -> 0.195s
- cargo build (3 type errors): 337 -> 102 tok (69.7%), answer kept: True, 0.042s -> 0.043s
- git log, last 20 commits: 1383 -> 383 tok (72.3%), answer kept: True, 0.009s -> 0.009s
- git: files in one commit: 850 -> 15 tok (98.2%), answer kept: True, 0.010s -> 0.008s
- git: files changed in 10 commits: 6143 -> 60 tok (99.0%), answer kept: True, 0.010s -> 0.010s
- unzip 400 files: 4172 -> 0 tok (100.0%), answer kept: True, 0.080s -> 0.077s
- tar -x 400 files: 3303 -> 0 tok (100.0%), answer kept: True, 0.149s -> 0.146s
- total habit -> recommended: 30963 -> 893 tok (97.1%), 1.33s -> 1.28s
- generic cuts that lost the answer (expected): clang++ template error (2 errors) ... | head -20; clang++ template error (2 errors) ... | tail -20
- all recommended forms kept the answer: True
