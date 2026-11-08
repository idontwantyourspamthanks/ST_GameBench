#!/usr/bin/env python3
"""P7 cell-cull view-variation gate: p4 baseline vs p4 + patches with the camera angles poked.

    python3 work/p7_cell_poke.py [--snapshot S ...] [--mine p7_cell_pre p7_cell_cull] [--flips 4]

The snapshots only show a few headings. At the first flip after an absolute VBL both runs apply the same live
patch set (base: p4, mine: p4 + --mine) and write the same camera angles (heading $6742, mirrored to $6294 and
$764a; bank $6746; pitch $674a, 10-bit angle words as the game keeps them), then save both screen buffers
`--flips` flips later (the simulation is per frame, so both runs show the same frame).  Compare md5.
Max two Hatari instances at a time.
"""
import argparse, hashlib, json, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari  # noqa: E402

P4 = ["p4_grid", "p4_hud_pfx_fill", "p4_hud_pfx_replay", "p4_hud_pfx_ymin", "p4_hud_reset",
      "p4_proj_axis", "p4_proj_cols", "p4_proj_div", "p4_walk", "p4_walk_c4", "p4_walk_ret", "p4_walk_tab"]
SNAPS = [("work/snapshots/1mb_ingame_walking.sav", 21500), ("work/snapshots/1mb_ingame_foot.sav", 17900),
         ("work/snapshots/ingame_foot_banked_turn.sav", 419400)]
# (heading, bank, pitch); angles are 10-bit (1024 = full turn), kept even by the game
ANGLES = [(0, None, None), (34, None, None), (100, None, None), (170, None, None), (256, None, None),
          (390, None, None), (512, None, None), (610, None, None), (768, None, None), (850, None, None),
          (940, None, None), (1002, None, None),
          (128, 40, None), (128, 984, None), (300, 60, 20), (300, 964, 1004), (700, 30, 1010), (700, 0, 30),
          (450, 80, 40), (900, 944, 8)]
# (cell x, map row y, heading): terrain array $40040 (100 x 100, 400 B rows); player cell x = pos/512, row = 100 - pos_y/512.
# Coast cells (water next to land), a west-edge peak (h 3262), plains.
POSITIONS = [(59, 48, 0), (59, 48, 256), (59, 48, 512), (62, 24, 128), (60, 65, 700), (63, 70, 900), (64, 26, 400),
             (60, 72, 600), (14, 60, 256), (14, 60, 768), (13, 59, 100), (45, 45, 300), (40, 60, 800), (30, 40, 500)]


def mk_live(names, tag):
    out = ROOT / "build" / "p7cell" / tag / "live"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(ROOT / "tools" / "mw2patch.py"), "live", "--only", *names,
                    "--out", str(out.relative_to(ROOT))], check=True, cwd=ROOT, stdout=subprocess.DEVNULL)
    return out


def cap(snap, at, live, out, flips, ang):
    pos = None
    if len(ang) == 3 and isinstance(ang[0], tuple):
        pos, ang = ang[0], ang[1]
    hd, bank, pitch = ang
    h = Hatari(snapshot=snap)
    try:
        spec = json.loads(Path(str(live) + ".json").read_text())
        cmds = [f"loadbin {Path(str(live) + '.img').resolve()} ${spec['img_base']:x}"]
        for s in spec["sites"]:
            cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
        for a in (0x6742, 0x6294, 0x764a):
            cmds.append(f"w ${a:x} ${hd >> 8:02x} ${hd & 255:02x}")
        if pos is not None:
            px, py = pos[0] * 512 + 256, (100 - pos[1]) * 512 - 256
            for a, v in ((0x66e6, px), (0x66ee, px), (0x66ea, py), (0x66f2, py)):
                cmds.append(f"w ${a:x} " + " ".join(f"${(v >> sh) & 255:02x}" for sh in (24, 16, 8, 0)))
        if bank is not None:
            cmds.append(f"w $6746 ${bank >> 8:02x} ${bank & 255:02x}")
        if pitch is not None:
            cmds.append(f"w $674a ${pitch >> 8:02x} ${pitch & 255:02x}")
        od = Path(out).resolve()
        od.mkdir(parents=True, exist_ok=True)
        capf = h.R / "cap.txt"
        capf.write_text(f"savebin {od}/buf60000.bin $60000 $8000\nsavebin {od}/buf70000.bin $70000 $8000\n"
                        f"savebin {od}/st.bin $6742 $10\nsavebin {od}/alt.bin $764c 2\n")
        cmds.append(f"b pc = ${h.FLIP:x} :{flips} :trace :once :file {capf}")
        app = h.R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${h.FLIP:x} :trace :once :file {app}")
        t = time.time()
        while not (od / "st.bin").exists():
            if time.time() - t > 300:
                raise TimeoutError("capture")
            time.sleep(0.5)
        time.sleep(0.5)
    finally:
        h.close()
        shutil.rmtree(h.R, ignore_errors=True)
    return {n: hashlib.md5((od / n).read_bytes()).hexdigest() for n in ("buf60000.bin", "buf70000.bin")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", nargs="*", default=[s for s, _ in SNAPS])
    ap.add_argument("--mine", nargs="+", default=["p7_cell_pre", "p7_cell_cull"])
    ap.add_argument("--flips", type=int, default=4)
    ap.add_argument("--positions", action="store_true", help="poke map positions (POSITIONS) instead of angles")
    a = ap.parse_args()
    base = mk_live(P4, "base_p4")
    mine = mk_live(P4 + a.mine, "mine_" + "_".join(a.mine))
    at_of = dict(SNAPS)
    ok = True
    n = same_n = 0
    for snap in a.snapshot:
        at = at_of[snap]
        name = Path(snap).stem
        for ang in ([((x, y), (hd, None, None)) + ((),) for x, y, hd in POSITIONS] if a.positions else ANGLES):
            tag = f"{name}_{'_'.join(str(x) for x in (ang if not a.positions else (ang[0][0], ang[0][1], ang[1][0])))}"
            bd = ROOT / "build" / "p7cell" / "poke" / ("base_" + tag)
            md = ROOT / "build" / "p7cell" / "poke" / ("mine_" + tag)
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(cap, snap, at, base, bd, a.flips, ang)
                fm = ex.submit(cap, snap, at, mine, md, a.flips, ang)
                b, m = fb.result(), fm.result()
            same = b == m
            ok &= same
            n += 1
            same_n += same
            sb = (bd / "st.bin").read_bytes()
            alt = int.from_bytes((bd / "alt.bin").read_bytes(), "big")
            print(f"{name} {ang[:2] if a.positions else ang} heading={sb[:2].hex()} alt764c={alt}: {'IDENTICAL' if same else 'DIFFER'}  "
                  f"md5 {b['buf60000.bin'][:8]} {b['buf70000.bin'][:8]} | {m['buf60000.bin'][:8]} {m['buf70000.bin'][:8]}", flush=True)
    print(f"{same_n}/{n} identical")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
