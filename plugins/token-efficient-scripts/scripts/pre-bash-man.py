#!/usr/bin/env python3
# PreToolUse(Bash) hook: deny an unfiltered `man` invocation and hand back the ladder.
# Enforcement, not suggestion — a skill can only bias the model, this stops the call.
# Dependency-free (stdlib only; no jq). Fails OPEN on any surprise: never block on a bug.
import sys, json, re

def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return                                   # unparseable stdin -> allow
    if d.get("tool_name") != "Bash":
        return
    cmd = (d.get("tool_input") or {}).get("command") or ""
    if not cmd or "TE_ALLOW_MAN=1" in cmd:       # explicit override
        return

    # Flags whose output is already tiny.
    SMALL = re.compile(r'(?:^|\s)-(?:k|w|f|V)\b|--(?:apropos|where|whatis|help|version)\b')
    # Downstream stages that actually REDUCE output. `col`/`cat`/`less` do not.
    REDUCE = re.compile(r'\b(?:grep|egrep|rg|ug|ack|head|tail|sed|awk|wc|jq|sort|uniq|cut|fzf)\b')
    ENV = re.compile(r'^(?:\w+=(?:"[^"]*"|\'[^\']*\'|\S*)\s+)*')   # leading VAR=val prefixes

    for pipeline in re.split(r';|&&|\|\||\n', cmd):
        stages = pipeline.split("|")
        head = ENV.sub("", stages[0].strip().lstrip("("))
        if not re.match(r'man\s+\S', head):   # bare `man` prints a one-line usage: harmless
            continue
        if SMALL.search(head) or re.search(r'>>?\s*\S', pipeline):
            continue                             # small output, or redirected to a file
        if len(stages) > 1 and REDUCE.search("|".join(stages[1:])):
            continue                             # already filtered
        tool = (re.findall(r'man\s+(?:-\S+\s+)*(\S+)', head) or ["CMD"])[0].strip("'\"")
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason":
                f"Unfiltered `man {tool}` costs ~1,500-6,400 tokens of context and often does not "
                f"contain the answer. Recover cheapest-first instead:\n"
                f"1. Re-read the error you already have — BSD/macOS tools print their usage when "
                f"they reject a flag (solves ~3/8 cases for free).\n"
                f"2. `{tool} --help` (~58 tokens).\n"
                f"3. Grep the page, tightly: "
                f"`man {tool} | col -b | grep -nE -m3 -B2 -A3 '<concept>'` — probe the concept "
                f"(depth, size of file, in-place, null), not the flag you guessed. `-B2` because "
                f"flag names sit above their prose; `-m3` not `| head -N`, which gets eaten by "
                f"early false positives.\n"
                f"4. Nothing returned? The flag does not exist here — search the web (~800 tokens). "
                f"That is the only thing a man page structurally cannot tell you.\n"
                f"Measured: 26,316 -> 438 tokens for the same answers. "
                f"Override with `TE_ALLOW_MAN=1 man {tool}` if you truly need the whole page."}}))
        return

main()
