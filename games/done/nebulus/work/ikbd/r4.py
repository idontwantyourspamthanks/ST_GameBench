"""Cold boot, no input until the title; then trace ACIA around one space tap (late, after the window)."""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
variant, dt, key = sys.argv[1], float(sys.argv[2]), sys.argv[3]
h = boot(variant, f'r4-{variant}')
try:
    ev = Path(h.R)/'ev.txt'; ev.write_text('e VBL\n')
    h.cmd(f'hatari-debug b pc = $1b172 :trace :once :file {ev}')
    m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=120, step=0.005)
    time.sleep(dt)
    print('ACIA before tap', hex(acia(h)), 'cell', rd(h,0x38498,2).hex())
    n0 = len(h._logtext())
    h.cmd('hatari-option --trace acia,mfp_exception,mfp_write')
    time.sleep(0.3)
    tap(h, key, 0.08)
    time.sleep(1.5)
    h.cmd('hatari-option --trace none')
    time.sleep(0.3)
    print('ACIA after tap', hex(acia(h)), 'cell', rd(h,0x38498,2).hex(), 'ISRB/IPRB', rd(h,0xfa0b,8).hex())
    txt = h._logtext()[n0:]
    lines = [l for l in txt.splitlines() if (l.startswith('acia') or l.startswith('mfp')) and not any(k in l for k in ('clock_tx','clock_rx rx_state=0','start timer','interrupt handler','ikbd acia'))]
    print(len(lines), 'acia trace lines')
    print('\n'.join(lines[:80]))
finally:
    h.close()
