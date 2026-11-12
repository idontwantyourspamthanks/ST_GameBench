"""Cold boot of a built HD set to a Raids island, then pad tests.
usage: cold.py TAG MACHINE MEM_KB BUILDDIR X Y SEQ [pad]
  MACHINE st|megast|ste|megaste|tt   BUILDDIR relative to the game dir (e.g. build/jag_a)   X Y = island hover point on the raids map
  SEQ = comma list of pad keys (see jt.py), 'pad' as last argument = the machine has pad ports (STE): expect FLAG=1; otherwise FLAG must be 2"""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
import mw2raids
from stharness import MACHINE_TOS
tag, machine, mem, bdir, x, y, seq = sys.argv[1:8]
pad = len(sys.argv) > 8 and sys.argv[8] == 'pad'
extra = PADX + (['--mmu', 'true'] if machine == 'tt' else [])
h = Hatari(snapshot=None, memsize_kb=int(mem), game_dir=G / bdir, machine=machine, tos=MACHINE_TOS[machine], extra=extra)
try:
    t0 = time.time()
    time.sleep(70 if machine == 'tt' else 25)
    ref = G / 'work' / 'ref' / 'mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): print('M/J/K screen', flush=True); break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): print('M accepted', flush=True); break
    time.sleep(45 if machine == 'tt' else 4)
    mw2raids._enter_raids_from_hall(h)
    print('raid map after %.0f s' % (time.time() - t0), flush=True)
    h.savemem(str(G / 'work/snapshots' / f'jag_{tag}_map.sav'))
    r = mw2raids.enter_raid(h, int(x), int(y))
    print(tag, 'entered', r, 'marker', memb(h, 0xb2ff8, 4), flush=True)
    time.sleep(5)
    h.savemem(str(G / 'work/snapshots' / f'jag_{tag}.sav'))
    jmode(h); time.sleep(2)
    S(h, 'J idle')
    battery(h, seq.split(','))
    d = memb(h, 0xb9ee0, 1)
    print(tag, 'FLAG', d[0], 'expected', 1 if pad else 2, 'PASS' if d[0] == (1 if pad else 2) else 'FAIL')
    be = bus_errors(h)
    print(tag, 'bus-error log lines:', be[:6])
    h.shot(str(G / 'work/jagpad' / f'{tag}_end.png'))
finally:
    h.close()
