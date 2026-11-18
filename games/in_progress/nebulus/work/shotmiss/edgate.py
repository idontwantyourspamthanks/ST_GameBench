"""F10/D editor-manager entry gate with the current default set (np_lift included), cold boot. Model: work/editor/e170.py.
usage: edgate.py GAMEDIR WORKDIR [ste|megaste]"""
import sys, struct
ELIB = "/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor"
sys.path.insert(0, ELIB)
from ed import *
gd = __import__('pathlib').Path
GAMEDIR, WD = sys.argv[1], sys.argv[2]
MACH = sys.argv[3] if len(sys.argv) > 3 else 'ste'
kw = dict(machine='megaste', tos=__import__('stharness').TOS['2.06'], memsize_kb=4096) if MACH == 'megaste' else {}
h = Nebulus(workdir=WD, game=gd(GAMEDIR), **kw)
fails = []
def chk(n, g, e):
    ok = g == e
    print(('PASS ' if ok else 'FAIL ') + n + ': ' + repr(g) + ('' if ok else ' expected ' + repr(e)), flush=True)
    if not ok: fails.append(n)
def vblvec(): return struct.unpack('>L', grab(h, 0x70, 4, 'v'))[0]
try:
    print('title', h.boot_to_title(timeout=240), flush=True); time.sleep(3)
    m = grab(h, 0xb0020, 8, 'mk')
    print('marker/count', m[:4], struct.unpack('>H', m[4:6])[0], '| $37c42', grab(h, 0x37c42, 14, 'nl').hex())
    chk('marker NEPO', m[:4], b'NEPO')
    chk('hook $3851a -> jmp', grab(h, 0x3851a, 2, 'a').hex(), '4ef9')
    chk('hook $3d662 -> jmp', grab(h, 0x3d662, 2, 'b').hex(), '4ef9')
    chk('CODE1 jump table $75740', grab(h, 0x75740, 2, 'c').hex(), '4ef9')
    chk('np_shot site $3b87a', grab(h, 0x3b87a, 4, 'ns').hex(), '66084880')
    chk('trainer blob $76c08', grab(h, 0x76c08, 2, 'e').hex(), '4eb9')
    chk('VBL vector normal', hex(vblvec()), '0x382d8')
    h.key('F10', hold=0.1); time.sleep(2); v = vblvec()
    chk('F10 (100 ms) opens the manager (VBL vector leaves $382d8)', v != 0x382d8, True)
    h.shot(f'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss/sh_edgate_{MACH}_manager.png')
    h.key('F10', hold=0.1); time.sleep(2.5)
    chk('F10 (100 ms) leaves again', vblvec(), 0x382d8)
    time.sleep(1); h.key('d', hold=0.1); time.sleep(2); v = vblvec()
    chk('D (100 ms) opens the manager', v != 0x382d8, True)
    h.shot(f'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss/sh_edgate_{MACH}_manager_D.png')
    h.key('F10', hold=0.1); time.sleep(2.5)
    chk('F10 leaves the D-opened manager', vblvec(), 0x382d8)
    h.key('F10', hold=0.1); time.sleep(2.0)
    chk('F10 re-enters', vblvec() != 0x382d8, True)
    h.key('F10', hold=0.1); time.sleep(2.5)
    chk('and leaves again', vblvec(), 0x382d8)
finally:
    print('FAILS', fails)
    h.close()
