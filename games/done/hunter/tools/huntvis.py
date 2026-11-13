#!/usr/bin/env python3
"""Gates and screenshots for the v1.2 visual patches (pal_*, sky_*): work/notes/visuals.md.

    python3 tools/huntvis.py shots                     before/after screenshots + contact sheet -> work/shots/visuals_*.png
    python3 tools/huntvis.py raster [--hz 50 60]       raster exactness: every (row, colour index) shows ONE colour, colour 15 changes
                                                       only on the expected rows, the other 15 only between rows 139 and 140
    python3 tools/huntvis.py pix [--set sky|pal|panel] frame-buffer gate: which bytes of the two screen pages change (huntab captures)
    python3 tools/huntvis.py palette                   palette read-out day / dusk / night, original against pal_
    python3 tools/huntvis.py prof                      cycles per VBL in the sky blob and in the VBL handler
    python3 tools/huntvis.py vbllen [--hz 50 60]       raster line on which the VBL handler returns (must be before the display)

Everything runs on the project snapshots with the patch set applied live at a flip (snapshots hold unpatched code); the cold
boots of the real builds are tools/huntvis_cold.py.  One Hatari at a time.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from hunter import Hunter, SNAP  # noqa: E402

WORK = Path("/tmp/huntvis")
SHOTS = GAME / "work" / "shots"
PAL = ["pal_fade", "pal_load"]
SKY = ["sky_vbl", "sky_fill", "sky_clr", "sky_fdst", "sky_ldst", "sky2_aciax", "sky_vblx"]
A5 = 0x806
D = [62, 30, 14, 6, 2, 0]                 # band boundaries above the horizon row (Amiga table $62f8, cumulative)


def sky_base() -> int:
    m = re.search(r"^SKY\s+equ\s+\$([0-9a-f]+)", (GAME / "patches" / "sky_vbl.s").read_text(), re.M | re.I)
    return int(m.group(1), 16)


CFG = sky_base() + 28                     # option byte (bit0 sky, bit1 tint, bit2 lit panel); CFG+1 = line-synchronous band mask
VAR = int(re.search(r"^SKYV\s+equ\s+\$([0-9a-f]+)", (GAME / "patches" / "sky_vbl.s").read_text(), re.M | re.I).group(1), 16)   # state block


# ---- live patch sets ---------------------------------------------------------------------------------------------------
def mklive(names: list[str], tag: str, ste: bool = True, samples: bool = False) -> str:
    WORK.mkdir(exist_ok=True)
    out = WORK / tag
    r = subprocess.run([sys.executable, str(HERE / "huntpatch.py"), "live", "--only", *names, "--out", str(out)]
                       + ([] if ste else ["--no-ste"]) + (["--samples", str(GAME / "build" / "hunter_snd.bin")] if samples else []),
                       capture_output=True, text=True, cwd=GAME)
    if r.returncode:
        raise SystemExit(r.stdout[-3000:] + r.stderr[-3000:])
    return str(out)


def apply_live(h: Hunter, live: str | None, extra=(), at: int = 0x5FEE, wait: float = 30):
    """Apply a live set (and/or debugger lines) at the next flip."""
    cmds = []
    if live:
        spec = json.loads(Path(live + ".json").read_text())
        cmds.append(f"loadbin {live}.img ${spec['img_base']:x}")
        for s in spec["sites"]:
            raw = bytes.fromhex(s["new"])
            for o in range(0, len(raw), 40):
                cmds.append(f"w ${s['addr'] + o:x} " + " ".join(f"${b:02x}" for b in raw[o:o + 40]))
    cmds += list(extra)
    if not cmds:
        return
    f = h.R / "apply_hv.txt"
    f.write_text("\n".join(cmds) + "\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${at:x} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > wait:
            raise TimeoutError(h._logtext()[-800:])
        time.sleep(0.2)
    time.sleep(0.3)


def set_time(h: Hunter, hh: int, mm: int, ticks: int = 0):
    """Game clock: $1b2 ticks (60 = a minute), $1b4 minutes, $1b6 hours."""
    h.debug(f"w ${A5 + 0x1b2:x} $00 ${ticks:02x} $00 ${mm:02x} $00 ${hh:02x}", 0.3)


def to_hour(h: Hunter, hour: int, settle: float = 7.0):
    """Let the clock roll over into `hour`: the game then fades the palette to that hour's brightness ($c3e4, table $c42a)."""
    set_time(h, (hour - 1) % 24, 59, 58)
    time.sleep(settle)


def var(h: Hunter) -> dict:
    b = h.peek(VAR, 16) + h.peek(VAR + 16, 16)
    return dict(cfg=h.peek(CFG, 1)[0], st=b[1], H=b[2] * 256 + b[3], LH=b[4] * 256 + b[5], key=b[6:8].hex(), pneed=b[11], c1=b[13], c2=b[14],
                base=b[18:22].hex())


