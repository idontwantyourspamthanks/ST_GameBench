"""trace.py snap out K [--live PREFIX] [--pre 'cmd;cmd'] [--at-vbl N]
cpu_disasm trace of K whole passes of sub_014e00 ($14e00 .. next $14e00), started at the 3rd $14e00 hit after the
live set (default patch set, PREFIX.img/.json) has been applied at a flip.  Pokes in --pre are applied right after the live set."""
import sys, time, json, argparse
from pathlib import Path
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/tools']
from mw1 import MW1
ap = argparse.ArgumentParser()
ap.add_argument('snap'); ap.add_argument('out'); ap.add_argument('K', type=int)
ap.add_argument('--live'); ap.add_argument('--pre', default='')
ap.add_argument('--skipn', type=int, default=3)
ap.add_argument('--wait', type=int, default=300)
a = ap.parse_args()
h = MW1(snapshot=a.snap)
try:
    R = h.R
    on = R/'on.txt'; off = R/'off.txt'
    on.write_text(f"trace cpu_disasm\nb pc = $14e00 :{a.K} :trace :once :file {off}\n")
    off.write_text("trace none\nb all\n")
    cmds = []
    if a.live:
        spec = json.loads(Path(a.live + '.json').read_text())
        cmds.append(f"loadbin {Path(a.live + '.img').resolve()} ${spec['img_base']:x}")
        for s in spec['sites']:
            raw = bytes.fromhex(s['new'])
            for o in range(0, len(raw), 40):
                cmds.append(f"w ${s['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
    for p in a.pre.split(';'):
        if p.strip(): cmds.append(p.strip())
    cnt = f" :{a.skipn}" if a.skipn > 1 else ""
    cmds.append(f"b pc = $14e00{cnt} :trace :once :file {on}")
    app = R/'apply.txt'; app.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    v = h.vbl()
    n0 = h.logpath.stat().st_size
    h.cmd(f"hatari-debug b VBL > {v+10} && pc = $bd9a :trace :once :file {app}")
    t = time.time()
    while time.time() - t < a.wait:
        time.sleep(1)
        txt = h.logpath.read_bytes()[n0:]
        if b'trace none' in txt[-20000:] and txt.count(b'Removed CPU breakpoint') >= 3:
            break
    time.sleep(2)
    Path(a.out).write_bytes(h.logpath.read_bytes()[n0:])
    vec = h.peek(0x60, 0xe0)
    Path(a.out + '.vec').write_bytes(vec)
    print('log bytes', h.logpath.stat().st_size - n0, 'vbl', h.vbl())
finally:
    h.close()
