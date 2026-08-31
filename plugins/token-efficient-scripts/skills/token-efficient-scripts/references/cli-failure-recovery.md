# Recovering from a failed CLI invocation — benchmark findings

The main findings file measures how to write a *good* command. This one measures the moment
a command **fails**, and what the recovery costs. The default agent reflex — read the man
page — is the most expensive documentation habit available, and on two of eight scenarios it
cannot produce the answer at any token price.

## Method

Eight real failures on BSD userland (Darwin 25.5, arm64): GNU flags and tools an agent
reaches for by habit, none of which work here. Each was confirmed to actually fail, and each
has a replacement command **verified to produce a correct answer** in the same run.

```
date -d '2 days ago'   stat -c %s      du --max-depth=1    grep -P '\d+'
xargs -d,              sed -i s/a/b/   find -printf '%f'   timeout 1 sleep 2
```

For every scenario, six recovery strategies were measured on three axes:

| axis | why it matters |
|---|---|
| **tokens returned** | what lands in context, permanently, for the rest of the session |
| **answer actually present** | a regex for the correct flag, checked against the returned text |
| **wall clock** | min-of-3 for local commands, single run for the network leg |

The second axis is what makes this benchmark honest: a strategy is only credited when the
text it returned **contains the answer**. Cheap and useless scores as useless.

Run it with `/bench-recovery`, or directly:

```
python3 scripts/bench-recovery.py [log-path]
```

Scenarios are **prechecked**: if a command does not fail on the host it is excluded and
reported not-applicable. On GNU userland all eight succeed and the benchmark reports nothing
to measure — a valid result. `BENCH_NET=0` skips the network leg.

Commands run through `bash -c` with explicit `/usr/bin` paths, to bypass any shell wrapper
functions the harness installs over `find`/`grep`.

## Results — 2026-08-31, Darwin 25.5 arm64, cl100k_base

Tokens returned to the agent. `*` = that text actually contained the answer.

| scenario | error only | `--help` | `man` (full) | `man\|grep` loose | `man\|grep` TIGHT | web (cheat.sh) |
|---|---|---|---|---|---|---|
| `date -d` (relative date) | 89* | 88* | 3555* | 648* | 155* | 536 |
| `stat -c` (file size) | 40 | 39 | 3028* | 485 | 55* | 240 |
| `du --max-depth` | 67* | 64* | 1462* | 125* | 138* | 740 |
| `grep -P` (digits) | 97* | 90* | 3388* | 440* | 209* | 587* |
| `xargs -d` (delimiter) | 66 | 67 | 1978* | 114* | 161* | 880* |
| `sed -i` (in-place) | 15 | 50* | 3950* | 481* | 152* | 1002 |
| `find -printf` (basename) | 10 | 58 | 6385 | 482 | **0** | 2636* |
| `timeout` (missing binary) | 8 | 8 | 2570 | 398 | **0** | 92* |
| **total tokens** | 392 | 464 | **26316** | 3173 | **870** | 6713 |
| **solved** | 3/8 | 4/8 | 6/8 | 5/8 | **6/8** | 4/8 |
| **tokens per answer** | 131 | 116 | **4386** | 635 | **145** | 1678 |
| **wall clock (8 scenarios)** | 0.00s | 0.04s | 0.85s | 0.85s | 0.81s | 1.96s |

A tight `man | grep` returns **the same 6/8 answers as reading the full pages, for 1/30th of
the tokens** (870 vs 26,316).

## Escalation ladders

The error text is already in context when the command fails: it costs 0 extra tokens and 0
extra tool calls to re-read.

| ladder | tokens | solved | tool calls | wall clock | tok/answer |
|---|---|---|---|---|---|
| A. straight to `man` | 26,316 | 6/8 | 8 | 0.85s | 4,386 |
| B. error -> `--help` -> full `man` | 14,183 | 6/8 | 9 | 0.44s | 2,364 |
| C. error -> `--help` -> tight `man\|grep` | **438** | 6/8 | 9 | 0.43s | 73 |
| D. C, then the web for what local docs lack | **3,166** | **8/8** | 11 | 0.90s | 396 |

**D beats A by 8.3x on tokens while solving two more scenarios.** Per single failure that is
~3,290 tokens down to ~400.

## What this saves, and what it does not

- **Context tokens: the win.** 8.3x on the full ladder, 30x on the man-page leg alone.
- **Answer rate: the win.** 6/8 -> 8/8. Two scenarios are unsolvable from local docs at any
  token price, because the fact needed is *"this flag does not exist here"* — an absence no
  man page states.
- **Wall clock: no meaningful change.** Every ladder lands between 0.43s and 0.90s.
  Do not claim a speed saving from this benchmark; it does not measure one.
- **Tool round trips: a real cost.** Per failure the naive path is 1 call; the ladder is 0-3.
  It is partly self-funding — 3/8 scenarios are solved from the error text with **zero**
  calls — but the ladder can add up to 2 round trips to buy its token saving.

