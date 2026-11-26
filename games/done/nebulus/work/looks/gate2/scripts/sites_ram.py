"""Live RAM check of a build: boot to the title, read every patch site (+ the credit blob at $779FA) from the running game and compare with the build's site table
(BUILD.json: addr / new bytes).  Covers np_lift ($37c42..$37d90) and np_shot ($3b87a) sites in the merged build.   usage: sites_ram.py BUILD_DIR [ste|megaste|st]"""
import sys, json, time
sys.path.insert(0, '/tmp/nlg/games/in_progress/nebulus/work/editor')
from ed import *
from pathlib import Path
import stharness
B, M = sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'ste'
kw = {'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if M == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if M == 'st' else {}
sites = json.load(open(B + '.json'))['sites']
h = Nebulus(workdir='/tmp/nlg/x/wd_sites_' + M, game=Path(B), **kw); bad = 0
try:
    print('title', h.boot_to_title(timeout=240), flush=True); time.sleep(3)
    print('marker', grab(h, 0xB0020, 4, 'm'))
    for s in sites:
        n = len(bytes.fromhex(s['new'])); got = grab(h, s['addr'], n, 's'); ok = got == bytes.fromhex(s['new']); bad += not ok
        print(('PASS' if ok else 'FAIL'), f"site ${s['addr']:06x} new {s['new']} RAM {got.hex()}", flush=True)
    cb = grab(h, 0x779fa, 64, 'c'); print('credit blob $779FA:', cb[:12].hex(), b'enhanced by dad_prg' in cb)
    print('SITES FAILS', bad)
finally:
    h.close()
