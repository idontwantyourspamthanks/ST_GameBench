#!/usr/bin/env python3
"""Gates for the Amiga panel (patches/sky2_pnl.s, work/notes/panel.md) on the project snapshots (1 MB; the live image carries the
'HPAN' block, and the install a cold boot does at $8142 is replayed by pokes: the unpacked bitmap into the HUD master $3682c,
option bit 3, V_PAN, V_KEY = -1).  The cold boots of the real builds are tools/pnl_cold.py.

    python3 tools/pnl_gate.py shots  [--scene day night dusk ...]       before (v1.2) / after screenshots -> work/shots/panel_*.png
    python3 tools/pnl_gate.py raster  [--hz 50 60] [--scene ...]        rows 0..139 as huntvis raster; rows 140..199: every
                                                                        (row, index) ONE colour = the Amiga colour at the panel level
    python3 tools/pnl_gate.py jitter  [--hz 50 60] [--snd]              raster position of the panel palette write (sky_tbp)
    python3 tools/pnl_gate.py prof                                      cycles per VBL, panel on / off
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import numpy as np                                # noqa: E402
from PIL import Image                             # noqa: E402
import huntvis as hv                              # noqa: E402
from huntvis import *                             # noqa: E402,F401
import pnl_data                                   # noqa: E402

PNL = ["sky2_pnl"]
PTAB = [0, 2, 4, 6, 9, 11, 13, 15]                # sky_ptab: panel level below night level 7
PAN_BIN = "/tmp/pn/pan.bin"
CMAP = pnl_data.cmap_amiga_words(pnl_data.amiga_pic())


def ensure_bin():
    if not Path(PAN_BIN).exists():
        Path(PAN_BIN).write_bytes(pnl_data.st_planar(pnl_data.pixels(pnl_data.amiga_pic()), 0, 60))


def expected(level: int, ste: bool = True):
    """The 16 panel colours at the given landscape level, as the 8-bit RGB the screenshot shows."""
    lv = 15 if level >= 7 else PTAB[level]
    out = []
    for w in CMAP:
        g = [(c * lv * 17 + 128) >> 8 for c in ((w >> 8) & 15, (w >> 4) & 15, w & 15)]
        if not ste:
            g = [x >> 1 << 1 for x in g]
        out.append(tuple(x * 17 for x in g))
    return out


VARIANTS = {                                       # (names, cfg byte or None, install the Amiga panel)
    "v12": (PAL + SKY, None, False),
    "amiga": (PAL + SKY + PNL, 0x0F, True),
    "amiga_notint": (PAL + SKY + PNL, 0x0D, True),
    "amiga_nosky": (PAL + SKY + PNL, 0x0C, True),  # lit-panel bit + Amiga panel, no bands
    "off1mb": (PAL + SKY + PNL, None, False),      # the new patch on a 1 MB machine: bit 3 never set (phystop < 2 MB)
}


def run_variant(scene, variant: str, fn=None, hz: int = 50, machine: str = "ste"):
    ensure_bin()
    name, snap, hour, pokes, _desc, *late = scene
    names, cfg, inst = VARIANTS[variant]
    h = Hunter(snapshot=str(SNAP / f"{snap}.sav"))
    try:
        time.sleep(1.0)
        extra = list(pokes)
        if cfg is not None:
            extra.append(f"w ${CFG:x} ${cfg:02x}")
        if inst:
            extra += [f"loadbin {PAN_BIN} $3682c", f"w ${VAR + 15:x} $01", f"w ${VAR + 6:x} $ff $ff"]
        apply_live(h, mklive(names, "pg_" + variant, samples=True), extra)
        if hz == 60:
            h.debug("w $ff820a $00", 0.4)
        to_hour(h, hour)
        for ln in (late[0] if late else []):          # after the clock fade has settled
            h.debug(ln, 0.3)
        if late:
            time.sleep(0.5)
        return fn(h) if fn else None
    finally:
        h.close()


SCENES = hv.SCENES + [("nohorizon", "1mb_hills_stand", 12, [f"w ${hv.CAM:x} $12 $00"], "hills, camera very high (horizon row > 139: no sky, panel only)"),
    ("fade3", "1mb_foot_stand", 12, [], "noon, brightness poked to 3 (a screen-change fade): panel level 6", [f"w ${A5 + 0x18c:x} $00 $03"]),
    ("fade9", "1mb_foot_stand", 12, [], "noon, brightness poked to 9", [f"w ${A5 + 0x18c:x} $00 $09"])]


def panel_check(idx: np.ndarray, rgb: np.ndarray, level: int, ste=True):
    """rows 140..199: every (row, index) shows ONE colour and it is the Amiga colour of that index at the panel level."""
    exp = expected(level, ste)
    msgs, seen = [], set()
    for y in range(140, 200):
        for i in np.unique(idx[y]):
            u = np.unique(rgb[y][idx[y] == i].reshape(-1, 3), axis=0)
            seen.add(int(i))
            if len(u) != 1:
                msgs.append(f"row {y} index {i}: {len(u)} colours")
            elif tuple(int(v) for v in u[0]) != exp[int(i)]:
                msgs.append(f"row {y} index {i}: {tuple(int(v) for v in u[0])} expected {exp[int(i)]}")
    return (not msgs), msgs, sorted(seen)


def cmd_shots(a):
    SHOTS.mkdir(parents=True, exist_ok=True)
    for sc in SCENES:
        if a.scene and sc[0] not in a.scene:
            continue
        for v in a.variant:
            out = SHOTS / f"panel_{sc[0]}_{v}.png"

            def grab(h, out=out):
                Image.open(h.shot(str(WORK / "s.png"))).convert("RGB").crop((96, 58, 736, 458)).save(out)
                return var(h), h.peek(VAR + 15, 1)[0]
            print(f"{out.name}: {sc[4]}; {v}; {run_variant(sc, v, grab)}", flush=True)


def cmd_raster(a):
    bad = 0
    for hz in a.hz:
        for sc in SCENES:
            if a.scene and sc[0] not in a.scene:
                continue
            for v in a.variant:
                def chk(h):
                    idx, rgb = frozen(h, "pr")
                    vv = var(h)
                    lvl = int.from_bytes(h.peek(A5 + 0x18C, 2), "big")
                    hx = vv["H"] if vv["cfg"] & 1 else 0
                    bi = band_info(h)
                    ok, msgs, t = raster_check(np.vstack([idx[:140], np.zeros((60, 320), np.uint8)]), np.vstack([rgb[:140], np.zeros((60, 320, 3), np.uint8)]), hx, bands=bi)
                    okp, mp, seen = panel_check(idx, rgb, lvl) if v != "v12" else (True, [], [])
                    more = 0
                    for k in range(a.repeat):
                        rgb2 = shot_rgb(h, str(WORK / "pr2.png"))
                        o2, m2, _ = raster_check(np.vstack([idx[:140], np.zeros((60, 320), np.uint8)]), np.vstack([rgb2[:140], np.zeros((60, 320, 3), np.uint8)]), hx, bands=bi)
                        p2, mp2, _ = panel_check(idx, rgb2, lvl) if v != "v12" else (True, [], [])
                        more += (not o2) + (not p2)
                        msgs += m2[:2] + mp2[:2]
                    return ok and okp and not more, msgs + mp, t, vv, lvl, seen, h.peek(VAR + 15, 1)[0]
                ok, msgs, t, vv, lvl, seen, pan = run_variant(sc, v, chk, hz=hz)
                bad += not ok
                print(f"RASTER {hz} Hz {sc[0]:10s} {v:12s} H={vv['H']:3d} level={lvl:2d} V_PAN={pan} panel-split={'yes' if vv['pneed'] else 'no '} panel indices {seen} "
                      f"colour-15 changes after rows {[x[0] for x in t]}: {'PASS' if ok else 'FAIL'}", flush=True)
                for m in msgs[:6]:
                    print("    ", m)
    print("PANEL RASTER ALL PASS" if not bad else f"PANEL RASTER {bad} FAILED")
    sys.exit(1 if bad else 0)


def tbp_pc(live: str) -> int:
    img = Path(live + ".img").read_bytes()
    o = img.find(bytes.fromhex("48f802fe8240"))
    assert o > 0, "panel palette write not found"
    return json.loads(Path(live + ".json").read_text())["img_base"] + o


def cmd_jitter(a):
    """Raster position of the 16-colour panel palette write.  LineCycles = Hatari's cycle position in the line at the instruction;
    the line count (`e HBL`).  The movem is entered at the end of row 139 (cycle ~376 = the start of the horizontal blank)."""
    live = mklive(PAL + SKY + PNL + (["snd_core"] if a.snd else []), "pj", samples=True)
    pc = tbp_pc(live)
    ensure_bin()
    h = Hunter(snapshot=str(SNAP / f"{a.snapshot}.sav"))
    try:
        time.sleep(1)
        apply_live(h, live, [f"w ${CFG:x} $0f", f"loadbin {PAN_BIN} $3682c", f"w ${VAR + 15:x} $01", f"w ${VAR + 6:x} $ff $ff"])
        if a.hz == 60:
            h.debug("w $ff820a $00", 0.4)
        to_hour(h, a.hour)
        if a.snd:
            for eff, ch, vol in ((13, 1, 12), (11, 2, 10)):
                h.debug(f"w ${0x11388 + ch:x} ${eff:02x}", 0.15)
                h.debug(f"w ${0x1138C + 2 * ch:x} $00 ${vol:02x}", 0.15)
        if a.keys:
            h.hold(*a.keys)
        f = h.R / "jt.txt"
        f.write_text("e LineCycles\ne HBL\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}")
        time.sleep(0.2)
        h.cmd("hatari-option --fast-forward on")
        time.sleep(a.secs)
        h.cmd("hatari-option --fast-forward off")
        time.sleep(0.3)
        h.debug("b all", 0.6)
        if a.keys:
            h.release(*a.keys)
        t = h._logtext()[start:]
    finally:
        h.close()
    from collections import Counter
    lc, hbl = [], Counter()
    for blk in t.split("CPU breakpoint condition(s) matched")[1:]:
        v = re.findall(r"#(\d+) \(dec\)", blk)
        if len(v) >= 2:
            lc.append(int(v[0])); hbl[int(v[1])] += 1
    if not lc:
        print("JITTER: no hits"); return
    c = Counter(x // 16 * 16 for x in lc)
    print(f"JITTER panel palette write {a.snapshot} hour {a.hour} {a.hz} Hz{' +DMA mixer' if a.snd else ''}: {len(lc)} frames, "
          f"LineCycles min {min(lc)} max {max(lc)}; histogram (16-cycle buckets) {dict(sorted(c.items()))}")
    print(f"   raster line (HBL counter) of the hits: {dict(sorted(hbl.items()))}")


def cmd_prof(a):
    """Cost per VBL as huntvis.py prof: game paused, so the main program is the 26-cycle spin $260a/$2610 and every other
    cycle is interrupt work; unpaused first for the fill.  Panel on (amiga) against the v1.2 set (v12), same scene."""
    rows = []
    for v, hour in [("v12", 12), ("amiga", 12), ("v12", 2), ("amiga", 2), ("amiga_nosky", 12), ("off1mb", 12)]:
        def prof(h):
            pr = h.profile_cc(a.vbls)
            fill = sum(c for ad, (c, _) in pr.items() if 0xC84A <= ad < 0xC8F8)
            fills = pr.get(0xC8F6, (0, 0))[1] or 1
            h.key("p", 0.5)
            time.sleep(1.5)
            pr = h.profile_cc(a.vbls)
            tot = sum(c for c, _ in pr.values())
            spins = pr.get(0x260A, (0, 0))[1]
            return fill / fills, (tot - 26 * spins) / a.vbls, tot / a.vbls, var(h)
        sc = ("x", a.snapshot, hour, [], "")
        fill, irq, tot, vv = run_variant(sc, v, prof)
        rows.append((v, hour, fill, irq))
        base = next(r for r in rows if r[0] == "v12" and r[1] == hour)
        print(f"PROF {v:12s} hour {hour:2d}: interrupt work {irq:7.0f} cycles/VBL ({irq - base[3]:+6.0f} = {100 * (irq - base[3]) / tot:+.2f} % of a VBL), "
              f"fill $c84a {fill:6.0f} cycles/frame ({fill - base[2]:+6.0f}); profiled {tot:.0f} cycles/VBL {vv}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("shots", "raster"):
        p = sub.add_parser(nm)
        p.add_argument("--scene", nargs="*")
        p.add_argument("--variant", nargs="*", default=["v12", "amiga"])
        p.add_argument("--hz", nargs="*", type=int, default=[50])
        p.add_argument("--repeat", type=int, default=3)
    pf = sub.add_parser("prof")
    pf.add_argument("--snapshot", default="1mb_foot_stand")
    pf.add_argument("--vbls", type=int, default=600)
    j = sub.add_parser("jitter")
    j.add_argument("--snapshot", default="1mb_foot_walk")
    j.add_argument("--hz", type=int, default=50)
    j.add_argument("--hour", type=int, default=12)
    j.add_argument("--snd", action="store_true")
    j.add_argument("--keys", nargs="*", default=["Up"])
    j.add_argument("--secs", type=float, default=20)
    a = ap.parse_args()
    hv.WORK.mkdir(exist_ok=True)
    {"shots": cmd_shots, "raster": cmd_raster, "jitter": cmd_jitter, "prof": cmd_prof}[a.cmd](a)


if __name__ == "__main__":
    main()
