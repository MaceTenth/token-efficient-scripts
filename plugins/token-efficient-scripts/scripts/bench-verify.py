#!/usr/bin/env python3
# Portable benchmark: what does it cost an agent to run a command only to CHECK something —
# a test suite, a build, git history, an archive extraction — when just the verdict matters?
# Each scenario compares the habitual (loud) form with the quiet form on tokens returned,
# whether the returned text still contains the answer, and wall clock (median of 5).
# tiktoken if present, else chars/4 proxy. Appends a dated summary to arg1 if given.
#
# Hermetic: every fixture (test suite, C++ file, cargo crate, git repo, archives) is generated
# in a temp dir. A scenario whose tool is not installed is reported not-applicable, never faked.
# Exits 1 if a recommended quiet form lost the answer, or a loud baseline never had it.
import os, sys, math, shutil, shlex, tempfile, time, statistics, subprocess as s
try:
    import tiktoken; _e = tiktoken.get_encoding("cl100k_base"); tok = lambda x: len(_e.encode(x)); TK = "cl100k"
except Exception:
    tok = lambda x: round(len(x) / 4); TK = "chars/4 proxy"

W = tempfile.mkdtemp(prefix="bench-verify-")
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
           GIT_AUTHOR_NAME="bench", GIT_AUTHOR_EMAIL="bench@example.com",
           GIT_COMMITTER_NAME="bench", GIT_COMMITTER_EMAIL="bench@example.com",
           CARGO_TERM_COLOR="never", CARGO_TARGET_DIR=os.path.join(W, "target"), NO_COLOR="1")

def sh(c, cwd=W, t=180):
    try:
        r = s.run(["bash", "-c", c], cwd=cwd, env=ENV, capture_output=True, text=True, timeout=t)
        return (r.stdout or "") + (r.stderr or ""), r.returncode
    except Exception as e:
        return f"<{e}>", 99

def timed(c, cwd, n=5):
    """median-of-n wall clock; returns (output, rc, seconds)."""
    ts = []
    for _ in range(n):
        st = time.perf_counter(); o, rc = sh(c, cwd); ts.append(time.perf_counter() - st)
    return o, rc, statistics.median(ts)

def put(rel, txt):
    p = os.path.join(W, rel); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(txt)

# this interpreter's pytest if it has one, else whatever `pytest` is on PATH
PYT = (shlex.quote(sys.executable) + " -m pytest"
       if s.run([sys.executable, "-c", "import pytest"], capture_output=True).returncode == 0
       else "pytest" if shutil.which("pytest") else None)

def have(t):
    return PYT is not None if t == "pytest" else shutil.which(t) is not None

def nfiles(d):
    return sum(len(f) for _, _, f in os.walk(os.path.join(W, d)))

PY = f"{PYT} -p no:cacheprovider"

def pytest_sc(d, fail=False, warn=False):
    def setup():
        for i in range(30):
            t = "import warnings\n" + "".join(
                f"def test_{j}():\n" + ("    warnings.warn('old api', DeprecationWarning)\n" if warn and j == 0 else "")
                + f"    assert {j} + 1 == {j + 1}\n" for j in range(10))
            if fail and i == 17: t += "def test_bad():\n    assert sum([1, 2, 3]) == 7\n"
            put(f"{d}/test_m{i}.py", t)
        v = [("pytest", f"{PY} {d}", "habit"), ("pytest -v", f"{PY} -v {d}", "info"),
             ("pytest -q", f"{PY} -q {d}", "info")]
        if warn: v.append(("pytest -q --disable-warnings", f"{PY} -q --disable-warnings {d}", "info"))
        v.append(("pytest -q >log 2>&1 && echo ok || tail -5 log",
                  f"{PY} -q {d} >{d}.log 2>&1 && echo ok || tail -5 {d}.log", "rec"))
        ok = ((lambda o, rc: f"{d}/test_m17.py::test_bad" in o and "assert 6 == 7" in o) if fail else
              (lambda o, rc: rc == 0 and "failed" not in o and ("300 passed" in o or o.strip() == "ok")))
        return W, v, ok
    return setup

def clang_setup():
    put("cpp/bad.cpp", "#include <algorithm>\n#include <map>\n#include <string>\n#include <vector>\n"
        "struct P { int a; };\nint main() {\n  std::vector<P> v;\n  std::sort(v.begin(), v.end());\n"
        "  std::map<std::string, int> m;\n  m.insert(42);\n}\n")
    c = "clang++ -fsyntax-only bad.cpp 2>&1"
    # the answer is the two ROOT causes; the sort() one cascades into ~20 template errors
    ref = ["no matching member function for call to 'insert'", "invalid operands to binary expression"]
    return os.path.join(W, "cpp"), [("clang++ -fsyntax-only bad.cpp", c, "habit"),
        ("... | head -20", c + " | head -20", "trap"), ("... | tail -20", c + " | tail -20", "trap"),
        ("... | grep -m5 'error:'", c + " | grep -m5 'error:'", "rec")], \
        lambda o, rc: all(l in o for l in ref)

