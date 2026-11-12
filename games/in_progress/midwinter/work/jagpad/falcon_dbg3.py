import time, re
from jlib import *
h = MW1(snapshot=None, game_dir=str(GAME/'build'/'jag'), machine='falcon', memsize_kb=4096, extra=PAD)
try:
    h.boot_to_options(timeout=300)
    items=[(0xb6bf0, 8), (0x24f98, 8), (0x24fba, 2), (0x12c98, 2), (0x15110, 2), (0x15112, 2), (0x12d5e, 4),(0x1efde, 2), (0x2c324, 4), (0x2c176, 6), (0x24faa, 8), (0x24fa2, 8), (0xb2ff8, 4)]
    f = h.R/'s.txt'; f.write_text('e VBL\n'+''.join(f'm ${a:x} {n}\n' for a,n in items))
    n = len(h._logtext()); h.cmd(f'hatari-debug parse {f}'); time.sleep(4)
    print(h._logtext()[n:])
finally:
    h.close()
