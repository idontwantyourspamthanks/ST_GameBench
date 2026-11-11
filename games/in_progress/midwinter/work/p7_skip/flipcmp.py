"""flipcmp.py snap base_live patched_live [--pre ..] [--at-offset N] [--upto 9]: apply like gatew --soon, capture flips 2..upto (drawn buffer, inputs,
GEN/GENB) in both runs (2 instances) and print per flip: inputs equal?, drawn window equal?"""
import sys, time, json, argparse, struct
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/tools']
from mw1 import MW1
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/tools')
import mw1ab
ap = argparse.ArgumentParser(); ap.add_argument('snap'); ap.add_argument('base'); ap.add_argument('sk')
ap.add_argument('--pre', default=''); ap.add_argument('--upto', type=int, default=9); ap.add_argument('--soon', type=int, default=280)
a = ap.parse_args()
sp = mw1ab.snap_path(a.snap); at = mw1ab.at_vbl_for(sp) - a.soon
INPUTS = [(0x12c60, 0x24), (0x12c98, 2), (0x157a8, 2), (0x159a0, 4), (0x171f0, 0x2e), (0x19cd4, 4), (0x1d418, 2), (0x1d816, 6), (0x1cd64, 4), (0x12d54, 2), (0x1cd7e, 0xb0), (0xb3700, 12)]
def cap(live, tag):
    out = Path(f'/tmp/p7s/fc_{tag}'); out.mkdir(exist_ok=True)
    for f in out.glob('*'): f.unlink()
    h = MW1(snapshot=str(sp))
    try:
        spec = json.loads(Path(live + '.json').read_text())
        cmds = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
        for s in spec['sites']:
            raw = bytes.fromhex(s['new'])
            for o in range(0, len(raw), 40):
                cmds.append(f"w ${s['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
        for p in a.pre.split(';'):
            if p.strip(): cmds.append(p.strip())
        for k in range(2, a.upto + 1):
            cf = h.R / f'c{k}.txt'
            lines = [f"savebin {out}/{k}_in{j}.bin ${ad:x} ${ln:x}" for j, (ad, ln) in enumerate(INPUTS)]
            lines += [f"savebin {out}/{k}_tab.bin $2c376 4", f"savebin {out}/{k}_d.bin $b6000 $10"]
            lines += [f"savebin {out}/{k}_b{n}.bin ${ad:x} $7d00" for n, ad in (('58', 0x58000), ('68', 0x68000), ('78', 0x78000))]
            lines += [f"savebin {out}/{k}_done.bin $b6000 4"]
            cf.write_text("\n".join(lines) + "\n")
            cmds.append(f"b pc = $bd9a :{k} :trace :once :file {cf}")
        app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b VBL > {at} && pc = $bd9a :trace :once :file {app}")
        t = time.time()
        while not (out / f'{a.upto}_done.bin').exists():
            if time.time() - t > 300: raise TimeoutError
            time.sleep(0.5)
        time.sleep(1)
    finally:
        h.close()
    return out
with ThreadPoolExecutor(2) as ex:
    fb = ex.submit(cap, a.base, 'base'); fs = ex.submit(cap, a.sk, 'sk')
    ob, os_ = fb.result(), fs.result()
for k in range(2, a.upto + 1):
    ib = b''.join((ob / f'{k}_in{j}.bin').read_bytes() for j in range(len(INPUTS)))
    is_ = b''.join((os_ / f'{k}_in{j}.bin').read_bytes() for j in range(len(INPUTS)))
    tb = struct.unpack('>I', (ob / f'{k}_tab.bin').read_bytes())[0]; ts = struct.unpack('>I', (os_ / f'{k}_tab.bin').read_bytes())[0]
    res = []
    for n in ('58', '68', '78'):
        x = np.fromfile(ob / f'{k}_b{n}.bin', dtype=np.uint8).reshape(200, 160)[51:182]; y = np.fromfile(os_ / f'{k}_b{n}.bin', dtype=np.uint8).reshape(200, 160)[51:182]
        res.append(int((x != y).sum()))
    d = (os_ / f'{k}_d.bin').read_bytes()
    print(f'flip {k}: drawn buffer base {tb:#x} patched {ts:#x}; inputs {"EQUAL" if ib == is_ else "differ"}; window diff bytes per buffer (58,68,78) {res}; patched D: GEN {struct.unpack(">H", d[4:6])[0]} GENB {struct.unpack(">3H", d[6:12])}')
