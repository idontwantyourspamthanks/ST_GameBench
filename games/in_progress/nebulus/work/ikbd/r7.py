"""Exact dist/run_ste.sh options (no --fast-boot, no --joy1 keys): cold boot BUILD, one space tap at +DT after START's window start, ISR probe at the title. usage: r7.py BUILD DT"""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
build, dt = sys.argv[1], float(sys.argv[2])
h = boot(build, f'r7-{build}', extra=['--fast-boot', 'no', '--joy1', 'none'])
try:
    ev = Path(h.R)/'ev.txt'; ev.write_text('e VBL\n')
    h.cmd(f'hatari-debug b pc = $1b172 :trace :once :file {ev}')
    m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=200, step=0.005)
    print(build, 'window start VBL', m.group(1) if m else None)
    time.sleep(dt)
    if dt >= 0: tap(h, 'space', 0.08)
    time.sleep(8)
    print(build, f'dt={dt}: marker', h._marker_present(), 'ISR hits for key a:', probe(h))
finally:
    h.close()