def cargo_setup():
    sh("cargo new -q --offline --vcs none app")
    put("app/src/main.rs", "fn add(a: i32, b: i32) -> i32 { a + b }\nfn main() {\n"
        "    let s: String = add(1, 2);\n    let n: i32 = \"x\";\n    let v: Vec<u8> = add(3, 4);\n"
        "    println!(\"{}{}{:?}\", s, n, v);\n}\n")
    return os.path.join(W, "app"), [("cargo build", "cargo build --offline", "habit"),
        ("cargo build -q --message-format=short", "cargo build --offline -q --message-format=short", "rec")], \
        lambda o, rc: all(f"main.rs:{n}:" in o for n in (3, 4, 5))

def repo():
    R = os.path.join(W, "repo")
    if not os.path.isdir(R):
        sh("git init -q repo")
        for c in range(30):
            fs = [f"src/m{(c * 3 + k) % 12}.py" for k in range(3)]
            for k, f in enumerate(fs):
                p = os.path.join(R, f); os.makedirs(os.path.dirname(p), exist_ok=True)
                open(p, "a").write("".join(f"def f{c}_{k}_{i}(x):\n    return x * {i} + {c}\n" for i in range(8)))
            dt = f"2026-01-{c + 1:02d}T12:00:00"
            sh(f"git add -A && GIT_AUTHOR_DATE={dt} GIT_COMMITTER_DATE={dt} "
               f"git commit -q -m 'change {c}: update {' '.join(os.path.basename(f) for f in fs)}'", R)
    return R

def git_sc(kind):
    def setup():
        R = repo()
        if kind == "log":
            ref = sh("git log --format=%s -20", R)[0].splitlines()
            v = [("git log -20", "git log -20", "habit"), ("git log --oneline -20", "git log --oneline -20", "rec")]
        elif kind == "show":
            ref = sh("git show --name-only --format= HEAD~3", R)[0].split()
            v = [("git show HEAD~3", "git show HEAD~3", "habit"),
                 ("git show --stat --format= HEAD~3", "git show --stat --format= HEAD~3", "info"),
                 ("git show --name-only --format= HEAD~3", "git show --name-only --format= HEAD~3", "rec")]
        else:
            ref = sh("git diff --name-only HEAD~10 HEAD", R)[0].split()
            v = [("git diff HEAD~10 HEAD", "git diff HEAD~10 HEAD", "habit"),
                 ("git diff --stat HEAD~10 HEAD", "git diff --stat HEAD~10 HEAD", "info"),
                 ("git diff --name-only HEAD~10 HEAD", "git diff --name-only HEAD~10 HEAD", "rec")]
        return R, v, lambda o, rc: bool(ref) and all(x in o for x in ref)
    return setup

def tree(d):
    for a in range(20):
        for b in range(20): put(f"{d}/tree/d{a}/f{b}.txt", f"{a} {b}\n")

def unzip_setup():
    tree("z"); D = os.path.join(W, "z"); sh("zip -qr x.zip tree", D)
    return D, [("unzip x.zip", "rm -rf out && unzip x.zip -d out", "habit"),
               ("unzip -q x.zip", "rm -rf out && unzip -q x.zip -d out", "rec")], \
        lambda o, rc: rc == 0 and nfiles("z/out") == 400

def tar_setup():
    tree("t"); D = os.path.join(W, "t"); sh("tar -cf x.tar tree", D)
    return D, [("tar -xvf x.tar", "rm -rf out && mkdir out && tar -xvf x.tar -C out", "habit"),
               ("tar -xf x.tar", "rm -rf out && mkdir out && tar -xf x.tar -C out", "rec")], \
        lambda o, rc: rc == 0 and nfiles("t/out") == 400

# name, tools it needs, setup -> (cwd, [(label, cmd, role)], answer_present(out, rc))
# role: habit = the loud baseline, rec = the recommended quiet form, info = shown for context,
#       trap = a generic cut (head/tail) that is EXPECTED to lose the answer
SC = [
 ("pytest, 300 tests pass", ["pytest"], pytest_sc("tp")),
 ("pytest, 1 of 301 fails", ["pytest"], pytest_sc("tf", fail=True)),
 ("pytest, 1 fails + 30 warnings", ["pytest"], pytest_sc("tw", fail=True, warn=True)),
 ("clang++ template error (2 errors)", ["clang++"], clang_setup),
 ("cargo build (3 type errors)", ["cargo"], cargo_setup),
 ("git log, last 20 commits", ["git"], git_sc("log")),
 ("git: files in one commit", ["git"], git_sc("show")),
 ("git: files changed in 10 commits", ["git"], git_sc("diff")),
 ("unzip 400 files", ["zip", "unzip"], unzip_setup),
 ("tar -x 400 files", ["tar"], tar_setup),
]

