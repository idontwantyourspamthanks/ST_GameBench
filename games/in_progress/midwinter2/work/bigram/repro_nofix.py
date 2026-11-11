"""Reproduce the hang on the pre-fix build (staging, no pp_bigram_cache) and show the $B3000 wipe."""
import sys, time, re
from pathlib import Path
sys.path.insert(0,'tools')
from mw2harness import Hatari
h = Hatari(snapshot=None, memsize_kb=4096, game_dir=Path(sys.argv[1]), machine='megaste',
           tos=Path('tos/TOS_2_06.img').resolve(), extra=['--trace', 'gemdos'])
try:
    h.cmd('hatari-debug b all'); time.sleep(0.3)
    h.cmd('hatari-debug b ($b3004).l ! ($b3004).l :trace'); time.sleep(0.5)
    time.sleep(25)
    ref = Path('work/ref/mode_select.png')
    for i in range(14):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): print('M/J/K reached at poll', i); break
    else: print('M/J/K NOT reached after 14 polls (~100 s)')
    print(h.debug('m $b2ff8 4').strip().splitlines()[-1])
    print(h.debug('m $b3000 16').strip().splitlines()[-1])
    h.shot(Path('work/bigram/repro_nofix.png'))
    t = h._logtext()
    for m in re.finditer(r'.*(\$b3004|b3004).*', t): print(m.group(0))
    print('\n'.join(l for l in t.splitlines() if 'Fread' in l and '0x81000' in l))
finally:
    h.close()
