"""RAM-poke proof: the tower index is read at six separate sites at level start; force each site to another tower's index independently.
Campaign LOOKS (same grid, only the record's mission/tower byte differs). Steps (at the start of level k we poke, then force the door => level k+1 starts with the poked sites):
  step A (at level 0): eye-sprite site $363a4 -> index 2          => level 1 = T2 palette/body, tower-3 eyes
  step B (at level 1): undo A; palette sites $3522e,$3dc1e -> 4   => level 2 = T3 eyes/body, tower-5 palette
  step C (at level 2): undo B; body sites $36b68,$366de -> 6      => level 3 = T4 palette/eyes, tower-7 body (texture+mask)
usage: run_poke.py BUILD_DIR OUT_DIR"""
import sys,time,struct,os
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ed import *
from pathlib import Path
import ed as _ed
_W0=_ed.W
def W(h,a):
    for _ in range(6):
        try: return _W0(h,a)
        except Exception: time.sleep(0.3)
    raise RuntimeError('W failed')
_r0=_ed.grab
build=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
RS=0x77c80
ORIG=bytes.fromhex('303900033 90c'.replace(' ',''))
def imm(n): return bytes.fromhex('303c%04x4e71'%n)
h=Nebulus(workdir='/tmp/looks/wd_poke',game=build)
def K(k,n=1,hold=0.2,gap=0.35):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def rs(): return struct.unpack('>20H',grab(h,RS,40,'rs'))
def force():
    poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
def wait_level(pos,timeout=120):
    t0=time.time()
    while time.time()-t0<timeout:
        time.sleep(1.0)
        w=rs()
        if w[1]==pos and W(h,0x33a20)==0 and W(h,0x33938)==1: return True
    return False
SITES=dict(eye=[0x363a4],pal=[0x3522e,0x3dc1e],body=[0x36b68,0x366de],tex=[0x36b68],sky=[0x366de])
def setsite(kind,n):
    for a in SITES[kind]:
        b=grab(h,a,6,'s'); assert b in (ORIG,)+tuple(imm(i) for i in range(8)), (hex(a),b.hex())
        poke(h,a,ORIG if n is None else imm(n))
def dump(i,tag):
    ok=wait_level(i); poke(h,0x76c04,bytes([0xff,0xff])); time.sleep(2.5)
    print(f"{tag}: level {i} ok={ok} tower {W(h,0x3390c)} mission {W(h,0x33910)} sites "+" ".join(f"{a:x}={grab(h,a,6,'s').hex()}" for k in SITES for a in SITES[k]),flush=True)
    d=grab(h,0,0x80000,'big'); open(out/f'{tag}.bin','wb').write(d)
    poke(h,0x76c04,bytes([0,0]))                      # enemies back on for the screenshots
    for k in range(3):
        time.sleep(2.2); h.shot(str(out/f'{tag}_e{k}.png'))
        print(f"   shot {k} states {[W(h,0x3398c+2*j) for j in range(4)]} frogst {W(h,0x33a20)}",flush=True)
    poke(h,0x76c04,bytes([0xff,0xff]))
    t0=time.time()
    while time.time()-t0<40 and not (W(h,0x33a20)==0): time.sleep(1)
try:
    print('title',h.boot_to_title(timeout=240),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down'); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=0.5)
    if len(sys.argv)>3 and sys.argv[3]=='C':      # short run: body sites only (level 0 -> level 1 = T2 palette/eyes, tower-7 body)
        dump(0,'p0'); setsite('body',6); force()
        dump(1,'pC2'); setsite('body',None)
    elif len(sys.argv)>3 and sys.argv[3]=='D':    # split the body: mask/skyline site alone (level start), then the texture site alone (acts per frame)
        dump(0,'p0'); setsite('sky',6); force()
        dump(1,'pD_sky'); setsite('sky',None); setsite('tex',6)
        time.sleep(3); h.shot(str(out/'pD_tex.png')); poke(h,0x76c04,bytes([0,0])); time.sleep(2.5); h.shot(str(out/'pD_tex_e.png')); setsite('tex',None)
    else:
        dump(0,'p0'); setsite('eye',2); force()
        dump(1,'pA'); setsite('eye',None); setsite('pal',4); force()
        dump(2,'pB'); setsite('pal',None)
finally: h.close()