rows, skipped = [], []
try:
    for name, needs, setup in SC:
        miss = [t for t in needs if not have(t)]
        if miss: skipped.append(f"{name} (no {', '.join(miss)})"); continue
        cwd, variants, ok = setup()
        res = []
        for label, cmd, role in variants:
            o, rc, sec = timed(cmd, cwd)
            res.append((label, role, tok(o), ok(o, rc), sec))
        rows.append((name, res))
finally:
    shutil.rmtree(W, ignore_errors=True)

if not rows:
    print(f"not applicable on this host: none of the tools for the {len(SC)} scenarios are installed.")
    sys.exit(0)

pct = lambda a, b: f"{math.floor((1 - b / a) * 1000) / 10}%" if a else "n/a"   # floor: never round up
print(f"token counter: {TK}   |   {len(rows)}/{len(SC)} scenarios applicable on this host")
if skipped: print("not applicable (tool not installed): " + "; ".join(skipped))
print("\nTOKENS RETURNED TO THE AGENT   (* = that text still contains the answer)\n")
for name, res in rows:
    print(name)
    for label, role, t, a, sec in res:
        tag = {"habit": "habit", "rec": "<- recommended", "info": "", "trap": "generic cut"}[role]
        print(f"   {label:<48}{t:>7}{'*' if a else ' '}  {sec:6.3f}s  {tag}")

pick = lambda res, r: next(x for x in res if x[1] == r)
summ = [(n, pick(res, "habit"), pick(res, "rec")) for n, res in rows]
H = sum(h[2] for _, h, _ in summ); R = sum(r[2] for _, _, r in summ)
HS = sum(h[4] for _, h, _ in summ); RS = sum(r[4] for _, _, r in summ)
traps = [f"{n} {x[0]}" for n, res in rows for x in res if x[1] == "trap" and not x[3]]
held = [f"{n} {x[0]}" for n, res in rows for x in res if x[1] == "trap" and x[3]]
lost = [n for n, _, r in summ if not r[3]]
nobase = [n for n, h, _ in summ if not h[3]]

print("\n" + "=" * 78 + "\nHABIT -> RECOMMENDED   (tokens, answer kept, median wall clock)\n")
for n, h, r in summ:
    print(f"   {n:<36}{h[2]:>7} -> {r[2]:<5} {pct(h[2], r[2]):>7}   kept: {'yes' if r[3] else 'NO'}"
          f"   {h[4]:.3f}s -> {r[4]:.3f}s")
print(f"   {'TOTAL':<36}{H:>7} -> {R:<5} {pct(H, R):>7}   {HS:.2f}s -> {RS:.2f}s")
if traps: print("\ngeneric head/tail cuts that LOST the answer (the trap):\n   " + "\n   ".join(traps))
if held: print("\nNOTE: a generic cut kept the answer this time (trap did not reproduce): " + "; ".join(held))
if nobase: print("\nFAIL: the loud baseline did not contain the answer (fixture broken?): " + "; ".join(nobase))
print(f"\nall recommended forms kept the answer: {not lost}" + (f"  (LOST: {'; '.join(lost)})" if lost else ""))

if len(sys.argv) > 1:
    import datetime as d
    b = [f"token counter: {TK}", f"applicable scenarios: {len(rows)}/{len(SC)}"]
    if skipped: b.append("- not applicable: " + "; ".join(skipped))
    for n, h, r in summ:
        b.append(f"- {n}: {h[2]} -> {r[2]} tok ({pct(h[2], r[2])}), answer kept: {r[3]}, {h[4]:.3f}s -> {r[4]:.3f}s")
    b.append(f"- total habit -> recommended: {H} -> {R} tok ({pct(H, R)}), {HS:.2f}s -> {RS:.2f}s")
    if traps: b.append("- generic cuts that lost the answer (expected): " + "; ".join(traps))
    if held: b.append("- trap did not reproduce: " + "; ".join(held))
    b.append(f"- all recommended forms kept the answer: {not lost}")
    open(sys.argv[1], "a").write(f"\n---\n# /bench-verify run — {d.date.today()}\n\n" + "\n".join(b) + "\n")
    print("\nlogged ->", sys.argv[1])
sys.exit(1 if lost or nobase else 0)
