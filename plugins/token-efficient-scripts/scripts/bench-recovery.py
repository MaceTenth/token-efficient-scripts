#!/usr/bin/env python3
# Portable benchmark: what does it cost an agent to RECOVER from a FAILED CLI invocation?
# Compares recovery strategies on tokens returned to the agent, whether the returned text
# actually contains the answer, and wall-clock. tiktoken if present, else chars/4 proxy.
# Appends a dated summary to arg1 if given.
#
# Scenarios are GNU-flag-on-BSD failures. Each is PRECHECKED: if the command does not
# actually fail on this host (e.g. GNU userland), the scenario is reported not-applicable
# and excluded, so the numbers never claim more than the platform supports.
import os, sys, re, json, time, subprocess as s
try:
    import tiktoken; _e = tiktoken.get_encoding("cl100k_base"); tok = lambda x: len(_e.encode(x)); TK = "cl100k"
except Exception:
    tok = lambda x: round(len(x) / 4); TK = "chars/4 proxy"

def sh(c, t=30):
    try:
        r = s.run(["bash", "-c", c], capture_output=True, text=True, timeout=t)
        return (r.stdout or "") + (r.stderr or ""), r.returncode
    except Exception as e:
        return f"<{e}>", 99

def timed(c, n=3, t=30):
    """min-of-n wall clock; returns (output, seconds)."""
    b = 9e9; o = ""
    for _ in range(n):
        st = time.perf_counter(); o = sh(c, t)[0]; b = min(b, time.perf_counter() - st)
    return o, b

MAN = 'env MANWIDTH=80 MANPAGER=cat man %s 2>/dev/null | col -b'
NET = os.environ.get("BENCH_NET", "1") == "1"   # BENCH_NET=0 skips the network leg

# name, failing cmd, tool, loose probe, tight probe, answer regex, verified fix, expected regex
SC = [
 ("date -d (relative date)", "date -d '2 days ago' +%F", "date",
  "ago|relative|adjust", "adjust", r"-v ?\[?[+-]", "date -v-2d +%F", r"^\d{4}-\d{2}-\d{2}$"),
 ("stat -c (file size)", "stat -c %s /etc/hosts", "stat",
  "size|format", "size of file", r"\bz\b.*size|%z", "stat -f %z /etc/hosts", r"^\d+$"),
 ("du --max-depth", "du --max-depth=1 /etc", "du",
  "depth", "depth", r"-d *depth|-d *[0-9]", "du -d 1 /etc/ 2>/dev/null|tail -1", r"\d"),
 ("grep -P (digits)", "/usr/bin/grep -P '\\d+' /etc/hosts", "grep",
  "perl|extended|regular expression", "extended regular", r"-E\b",
  "/usr/bin/grep -cE '[0-9]+' /etc/hosts", r"^\d+$"),
 ("xargs -d (delimiter)", "printf 'a,b,c'|xargs -d, -n1 echo", "xargs",
  "delimit|separat|null", "null|NUL", r"-0\b",
  "printf 'a,b,c'|tr ',' '\\0'|xargs -0 -n1 echo", r"a"),
 ("sed -i (in-place)", "cd /tmp&&cp /etc/hosts br1&&sed -i s/localhost/LH/ br1", "sed",
  "in-place|in place|-i", "in-place|in place", r"-i *extension|-i *''",
  "cd /tmp&&cp /etc/hosts br2&&sed -i '' s/localhost/LH/ br2&&grep -c LH br2", r"^\d+$"),
 ("find -printf (basename)", "/usr/bin/find /etc/ -maxdepth 1 -printf '%f\\n'", "find",
  "printf|format|print", "printf", r"-exec +basename|basename",
  "/usr/bin/find /etc/ -maxdepth 1 -name hosts -exec basename {} ';'", r"hosts"),
 ("timeout (missing binary)", "timeout 1 sleep 2", "timeout",
  "timeout|duration", "duration|SECONDS", r"gtimeout|coreutils|brew install",
  "perl -e 'alarm 1;exec @ARGV' sleep 2;echo rc=$?", r"rc="),
]

rows, skipped = [], []
for nm, fail, c, loose, tight, ans, fix, exp in SC:
    fo, frc = sh(fail)
    # PRECHECK: the premise is that this invocation fails here.
    if frc == 0 and not re.search(r"illegal option|invalid option|unknown primary|not supported|unrecognized|command not found|usage:", fo, re.I):
        skipped.append(nm); continue
    st = {}
    st["error only"]   = (fo, 0.0)                                  # already in context: free, no call
    st["--help"]       = timed(f"{c} --help", 3, 10)
    st["man (full)"]   = timed(MAN % c)
    st["man|grep loose"] = timed(f"{MAN % c}|grep -nE -B1 -A3 '{loose}'|head -40")
    st["man|grep TIGHT"] = timed(f"{MAN % c}|grep -nE -m3 -B2 -A3 '{tight}'")
    if NET:
        st["web (cheat.sh)"] = timed(f"curl -sS -m 15 'https://cheat.sh/{c}?T'", 1)
    xo, xrc = sh(fix)
    rows.append(dict(name=nm, fix_ok=(xrc == 0 and bool(re.search(exp, xo.strip(), re.M))),
                     out=" ".join(xo.split())[:34],
                     s={k: (tok(v), bool(re.search(ans, v, re.I)), sec) for k, (v, sec) in st.items()}))

