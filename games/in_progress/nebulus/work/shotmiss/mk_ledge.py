"""Make a Hatari snapshot with the frog standing on tower-1's ledge row 14 at x=105,y=60 (the spot in front of the 2-block stack; stack
and ball are poked per attempt).  Gentle teleport in 4-unit steps (a single big jump hangs the draw loop, trainers.md section 4)."""
import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus
W='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/'
h = Nebulus(snapshot=W+'input/snap/play_enemy.sav', workdir='/tmp/sr-led')
def pk(a): return h.peekw(a)
try:
    time.sleep(1.0)
    h.debug('w $3ad98 0 $48 0 $48 0 $48', 0.2); h.debug('w $3792c $4e $75', 0.2); h.debug('w $33944 0 0 0 0 0 0 0 0', 0.2)
    for k in range(4): h.debug('w $%x 0 0' % (0x3398c + 2*k), 0.1)
    time.sleep(0.5)
    print('start x y st', pk(0x33a16), pk(0x33a18), pk(0x33a20))
    GR=0x327f0
    saved={}
    for c,r in [(3,1),(4,1),(11,1),(13,1)]+[(13,r) for r in range(2,14)]:
        saved[(c,r)]=None
    import re
    def rb(a):
        o=h.debug('m $%x 1'%a,0.15); m=re.search(r'%08X:\s+([0-9a-f]{2})'%a,o); return int(m.group(1),16)
    for (c,r) in saved: saved[(c,r)]=rb(GR+c*256+r)
    print('saved',saved)
    for (c,r) in saved: h.debug('w $%x $81'%(GR+c*256+r),0.1)
    for x in range(8, 106, 4):
        h.debug('w $33a16 0 %d' % x, 0.12); print('x',x,pk(0x33a16),pk(0x33a18),pk(0x33a20))
    h.debug('w $33a16 0 105', 0.12)
    for y in range(12, 61, 4):
        h.debug('w $33a18 0 %d' % y, 0.12); print('y',y,pk(0x33a16),pk(0x33a18),pk(0x33a20),pk(0x33a1e))
    for (c,r),v in saved.items(): h.debug('w $%x $%x'%(GR+c*256+r,v),0.1)
    for i in range(8):
        time.sleep(0.6); print(i, 'x y st sub scroll', pk(0x33a16), pk(0x33a18), pk(0x33a20), pk(0x33a1e), pk(0x338fe), 'timer', pk(0x3ad9c))
    h.debug('w $3ad98 0 $48 0 $48 0 $48', 0.2)
    time.sleep(0.5); print('timer', [pk(a) for a in (0x3ad98,0x3ad9a,0x3ad9c)], 'run', pk(0x33938), 'st', pk(0x33a20))
    h.shot(W+'shotmiss/ledge.png')
    h.savemem(W+'shotmiss/ledge.sav')
finally:
    h.close()
