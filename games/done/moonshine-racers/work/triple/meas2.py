"""Latch-wait / idle measurement of the extra frames (Hatari, STE 8 MHz): python3 meas.py SNAP LIVEPREFIX MHZ NPASS OUT.json
Persistent trace breakpoints (each :file prints `e $tag`, `e VBL`, `e FrameCycles`):
 1 loop top $796a   2 render start $7a88   3 main flip entry $b8100   4 any flip $d1ca   5 extra flip $b867c   6 extra start $b8604
 7 extra latch-wait loop $b862e   8 first road write $17c42 (main + extras)   9 main latch guard $b8200
 10 VBL latch (VBL ISR $b8006 with PEND != 0)   11 tick end $b816a (m NEXTRA, $100e, DEXT)
Steering: zig = up / up+left / up / up+right, 15 passes each, a pure function of $100e (as work/tint/steer_int.py mode=pass)."""
import sys, json, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint')
from mxlib_int import *
import msrabtest as ab
from msr import Moonshine
from pathlib import Path
snap, livep, mhz, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
pokes = [a[5:] for a in sys.argv[6:] if a.startswith('poke=')]
vals, per = [0x01, 0x05, 0x01, 0x09], 15
live = Path(livep)
if pokes: live = ab.with_pokes(live, pokes, 't3_' + out.split('/')[-1].replace('.json', ''))
h = Moonshine(snapshot=ab.snap_path(snap))
R = h.R
EV = {1: 0x796a, 2: 0x7a88, 3: 0xb8100, 4: 0xd1ca, 5: 0xb867c, 6: 0xb8604, 7: 0xb862e, 8: 0x17c42, 9: 0xb8200, 11: 0xb816a,
      20: 0xb8a46, 21: 0xb85f0, 22: 0xb861a, 23: 0xb8620, 24: 0xb863c, 25: 0xb8648, 26: 0xb866c, 27: 0xb8672, 28: 0xb8678, 30: 0xb8ab6, 31: 0xb8710, 32: 0xb8400}
try:
    time.sleep(1.5)
    ab.apply_live(h, live, 0x7A88)
    if mhz: h.set_cpuclock(mhz)
    time.sleep(0.4); h.debug('b all', 0.3)
    for t, pc in EV.items():
        extra = "m $b8f32 2\nm $100e 2\nm $b8f24 2\nm $11ab 1\n" if t == 11 else ""
        (R / f'ev{t}.txt').write_text(f"e ${t:x}\ne VBL\ne FrameCycles\n{extra}")
    for K in range(0, 4000):
        (R / f'z_{K}.txt').write_text(f"w $6105 ${vals[(K // per) % len(vals)]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {R}/z_{K + 1}.txt\n")
    n0 = len(h._logtext())
    for t, pc in EV.items():
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {R}/ev{t}.txt"); time.sleep(0.15)
    K0 = h.peekw(0x100e) + 25
    h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${K0:x} :trace :once :file {R}/z_{K0}.txt"); time.sleep(0.2)
    h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = 1 :trace :file {R}/z_1.txt")
    t0 = time.time()
    while h._logtext()[n0:].count('> e $b\n') < npass and time.time() - t0 < 3400: time.sleep(2)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
open(out + '.log', 'w').write(log)
print(len(log))
