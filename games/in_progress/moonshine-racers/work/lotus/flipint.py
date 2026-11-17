import sys, re, time, collections
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/lotus')
from lotus import *
L='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/lotus/'
def run(snap, clock, name, pokes=((0x70569,1),), seconds=10):
    h = Lotus(snapshot=snap, extra=['--joy1','keys'])
    try:
        time.sleep(2)
        if clock != 8: h.set_cpuclock(clock); time.sleep(1)
        for a,v in pokes: h.debug(f'w ${a:x} ${v:x}', 0.2)
        (h.R/'fl.txt').write_text('e VBL\ne FrameCycles\n')
        h.debug('b all',0.3)
        n0=len(h._logtext())
        h.cmd(f'hatari-debug b pc = $755f6 :trace :file {h.R}/fl.txt')
        time.sleep(seconds)
        h.debug('b all',0.3)
        log=h._logtext()[n0:]
    finally:
        h.close()
    ev=[]; vbl=None
    for ln in log.splitlines():
        m=re.search(r'#(\d+) \(dec\)',ln)
        if m:
            v=int(m.group(1))
            if vbl is None: vbl=v
            else: ev.append((vbl,v)); vbl=None
    CYC=160256
    t=[v*CYC+fc for v,fc in ev]
    # VBL counter wraps vs FrameCycles: just use VBL numbers
    vb=[v for v,fc in ev]
    d=[b-a for a,b in zip(vb,vb[1:])]
    c=collections.Counter(d)
    print(name,'flips',len(vb),'mean VBL/flip %.3f'%(sum(d)/len(d)), dict(sorted(c.items())))
    open(L+f'prof/flipint_{name}.txt','w').write(' '.join(map(str,vb)))
run(L+'race1.sav',8,'1p8')
run(L+'race1.sav',16,'1p16')
run(L+'race2p.sav',8,'2p8',pokes=((0x70569,1),(0x7056a,1)))
