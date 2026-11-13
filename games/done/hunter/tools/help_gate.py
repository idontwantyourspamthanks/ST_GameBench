#!/usr/bin/env python3
"""Gates for patches/help_pause.s (pause shows a controls guide; work/notes/help.md).

    python3 tools/help_gate.py shots [--scene day dusk night] [--pad a|none] [--hz 50|60] [--tb]   # paused screenshots (snapshot, live set).
         --pad a only selects Hatari's pad config (host p = the pad's Pause); the overlay's pad column follows jag_pad's JAG_ST ($8D9E0 = 1 on
         every STE/Falcon, pad plugged or not), so the no-pad overlay is the ST / TT cold boot.
    python3 tools/help_gate.py hold  [--scene day] [--secs 10] [--tb] [--hz 60]        # 10 s paused: the overlay stays (page md5 every 2 s, screenshots)
    python3 tools/help_gate.py ab    [--tb] [--hz 60] [--snap 1mb_car_drive] --cyc N [--neg]   # restore exactness vs pause without overlay (see help.md)
    python3 tools/help_gate.py ab    --selftest [--shift V] [--cyc N]                     # the control against itself (noise floor)
    python3 tools/help_gate.py cold  --machine ste|st|tt|falcon [--floppy --game build/help_fl/HUNTER_disk1.st] [--mem 1024]   # cold boot, pause, unpause
build/help_hd and build/help_fl = the default set + help_pause (huntpatch.py build [--floppy] --only <defaults> help_pause --samples build/hunter_snd.bin).

Live sets: PAL + SKY + key_item jag_pad jag_stick (+ tb_*) with or without help_pause (`--nohelp` = control).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import huntjag as J  # noqa: E402
import huntvis as V  # noqa: E402
import huntab as AB  # noqa: E402
from hunter import Hunter, SNAP  # noqa: E402

A5 = 0x806
J_SNAP = lambda n: Path(J.snap(n))
SHOTS = GAME / "work" / "shots" / "help"
BASE = V.PAL + V.SKY + ["key_item", "jag_pad", "jag_stick"]
HELP = "help_pause"
TB = ["tb_flip", "tb_frame", "tb_vbl"]
HOURS = {"day": 12, "dusk": 21, "night": 2}
BOX = (16, 24, 304, 112)                      # x0, y0, x1, y1 of the rectangle in the 320x200 picture


def page(h: Hunter, which: str = "shown") -> tuple[int, bytes]:
    a = int.from_bytes(h.peek(A5 + (0x148 if which == "shown" else 0x144), 4), "big")
    f = str(V.WORK / f"pg_{which}_{os.getpid()}.bin")
    V.WORK.mkdir(exist_ok=True)
    h.dump(f, a, 32000)
    return a, Path(f).read_bytes()


def start(scene: str, snap: str, help_on: bool, pad: str, tb: bool, hz: int = 50) -> Hunter:
    names = BASE + ([HELP] if help_on else []) + (TB if tb else [])
    h = Hunter(snapshot=J.snap(snap), extra=J.pad_extra(pad))
    time.sleep(1.5)
    V.apply_live(h, V.mklive(names, "help_" + ("h" if help_on else "n") + ("t" if tb else "")), at=0x253e if tb else 0x5FEE)
    if hz == 60:
        h.debug("w $ff820a $00", 0.4)
    V.to_hour(h, HOURS[scene])
    return h


def pause(h: Hunter, settle: float = 2.5):
    h.key("p", 0.4)
    time.sleep(settle)


def unpause(h: Hunter, settle: float = 1.0):
    h.key("p", 0.4)
    time.sleep(settle)


def box_pixels(buf: bytes) -> np.ndarray:
    idx = V.planar(buf)
    x0, y0, x1, y1 = BOX
    return idx[y0:y1, x0:x1]


def cmd_shots(a):
    SHOTS.mkdir(parents=True, exist_ok=True)
    for sc in a.scene:
        h = start(sc, "1mb_foot_stand", True, a.pad, a.tb, a.hz)
        try:
            pause(h)
            st = h.peek(0x899, 1)[0]
            jag = h.peek(0x8D9E0, 1)[0]
            ad, buf = page(h)
            px = box_pixels(buf)
            vals, cnt = np.unique(px, return_counts=True)
            out = SHOTS / f"help_{sc}_{a.pad}_{a.hz}hz.png"
            V.shot_rgb(h, str(out))
            Image.fromarray(V.shot_rgb(h, str(V.WORK / "x.png"))).resize((640, 400), Image.NEAREST).save(out)
            print(f"{sc} pad={a.pad} $93={st:02x} JAG_ST={jag:02x} shown={ad:#x} box colours {dict(zip(vals.tolist(), cnt.tolist()))} -> {out}")
        finally:
            h.close()


def cmd_hold(a):
    h = start(a.scene[0], "1mb_foot_stand", True, a.pad, a.tb, a.hz)
    try:
        pause(h)
        v0 = h.vbl()
        a0, b0 = page(h)
        ref = hashlib.md5(b0[:22400]).hexdigest()
        s0 = V.shot_rgb(h, str(V.WORK / "hold0.png"))
        t0 = time.time()
        while time.time() - t0 < a.secs:
            time.sleep(2)
            ad, b = page(h)
            print(f"t={time.time() - t0:5.1f}s VBL +{h.vbl() - v0} shown={ad:#x} rows0..139 md5 {hashlib.md5(b[:22400]).hexdigest()} same-as-first={hashlib.md5(b[:22400]).hexdigest() == ref} $93={h.peek(0x899, 1)[0]:02x}")
        s1 = V.shot_rgb(h, str(V.WORK / "hold1.png"))
        win = np.abs(s0[:140].astype(int) - s1[:140].astype(int)).sum()
        print(f"screenshot rows 0..139 at t=0 and t={time.time() - t0:.1f}s: summed RGB difference {win} (VBLs run: {h.vbl() - v0})")
        Image.fromarray(s1).resize((640, 400), Image.NEAREST).save(SHOTS / f"help_hold_{a.scene[0]}_{a.secs:g}s.png")
    finally:
        h.close()


def wait_addr(help_on: bool) -> int:
    """Address of the pause spin loop: $260a in the original, the blob's own `btst #5,$93(a5)` (second occurrence) with help_pause."""
    if not help_on:
        return 0x260A
    d = (GAME / "build" / "help_hd" / "FILES" / "P").read_bytes()
    hits = [i for i in range(len(d)) if d[i:i + 6] == bytes.fromhex("082d00050093")]
    blob = [0x8BA00 + i for i in hits if 0x8CBBE <= 0x8BA00 + i < 0x8CE00]
    return blob[1]


