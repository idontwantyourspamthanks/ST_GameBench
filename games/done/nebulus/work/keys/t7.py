"""t7.py machine: game start with --joy1 keys, F10/D in a tower do nothing, latch cleared, quit to title, no stale open, F10 then opens."""
import os, sys, time
from kh import KH
from stharness import TOS
IMG=os.environ['IMG']; mach=sys.argv[1] if len(sys.argv)>1 else 'ste'
wd=f'/tmp/nf/t7_{mach}'
if mach=='megaste': h=KH(IMG, workdir=wd, machine='megaste', tos=TOS['2.06'], mem=4096, auto=r'C:\NEBULUS\START.TOS', joy=True)
else: h=KH(IMG, workdir=wd, auto=r'C:\NEBULUS\START.TOS', joy=True)
while '48 69 67 68' not in h.debug('m $3d00f 4',0.25): time.sleep(1.5)
print('title at', round(time.time()-h.t0), 's;', 'marker', h.debug('m $b0020 8',0.3).strip().splitlines()[-1])
print('$4ba twice:', h.peekl(0x4ba), end=' '); time.sleep(1); print(h.peekl(0x4ba))
time.sleep(2)
h.tap('Right',0.5); time.sleep(0.5); h.tap('Control_R',1.0); time.sleep(5)
tm=lambda: tuple(h.peekw(0x3ad98+2*i) for i in range(3))
print('tower timer', tm(), 'state $33a20', h.peekw(0x33a20), 'tower', h.peekw(0x3390c))
for k in ('F10','d','F10','d'):
    h.tap(k,0.1); time.sleep(0.6)
print('after F10/d/F10/d in tower: $70', hex(h.peekl(0x70)), 'rsKey', hex(h.peekw(0x77caa)), 'timer', tm())
h.shot('/tmp/nf/t7_tower.png')
time.sleep(1); print('timer later', tm())
# quit to title with Q (game key)
h.tap('q',0.3); time.sleep(0.3)
time.sleep(5)
time.sleep(4)
print('title? page', h.peekw(0x3d5b6), 'timer', tm(), '$70', hex(h.peekl(0x70)), 'rsKey', hex(h.peekw(0x77caa)))
h.shot('/tmp/nf/t7_title.png')
h.tap('F10',0.1); time.sleep(1.5)
print('F10 on title: $70', hex(h.peekl(0x70)))
h.shot('/tmp/nf/t7_mgr.png')
h.close()
