#!/usr/bin/env python3
# Portable, dependency-light benchmark for the token-efficient-scripts skill.
# tiktoken if present, else chars/4 proxy. Writes a dated summary to arg1 (log path) if given.
import os,sys,subprocess as s,tempfile,time
try:
    import tiktoken; _e=tiktoken.get_encoding("cl100k_base"); tok=lambda x:len(_e.encode(x)); TK="cl100k"
except Exception:
    tok=lambda x:round(len(x)/4); TK="chars/4 proxy"

D=tempfile.mkdtemp()
log=open(f"{D}/access.log","w")
for i in range(60000):
    log.write(f"10.0.{i%256}.{(i*7)%256} - - {[200,200,404,500,301][i%5]} /p/{i%50}\n")
log.close()
open(f"{D}/data.csv","w").write("id,value,cat\n"+"".join(f"{i},{(i*13)%1000},{'AB'[i%2]}\n" for i in range(100000)))

def run(c):
    b=9e9;o=""
    for _ in range(3):
        t=time.perf_counter();r=s.run(["bash","-c",c],capture_output=True,text=True);b=min(b,time.perf_counter()-t);o=r.stdout
    return o,b

def num(o): import re; m=re.findall(r"-?\d+",o); return int(m[0]) if m else None

rows=[]
# 1 output control: dump matches vs count. answer = number of 404 lines.
a,_=run(f"grep ' 404 ' {D}/access.log"); b,_=run(f"grep -c ' 404 ' {D}/access.log")
same1 = len([l for l in a.splitlines() if l]) == num(b)
rows.append(("output-control: grep -> grep -c", tok(a), tok(b), same1))
# 2 output control: dump cat=A rows vs aggregate of the SAME task (sum value where cat=A).
a,_=run(f"awk -F, 'NR>1&&$3==\"A\"' {D}/data.csv"); b,_=run(f"awk -F, '$3==\"A\"{{s+=$2}}END{{print s}}' {D}/data.csv")
same2 = sum(int(l.split(',')[1]) for l in a.splitlines() if l) == num(b)
rows.append(("output-control: rows -> aggregate", tok(a), tok(b), same2))
# 3 code trimming: verbose python vs find|wc — verify identical count.
v="import os\nn=0\nfor r,_,fs in os.walk('%s'):\n for f in fs:n+=1\nprint(n)"%D
m="find %s -type f|wc -l"%D
va,_=run("python3 -c \"%s\""%v.replace('"','\\"')); mb,_=run(m)
rows.append(("code: python walk -> find|wc", tok(v), tok(m), num(va)==num(mb)))
# 4 pushdown timing (same tiny output; measure speed)
_,t1=run(f"sort {D}/access.log|awk '$4==500{{print $1}}'|sort -u|wc -l")
_,t2=run(f"awk '$4==500{{print $1}}' {D}/access.log|sort -u|wc -l")

print(f"token counter: {TK}")
print(f"{'experiment':<34}{'before':>9}{'after':>9}{'reduction':>11}  same")
for n,bef,aft,ok in rows:
    red = f"{100*(bef-aft)/bef:.0f}%" if bef else "-"
    print(f"{n:<34}{bef:>9}{aft:>9}{red:>11}  {'yes' if ok else 'DIFF'}")
print(f"predicate pushdown speedup (filter before sort): {t1/t2:.2f}x")

if len(sys.argv)>1:
    import datetime as d
    body=[f"token counter: {TK}"]
    for n,bef,aft,ok in rows:
        red = f"{100*(bef-aft)/bef:.0f}%" if bef else "-"
        body.append(f"- {n}: {bef} -> {aft} ({red}), same_answer={ok}")
    body.append(f"- predicate pushdown: {t1/t2:.2f}x faster")
    open(sys.argv[1],"a").write(f"\n---\n# /bench run — {d.date.today()}\n\n"+"\n".join(body)+"\n")
    print("logged ->",sys.argv[1])
