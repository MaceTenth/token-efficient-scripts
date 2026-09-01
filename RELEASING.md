# Releasing a version

Written from what actually broke. Every "why it matters" below is a mistake that shipped at
least once — including the slide going stale for two releases, which is why this file exists.

The hazard in this repo is **one measurement living in six places**. `26,316` appears in the
root README, `CHANGELOG.md`, `SKILL.md`, `references/cli-failure-recovery.md`, and `slide.html`.
Change a number in one and the others silently become lies.

Run `python3 plugins/token-efficient-scripts/scripts/check-release.py` before every push — it
mechanises most of what follows.

---

## 1. Before you change anything: prove the current state

```bash
python3 plugins/token-efficient-scripts/scripts/test-cheatsheet.py      # advice still correct?
python3 plugins/token-efficient-scripts/scripts/test-pre-bash-man.py    # hook still correct?
python3 plugins/token-efficient-scripts/scripts/bench.py                # levers
python3 plugins/token-efficient-scripts/scripts/bench-recovery.py       # recovery
```

A `test-cheatsheet.py` failure means the **shipped advice in SKILL.md is wrong on this OS** — an
OS update changed `stat -f %z` or `date -v`. Fix that before anything else; it is worse than any
benchmark drift.

**Before concluding the advice is wrong, check whether the *test* is wrong.** Both of that
suite's first two failures were test bugs (scratch-file pollution between rows, an async shell
notice appended after the checked output). Never reconcile a failure by editing the platform
table *or* by loosening a predicate without understanding which side is at fault.

## 2. The files that must change

### Plugin
| File | What | Why it matters |
|---|---|---|
| `.claude-plugin/plugin.json` | `version`, `description`, `keywords` | `version` is what triggers an update for installed users. **Don't bump for docs/tests-only changes** — it forces a pointless re-download. |
| `skills/…/SKILL.md` | the guidance itself | |
| `skills/…/SKILL.md` **frontmatter `description`** | trigger phrasing | ⚠️ Easiest miss with the worst blast radius. If the description doesn't match the situation, **the skill never loads and the release does nothing.** v0.5.0 needed "a command has just FAILED" added or the ladder would never have fired. |
| `skills/…/references/*.md` | findings | Append-only logs. Never rewrite a past datapoint. |
| `commands/*.md` | new slash commands | |
| `hooks/hooks.json` | new hooks | A hook changes behaviour for everyone who installs. Document how to disable it. |
| `scripts/*` | code **and its tests** | |

### Repo root
| File | What | Why it matters |
|---|---|---|
| `.claude-plugin/marketplace.json` | plugin `description` | What people see in `/plugin`. Separate from `plugin.json` — both drift. |
| `README.md` | headline numbers, new section | |
| `CHANGELOG.md` | new entry, newest first | Include an **"Explicitly not claimed"** block. |
| `slide.html` | the public explainer | ⚠️ **Served live at [macetenth.github.io/…/slide.html](https://macetenth.github.io/token-efficient-scripts/slide.html)** and linked from the README. It is not near the code, so it is the thing you forget — it sat two releases stale. GitHub Pages publishes it on push; there is no build step and no failure signal. |

### Outside the repo
| Thing | When |
|---|---|
| `~/.claude/scheduled-tasks/token-efficient-scripts-weekly-bench/SKILL.md` | Whenever you add a benchmark or test suite. The weekly task hardcodes its commands — **a new script is not picked up automatically.** Pin the expected output so a regression is obvious, and exclude anything that costs money (`--e2e`). |

## 3. Consistency rules

- **A number must be identical everywhere it appears.** Grep for it before pushing.
- **State which comparison a percentage describes.** 98%, 97% and 88% are all true of the same
  benchmark; they are different pairings. A bare percentage invites an accusation of cherry-picking.
- **Never round up.** 88.0% is not "90%". The repo's own protocol says never inflate a claim, and
  a like-for-like pairing usually gives a *bigger* honest number than a rounded dishonest one.
- **Say what a change does *not* buy.** The recovery ladder saves tokens and answer rate, not wall
  clock, and it costs tool round trips. Both non-claims are documented so a reader can't infer them.
- **Promotion into `SKILL.md` needs ≥2 replications** and is a human step. Bench-bot never edits it.

## 4. Publish

```bash
python3 plugins/token-efficient-scripts/scripts/check-release.py    # must exit 0
python3 plugins/token-efficient-scripts/scripts/test-pre-bash-man.py --e2e   # COSTS MONEY (~$0.15)
git add -A && git commit -m "vX.Y.Z: <what changed>" && git push origin main
```

Run `--e2e` **once per release**, not per commit. The 29 unit cases test the hook's decision
logic; only `--e2e` proves the harness still honours the `permissionDecision` contract. If
Claude Code ever changes that schema, the unit tests keep passing while the hook silently stops
working in production.

## 5. After pushing

- `/plugin marketplace update macetenth-plugins` then `/reload-plugins`, and confirm the new
  version actually installs.
- Load the live slide URL and confirm your changes are there — Pages caches.
- Traffic, if you care: `gh api repos/MaceTenth/token-efficient-scripts/traffic/clones`
  (GitHub keeps **14 days only**; clones ≈ plugin installs, views ≈ humans, and for this repo
  clones outnumber views ~7:1).