def hwpal(h: Hunter) -> list[int]:
    return [int.from_bytes(h.peek(0xFF8240 + 2 * i, 2), "big") & 0xFFF for i in range(16)]


def words(h: Hunter, addr: int, n: int) -> list[int]:
    out = []
    for o in range(0, 2 * n, 16):
        b = h.peek(addr + o, min(16, 2 * n - o))
        out += [int.from_bytes(b[i:i + 2], "big") for i in range(0, len(b), 2)]
    return out


def fmt(p) -> str:
    return " ".join(f"{x:03x}" for x in p)


# ---- pictures ----------------------------------------------------------------------------------------------------------
def planar(buf: bytes) -> np.ndarray:
    a = np.frombuffer(buf[:32000], dtype=">u2").reshape(200, 20, 4)
    out = np.zeros((200, 320), dtype=np.uint8)
    for p in range(4):
        bits = ((a[:, :, p][:, :, None] >> np.arange(15, -1, -1)) & 1).reshape(200, 320)
        out |= (bits << p).astype(np.uint8)
    return out


def shot_rgb(h: Hunter, path: str) -> np.ndarray:
    """Screenshot -> 200 x 320 RGB (every second pixel of the 640 x 400 picture at (96,58))."""
    for _ in range(3):
        try:
            im = np.asarray(Image.open(h.shot(path)).convert("RGB"))
            return im[58:58 + 400:2, 96:96 + 640:2]
        except Exception:                               # a screenshot file can be read half written
            time.sleep(0.5)
    raise RuntimeError("no screenshot")


def frozen(h: Hunter, tag: str, pause: bool = True):
    """Pause the game (P), then return (colour indices of the shown page, screenshot RGB)."""
    WORK.mkdir(exist_ok=True)
    if pause:
        h.key("p", 0.5)
        time.sleep(1.5)
    vb = (h.peek(0xFF8201, 1)[0] << 16) | (h.peek(0xFF8203, 1)[0] << 8)
    h.dump(str(WORK / f"{tag}.scr"), vb, 32000)
    rgb = shot_rgb(h, str(WORK / f"{tag}.png"))
    return planar((WORK / f"{tag}.scr").read_bytes()), rgb


def band_info(h: Hunter):
    """(six band colours, the palette's own colour 15) as hardware words, masked to the bits the machine has."""
    m = 0xFFF if h.peek(0x8BFF0, 4)[3] & 1 else 0x777
    return [w & m for w in words(h, VAR + 58, 6)], words(h, VAR + 80 + 30, 1)[0] & m


def raster_check(idx: np.ndarray, rgb: np.ndarray, H: int, rows: int = 200, bands=None):
    """(ok, messages, colour-15 transitions).  H = horizon row the sky was built for (0 = no sky expected).
    bands = band_info(): a boundary between two bands of the SAME hardware colour (plain ST at night: 3 bits per gun)
    must show no change; every other boundary must."""
    msgs, col = [], {}
    for y in range(rows):
        for i in np.unique(idx[y]):
            u = np.unique(rgb[y][idx[y] == i].reshape(-1, 3), axis=0)
            if len(u) != 1:
                msgs.append(f"row {y} index {i}: {len(u)} colours")
            col[(y, int(i))] = tuple(int(v) for v in u[0])
    exp = sorted({H - d for d in D if 0 < H - d < 140}) if H else []
    t15, prev = [], None
    for y in range(rows):
        c = col.get((y, 15))
        if c is None:
            continue
        if prev is not None and c != prev[1]:
            t15.append((prev[0], y))
            if not [e for e in exp + [140] if prev[0] < e <= y]:
                msgs.append(f"index 15 changes between rows {prev[0]} and {y} (expected only at {exp + [140]})")
        prev = (y, c)
    same = set()
    if bands and H:
        cur = bands[1]
        for d, c in zip(D, bands[0]):
            y = H - d
            if 0 < y < 140 and c == cur:
                same.add(y)
            cur = c
    for e in exp:
        if (e - 1, 15) in col and (e, 15) in col and (col[(e - 1, 15)] == col[(e, 15)]) != (e in same):
            msgs.append(f"{'unexpected' if e in same else 'no'} colour-15 change at row {e}")
    for i in range(15):
        prev = None
        for y in range(rows):
            c = col.get((y, i))
            if c is None:
                continue
            if prev is not None and c != prev[1] and not (prev[0] < 140 <= y):
                msgs.append(f"index {i} changes between rows {prev[0]} and {y}")
            prev = (y, c)
    return (not msgs), msgs, t15