def run_ab(help_on: bool, tb: bool, snap: str = "1mb_foot_stand", frames=(1, 2, 3), pause_wall: float = 0.0, outdir: str | None = None, scene: str = "day", shift: int = 0, cyc: int = 0, hz: int = 50) -> dict:
    """Deterministic: at the first flip after VBL X the live set is applied, the frame lock set and the pause bit poked; at the first run of the
    spin loop the pages are saved and the bit is cleared; the pages and the game's variables are saved at the next `frames` flips."""
    names = BASE + ([HELP] if help_on else []) + (TB if tb else [])
    h = Hunter(snapshot=J.snap(snap), extra=J.pad_extra("none"))
    try:
        time.sleep(1.5)
        live = V.mklive(names, "help_ab_" + ("h" if help_on else "n") + ("t" if tb else ""))
        spec = __import__("json").loads(Path(live + ".json").read_text())
        od = Path(outdir or (V.WORK / f"ab_{int(help_on)}{int(tb)}"))
        od.mkdir(parents=True, exist_ok=True)
        for f in od.glob("*.bin"):
            f.unlink()
        pages = [("A", 0x23000), ("B", 0x2AD00)] + ([("C", 0x81000)] if tb else [])
        sv = lambda tag: "".join(f"savebin {od}/{tag}_{n}.bin ${a:x} $7d00\n" for n, a in pages) + f"savebin {od}/{tag}_var.bin $800 $1800\n"
        flip = 0x5FD2
        wa = wait_addr(help_on)
        files = {}
        for i, n in enumerate(frames):
            cnt = f" :{n}" if n > 1 else ""
            files[f"cap{n}"] = (sv(f"f{n}") + "e VBL\n", f"b pc = ${flip:x}{cnt} :trace :once :file {h.R}/cap{n}.txt")
        (h.R / "ex.txt").write_text("e FrameCycles\ne VBL\n" + sv("exit"))
        (h.R / "en.txt").write_text(sv("entry"))
        unp = sv("paused") + "e VBL\ne FrameCycles\nw $899 $00\n" + f"b pc = $2612 :trace :once :file {h.R}/ex.txt\n" + "".join(f"{files[k][1]}\n" for k in files)
        (h.R / "unp.txt").write_text(unp)
        for k, (body, _) in files.items():
            (h.R / f"{k}.txt").write_text(body)
        cmds = [f"loadbin {live}.img ${spec['img_base']:x}"]
        for st in spec["sites"]:
            raw = bytes.fromhex(st["new"])
            for o in range(0, len(raw), 40):
                cmds.append(f"w ${st['addr'] + o:x} " + " ".join(f"${b:02x}" for b in raw[o:o + 40]))
        cmds += ["w $9ad $0e", "e VBL"] + (["w $ff820a $00"] if hz == 60 else [])
        at = AB.at_vbl_for(J_SNAP(snap))
        cmds.append(f"b VBL > {at + 60 + shift}{f' && FrameCycles > {cyc}' if cyc else ''} && pc = ${wa:x} :trace :once :file {h.R}/unp.txt")      # both runs unpause in the same VBL
        cmds.append(f"b pc = ${(0x8CBBE if help_on else 0x260A):x} :trace :once :file {h.R}/en.txt")
        cmds.append("w $899 $a0")
        (h.R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${(0x253E if tb else flip):x} :trace :once :file {h.R}/apply.txt")
        t = time.time()
        last = od / f"f{frames[-1]}_var.bin"
        while not last.exists():
            if time.time() - t > 300:
                raise TimeoutError(h._logtext()[-1500:])
            time.sleep(0.5)
        time.sleep(1.0)
        log = h._logtext()[start:]
        import re as _re
        print("FrameCycles/VBL lines:", _re.findall(r"(?:FrameCycles|VBL)[^\n]*=[^\n]*|#\d+ \(dec\)", log)[:12])
        return {"dir": od, "log": log}
    finally:
        h.close()


def cmd_ab(a):
    res = {}
    runs = {"help": (True, a.tb, None, 0, 0), "ctrl": (False, a.tb, None, 0, a.cyc)}
    if a.selftest:                              # the gate's noise floor: the control twice
        runs = {"help": (False, a.tb, str(V.WORK / "ab_self1"), 0), "ctrl": (False, a.tb, str(V.WORK / "ab_self2"), a.shift, a.cyc)}
    for key, (on, tb, od, *sh) in runs.items():
        res[key] = run_ab(on, tb, snap=a.snap, scene=a.scene[0], outdir=od, shift=sh[0] if sh else 0, cyc=sh[1] if len(sh) > 1 else 0, hz=a.hz)
        print(key, "dir", res[key]["dir"])
    A, B = res["help"]["dir"], res["ctrl"]["dir"]
    allsame = True
    names = ["A", "B"] + (["C"] if a.tb else [])
    for tag in ["paused", "f1", "f2", "f3"]:
        for n in names + ["var"]:
            fa, fb = A / f"{tag}_{n}.bin", B / f"{tag}_{n}.bin"
            if not fa.exists() or not fb.exists():
                print(tag, n, "missing")
                continue
            xa, xb = fa.read_bytes(), fb.read_bytes()
            if n == "var":
                d = [i for i in range(min(len(xa), len(xb))) if xa[i] != xb[i]]
                print(f"{tag} var: {len(d)} bytes differ" + (f" at {[hex(0x800 + i) for i in d[:24]]}" if d else ""))
                continue
            d = np.nonzero(np.frombuffer(xa, np.uint8) != np.frombuffer(xb, np.uint8))[0]
            same = len(d) == 0
            if tag != "paused":
                allsame &= same
            rows = sorted(set((d // 160).tolist()))
            print(f"{tag} page {n}: {'IDENTICAL' if same else 'DIFFER'} {len(d)} bytes" + ("" if same else f" rows {rows[0]}..{rows[-1]}"))
    ev = (A / "entry_var.bin").read_bytes()
    shown = int.from_bytes(ev[0x94E - 0x800:0x94E - 0x800 + 4], "big")
    print(f"shown page at the pause: {shown:#x}")
    for n in names:                                          # the restore itself: the shown page at the pause entry against the page at the exit ($2612)
        xa, xb = (A / f"entry_{n}.bin").read_bytes(), (A / f"exit_{n}.bin").read_bytes()
        d = np.nonzero(np.frombuffer(xa, np.uint8) != np.frombuffer(xb, np.uint8))[0]
        rows = sorted(set((d // 160).tolist()))
        win = [r for r in rows if r < 140]
        print(f"help run, page {n}: entry vs exit: {len(d)} bytes differ, rows {rows[:3]}..{rows[-1:] }, window rows 0..139 differing: {len(win)}")
        if {"A": 0x23000, "B": 0x2AD00, "C": 0x81000}[n] == shown:
            allsame &= (len(win) == 0)
        else:
            print("   (the draw page: the scratch copy of the shown picture, redrawn by the next pass)")
    print("ALL IDENTICAL" if allsame else "MISMATCH")
    sys.exit(0 if allsame else 1)


def overlay_state(h: Hunter) -> str:
    """What the shown page holds in the rectangle: pixel colours there and how many are colour 8 (the overlay's text and frame)."""
    a, buf = page(h)
    px = box_pixels(buf)
    vals, cnt = np.unique(px, return_counts=True)
    c = dict(zip(vals.tolist(), cnt.tolist()))
    return f"shown={a:#x} box colours {c}"


def cmd_cold(a):
    from stharness import MACHINE_TOS, TOS
    import huntvis_cold as VC
    shot = str(SHOTS / f"help_cold_{a.machine}{'_floppy' if a.floppy else '_hd'}")
    SHOTS.mkdir(parents=True, exist_ok=True)
    V.WORK.mkdir(exist_ok=True)
    hmod = orig = None
    extra = ["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"] if a.machine == "tt" else []
    if a.floppy:
        from huntfloppy import HunterFloppy
        dt = {"ste": "1.62", "st": "1.04", "falcon": "4.04", "tt": "3.06"}
        h = HunterFloppy(GAME / a.game, None, drives=1, machine=a.machine, tos=TOS[a.tos or dt[a.machine]], memsize_kb=a.mem, extra=extra, fastfdc="no")
        VC.harden(h)
        ok = h.boot_floppy("none", blind=a.blind, pb_key_at=a.pb_at)
        print("BOOT", "OK" if ok else "FAILED", flush=True)
    else:
        import hunter as hmod
        orig = hmod.build_hd
        hmod.build_hd = lambda img, **k: orig(img, game=GAME / a.game, **k)
        h = hmod.Hunter(machine=a.machine, tos=TOS[a.tos] if a.tos else MACHINE_TOS[a.machine], memsize_kb=a.mem, extra=extra)
        VC.harden(h)
        if a.machine in ("st", "megast"):
            from huntpatch import blind_boot
            blind_boot(h)
        elif a.machine == "tt":                           # as huntvis_cold.cmd_hd
            time.sleep(10)
            h.keypress(57)
            time.sleep(3)
            if not h.wait_stage("title2", 200, 2):
                raise RuntimeError("screen title2 not reached")
            time.sleep(1.5)
            h.key("space", 0.3)
            for st_, xy in (("main", h.START_XY), ("games", h.ACTION_XY)):
                if not h.wait_stage(st_, 40, 2):
                    raise RuntimeError(f"screen {st_} not reached")
                h.goto(*xy, home_xy=h.HOME_XY)
                h.click()
            if not h.wait_stage("name", 30, 2):
                raise RuntimeError("name not reached")
            for c in "bench":
                h.key(c, 0.15)
                time.sleep(0.3)
            h.click()
            if not h.wait_stage("mission", 30, 2):
                raise RuntimeError("mission not reached")
            h.click()
            if not h.wait_stage("game", 60, 2):
                raise RuntimeError("game HUD not reached")
            time.sleep(1.0)
        else:
            h.boot_to_game()
    try:
        print(f"machine={a.machine} floppy={a.floppy} mem={a.mem}K in_game={h.in_game()} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()} "
              f"JAG_ST={h.peek(0x8D9E0, 1).hex()} tb mode={h.peek(0x8C1B2 + 4, 2).hex()} $260a={h.peek(0x260A, 8).hex()} $93={h.peek(0x899, 1).hex()}", flush=True)
        print("  running :", overlay_state(h), flush=True)
        h.key("p", 0.4)
        time.sleep(a.settle)
        print(f"  PAUSED  : $93={h.peek(0x899, 1).hex()} JAG_ST={h.peek(0x8D9E0, 1).hex()}", overlay_state(h), flush=True)
        h.shot(shot + "_paused.png")
        ad, buf = page(h)
        (V.WORK / (Path(shot).name + "_paused.pg")).write_bytes(buf)
        px = V.planar(buf)[24:112, 16:304]
        print("  pixels of colour 8 per text row band (rows 0-13, 14-27, 28-87):", [(int((px[a:b] == 8).sum())) for a, b in ((0, 14), (14, 28), (28, 88))], "; right pad column x 250..282 colour-8 pixels:", int((px[:, 250 - 16:282 - 16] == 8).sum()), flush=True)
        time.sleep(3)
        print(f"  +3 s    :", overlay_state(h), flush=True)
        h.key("p", 0.4)
        time.sleep(a.settle)
        print(f"  UNPAUSED: $93={h.peek(0x899, 1).hex()} in_game={h.in_game()}", overlay_state(h), flush=True)
        h.shot(shot + "_unpaused.png")
        print("  fps", h.fps(250), flush=True)
    finally:
        if orig:
            hmod.build_hd = orig
        h.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["shots", "hold", "ab", "cold"])
    ap.add_argument("--scene", nargs="+", default=["day"])
    ap.add_argument("--pad", default="none")
    ap.add_argument("--hz", type=int, default=50)
    ap.add_argument("--secs", type=float, default=10)
    ap.add_argument("--tb", action="store_true")
    ap.add_argument("--snap", default="1mb_foot_stand")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default=None)
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--game", default="build/help_hd")
    ap.add_argument("--floppy", action="store_true")
    ap.add_argument("--blind", action="store_true")
    ap.add_argument("--pb-at", type=float, default=12)
    ap.add_argument("--settle", type=float, default=3.0)
    ap.add_argument("--shift", type=int, default=0, help="ab --selftest: unpause the second control this many VBLs later")
    ap.add_argument("--cyc", type=int, default=0, help="ab --selftest: unpause the second control only when FrameCycles > this")
    ap.add_argument("--selftest", action="store_true", help="ab: compare the control with itself (noise floor of the gate)")
    ap.add_argument("--neg", action="store_true", help="negative control: help_neg (no restore)")
    a = ap.parse_args()
    global HELP
    HELP = "help_neg" if a.neg else "help_pause"
    {"shots": cmd_shots, "hold": cmd_hold, "ab": cmd_ab, "cold": cmd_cold}[a.cmd](a)


if __name__ == "__main__":
    main()
