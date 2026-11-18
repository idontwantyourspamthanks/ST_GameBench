"""Warm-boot / junk-RAM test (MiSTer does not clear RAM on a reset). Cold boot BUILD; at START's window start ($1b172, payload already loaded, game not yet depacked) overwrite
RAM with random bytes: MODE all = whole blob zone $76b10..$77ec0 (RS/V included), rs = only RS+V $77c80..$77dbf (unverified by nepatch). Then report NEPO/NEPF, whether the ISR is alive,
whether the title/editor shows, and a screenshot. usage: j1.py BUILD MODE SEED"""
import sys, random
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
build, mode, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
rng = random.Random(seed)
lo, hi = (0x76b10, 0x77ec0) if mode == 'all' else (0x77c80, 0x77dc0)
junk = bytes(rng.randrange(256) for _ in range(hi - lo))
jf = Path(f'/tmp/strun-ikbd-junk{seed}.bin'); jf.write_bytes(junk)
h = boot(build, f'j1-{build}')
try:
    ev = Path(h.R)/'ev.txt'; ev.write_text(f'loadbin {jf} ${lo:x}\ne VBL\n')
    h.cmd(f'hatari-debug b pc = $1b172 :trace :once :file {ev}')
    m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=120, step=0.005)
    t0 = time.time()
    while time.time() - t0 < 60:
        time.sleep(2)
        if h._marker_present(): break
    time.sleep(5)
    mk = rd(h, 0xb0020, 4)
    print(f'{build} mode={mode} seed={seed}: marker {mk} ({mk.decode(errors="replace") if mk else None}), sites {rd(h,0xb0024,2).hex()}, ISR hits for a key: {probe(h)}, $70={rd(h,0x70,4).hex()}, RS rsTest/rsEd/rsKey = {rd(h,0x77c80+0x2a,2).hex()} (RS+42)')
    h.shot(str(G/f'work/ikbd/j1_{build}_{mode}_{seed}.png'))
finally:
    h.close()
