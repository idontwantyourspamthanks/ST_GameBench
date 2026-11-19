"""t4.py SCEN [machine]: A = mash F9/F10 taps (100 ms) every 2 s during the whole load, then F10 at the title; B = F9 at the title only"""
import os, sys, time
from kh import KH
from stharness import TOS
IMG=os.environ.get('IMG','/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-18.img')
sc=sys.argv[1]; mach=sys.argv[2] if len(sys.argv)>2 else 'ste'
wd=os.environ.get('WD','/tmp/nf/t4'+sc)
if mach=='megaste': h=KH(IMG, workdir=wd, machine='megaste', tos=TOS['2.06'], mem=4096, auto=r'C:\NEBULUS\START.TOS')
else: h=KH(IMG, workdir=wd, auto=r'C:\NEBULUS\START.TOS')
def mark(): return '48 69 67 68' in h.debug('m $3d00f 4',0.25)
n=0
if sc=='A':
    t=time.time()
    while not mark():
        k='F9' if n%2==0 else 'F10'
        h.tap(k,0.1); n+=1; time.sleep(1.7)
    print('title after', round(time.time()-h.t0), 'taps', n)
    time.sleep(3)
    print('vbl70', hex(h.peekl(0x70)), 'rsKey', hex(h.peekw(0x77cAA)) )
    h.tap('F10',0.1); time.sleep(1.5)
    print('after F10: $70', hex(h.peekl(0x70)))
    h.shot('/tmp/nf/t4A_f10.png')
else:
    while not mark(): time.sleep(1.5)
    time.sleep(4)
    print('before: $70', hex(h.peekl(0x70)))
    h.shot('/tmp/nf/t4B_before.png')
    h.tap('F9',0.1)
    for i,dt in enumerate((3,7,10,20)):
        time.sleep(dt); h.shot(f'/tmp/nf/t4B_after{i}.png'); print(i, hex(h.peekl(0x70)))
    print('after F9 100ms: $70', hex(h.peekl(0x70)), 'marker', h.debug('m $3d00f 4',0.3).strip().splitlines()[-1])
h.close()
