"""Editor wedge gate: cold boot BUILD, open the editor (F10), wedge the ACIA while it is active (IERB cleared via the debugger = pending bit lost; a key is sent; IERB restored = no edge),
then press a key and count ISR entries ($384fc). usage: e1.py BUILD"""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
build = sys.argv[1]
h = boot(build, f'e1-{build}')
def vec70(): return int.from_bytes(rd(h, 0x70, 4, 0.35), 'big')
try:
    t0 = time.time()
    while time.time() - t0 < 120:
        time.sleep(2)
        if h._marker_present(): break
    time.sleep(5)
    print(build, 'marker', rd(h, 0xb0020, 4), 'sites $38486:', rd(h, 0x38486, 8).hex(), '$3853a:', rd(h, 0x3853a, 8).hex(), 'blob $7726c:', rd(h, 0x7726c, 16).hex())
    tap(h, 'F10', 0.3); time.sleep(1.5)
    print('editor active ($70 != $382d8):', hex(vec70()))
    print('sanity, ISR hits for a key in the editor:', probe(h))
    h.debug('w $fffa09 $00', 0.4)           # IERB = 0: GPIP4 disabled, its pending bit cleared
    tap(h, 'a', 0.3); time.sleep(0.5)        # make+break arrive while GPIP4 is disabled: bytes sit in the ACIA
    h.debug('w $fffa09 $40', 0.4)           # re-enable: the line is already low -> no edge
    time.sleep(1.0)
    print('after the wedge: ISR hits for the next key (0 = wedged, >=3 = healed: 1-2 stale bytes + 2 for the key):', probe(h))
    time.sleep(1.0)
    print('again:', probe(h))
    h.shot(str(G/f'work/ikbd/e1_{build}.png'))
finally:
    h.close()