if not rows:
    print(f"not applicable on this host: all {len(SC)} scenarios succeeded "
          f"(GNU userland?). This benchmark measures GNU-flag-on-BSD failures.")
    sys.exit(0)

K = list(rows[0]["s"].keys()); w = max(len(r["name"]) for r in rows) + 1
N = len(rows)
print(f"token counter: {TK}   |   {N}/{len(SC)} scenarios applicable on this host")
if skipped: print(f"not applicable (did not fail here): {', '.join(skipped)}")
print("\nTOKENS RETURNED TO THE AGENT   (* = that text actually contains the answer)\n")
print("scenario".ljust(w) + "".join(k.rjust(16) for k in K))
for r in rows:
    print(r["name"].ljust(w) + "".join(f"{r['s'][k][0]}{'*' if r['s'][k][1] else ''}".rjust(16) for k in K))
print("-" * (w + 16 * len(K)))
tot = {k: sum(r["s"][k][0] for r in rows) for k in K}
sol = {k: sum(1 for r in rows if r["s"][k][1]) for k in K}
sec = {k: sum(r["s"][k][2] for r in rows) for k in K}
print("total tokens".ljust(w) + "".join(str(tot[k]).rjust(16) for k in K))
print("solved".ljust(w) + "".join(f"{sol[k]}/{N}".rjust(16) for k in K))
print("tok/answer".ljust(w) + "".join((f"{tot[k]/sol[k]:.0f}" if sol[k] else "never").rjust(16) for k in K))
print("wall-clock s".ljust(w) + "".join(f"{sec[k]:.2f}".rjust(16) for k in K))

def ladder(order, label, search=None):
    t = n = calls = 0.0; sc = 0; tr = []
    for r in rows:
        c = 0; cl = 0; hit = None; el = 0.0
        for st in order:
            tk, f, se = r["s"][st]
            if st != "error only":            # the error text costs no call and no tokens
                c += tk; cl += 1; el += se
            if f: hit = st; break
        if hit is None and search and search in r["s"]:
            tk, f, se = r["s"][search]
            c += tk; cl += 1; el += se
            if f: hit = search
        t += c; calls += cl; n += el; sc += hit is not None
        tr.append((r["name"], c, cl, hit or "UNSOLVED"))
    print(f"\n{label}")
    for a, b, cl, h in tr: print(f"   {a:<26}{b:>6} tok  {cl} call(s)  via {h}")
    print(f"   => {int(t)} tok, {sc}/{N} solved, {int(calls)} tool calls, {n:.2f}s"
          + (f", {t/sc:.0f} tok/answer" if sc else ""))
    return int(t), sc, int(calls), n

print("\n" + "=" * 78 + "\nESCALATION LADDERS  (the error text is already in context: 0 tokens, 0 calls)")
A = ladder(["man (full)"], "A. naive: go straight to the man page")
B = ladder(["error only", "--help", "man (full)"], "B. error -> --help -> full man")
C = ladder(["error only", "--help", "man|grep TIGHT"], "C. error -> --help -> tight man|grep")
D = ladder(["error only", "--help", "man|grep TIGHT"],
           "D. C, then the web for what local docs lack", search="web (cheat.sh)") if NET else None
print("\nfixes verified to produce a correct answer:")
for r in rows: print(f"   {'OK  ' if r['fix_ok'] else 'FAIL'} {r['name']:<26} -> {r['out']}")

if len(sys.argv) > 1:
    import datetime as d
    b = [f"token counter: {TK}", f"applicable scenarios: {N}/{len(SC)}"]
    for k in K:
        b.append(f"- {k}: {tot[k]} tok, solved {sol[k]}/{N}, "
                 f"{(f'{tot[k]/sol[k]:.0f}' if sol[k] else 'never')} tok/answer, {sec[k]:.2f}s")
    for lab, L in (("A naive full man", A), ("B error/help/full man", B), ("C error/help/tight grep", C)) + ((("D C+web", D),) if D else ()):
        b.append(f"- ladder {lab}: {L[0]} tok, {L[1]}/{N} solved, {L[2]} calls, {L[3]:.2f}s")
    b.append(f"- all fixes verified correct: {all(r['fix_ok'] for r in rows)}")
    open(sys.argv[1], "a").write(f"\n---\n# /bench-recovery run — {d.date.today()}\n\n" + "\n".join(b) + "\n")
    print("\nlogged ->", sys.argv[1])
