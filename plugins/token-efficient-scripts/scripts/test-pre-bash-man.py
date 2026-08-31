#!/usr/bin/env python3
# Tests for the PreToolUse `man` hook. Stdlib only; exits non-zero on any failure.
#   python3 test-pre-bash-man.py           unit matrix (fast, free, no network, no API)
#   python3 test-pre-bash-man.py --e2e     ALSO drives a real `claude -p` process (COSTS MONEY)
import json, os, subprocess as s, sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pre-bash-man.py")

def decide(payload):
    r = s.run([sys.executable, HOOK], input=json.dumps(payload), capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return f"CRASH(rc={r.returncode}) {r.stderr.strip()[:80]}"
    if not r.stdout.strip():
        return "allow"
    try:
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"]
    except Exception:
        return f"BADJSON {r.stdout.strip()[:80]}"

# (expected, command) — expected is "deny" or "allow"
CASES = [
    # denied: the whole page would land in context
    ("deny",  "man find"),
    ("deny",  "man 5 hosts"),
    ("deny",  "man sed"),
    ("deny",  "MANWIDTH=80 man date"),
    ("deny",  "MANPAGER=cat man stat"),
    ("deny",  "cd /tmp && man xargs"),
    ("deny",  "echo hi; man awk"),
    # piped, but to something that does NOT reduce output
    ("deny",  "man find | col -b"),
    ("deny",  "man find | cat"),
    ("deny",  "man git-rebase|less"),
    # allowed: already filtered down
    ("allow", "man find | col -b | grep -nE -m3 -B2 -A3 'printf'"),
    ("allow", "man find|head -40"),
    ("allow", "man sed | col -b | sed -n '1,20p'"),
    ("allow", "man xargs | rg -m2 null"),
    # allowed: flags whose output is already tiny
    ("allow", "man -k compress"),
    ("allow", "man -w find"),
    ("allow", "man -f ls"),
    ("allow", "man --help"),
    # allowed: never enters context
    ("allow", "man find > /tmp/x"),
    ("allow", "man find >> /tmp/x"),
    # allowed: explicit override
    ("allow", "TE_ALLOW_MAN=1 man find"),
    # allowed: must not false-positive
    ("allow", "man"),
    ("allow", "echo woman"),
    ("allow", "command -v man"),
    ("allow", "ls /usr/share/man"),
    ("allow", "grep -rn human ."),
    ("allow", "apropos compress"),
    ("allow", "date -v-2d +%F"),
    ("allow", "MANPATH=/x ls"),
]

fails = []
for want, cmd in CASES:
    got = decide({"tool_name": "Bash", "tool_input": {"command": cmd}})
    ok = got == want
    if not ok: fails.append((cmd, want, got))
    print(f"  {'ok  ' if ok else 'FAIL'} {got:<6} {cmd}")

# must fail OPEN: a hook that misfires is worse than no hook
print("\nfail-open:")
for label, payload in [
    ("non-Bash tool",     {"tool_name": "Read", "tool_input": {"file_path": "/x"}}),
    ("missing tool_input",{"tool_name": "Bash"}),
    ("empty command",     {"tool_name": "Bash", "tool_input": {"command": ""}}),
    ("null command",      {"tool_name": "Bash", "tool_input": {"command": None}}),
    ("empty object",      {}),
]:
    got = decide(payload); ok = got == "allow"
    if not ok: fails.append((label, "allow", got))
    print(f"  {'ok  ' if ok else 'FAIL'} {got:<6} {label}")
r = s.run([sys.executable, HOOK], input="not json at all", capture_output=True, text=True)
ok = r.returncode == 0 and not r.stdout.strip()
if not ok: fails.append(("unparseable stdin", "allow", f"rc={r.returncode} out={r.stdout[:40]}"))
print(f"  {'ok  ' if ok else 'FAIL'} allow  unparseable stdin")

print(f"\n{len(CASES)+6-len(fails)}/{len(CASES)+6} passed")
for c, w, g in fails: print(f"  FAILED: {c!r} wanted {w}, got {g}")

if "--e2e" in sys.argv and not fails:
    print("\n=== end-to-end (real `claude -p`; this COSTS MONEY) ===")
    import tempfile
    d = tempfile.mkdtemp()
    cfg = os.path.join(d, "settings.json")
    open(cfg, "w").write(json.dumps({"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": f'python3 "{HOOK}"'}]}]}}))
    def ask(prompt):
        r = s.run(["claude", "-p", prompt, "--settings", cfg, "--allowed-tools", "Bash",
                   "--output-format", "json"], capture_output=True, text=True, cwd=d,
                  stdin=s.DEVNULL, timeout=300)
        try: return json.loads(r.stdout).get("result", "")
        except Exception: return f"<no json: {r.stdout[:200]} {r.stderr[:200]}>"
    a = ask("Run this exact command with Bash: man find — then say in one sentence what happened.")
    print("  denied path ->", a[:220])
    ok1 = "block" in a.lower() or "hook" in a.lower()
    b = ask("Run this exact command with Bash and say whether it succeeded: "
            "man find | col -b | grep -nE -m3 -B2 -A3 'maxdepth'")
    print("  allowed path ->", b[:220])
    ok2 = "succeed" in b.lower() or "success" in b.lower()
    print(f"  e2e: deny={'ok' if ok1 else 'FAIL'} allow={'ok' if ok2 else 'FAIL'}")
    if not (ok1 and ok2): fails.append(("e2e", "deny+allow", f"{ok1},{ok2}"))

sys.exit(1 if fails else 0)
