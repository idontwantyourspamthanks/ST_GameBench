"""Cold boot with ACIA/IKBD trace; one tap of KEY at +DT after START's SR=$2700; show what the ACIA did."""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
variant, dt, key = sys.argv[1], float(sys.argv[2]), sys.argv[3]
tf = f'/tmp/strun-ikbd-r3-{variant}.trace'
Path(tf).unlink(missing_ok=True)
h = boot(variant, f'r3-{variant}', extra=['--trace', 'acia,ikbd_cmds,ikbd_acia,ikbd_exec', '--trace-file', tf])
try:
    ev = Path(h.R)/'ev.txt'; ev.write_text('e VBL\n')
    h.cmd(f'hatari-debug b pc = $1b172 :trace :once :file {ev}')
    m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=120, step=0.005)
    print('window start VBL', m.group(1) if m else None)
    time.sleep(dt)
    print('tap at VBL', h.vbl())
    tap(h, key, 0.08)
    time.sleep(8)
    print('ACIA status', hex(acia(h)), 'cell', rd(h,0x38498,2).hex(), 'VBL', h.vbl())
    h._xdo('keydown','--window',h.win,'a'); time.sleep(0.5)
    print('during a: cell', rd(h,0x38498,2).hex(), 'ACIA', hex(acia(h)))
    h._xdo('keyup','--window',h.win,'a'); time.sleep(0.5)
    print('after a: cell', rd(h,0x38498,2).hex(), 'ACIA', hex(acia(h)))
finally:
    h.close()
t = Path(tf).read_text(errors='replace').splitlines()
print(len(t), 'trace lines')
# keep lines after the window start
keep = [l for l in t if ('rdr' in l or 'irq' in l or 'ikbd' in l.lower() or 'received' in l or 'overrun' in l)]
print('\n'.join(keep[-60:]))
