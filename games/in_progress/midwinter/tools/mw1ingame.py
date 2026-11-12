"""Boot a build into the ski 3D view (tools/mw1.py boot_to_game), print marker and walk, savebin RAM.

    python3 tools/mw1ingame.py NAME MACHINE TOS MEM_KB GAME_DIR      # dumps /tmp/mw1/ig_NAME.bin, ig2_NAME.bin (after a walk)
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mw1  # noqa: E402
from mw1 import MW1  # noqa: E402

name, machine, tos, mem, game = sys.argv[1:6]
Path("/tmp/mw1").mkdir(exist_ok=True)
h=MW1(game_dir=Path(game).resolve(),memsize_kb=int(mem),machine=machine,tos=mw1.TOS[tos])
try:
    h.boot_to_game('M')
    print(name,'in 3D view:',h.gstate(),flush=True)
    print(name,'marker:',h.debug('m $b2ff8 4').strip().splitlines()[-1])
    h.debug(f'savebin /tmp/mw1/ig_{name}.bin 0 {min(int(mem)*1024,0x400000)}',wait=4)
    h.shot(f'/tmp/mw1/ig_{name}.png')
    # walk a little
    s0=h.gstate(); h.walk(); time.sleep(8); s1=h.gstate()
    print(name,'walk:',s0['x'],s0['z'],'->',s1['x'],s1['z'],'speed',s1['speed'],flush=True)
    h.debug(f'savebin /tmp/mw1/ig2_{name}.bin 0 {min(int(mem)*1024,0x400000)}',wait=4)
finally:
    h.close()
