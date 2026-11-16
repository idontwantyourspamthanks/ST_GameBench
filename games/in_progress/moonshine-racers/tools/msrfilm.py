#!/usr/bin/env python3
"""Draw-order film strip of one frame: save both screen buffers after every call of the frame loop and of $ef7a, then report
which call changed which pixels (bounding box) and build a contact sheet.

    python3 tools/msrfilm.py work/snapshots/ste1m_race_start.sav work/film [--drive]
Chain of `b pc = <return address of each jsr/bsr> :trace :once :file` breakpoints (each stage file saves $70000/$78000 and arms the
next), so the whole film is one frame.  Output: work/shots/film/*.png, work/shots/film_sheet.png, bbox list on stdout."""
import argparse, glob, hashlib, os, re, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME
import planar
from PIL import Image

BENCH = GAME.parent.parent.parent
DUMP = GAME / "work/dumps/ram_race_up.bin"
ap = argparse.ArgumentParser(); ap.add_argument("snap"); ap.add_argument("out"); ap.add_argument("--drive", action="store_true")
a = ap.parse_args()
out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*.bin"): f.unlink()

def dis(x, y):
    return subprocess.run([sys.executable, str(BENCH / "tools/m68dis.py"), str(DUMP), x, "--end", y], capture_output=True, text=True).stdout
rets = []
for ln in (dis("7a88", "7b72") + dis("ef7a", "efc6")).splitlines():
    m = re.match(r"([0-9a-f]{6}):\s+([0-9a-f]+)\s+(jsr|bsr)", ln)
    if m: rets.append((int(m.group(1), 16), int(m.group(1), 16) + len(m.group(2)) // 2))
main = [r for x, r in rets if 0x7a88 <= x < 0x7b80]; ef = [r for x, r in rets if 0xef7a <= x < 0xefc6]
seq = [r for r in main if r <= 0x7b4c] + ef + [r for r in main if r > 0x7b4c]
h = Moonshine(snapshot=a.snap)
try:
    time.sleep(3)
    if a.drive: h.drive(True)
    for i, r in enumerate(seq):
        lines = [f"savebin {out}/{i:02d}_{r:x}_70.bin $70000 $7d00", f"savebin {out}/{i:02d}_{r:x}_78.bin $78000 $7d00"]
        if i + 1 < len(seq): lines.append(f"b pc = ${seq[i + 1]:x} :trace :once :file {h.R}/film_{seq[i + 1]:x}.txt")
        (h.R / f"film_{r:x}.txt").write_text("\n".join(lines) + "\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${seq[0]:x} :trace :once :file {h.R}/film_{seq[0]:x}.txt")
    time.sleep(10)
finally:
    h.close()
cand = {w: sorted(out.glob(f"*_{w}.bin")) for w in ("70", "78")}
nd = {w: len({hashlib.md5(f.read_bytes()).hexdigest() for f in fs}) for w, fs in cand.items()}
back = max(nd, key=nd.get)          # the buffer being drawn changes from stage to stage, the displayed one does not
files = cand[back]
print(len(files), "stages; back buffer $%s000 (distinct states 70: %d, 78: %d)" % (back[0] + "0" if back == "70" else "78", nd["70"], nd["78"]))
shots = GAME / "work/shots/film"; shots.mkdir(parents=True, exist_ok=True)
stages = [(f.name[:-7], f.read_bytes()[:32000]) for f in files]   # name = <stage>_<pc>
last = None; distinct = []; prev = None
for n, d in stages:
    hsh = hashlib.md5(d).hexdigest()
    if hsh != last:
        if prev is not None:
            rows = [o // 160 for o in range(32000) if d[o] != prev[o]]; cols = [(o % 160) // 8 * 16 for o in range(32000) if d[o] != prev[o]]
            print(f"-> {n}: {len(rows)} bytes differ vs previous distinct stage; rows {min(rows)}-{max(rows)}, x {min(cols)}-{max(cols) + 15}")
        distinct.append((n, d)); prev = d
    last = hsh
W = 3; H = (len(distinct) + W - 1) // W
sheet = Image.new("RGB", (320 * W, 200 * H))
for i, (n, d) in enumerate(distinct):
    im = planar.decode(d); im.save(shots / f"{n}.png"); sheet.paste(im, ((i % W) * 320, (i // W) * 200))
sheet.save(GAME / "work/shots/film_sheet.png")
