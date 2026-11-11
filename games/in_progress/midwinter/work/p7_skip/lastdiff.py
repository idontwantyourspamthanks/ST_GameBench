import sys, time, json, struct
from pathlib import Path
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/tools']
from mw1 import MW1
snap, live, pre = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else '')
snap = snap if '/' in snap else f'../snapshots/1mb_ski_{snap}.sav'
h = MW1(snapshot=snap)
try:
    spec = json.loads(Path(live + '.json').read_text())
    cmds = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
    for s in spec['sites']:
        raw = bytes.fromhex(s['new'])
        for o in range(0, len(raw), 40):
            cmds.append(f"w ${s['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
    for p in pre.split(';'):
        if p.strip(): cmds.append(p.strip())
    app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
    v = h.vbl(); h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b VBL > {v+20} && pc = $bd9a :trace :once :file {app}")
    time.sleep(3)
    while h.vbl() < v + 120: time.sleep(0.5)
    prev = None
    names = {}
    for i in range(10):
        last = h.peek(0xb6040, 248)
        if prev:
            d = [o for o in range(0, 248, 2) if last[o:o+2] != prev[o:o+2]]
            print(i, 'differing word offsets in LAST', [hex(o) for o in d], [(last[o:o+2].hex()) for o in d][:8])
        prev = last
        time.sleep(0.7)
finally:
    h.close()
