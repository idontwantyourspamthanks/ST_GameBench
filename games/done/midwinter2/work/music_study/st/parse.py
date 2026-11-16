import re,sys
t=open(sys.argv[1],errors='replace').read()
# split on hit
parts=re.split(r'\n\d+\. CPU breakpoint condition\(s\) matched \d+ times\.\n',t)
for p in parts[1:]:
    m=re.match(r'\s*pc = \$([0-9a-f]+)',p)
    pc=m.group(1)
    vbl=re.search(r'#(\d+) \(dec\)',p)
    regs=dict(re.findall(r'\b([DA]\d) ([0-9A-F]{8})',p))
    m2=re.search(r'> m a7 16\n[0-9A-F]+: ((?:[0-9a-f]{2} ?)+)',p)
    st=m2.group(1).split() if m2 else []
    l=lambda i:''.join(st[i:i+4])
    def g(c):
        m=re.search(r'> m %s \d\n[0-9A-Fa-f]+: ((?:[0-9a-f]{2} ?)+)'%re.escape(c),p); return ''.join(m.group(1).split()) if m else '?'
    print(f"pc=${pc:7s} VBL={vbl.group(1) if vbl else '?':6s} d0={regs.get('D0')} ret={l(0)} {l(4)} {l(8)} 7626={g('$7626')} b96={g('$b96')} 757c={g('$757c')} 700a={g('$700a')}")
