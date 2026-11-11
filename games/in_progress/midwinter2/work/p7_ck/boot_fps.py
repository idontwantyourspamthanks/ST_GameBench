#!/usr/bin/env python3
"""Cold boot, then alternate cull sites live / reverted while standing and walking: flips per 1000 VBL.
    python3 work/p7_ck/boot_fps.py MACHINE TOS MEM_KB GAME_DIR"""
import sys, json, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
machine, tos, mem, game = sys.argv[1:5]
TOS = {'206': ROOT / 'tos/TOS_2_06.img', '162': Path.home() / 'Emulators/BIOS/AtariST/TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img'}
sites = [s for s in json.load(open('/tmp/ck/p4_all.json'))['sites'] if s['name'] in ('p7_ck_poly', 'p7_ck_obj', 'p7_ck_fill')]
h = Hatari(snapshot=None, memsize_kb=int(mem), game_dir=ROOT / game, machine=machine, tos=TOS[tos])
def setsites(key):
    for s in sites: h.debug(f"w ${s['addr']:x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(s[key])), 0.3)
try:
    h.boot_to_game('M'); h.center(); time.sleep(3)
    print('standing:')
    for key in ('new', 'orig', 'new', 'orig'):
        setsites(key); time.sleep(2); f = h.fps(1000); print(' ', 'cull live' if key == 'new' else 'reverted ', f['flips'], 'flips/1000 VBL', flush=True)
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(5)
    print('walking:')
    for key in ('new', 'orig', 'new', 'orig'):
        setsites(key); time.sleep(2); f = h.fps(1000); print(' ', 'cull live' if key == 'new' else 'reverted ', f['flips'], 'flips/1000 VBL', 'pos', hex(h.peekw(0x66e8)), flush=True)
finally:
    h.close()
