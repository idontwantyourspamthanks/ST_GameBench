"""python3 pixcmp2.py DIR_A DIR_B [--k1]: compare the main frames (drawn buffer = $1008 at the first flip of the pass) pixel by pixel, by pass key.
Classes per differing frame: (1) only inside the stated mouth rect x 280-294, y 43-60 (the assignment's allowance for ta_facestat);
(2) inside the face sprite box x 272-303, y 17-64 but not only in the stated rect (the same face sprite's other pixels; bounding box printed);
(3) anything outside the face box (must be 0 for a pass).  --k1: compare pass k of A with pass k+1 of B (negative control: must differ)."""
import sys, json
import numpy as np
from pathlib import Path
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/tools")
import msrmask
def load(d):
    d = Path(d); m = json.load(open(d / "meta.json")); r = {}
    for i, e in enumerate(m):
        name = "70000" if e["back"] == 0x70000 else "78000"
        if e["pass_"] not in r: r[e["pass_"]] = msrmask.planar_to_idx((d / f"p{i:03d}_{name}.bin").read_bytes())
    return r
A, B = load(sys.argv[1]), load(sys.argv[2])
k1 = "--k1" in sys.argv
rect = np.zeros((200, 320), bool); rect[43:61, 280:295] = True
face = np.zeros((200, 320), bool); face[17:65, 272:304] = True
common = sorted(set(A) & set({k - 1 for k in B})) if k1 else sorted(set(A) & set(B))
ident = 0; c1 = 0; c2 = 0; c3 = 0; worst3 = 0; worst2 = 0; bad3 = []; bb2 = [999, -1, 999, -1]
for k in common:
    a, b = A[k], B[k + 1] if k1 else B[k]
    d = a != b
    if not d.any(): ident += 1; continue
    o3 = int((d & ~face).sum())
    o2 = int((d & face & ~rect).sum())
    if o3: c3 += 1; worst3 = max(worst3, o3); bad3.append((k, o3))
    elif o2:
        c2 += 1; worst2 = max(worst2, o2)
        ys, xs = np.where(d); bb2 = [min(bb2[0], ys.min()), max(bb2[1], ys.max()), min(bb2[2], xs.min()), max(bb2[3], xs.max())]
    else: c1 += 1
print(f"{sys.argv[1]} ({len(A)} passes) vs {sys.argv[2]} ({len(B)}){' [k vs k+1 control]' if k1 else ''}: common {len(common)} main frames; identical {ident}; "
      f"only in the stated mouth rect {c1}; in the face box beyond the stated rect {c2}" + (f" (worst {worst2} px, bbox y{bb2[0]}-{bb2[1]} x{bb2[2]}-{bb2[3]})" if c2 else "") + f"; OUTSIDE the face box {c3}" + (f" (worst {worst3} px)" if c3 else ""))
if bad3: print("   outside-face-box diffs (pass, px):", bad3[:12])
