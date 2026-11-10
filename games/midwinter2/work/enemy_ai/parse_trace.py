import re,sys
def parse(path,ns=5):
    txt=open(path,errors='replace').read()
    hits=txt.split('Reading debugger commands')
    out=[]
    for h in hits[1:]:
        cur=None; buf={}
        for line in h.splitlines():
            if line.startswith('> m $'):
                cur=int(line.split('$')[1].split()[0],16)
            m=re.match(r'^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} ?)+)',line,re.I)
            if m and cur is not None:
                a=int(m.group(1),16)
                for i,b in enumerate(m.group(2).split()):
                    buf[a+i]=int(b,16)
            m=re.match(r'^= .*#(\d+) \(dec\)',line)
            if m: buf['vbl']=int(m.group(1))
        out.append(buf)
    return out
def ent(buf,base):
    g=lambda o,n=2: int.from_bytes(bytes(buf.get(base+o+i,0) for i in range(n)),'big')
    s=lambda o: g(o)-65536 if g(o)>=32768 else g(o)
    return dict(id=s(0),x=g(6,4),y=g(0xa,4),alt=s(0xe),spd=s(0x18),hv=(s(0x1a),s(0x1c)),tgt=(g(0x22,4),g(0x26,4)),talt=s(0x2a),
                typ=s(0x2e),unit=g(0x30,4),st=g(0x3a),t36=s(0x36),t38=s(0x38),t3c=s(0x3c),t3e=s(0x3e),t40=s(0x40),w34=s(0x34),hdg=s(0x14),bank=s(0x16),pv=(s(0x1e),s(0x20)))
def glob(buf):
    g=lambda a,n=2: int.from_bytes(bytes(buf.get(a+i,0) for i in range(n)),'big')
    return dict(c6820=g(0x6820),c6822=g(0x6822),c6824=g(0x6824),c6826=g(0x6826),hit=g(0x6282),px=g(0x66e6,4),py=g(0x66ea,4),palt=g(0x764c))
if __name__=='__main__':
    rows=parse(sys.argv[1]); ns=5
    seen=set()
    for r in rows:
        v=r.get('vbl')
        if v in seen: continue   # one line per tick (hit repeats per active NPC)
        seen.add(v)
        G=glob(r)
        line=[f"vbl {v} cnt(b/c,7,hostile,a)={G['c6820']},{G['c6822']},{G['c6824']},{G['c6826']} hit={G['hit']&1}"]
        for i in range(ns):
            e=ent(r,0x3532+0x42*i)
            if e['typ']<=0: continue
            line.append(f" [{i}] T{e['typ']} s{e['st']} v{e['spd']} p({e['x']},{e['y']},{e['alt']}) t36/38/3c/3e/40={e['t36']},{e['t38']},{e['t3c']},{e['t3e']},{e['t40']} w34={e['w34']}")
        print(''.join(line))
