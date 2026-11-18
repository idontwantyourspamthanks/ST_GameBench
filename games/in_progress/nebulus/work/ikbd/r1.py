"""Cold boot; tap space at +DT s after START's SR=$2700 (pc=$1b172); then test whether input works at the title."""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
variant, dt = sys.argv[1], float(sys.argv[2])
h = boot(variant, f'r1-{variant}')
try:
    ev = Path(h.R)/'ev.txt'; ev.write_text('e VBL\nm $fffc00 2\n')
    h.cmd(f'hatari-debug b pc = $1b172 :trace :once :file {ev}')
    m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=120)
    print('window start VBL', m.group(1) if m else None)
    time.sleep(dt)
    tap(h, 'space', 0.08)
    # wait for the title marker
    t0=time.time()
    while time.time()-t0 < 30:
        time.sleep(1.0)
        if h._marker_present():
            pass
        if time.time()-t0 > 6: break
    time.sleep(3)
    print('ACIA status $fffc00:', hex(acia(h) or 0), ' cell $38498:', rd(h,0x38498,2).hex(), 'IPRB/ISRB $fa0d-$fa11:', rd(h,0xfa0d,6).hex())
    # now hold 'a' (scancode $1e) for 1 s and sample the cell
    h._xdo('keydown','--window',h.win,'a'); time.sleep(0.5)
    c1 = rd(h,0x38498,2).hex(); st = acia(h)
    h._xdo('keyup','--window',h.win,'a'); time.sleep(0.3)
    c2 = rd(h,0x38498,2).hex()
    print(f'after holding a: cell during hold {c1} (expect 001e/1e), after release {c2} (expect 9e), ACIA status {hex(st or 0)}')
    h.shot(str(G/f'work/ikbd/r1_{variant}_{dt}.png'))
finally:
    h.close()
