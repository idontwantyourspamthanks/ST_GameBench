"""Editor wedge gate v2: cold boot BUILD, open the editor (F10), hijack the editor's next poll call ($3853a) with work/ikbd/wedge.bin (creates the stall state), send a key, then count ISR entries
and probe a later key. usage: e1b.py BUILD"""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
build = sys.argv[1]
h = boot(build, f'e1b-{build}')
def vec70(): return int.from_bytes(rd(h, 0x70, 4, 0.35), 'big')
try:
    t0 = time.time()
    while time.time() - t0 < 120:
        time.sleep(2)
        if h._marker_present(): break
    time.sleep(5)
    print(build, 'marker', rd(h, 0xb0020, 4), 'poll entry $3853a:', rd(h, 0x3853a, 8).hex())
    tap(h, 'F10', 0.3); time.sleep(1.5)
    print('editor active ($70 != $382d8):', hex(vec70()), '| sanity, ISR entries for a key in the editor:', probe(h))
    cmds = Path(h.R) / 'wedge_cmds.txt'; cmds.write_text('r pc=$b8000\n')
    h.debug('b all', 0.3)
    h.debug('loadbin /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd/wedge.bin $b8000', 0.5)
    n0 = len(h._logtext())
    h.cmd('hatari-debug b pc = $384fc :trace'); time.sleep(0.2)
    h.cmd(f'hatari-debug b pc = $3853a :trace :once :file {cmds}'); time.sleep(0.6)
    tap(h, 'a', 0.15); time.sleep(1.5)
    txt = h._logtext()[n0:]
    print('hijack fired:', 'pc = $3853a' in txt, '| game ISR entries since the wedge (control: 0 = wedged; with ni_ikbd: >=1 = the watchdog ran the real handler):', len(re.findall(r'pc = \$384fc', txt)))
    h.debug('b all', 0.3)
    print('later key: ISR entries', probe(h), '(2 = input works)')
    time.sleep(1.0); print('again:', probe(h))
    print('editor still active:', hex(vec70()))
    h.shot(str(G/f'work/ikbd/e1b_{build}.png'))
finally:
    h.close()
