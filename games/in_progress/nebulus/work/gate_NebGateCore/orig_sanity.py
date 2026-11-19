"""NebGateCore: the ORIGINAL game (originals/NEBULGX, unpatched) cold boot + play, STE 1 MB TOS 1.62."""
import sys, time, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus, ORIGIN
def rd(h,a,n):
    o=h.debug(f'm ${a:x} {n}',0.6); b=bytearray()
    for l in o.splitlines():
        m=re.match(r'^([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)',l,re.I)
        if m and int(m.group(1),16)==a: b+=bytes.fromhex(m.group(2).replace(' ',''))
    return bytes(b[:n])
h=Nebulus(workdir='/tmp/gcore-orig', game=ORIGIN)
try:
    ok=h.boot_to_game(); print('boot_to_game (timer non-zero)', ok, flush=True)
    print('marker $b0020', rd(h,0xb0020,4).hex(), '(not 4e45504f = unpatched)', ' $39ffa', rd(h,0x39ffa,2).hex(), '$3dcf4', rd(h,0x3dcf4,6).hex())
    t=[rd(h,0x3ad98,6).hex()]
    for i in range(6):
        h.key('Right',hold=1.0); h.key('Control_R',hold=0.15); time.sleep(0.5); t.append(rd(h,0x3ad98,6).hex())
    print('timer words over play', t, 'tower', rd(h,0x3390c,2).hex(), 'frog x,y,state', rd(h,0x33a16,2).hex(), rd(h,0x33a18,2).hex(), rd(h,0x33a20,2).hex())
    v0=h.vbl(); time.sleep(2); print('vbl advancing', h.vbl()>v0)
    h.shot('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebGateCore/out/orig_play.png')
    log=h._logtext(); print('crash lines', len(re.findall(r'Address error|Illegal|double bus|CPU halted', log)))
finally:
    h.close()
