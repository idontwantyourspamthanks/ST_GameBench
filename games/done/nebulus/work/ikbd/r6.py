"""Evidence: ACIA trace of the stall. Restore the pre-window snapshot, trace ACIA+MFP-exception from the window start for ~3 s, tap space at +0.4 s. Print the relevant lines."""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
variant = sys.argv[1]
h = boot(variant, '', snapshot=str(G/f'work/ikbd/snap_{variant}.sav'))
try:
    ev = Path(h.R)/'ev.txt'; ev.write_text('e VBL\n')
    h.cmd(f'hatari-debug b pc = $1b172 :trace :once :file {ev}')
    m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=60, step=0.005)
    # also report when the game's handler is installed / interrupts enabled
    ev2 = Path(h.R)/'ev2.txt'; ev2.write_text('e VBL\n')
    h.cmd(f'hatari-debug b pc = $38486 :trace :once :file {ev2}')
    n0 = len(h._logtext())
    h.cmd('hatari-option --trace acia,mfp_exception')
    time.sleep(0.4); tap(h, 'space', 0.08)
    time.sleep(4.0)
    h.cmd('hatari-option --trace none'); time.sleep(0.5)
    print('ISR hits for a later key (a):', probe(h))
finally:
    h.close()
txt = (Path(h.R)/'log.txt').read_text(errors='replace')
keep=[]
for l in txt.splitlines():
    if re.match(r'acia ikbd (clock_rx received|clock_rx overrun|update irq|read rdr|read sr)', l) or ('mfp iack' in l and ('0x118' in l)) or re.match(r'= .*\(dec\)', l) or l.startswith('mfp write') and ('fffa09' in l or 'fffa13' in l or 'fffa15' in l or 'fffa11' in l):
        keep.append(l[:150])
print('\n'.join(keep[:60]))
