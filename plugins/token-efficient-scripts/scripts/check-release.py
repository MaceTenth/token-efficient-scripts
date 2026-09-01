#!/usr/bin/env python3
# Pre-push release gate. Catches the drift RELEASING.md warns about — stale slide, version
# mismatches, headline numbers that disagree between files. Stdlib only; exits non-zero on error.
import json, os, re, sys, subprocess as s

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
P = lambda *a: os.path.join(ROOT, *a)
PLUG = ("plugins", "token-efficient-scripts")
SKILL = P(*PLUG, "skills", "token-efficient-scripts", "SKILL.md")
def read(p):
    try: return open(p).read()
    except Exception: return ""

errs, warns = [], []
def err(m): errs.append(m); print(f"  FAIL  {m}")
def warn(m): warns.append(m); print(f"  warn  {m}")
def ok(m): print(f"  ok    {m}")

print("versions")
pj = json.loads(read(P(*PLUG, ".claude-plugin", "plugin.json")))
ver = pj["version"]
ok(f"plugin.json version = {ver}")
chg = read(P("CHANGELOG.md"))
top = re.search(r"^## (\d+\.\d+\.\d+)", chg, re.M)
if not top: err("CHANGELOG.md has no `## X.Y.Z` heading")
elif top.group(1) != ver: err(f"CHANGELOG newest is {top.group(1)} but plugin.json is {ver}")
else: ok(f"CHANGELOG newest entry matches ({ver})")

slide = read(P("slide.html"))
if not slide: err("slide.html missing")
elif ver not in slide:
    err(f"slide.html does not mention {ver} — it is served live and is the easiest file to forget")
else: ok(f"slide.html mentions {ver}")

print("\ndescriptions")
mk = json.loads(read(P(".claude-plugin", "marketplace.json")))
mkd = next((p.get("description", "") for p in mk.get("plugins", []) if p.get("name") == pj["name"]), "")
if not mkd: err("marketplace.json has no description for this plugin")
else: ok("marketplace.json describes the plugin")
fm = re.search(r"^---\n(.*?)\n---", read(SKILL), re.S)
if not fm: err("SKILL.md has no frontmatter")
elif "description:" not in fm.group(1): err("SKILL.md frontmatter has no description (skill will not trigger)")
else: ok("SKILL.md frontmatter description present")

print("\nheadline numbers agree across files")
# a number that appears in >1 file must appear consistently; each is (label, needle, files)
FILES = {"README": read(P("README.md")), "CHANGELOG": chg, "SKILL": read(SKILL), "slide": slide,
         "findings": read(P(*PLUG, "skills", "token-efficient-scripts", "references", "cli-failure-recovery.md"))}
for label, needle in [("naive man total", "26,316"), ("ladder C total", "438"), ("full ladder", "3,166")]:
    hits = [f for f, t in FILES.items() if needle in t or needle.replace(",", "") in t]
    (ok if len(hits) >= 2 else warn)(f"{label} {needle}: {', '.join(hits) or 'NOWHERE'}")
for bad in re.findall(r"\b9[05]% fewer tokens\b", FILES["README"]):
    err(f"README rounds a reduction up: {bad!r} (88.0% is not 90%)")

print("\nreferenced files exist")
for rel in [(*PLUG, "scripts", "bench.py"), (*PLUG, "scripts", "bench-recovery.py"),
            (*PLUG, "scripts", "test-cheatsheet.py"), (*PLUG, "scripts", "test-pre-bash-man.py"),
            (*PLUG, "scripts", "pre-bash-man.py"), (*PLUG, "hooks", "hooks.json"),
            (*PLUG, "commands", "bench.md"), (*PLUG, "commands", "bench-recovery.md"),
            ("RELEASING.md",)]:
    (ok if os.path.exists(P(*rel)) else err)(os.path.join(*rel))
try:
    json.loads(read(P(*PLUG, "hooks", "hooks.json"))); ok("hooks.json is valid JSON")
except Exception as e: err(f"hooks.json invalid: {e}")

print("\ntest suites")
for name in ("test-cheatsheet.py", "test-pre-bash-man.py"):
    r = s.run([sys.executable, P(*PLUG, "scripts", name)], capture_output=True, text=True)
    tail = [l for l in r.stdout.strip().splitlines() if l.strip()][-1] if r.stdout.strip() else "no output"
    (ok if r.returncode == 0 else err)(f"{name}: {tail}")

print("\nweekly task wiring")
wt = read(os.path.expanduser("~/.claude/scheduled-tasks/token-efficient-scripts-weekly-bench/SKILL.md"))
if not wt: warn("weekly task file not found on this host (fine if you are not the maintainer)")
else:
    for scr in ("bench.py", "bench-recovery.py", "test-cheatsheet.py", "test-pre-bash-man.py"):
        (ok if scr in wt else warn)(f"weekly task runs {scr}")
    # only flag an ACTUAL invocation; the task legitimately mentions --e2e to forbid it
    if re.search(r"\.py[^\n`]*--e2e", wt):
        err("weekly task INVOKES --e2e — that spawns a real claude and costs money")
    elif "--e2e" in wt: ok("weekly task mentions --e2e only to forbid it")

print(f"\n{len(errs)} error(s), {len(warns)} warning(s)")
for m in errs: print(f"  ERROR: {m}")
if errs: print("\nSee RELEASING.md.")
sys.exit(1 if errs else 0)