## Division of labour

- **Local docs answer:** *"the flag exists here, I used the GNU spelling."* `date -v`,
  `stat -f %z`, `du -d`, `grep -E`, `xargs -0`, `sed -i ''`.
- **The web answers:** *"this flag or tool does not exist here at all."* `find -printf`
  (no BSD equivalent), `timeout` (ships as `gtimeout` via coreutils).
- **The tight probe tells you which case you are in, for free.** On both web-only scenarios
  it returned **0 tokens** — an instant escalate signal instead of 8,955 wasted tokens.

Search-**first** is not the answer either: 6,713 tokens for 4/8, worse per answer than a
targeted grep. Community cheatsheets are GNU-centric — cheat.sh's `sed` page recommends
`sed -i 's/…'`, precisely the form that fails on BSD. One real `WebSearch` tool result
measured **799 tokens** and did contain the answer, so ~800 tokens is a fair planning figure
for the web leg.

## Traps this run exposed

1. **A man page can be the wrong document entirely.** `man timeout` returns ncurses
   `curs_inopts(3X)` — 2,570 tokens about `cbreak`/`noecho`, because coreutils' man page is
   installed while the binary is not. Expensive *and* misleading.
2. **`man X | grep … | head -N` truncates past the answer.** `%z` is defined at line 178 of
   `man stat`; a loose `size|format` probe spent its 40-line window on early "format"
   matches and never reached it. A tight probe with `-m3` found it in 55 tokens.
3. **Grep the man page with `-B` context, not `-A` alone.** Flag names sit *above* their
   prose. An `-A`-only window on `man date` returned the sentence "preceded by a plus or
   minus sign, the date is adjusted forward or backward" without ever naming `-v`.
4. **A usage line is often the whole answer.** BSD tools reject a bad flag with their synopsis
   attached, so 3/8 scenarios were already solved before any tool call.

## Limitations

- **Platform-specific by construction.** These are BSD-userland failures. On GNU userland the
  same commands succeed and the benchmark reports not-applicable.
- **Single host, and the two runs here were the same host.** Token counts reproduced exactly
  across two independent implementations; wall clock and the network leg will vary.
- **The `error only` column drifts ±1 token between runs** (the `sed` scenario's error text
  contains a transient temp filename). Totals of 392–393 for that column are the same result.
- **`cl100k_base`**, for continuity with the other findings file — not the private tokenizer
  or billing behaviour of any current harness. Treat token counts as directional.
- **"Answer present" is a regex check**, so it credits a strategy for containing the right
  flag, not for being easy to read.
- **The probe is chosen by a human who knows the answer.** Probes were written to be
  answer-agnostic (semantic words like `depth`, `size of file`, `in-place`), but an agent
  guessing a worse probe gets the loose-probe column, not the tight one — which is why both
  are reported.

---
# /bench-recovery run — 2026-08-31

token counter: cl100k
applicable scenarios: 8/8
- error only: 393 tok, solved 3/8, 131 tok/answer, 0.00s
- --help: 464 tok, solved 4/8, 116 tok/answer, 0.04s
- man (full): 26316 tok, solved 6/8, 4386 tok/answer, 0.89s
- man|grep loose: 3173 tok, solved 5/8, 635 tok/answer, 0.85s
- man|grep TIGHT: 870 tok, solved 6/8, 145 tok/answer, 0.87s
- web (cheat.sh): 6713 tok, solved 4/8, 1678 tok/answer, 1.95s
- ladder A naive full man: 26316 tok, 6/8 solved, 8 calls, 0.89s
- ladder B error/help/full man: 14183 tok, 6/8 solved, 9 calls, 0.45s
- ladder C error/help/tight grep: 438 tok, 6/8 solved, 9 calls, 0.47s
- ladder D C+web: 3166 tok, 8/8 solved, 11 calls, 0.95s
- all fixes verified correct: True

---
# /bench-recovery run — 2026-08-31

token counter: cl100k
applicable scenarios: 8/8
- error only: 393 tok, solved 3/8, 131 tok/answer, 0.00s
- --help: 464 tok, solved 4/8, 116 tok/answer, 0.03s
- man (full): 26316 tok, solved 6/8, 4386 tok/answer, 0.83s
- man|grep loose: 3173 tok, solved 5/8, 635 tok/answer, 0.81s
- man|grep TIGHT: 870 tok, solved 6/8, 145 tok/answer, 0.82s
- ladder A naive full man: 26316 tok, 6/8 solved, 8 calls, 0.83s
- ladder B error/help/full man: 14183 tok, 6/8 solved, 9 calls, 0.43s
- ladder C error/help/tight grep: 438 tok, 6/8 solved, 9 calls, 0.42s
- all fixes verified correct: True
