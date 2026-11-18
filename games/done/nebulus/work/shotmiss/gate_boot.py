"""Cold-boot gate: build dir, machine -> marker, site count, bytes at the sites, tower reached."""
import sys, time, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus, TOS
def rd(h, a, n):
    out = h.debug(f'm ${a:x} {n}', 0.6)
    return ' '.join(re.findall(rf'{a:08x}:\s+((?:[0-9a-f]{{2}} ?)+)', out, re.I)[-1].split())
def main(build, machine, tag):
    kw = {}
    if machine == 'megaste':
        kw = dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096)
    h = Nebulus(game=Path(build), workdir=f'/tmp/strun-shg{tag}', **kw)
    try:
        t0 = time.time()
        if machine == 'megaste':
            ok = False
            while time.time() - t0 < 300:
                time.sleep(2)
                if h._marker_present(): ok = True; break
                if time.time() - t0 > 25: h.keypress(57)
            if ok:
                time.sleep(2.0); h.key('Right', hold=0.5); time.sleep(0.5); h.key('Control_R', hold=1.0); time.sleep(4.0)
                ok = bool(h.peekw(h.TIMER))
        else:
            ok = h.boot_to_game()
        print(f'GATE {build} {machine}: in tower {ok} after {time.time()-t0:.0f}s')
        print('marker $b0020  :', rd(h, 0xb0020, 4), '(4e 45 50 4f = NEPO, 4e 45 50 46 = NEPF)')
        print('site count $b0024:', rd(h, 0xb0024, 2))
        for a, n in ((0x38514, 6), (0x3855a, 6), (0x39ffa, 2), (0x3a024, 2), (0x3a332, 2), (0x39e2c, 2), (0x3b87a, 4), (0x3dcf4, 6), (0x76c00, 12), (0x76d00, 12)):
            print(f'${a:x}:', rd(h, a, n))
        print('timer $3ad98:', rd(h, 0x3ad98, 6), ' state $33a20:', rd(h, 0x33a20, 2))
        h.shot('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss/' + f'gate_{machine}.png')
    finally:
        h.close()
main(sys.argv[1], sys.argv[2], sys.argv[3])
