#!/usr/bin/env python3
# Verifies the SKILL.md platform table ("When a GNU invocation fails on BSD/macOS").
# Two assertions per row, so neither the advice nor the test can drift silently:
#   1. the row's key form is still present in SKILL.md
#   2. that form actually WORKS on this host
# Hermetic (own tmp tree, never /etc). Stdlib only. Exits non-zero on any failure.
import os, re, sys, shutil, tempfile, datetime as dt, subprocess as s

SKILL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "..", "skills", "token-efficient-scripts", "SKILL.md")
try:
    TABLE = re.search(r"### When a GNU invocation fails on BSD/macOS(.*?)\nPrior art",
                      open(SKILL).read(), re.S).group(1)
except Exception:
    print("FAIL: could not locate the platform table in SKILL.md"); sys.exit(1)

D = tempfile.mkdtemp()
for sub in ("sub/deep","fnd","sd"): os.makedirs(f"{D}/{sub}")
open(f"{D}/f.txt", "w").write("aaa 111\nbbb 222\nccc\n")          # 24 bytes
open(f"{D}/sub/x","w").write("x")
open(f"{D}/fnd/a.txt","w").write("a"); os.makedirs(f"{D}/fnd/b")
def sh(c): 
    r = s.run(["bash", "-c", c], capture_output=True, text=True, timeout=30)
    return ((r.stdout or "") + (r.stderr or "")).strip(), r.returncode

SIZE = os.path.getsize(f"{D}/f.txt")
TWO_AGO = (dt.date.today() - dt.timedelta(days=2)).isoformat()

# label, marker that must appear in the table, command, predicate(out, rc)
ROWS = [
 ("date -v",        "`date -v-2d`",                 "date -v-2d +%F",
  lambda o, r: o == TWO_AGO),
 ("stat -f %z",     "`stat -f %z f`",               f"stat -f %z {D}/f.txt",
  lambda o, r: o == str(SIZE)),
 ("du -d N",        "`du -d N`",                    f"du -d 1 {D} | grep -c deep",
  lambda o, r: o == "0"),                            # -d 1 must NOT reach depth 2
 ("grep -E",        "`grep -E '[0-9]+'`",           f"/usr/bin/grep -cE '[0-9]+' {D}/f.txt",
  lambda o, r: o == "2"),
 ("tr | xargs -0",  "xargs -0",                     "printf 'a,b,c' | tr ',' '\\0' | xargs -0 -n1 echo | tr '\\n' ' '",
  lambda o, r: o == "a b c"),
 ("sed -i ''",      "`sed -i '' s/a/b/ f`",         f"cp {D}/f.txt {D}/sd/s.txt && sed -i '' s/aaa/ZZZ/ {D}/sd/s.txt && head -1 {D}/sd/s.txt && ls {D}/sd/ | wc -l | tr -d ' '",
  lambda o, r: o.startswith("ZZZ 111") and o.rstrip().endswith("1")),   # changed, and no backup file left
 ("find basename",  "-mindepth 1 -exec basename",   f"/usr/bin/find {D}/fnd/ -maxdepth 1 -mindepth 1 -exec basename {{}} ';' | sort | tr '\\n' ' '",
  lambda o, r: o == "a.txt b"),                      # basenames only, start dir excluded
 ("perl alarm",     "perl -e 'alarm",               "perl -e 'alarm 1; exec @ARGV' sleep 5 >/dev/null 2>&1; echo rc=$?",
  lambda o, r: "rc=142" in o),      # bash may append an async "Alarm clock" notice
]

fails, skips = [], []
for label, marker, cmd, pred in ROWS:
    if marker not in TABLE:
        fails.append((label, f"marker {marker!r} MISSING from SKILL.md table")); print(f"  FAIL {label:<16} table drifted: {marker!r} not found"); continue
    out, rc = sh(cmd)
    if pred(out, rc): print(f"  ok   {label:<16} -> {out[:52]}")
    else: fails.append((label, f"got {out[:70]!r}")); print(f"  FAIL {label:<16} -> {out[:70]!r}")

# gtimeout is offered by the table but needs `brew install coreutils`; absence is a SKIP.
if "gtimeout" in TABLE:
    if shutil.which("gtimeout"):
        out, _ = sh("gtimeout 1 sleep 5; echo rc=$?")
        (print(f"  ok   {'gtimeout':<16} -> {out[-8:]}") if out.endswith("rc=124")
         else (fails.append(("gtimeout", out[:60])), print(f"  FAIL gtimeout -> {out[:60]!r}")))
    else:
        skips.append("gtimeout"); print(f"  SKIP {'gtimeout':<16} not installed (brew install coreutils) — table marks it untested")

shutil.rmtree(D, ignore_errors=True)
n = len(ROWS) + (1 if "gtimeout" in TABLE else 0)
print(f"\n{n - len(fails) - len(skips)}/{n} verified, {len(skips)} skipped, {len(fails)} failed")
for a, b in fails: print(f"  FAILED: {a} — {b}")
if fails:
    print("\nA failure here means the SHIPPED ADVICE in SKILL.md is wrong on this OS. Fix the table.")
sys.exit(1 if fails else 0)
