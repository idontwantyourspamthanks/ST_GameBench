import sys, time, re, shutil; from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; sys.path.insert(0,str(ROOT/'tools'))
from mw2harness import Hatari
mem=int(sys.argv[1]); gd=ROOT/sys.argv[2]
kw={}
if mem>=4096: kw=dict(machine='megaste', tos=ROOT/'tos/TOS_2_06.img')
h=Hatari(snapshot=None, memsize_kb=mem, game_dir=gd, **kw)
try:
    t0=time.time()
    h.boot_to_game('M')
    print('boot_to_game ok in %.0fs'%(time.time()-t0), flush=True)
    time.sleep(3)
    out=h.debug('m $b2ff8 4',0.8); print('marker:',re.findall(r'000B2FF8:\s+(.*)',out,re.I)[-1:] )
    print('6220',hex(h.peekw(0x6220)),'700a',hex(h.peekw(0x700a)))
    out=h.debug('m $b5c00 8',0.8); print('D:',re.findall(r'000B5C00:\s+(.*)',out,re.I)[-1:])
    # blob executed? breakpoint at the cull hook
    n0=len(h._logtext())
    h.cmd("hatari-debug b pc = $b5b00 :trace :once")
    t1=time.time()
    while 'CPU breakpoint' not in h._logtext()[n0:] or 'matched' not in h._logtext()[n0:]:
        if time.time()-t1>30: break
        time.sleep(0.5)
    print('cull hook hit:', 'matched' in h._logtext()[n0:])
    p0=(h.peekw(0x66e6),h.peekw(0x66e8),h.peekw(0x66ea),h.peekw(0x66ec)); hd0=h.peekw(0x6742)
    h.rel(0,-200); h.rel(0,-200)
    time.sleep(8)
    p1=(h.peekw(0x66e6),h.peekw(0x66e8),h.peekw(0x66ea),h.peekw(0x66ec))
    print('walk: pos',p0,'->',p1)
    h.rel(120,0); time.sleep(5); h.rel(120,0); time.sleep(5)
    print('turn: heading',hd0,'->',h.peekw(0x6742))
    out=h.debug('m $b5c00 8',0.8); print('D after:',re.findall(r'000B5C00:\s+(.*)',out,re.I)[-1:])
    h.shot('/tmp/cc/cold_%d.png'%mem)
    print('done')
finally:
    h.close()
