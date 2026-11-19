"""t8.py NF9 [machine]: title -> NF9 x F9 taps (100 ms, 0.5 s apart) -> (TOS reboots, --auto restarts START) -> second title -> NEPO? -> F10"""
import os, sys, time
from kh import KH
from stharness import TOS
IMG=os.environ.get('IMG','/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-18.img')
n9=int(sys.argv[1]); mach=sys.argv[2] if len(sys.argv)>2 else 'ste'
wd=os.environ.get('WD',f'/tmp/nf/t8_{n9}_{mach}')
if mach=='megaste': h=KH(IMG, workdir=wd, machine='megaste', tos=TOS['2.06'], mem=4096, auto=r'C:\NEBULUS\START.TOS')
else: h=KH(IMG, workdir=wd, auto=r'C:\NEBULUS\START.TOS')
def mark(): return '48 69 67 68' in h.debug('m $3d00f 4',0.25)
def snap(tag):
    h.debug(f'savebin {wd}/r_{tag}.bin 0 $100000',3.0)
    d=open(f'{wd}/r_{tag}.bin','rb').read()
    L=lambda a:int.from_bytes(d[a:a+4],'big')
    print(f'[{tag}] marker@b0020 {d[0xb0020:0xb0024]} count {int.from_bytes(d[0xb0024:0xb0026],"big")} | phystop $42e {L(0x42e):#x} memtop $436 {L(0x436):#x} | $118 {L(0x118):#x} $70 {L(0x70):#x} | $3851a {d[0x3851a:0x3851e].hex()} | $38498 {d[0x38498]:#x} rsKey {int.from_bytes(d[0x77caa:0x77cac],"big"):#x} | PPGX@80000 {d[0x80000:0x80004]} | $200 {d[0x200:0x206].hex()} | $3850c {d[0x3850c:0x38512].hex()}')
while not mark(): time.sleep(1.5)
time.sleep(3); print('title 1 at', round(time.time()-h.t0)); snap('t1')
for i in range(n9):
    h.tap('F9',0.1); time.sleep(0.5)
t=time.time(); seen=False
while time.time()-t<200:
    time.sleep(3)
    m=mark()
    if not m: seen=True
    if seen and m: break
print('title 2', 'reached' if seen and m else 'NOT reached', round(time.time()-t),'s after F9')
time.sleep(4); snap('t2')
h.shot(f'/tmp/nf/t8_{n9}_title2.png')
h.tap('F10',0.1); time.sleep(1.5)
print('F10 on 2nd title: $70', hex(h.peekl(0x70)), '(editor $75a.. / game $382d8)')
h.close()
