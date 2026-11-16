import sys
from pix3 import *
dump='h_start_7a88.bin'; kind='upleft'; NP=100
A = run_frames(dump, NP, 3, False, kind)
SS = runs_(dump, NP, 3, False, kind)[1]
def find(e, sig, lo=0xb8400, n=0x1000):
    img = e.read(lo, n); i = img.find(bytes.fromhex(sig)); assert i >= 0; return lo + i
def go(tag, poke):
  try:
    _go(tag, poke)
  except Exception as ex:
    print(tag, 'CRASH', ex)
def _go(tag, poke):
    e = Emu(dump); apply_live(e); e.setb(0xB8F21, 3); poke(e)
    F = []; P = []
    for p in range(NP):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        e.setb(0xB8F08,0); e.setl(0xB8F00,36*(p+1))
        e.run(0x7a88,0xb8100); F.append(e.read(e.l(0x1008),0x7d00)); e.run(0xb8100,0x7b7a); P.append(snap_ram(e)); e.run(0x7b7a,0x7a88)
    nf = sum(1 for p in range(NP) if F[p] != A[p])
    bad = {}
    for p in range(NP):
        for a in list(range(0x1000,0x7000))+list(range(0x7000,0x19000)):
            if SS[p][a] != P[p][a] and not masked(a) and not (0x7b00<=a<0x7b80 or 0xd120<=a<0xd130): bad.setdefault(a,[]).append(p)
    print(f"{tag}: frames differing {nf}/{NP}; differing logic bytes {len(bad)} ({[f'{s:x}-{t:x}' for s,t in region_runs(sorted(bad))][:6]})")
go("baseline", lambda e: None)
def kern_off(e):
    a = find(e, '0000dafe'.replace('0000','')) ; # KTAB first entry ($dafe) -> terminate table
    e.setl(a-2 if False else a, 0)
go("NEG kernel restore off (KTAB empty)", lambda e: e.setl(find(e,'0000dafe')+2, 0))
go("NEG ring window shortened ($23c8 window 32 -> 4)", lambda e: e.setw(find(e,'23c8'+'23c6'+'03ff')+6, 4))
go("NEG HUD flag restore off ($11c4 len 12 -> 0)", lambda e: e.setw(find(e,'11c4000c')+2, 0))
go("NEG slot restore size 2688 -> 4", lambda e: None)
