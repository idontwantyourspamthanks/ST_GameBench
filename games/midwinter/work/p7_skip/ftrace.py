"""ftrace.py snap live vbls: apply live at (restore VBL + 20) like gatew --soon, then log (vbl,x,z,speed,heading) per flip"""
import sys, time, json
from pathlib import Path
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/midwinter/tools']
from mw1 import MW1
snap, live, vbls = sys.argv[1], sys.argv[2], int(sys.argv[3])
snap = snap if '/' in snap else f'../snapshots/1mb_ski_{snap}.sav'
h = MW1(snapshot=snap)
try:
    spec = json.loads(Path(live + '.json').read_text())
    cmds = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
    for s in spec['sites']:
        raw = bytes.fromhex(s['new'])
        for o in range(0, len(raw), 40):
            cmds.append(f"w ${s['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
    app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
    v = h.vbl()
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b VBL > {v+20} && pc = $bd9a :trace :once :file {app}")
    time.sleep(3)
    while h.vbl() < v + 25: time.sleep(0.3)
    for r in h.flip_trace(vbls): print(*r)
finally:
    h.close()
