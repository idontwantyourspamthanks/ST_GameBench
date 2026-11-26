import re, subprocess, sys
def syms(src, tag):
    txt = open(src).read()
    txt2 = re.sub(r"\b(bra|bsr|b(?:eq|ne|cc|cs|hs|lo|hi|ls|mi|pl|ge|lt|gt|le|vc|vs))\.s\b", r"\1", txt)
    open(f'{tag}.s','w').write(txt2)
    r = subprocess.run(['vasmm68k_mot','-Fsrec','-m68000','-L',f'{tag}.lst','-o',f'{tag}.srec',f'{tag}.s'],capture_output=True,text=True); assert r.returncode==0, r.stderr
    lst = open(f'{tag}.lst').read()
    s = {m.group(1): int(m.group(2),16) for m in re.finditer(r"^(\w+)\s+A:([0-9A-Fa-f]+)", lst, re.M)}
    eq = {m.group(1) for m in re.finditer(r"^(\w+)\s+equ\s", txt, re.M)}
    s = {k:v for k,v in s.items() if k not in eq and v >= 0x75740 and v < 0x77ec0}
    mem = {}
    for ln in open(f'{tag}.srec'):
        if ln.startswith('S3'):
            n=int(ln[2:4],16); a=int(ln[4:12],16)
            for i in range(n-5): mem[a+i]=1
    ends = sorted(a+1 for a in mem if a+1 not in mem)
    order = sorted(s.items(), key=lambda kv: kv[1])
    size = {}
    addrs = sorted(set(s.values()))
    for k, a in order:
        nxt = [x for x in addrs if x > a]; end = min(x for x in ends if x > a)
        size[k] = (min(nxt[0], end) if nxt else end) - a
    return s, size
so, zo = syms(sys.argv[1], 'old'); sn, zn = syms(sys.argv[2], 'new')
rows = []
for k in sorted(set(zo)|set(zn)):
    a, b = zo.get(k), zn.get(k)
    if a != b: rows.append((k, a, b))
tot = 0
for k,a,b in sorted(rows, key=lambda r: (so.get(r[0]) or sn.get(r[0]))):
    d = (b or 0) - (a or 0); tot += d
    print(f'{k:12s} {str(a):>5s} -> {str(b):>5s}  {d:+d}')
print('sum of deltas', tot, '(labels at one address are each given the size up to the next address, and data labels that moved or lost their name shift bytes between neighbours: not a total; the total is gen_ed.py: 9404 -> 9152)')