def sheet(items: list[tuple[str, Path]], out: Path, cols: int, scale: float = 0.5):
    ims = [(lab, Image.open(p).convert("RGB")) for lab, p in items]
    w, hh = int(ims[0][1].size[0] * scale), int(ims[0][1].size[1] * scale)
    rows = (len(ims) + cols - 1) // cols
    S = Image.new("RGB", (cols * (w + 4), rows * (hh + 16)), (32, 32, 32))
    d = ImageDraw.Draw(S)
    for i, (lab, im) in enumerate(ims):
        x, y = (i % cols) * (w + 4), (i // cols) * (hh + 16)
        S.paste(im.resize((w, hh), Image.LANCZOS), (x, y + 14))
        d.text((x + 3, y + 1), lab, fill=(255, 255, 120))
    S.save(out)


# ---- scenes ------------------------------------------------------------------------------------------------------------
# (name, snapshot, hour, extra debugger pokes, description)
CAM = A5 + 0x1542                                       # camera height offset added at $37e6 (horizon = height/43 + 46, $6000)
SCENES = [
    ("day", "1mb_foot_stand", 12, [], "HQ, noon"),
    ("dusk", "1mb_foot_stand", 21, [], "HQ, 21:00 (brightness 11 of 15)"),
    ("night", "1mb_foot_stand", 2, [], "HQ, 02:00 (brightness 7 of 15)"),
    ("sea", "1mb_car_drive", 12, [], "car at the shore, noon"),
    ("sea_night", "1mb_car_drive", 2, [], "car at the shore, 02:00"),
    ("low", "1mb_hills_stand", 12, [], "hills, camera at eye height (horizon row 57)"),
    ("high", "1mb_hills_stand", 12, [f"w ${CAM:x} $03 $80"], "hills, camera raised (horizon row 75)"),
    ("higher", "1mb_hills_stand", 12, [f"w ${CAM:x} $06 $00"], "hills, camera raised more (horizon row 90)"),
]
VARIANTS = {"before": ([], None), "pal": (PAL, None), "sky": (PAL + SKY, 5), "sky_tint": (PAL + SKY, 7), "sky_nopal": (SKY, 5),
            "sky_nopanel": (PAL + SKY, 1), "panel_only": (PAL + SKY, 4), "sky_direct": (PAL + SKY, 5, 0x00), "sky_sync2": (PAL + SKY, 5, 0x30),
            "sky_syncall": (PAL + SKY, 5, 0x3F)}


def run_scene(scene, variant: str, fn=None, machine: str = "ste", hz: int = 50):
    name, snap, hour, pokes, _ = scene
    names, cfg, *sm = VARIANTS[variant]
    h = Hunter(snapshot=str(SNAP / f"{snap}.sav"))
    try:
        time.sleep(1.0)
        extra = list(pokes) + ([f"w ${CFG:x} ${cfg:02x}"] if cfg is not None else []) + ([f"w ${CFG + 1:x} ${sm[0]:02x}"] if sm else [])
        apply_live(h, mklive(names, "v_" + variant) if names else None, extra)
        if hz == 60:
            h.debug("w $ff820a $00", 0.4)
        to_hour(h, hour)
        return fn(h) if fn else None
    finally:
        h.close()


def cmd_shots(a):
    SHOTS.mkdir(parents=True, exist_ok=True)
    items = []
    for sc in SCENES:
        if a.scene and sc[0] not in a.scene:
            continue
        vs = ["before", "sky"] + (["pal", "sky_tint"] if sc[0] in ("dusk", "night", "day") else [])
        for v in vs:
            out = SHOTS / f"visuals_{sc[0]}_{v}.png"

            def grab(h, out=out):
                im = Image.open(h.shot(str(WORK / "s.png"))).convert("RGB").crop((96, 58, 736, 458))
                im.save(out)
                return var(h) if v != "before" and v != "pal" else None
            r = run_scene(sc, v, grab)
            print(f"{out.name}: {sc[4]}; {v}; {r}", flush=True)
    lab = {"before": "v1.1", "pal": "+ STE palette only", "sky": "v1.2: STE palette + sky + lit panel", "sky_tint": "v1.2 + dawn/dusk tint option"}
    for sc in SCENES:
        for v in ["before", "pal", "sky", "sky_tint"]:
            p = SHOTS / f"visuals_{sc[0]}_{v}.png"
            if p.exists():
                items.append((f"{sc[4]} | {lab[v]}", p))
    main_rows = []
    for sc in SCENES:
        for v in ["before", "sky"]:
            p = SHOTS / f"visuals_{sc[0]}_{v}.png"
            if p.exists():
                main_rows.append((f"{sc[4]} | {lab[v]}", p))
    sheet(main_rows, SHOTS / "visuals_sheet.png", cols=2, scale=0.75)
    opt = [(f"{sc[4]} | {lab[v]}", SHOTS / f"visuals_{sc[0]}_{v}.png") for sc in SCENES for v in ["before", "pal", "sky", "sky_tint"]
           if sc[0] in ("day", "dusk", "night") and (SHOTS / f"visuals_{sc[0]}_{v}.png").exists()]
    if opt:
        sheet(opt, SHOTS / "visuals_sheet_options.png", cols=4, scale=0.5)
    print("wrote", SHOTS / "visuals_sheet.png", SHOTS / "visuals_sheet_options.png")


def cmd_raster(a):
    bad = 0
    for hz in a.hz:
        for sc in SCENES:
            if a.scene and sc[0] not in a.scene:
                continue
            for v in a.variant:
                def chk(h):
                    idx, rgb = frozen(h, "r")
                    vv = var(h)
                    hx = vv["H"] if vv["cfg"] & 1 else 0        # no bands expected without the sky option
                    bi = band_info(h)
                    ok, msgs, t = raster_check(idx, rgb, hx, bands=bi)
                    more = 0
                    for k in range(a.repeat):               # more frames of the same paused picture (IKBD joystick replies every VBL)
                        rgb2 = shot_rgb(h, str(WORK / "r2.png"))
                        ok2, m2, _ = raster_check(idx, rgb2, hx, rows=140, bands=bi)
                        more += not ok2
                        msgs += m2[:2]
                    return ok and not more, msgs, t, vv
                ok, msgs, t, vv = run_scene(sc, v, chk, hz=hz)
                bad += not ok
                print(f"RASTER {hz} Hz {sc[0]:10s} {v:11s} H={vv['H']:3d} panel-split={'yes' if vv['pneed'] else 'no '} "
                      f"colour-15 changes after rows {[x[0] for x in t]}: {'PASS' if ok else 'FAIL'}", flush=True)
                for m in msgs[:6]:
                    print("    ", m)
    print("RASTER ALL PASS" if not bad else f"RASTER {bad} FAILED")
    sys.exit(1 if bad else 0)


def cmd_palette(a):
    for v in ["before", "pal"]:
        for hour, nm in [(12, "day"), (21, "dusk"), (2, "night")]:
            p = run_scene(("x", "1mb_foot_stand", hour, [], ""), v, hwpal)
            print(f"PALETTE {v:6s} {nm:5s} $ff8240: {fmt(p)}  distinct {len(set(p))}", flush=True)


# ---- frame-buffer gate ---------------------------------------------------------------------------------------------------
def cmd_pix(a):
    import huntab
    huntab.WORK.mkdir(exist_ok=True)
    sets = {"sky": (PAL + SKY, 5), "panel": (PAL + SKY, 4), "pal": (PAL, None), "skyonly": (SKY, 1)}
    if a.set == "full":                      # release gate: the whole default set (huntpatch default) against the same set without pal_/sky_
        dflt = [l.split()[0] for l in subprocess.run([sys.executable, str(HERE / "huntpatch.py"), "list"], capture_output=True, text=True,
                                                    cwd=GAME).stdout.splitlines()[2:] if len(l.split()) > 1 and l.split()[1] == "yes"]
        dflt = [n for n in dflt if not n.startswith("tb_")]   # huntab's fixed-address page capture cannot follow triple buffering (hunttb_ab.py does)
        sets["full"] = (dflt, None)
        base_names = [n for n in dflt if n not in PAL + SKY + ["sky2_pnl"]]
    else:
        base_names = None
    names, cfg = sets[a.set]
    live = huntab.make_live(names) if a.set == "full" else mklive(names, "pix_" + a.set)
    blive = huntab.make_live(base_names) if base_names is not None else None
    flips = [2, a.flip] if a.set == "full" else [1, a.flip]
    allok = True
    for sn in a.snapshot:
        sp = huntab.snap_path(sn)
        at0 = huntab.at_vbl_for(sp)
        tot = dict(pix=0, frames=0, same=0)
        ok = True
        notes = []
        for pi in range(a.views):
            at = at0 + pi * huntab.POINT_STEP
            view = pi if a.views > 1 else None
            pk = huntab.pokes_for(view, True)
            sfx = "_L" + (f"_v{view}" if view is not None else "")
            bd = huntab.WORK / ("base0" if blive is None else "basefull") / f"{sn}_{at}{sfx}_f{a.flip}"
            pd = huntab.WORK / ("vis_" + a.set) / f"{sn}_{at}{sfx}"
            b = huntab.one(sp, at, blive, bd, flips, 100, False, True, pk)
            p = huntab.one(sp, at, live, pd, flips, 100, False, False, pk + ([f"w ${CFG:x} ${cfg:02x}"] if cfg is not None else []))
            for n in flips:
                for nm in huntab.BUFS:
                    x = planar((bd / f"f{n}_{nm}.bin").read_bytes())
                    y = planar((pd / f"f{n}_{nm}.bin").read_bytes())
                    tot["frames"] += 1
                    df = x != y
                    if not df.any():
                        tot["same"] += 1
                        continue
                    ys, xs = np.nonzero(df)
                    good = (x[df] == 0) & (y[df] == 15) & (ys < 140) & (((xs + ys) & 1) == 0)
                    tot["pix"] += int(df.sum())
                    # the changed rows must be exactly the rows that had the dither: below them nothing else differs, and
                    # every changed pixel was one of the dither's colour-0 pixels
                    if not good.all() or a.set not in ("sky", "skyonly", "full"):
                        ok = False
                        notes.append(f"view {pi} flip {n} {nm}: {int((~good).sum())} unexpected of {int(df.sum())} changed pixels, "
                                     f"rows {ys.min()}..{ys.max()}")
                    else:
                        notes.append(f"view {pi} flip {n} {nm}: {int(df.sum())} pixels 0 -> 15 on rows {ys.min()}..{ys.max()}, "
                                     f"all at (x+y) even; frames base {b['frames'][:n]} patched {p['frames'][:n]}")
        allok &= ok
        print(f"PIX {a.set} {sn}: {'OK' if ok else 'FAIL'}: {tot['frames']} page captures, {tot['same']} byte-identical, "
              f"{tot['pix']} changed pixels in the others", flush=True)
        for m in notes[: (None if a.verbose else 4)]:
            print("    ", m)
    print("PIX ALL OK" if allok else "PIX MISMATCH")
    sys.exit(0 if allok else 1)


# ---- cost ----------------------------------------------------------------------------------------------------------------
def cmd_prof(a):
    """Cost per VBL, measured with the game paused: the main program is then the 2-instruction spin $260a `btst #5,$93(a5)` /
    $2610 `bne` (16 + 10 cycles), so every other cycle is interrupt work (VBL handler, IKBD, Timer B; Hatari books the 44-cycle
    exception entry on the interrupted instruction).  cost = (all cycles - 26 x spins) / VBLs, patched minus original.
    The sky's VBL hook, raster handlers and IKBD wrapper do the same work paused or not; the fill is measured unpaused."""
    rows = []
    for v, hour in [("before", 12), ("sky_direct", 12), ("sky", 12), ("sky_sync2", 12), ("sky_syncall", 12), ("before", 2), ("sky", 2),
                    ("sky_nopanel", 2), ("panel_only", 2)]:
        def prof(h):
            pr = h.profile_cc(a.vbls)                       # unpaused: the fill
            fill = sum(c for ad, (c, _) in pr.items() if 0xC84A <= ad < 0xC8F8)
            fills = pr.get(0xC8F6, (0, 0))[1] or 1
            h.key("p", 0.5)
            time.sleep(1.5)
            v0 = h.vbl()
            pr = h.profile_cc(a.vbls)
            tot = sum(c for c, _ in pr.values())
            spins = pr.get(0x260A, (0, 0))[1]
            return fill / fills, (tot - 26 * spins) / a.vbls, tot / a.vbls, (var(h) if v != "before" else {})
        fill, irq, tot, vv = run_scene(("x", a.snapshot, hour, [], ""), v, prof)
        rows.append((v, hour, fill, irq))
        base = next(r for r in rows if r[0] == "before" and r[1] == hour)
        print(f"PROF {v:11s} hour {hour:2d}: interrupt work {irq:7.0f} cycles/VBL ({irq - base[3]:+6.0f} = {100 * (irq - base[3]) / tot:+.2f} % of a VBL), "
              f"fill $c84a {fill:6.0f} cycles/frame ({fill - base[2]:+6.0f}); profiled {tot:.0f} cycles/VBL {vv}", flush=True)


def cmd_vbllen(a):
    """Raster line (Hatari HBL counter) on which the VBL handler returns ($c626 rte), with the default patches, the DMA mixer
    and two looping table-volume voices (the mixer's worst case, REPORT section 4).  The display starts on line 63 (50 Hz) /
    34 (60 Hz); the first Timer B interrupt of the sky is c1 lines later.  A handler that is still running then delays it."""
    base = ["p4_ikbd", "p4_edge", "p4_poly", "hn_hz", "snd_core"]
    live = mklive(base + PAL + SKY, "vbllen", samples=True)
    for hz in a.hz:
        for voices in ([], [(13, 1, 12)], [(13, 1, 12), (11, 2, 10)]):
            h = Hunter(snapshot=str(SNAP / f"{a.snapshot}.sav"))
            try:
                time.sleep(1)
                apply_live(h, live)
                if hz == 60:
                    h.debug("w $ff820a $00", 0.4)
                time.sleep(2)
                for eff, ch, vol in voices:                  # what the game's trigger $af0e does (tools/snd_test.py inject)
                    h.debug(f"w ${0x11388 + ch:x} ${eff:02x}", 0.15)
                    h.debug(f"w ${0x1138C + 2 * ch:x} $00 ${vol:02x}", 0.15)
                if a.keys:
                    h.hold(*a.keys)
                time.sleep(1)
                vv = var(h)
                f = h.R / "vl.txt"
                f.write_text("e HBL\n")
                start = len(h._logtext())
                h.cmd(f"hatari-debug b pc = $c626 :trace :file {f}")
                time.sleep(a.secs)
                h.debug("b all", 0.5)
                if a.keys:
                    h.release(*a.keys)
                t = h._logtext()[start:]
            finally:
                h.close()
            ls = [int(x) for x in re.findall(r"> e HBL\n= .*?#(\d+) \(dec\)", t)]
            first = (63 if hz == 50 else 34)
            if ls:
                late = sum(1 for x in ls if x >= first + vv["c1"] - 1)
                print(f"VBLLEN {hz} Hz {a.snapshot} voices={len(voices)}: {len(ls)} VBLs, handler returns on raster line min {min(ls)} "
                      f"mean {sum(ls) / len(ls):.1f} max {max(ls)}; display starts on line {first}, first sky interrupt on line "
                      f"{first + vv['c1'] - 1} (H={vv['H']}); handler still running then: {late} VBLs", flush=True)
            else:
                print("VBLLEN: no samples")


SLOT_SIG = bytes.fromhex("31fc0000825e11fc0000fa2121fc00000000012011fc00fefa0f4e73")


def slot_addrs(live: str):
    img = Path(live + ".img").read_bytes()
    o = img.find(SLOT_SIG)
    if o < 0:
        raise SystemExit("slot signature not found in the live image")
    b = json.loads(Path(live + ".json").read_text())["img_base"] + o
    return [b + 70 * k for k in range(6)], b + 420


def cmd_jitter(a):
    """Where on the raster line each colour-15 write happens (walking/driving, unpaused).  LineCycles is Hatari's cycle
    position in the line at the write instruction; the write itself completes about 12 cycles later.  Row pixels start at
    cycle 56 and end at 376; a write between 44 and 364 changes colour 15 inside the visible row (a late write)."""
    live = mklive(a.base + (["snd_core"] if a.snd else []) + PAL + SKY, "jit", samples=a.snd)
    slots, tbe = slot_addrs(live)
    h = Hunter(snapshot=str(SNAP / f"{a.snapshot}.sav"))
    try:
        time.sleep(1)
        extra = []
        if a.cam is not None:
            extra.append(f"w ${CAM:x} ${a.cam >> 8:02x} ${a.cam & 255:02x}")
        if a.smask is not None:
            extra.append(f"w ${CFG + 1:x} ${a.smask:02x}")
        apply_live(h, live, extra)
        if a.no_acia:
            spec = json.loads(Path(live + ".json").read_text())
            img = Path(live + ".img").read_bytes()
            o = img.find(bytes.fromhex("46fc250048e700f8"))
            acia = spec["img_base"] + o
            # wrapper := move.w #$2600,sr ; jmp $afde (one-piece movem), and the exit site back to the original
            apply_live(h, None, [f"w ${acia:x} $46 $fc $26 $00 $4e $f9 $00 $00 $af $de", "w $b004 $4c $df $1f $ff $4e $73"])
        if a.no_low:
            spec = json.loads(Path(live + ".json").read_text())
            o = Path(live + ".img").read_bytes().find(bytes.fromhex("08a900060015" "46fc2500"))
            assert o > 0, "IPL-lowering signature not found"
            apply_live(h, None, [f"w ${spec['img_base'] + o:x} $4e $71 $4e $71 $4e $71 $4e $71 $4e $71"])
        if a.hz == 60:
            h.debug("w $ff820a $00", 0.4)
        time.sleep(2)
        if a.snd:                                   # two looping voices at table volumes (tools/snd_test.py inject)
            for eff, ch, vol in ((13, 1, 12), (11, 2, 10)):
                h.debug(f"w ${0x11388 + ch:x} ${eff:02x}", 0.15)
                h.debug(f"w ${0x1138C + 2 * ch:x} $00 ${vol:02x}", 0.15)
        if a.keys:
            h.hold(*a.keys)
        f = h.R / "jt.txt"
        f.write_text("e LineCycles\ne HBL\nm a7 8\n")
        start = len(h._logtext())
        pcs = {}
        for k, s in enumerate(slots):
            pcs[s] = ("direct", k)
            pcs[s + 54] = ("sync", k)
        for pc in pcs:
            h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}")
            time.sleep(0.12)
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
    n = Counter(); late = Counter(); worst = Counter(); who = Counter()
    times = {}
    linelen = 512 if a.hz == 50 else 508
    for blk in t.split("CPU breakpoint condition(s) matched")[1:]:
        m = re.search(r"pc = \$([0-9a-f]+)", blk)
        v = re.findall(r"#(\d+) \(dec\)", blk)
        if not m or not v:
            continue
        kind, k = pcs[int(m.group(1), 16)]
        lc = int(v[0])
        n[kind] += 1
        if len(v) > 1:
            times.setdefault((kind, k), []).append(int(v[1]) * linelen + lc)
        if 44 <= lc < 364:                       # write completes at lc+12: inside the pixels of the row
            late[kind] += 1
            worst[kind] = max(worst[kind], lc)
            mm = re.search(r"^[0-9A-F]{8}: ((?:[0-9a-f]{2} ){8})", blk, re.M)
            if mm and kind == "direct":
                bb = bytes(int(x, 16) for x in mm.group(1).split())
                who[int.from_bytes(bb[2:6], "big")] += 1
    tag = f"JITTER {a.snapshot} keys={'+'.join(a.keys) or '-'} {a.hz} Hz smask={'default' if a.smask is None else hex(a.smask)}" \
          + (" NO-ACIA-FIX (control)" if a.no_acia else "") + (" VBL-AT-IPL7 (control)" if a.no_low else "") + (" +DMA mixer, 2 voices" if a.snd else "")
    for kind in ("direct", "sync"):
        if n[kind]:
            print(f"{tag}: {kind:6s} handlers {n[kind]:6d}, late writes {late[kind]:5d} = {100 * late[kind] / n[kind]:.2f} % "
                  f"(worst: {max(0, 2 * (worst[kind] + 12 - 56))} pixels into the row)")
    # a handler that comes one or more LINES late (the standing camera keeps every boundary on the same row)
    if a.rows:
        for (kind, k), ts in sorted(times.items()):
            c = Counter(t // linelen for t in ts)
            mode = c.most_common(1)[0][0]
            off = sum(v_ for ln, v_ in c.items() if abs(ln - mode) > 1)
            print(f"    slot {k} {kind:6s}: {len(ts):5d} entries on raster lines {dict(sorted(c.items()))}: more than one line from line {mode}: {off}")
    if who:
        print("    interrupted instruction ends at:", ", ".join(f"${pc:x} x{c}" for pc, c in who.most_common(6)))


TB = ["tb_flip", "tb_frame", "tb_vbl"]


def cmd_pages(a):
    """The sky follows the page the shifter shows.  Log every fill (draw page $144(a5), horizon $1544(a5), at $c84a) and every
    armed VBL (video base and horizon the raster list uses, at sky_vbl's `.arm`); each armed VBL must use the horizon of the
    LAST fill of the page it shows.  With --tb the triple-buffering patches run too (three pages)."""
    base = ["p4_ikbd", "p4_edge", "p4_poly", "hn_hz"] + (TB if a.tb else [])
    live = mklive(base + PAL + SKY, "pages_tb" if a.tb else "pages")
    spec = json.loads(Path(live + ".json").read_text())
    o = Path(live + ".img").read_bytes().find(bytes.fromhex("43f8fa004229001b302c006e"))
    assert o > 0
    arm = spec["img_base"] + o
    h = Hunter(snapshot=str(SNAP / f"{a.snapshot}.sav"))
    try:
        time.sleep(1)
        apply_live(h, live, at=0x253E)              # loop top: tb_frame replaces the `bsr $5fd2` a flip-time apply would return into
        time.sleep(2)
        if a.keys:
            h.hold(*a.keys)
        f1 = h.R / "pf.txt"
        f1.write_text(f"e VBL\nm ${A5 + 0x144:x} 4\nm ${A5 + 0x1544:x} 2\n")
        f2 = h.R / "pa.txt"
        f2.write_text(f"e VBL\nm ${VAR + 18:x} 4\nm ${VAR + 2:x} 2\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $c84a :trace :file {f1}")
        time.sleep(0.2)
        h.cmd(f"hatari-debug b pc = ${arm:x} :trace :file {f2}")
        t0 = time.time()
        k = 0
        while time.time() - t0 < a.secs:            # move the camera height so that the horizon changes from frame to frame
            cam = (0x58, 0x120, 0x1F0, 0x2C0, 0x390, 0x2C0, 0x1F0, 0x120)[k % 8]
            k += 1
            h.cmd(f"hatari-debug w ${CAM:x} ${cam >> 8:02x} ${cam & 255:02x}")
            time.sleep(0.12)
        h.debug("b all", 0.6)
        if a.keys:
            h.release(*a.keys)
        t = h._logtext()[start:]
    finally:
        h.close()
    last = {}
    fills = arms = bad = naive = 0
    newest = None
    pages, hs, frames = set(), set(), []
    prev_base = None
    for blk in t.split("CPU breakpoint condition(s) matched")[1:]:
        m = re.search(r"pc = \$([0-9a-f]+)", blk)
        rows = re.findall(r"^[0-9A-F]{8}: ((?:[0-9a-f]{2} )+)", blk, re.M)
        vb = re.findall(r"#(\d+) \(dec\)", blk)
        if not m or len(rows) < 2 or not vb:
            continue
        page = int(rows[0].replace(" ", "")[:8], 16)
        hh = int(rows[1].replace(" ", "")[:4], 16)
        if int(m.group(1), 16) == 0xC84A:
            last[page] = hh
            newest = hh
            fills += 1
            pages.add(page)
            hs.add(hh)
        else:
            arms += 1
            naive += newest is not None and newest != hh
            if page != prev_base:
                frames.append(int(vb[0]))
                prev_base = page
            if page in last and last[page] != hh:
                bad += 1
                if bad < 6:
                    print(f"    VBL {vb[0]}: shows ${page:x}, bands for horizon {hh}, but that page was filled with {last[page]}")
    span = (frames[-1] - frames[0]) / max(1, len(frames) - 1) if len(frames) > 1 else 0
    print(f"PAGES {a.snapshot} keys={'+'.join(a.keys) or '-'} {'triple buffering' if a.tb else 'double buffering'}: {fills} fills on pages "
          f"{sorted(hex(p) for p in pages)}, horizons {min(hs)}..{max(hs)}, {arms} armed VBLs, {len(frames)} page changes "
          f"({span:.2f} VBL/frame), wrong horizon: {bad}: {'PASS' if not bad and arms else 'FAIL'} "
          f"(control: {naive} VBLs would be wrong with the game's single horizon variable $1544 instead of the per-page table)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("shots"); s.add_argument("--scene", nargs="*")
    s = sub.add_parser("raster"); s.add_argument("--hz", nargs="*", type=int, default=[50, 60]); s.add_argument("--scene", nargs="*")
    s.add_argument("--variant", nargs="*", default=["sky"]); s.add_argument("--repeat", type=int, default=4)
    sub.add_parser("palette")
    s = sub.add_parser("pix"); s.add_argument("--set", default="sky"); s.add_argument("--views", type=int, default=3)
    s.add_argument("--flip", type=int, default=5); s.add_argument("--verbose", action="store_true")
    s.add_argument("--snapshot", nargs="*", default=["foot_stand", "foot_walk", "car_stand", "car_drive", "car_turn", "hills_stand", "4mb_foot_stand"])
    s = sub.add_parser("prof"); s.add_argument("--vbls", type=int, default=400); s.add_argument("--snapshot", default="1mb_foot_stand")
    s = sub.add_parser("vbllen"); s.add_argument("--hz", nargs="*", type=int, default=[50, 60]); s.add_argument("--secs", type=float, default=6)
    s.add_argument("--snapshot", default="1mb_foot_walk"); s.add_argument("--keys", nargs="*", default=["Up"])
    s = sub.add_parser("jitter"); s.add_argument("--secs", type=float, default=20); s.add_argument("--snapshot", default="1mb_foot_walk")
    s.add_argument("--keys", nargs="*", default=["Up"]); s.add_argument("--smask", type=lambda x: int(x, 0), default=None)
    s.add_argument("--base", nargs="*", default=["p4_ikbd", "p4_edge", "p4_poly", "hn_hz"]); s.add_argument("--hz", type=int, default=50)
    s.add_argument("--cam", type=lambda x: int(x, 0), default=None, help="camera height offset poke ($1542(a5))")
    s.add_argument("--snd", action="store_true", help="add snd_core with the sample bank and two looping voices")
    s.add_argument("--rows", action="store_true", help="per slot: handlers that come whole lines late (use a standing snapshot)")
    s.add_argument("--no-low", action="store_true", help="negative control: the VBL handler keeps IPL 7 (sky_vbl's `move.w #$2500,sr` removed)")
    s.add_argument("--no-acia", action="store_true", help="negative control: the IKBD handler keeps its one-piece movem and IPL 6")
    s = sub.add_parser("pages"); s.add_argument("--tb", action="store_true"); s.add_argument("--snapshot", default="1mb_hills_stand")
    s.add_argument("--keys", nargs="*", default=[]); s.add_argument("--secs", type=float, default=12)
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    {"shots": cmd_shots, "raster": cmd_raster, "palette": cmd_palette, "pix": cmd_pix, "prof": cmd_prof, "vbllen": cmd_vbllen,
     "jitter": cmd_jitter, "pages": cmd_pages}[a.cmd](a)


if __name__ == "__main__":
    main()
