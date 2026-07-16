import sys,datetime as d
t=sys.argv[1] if len(sys.argv)>1 else "run"
b=sys.stdin.read().rstrip()
f=__file__.rsplit("/",1)[0]+"/benchmark-findings.md"
open(f,"a").write(f"\n---\n# {t} — {d.date.today()}\n\n{b}\n")
print("logged:",t)
