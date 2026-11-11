#!/usr/bin/env python3
"""Live tests of patches/snd_core.s (STE DMA sound) on the Hunter snapshots and cold boots.

    snd_test.py mixcheck  [--snap 1mb_foot_stand] [--ticks 80] [--inject EFF:CH:VOL@SEC ...]
    snd_test.py record    NAME [--snap 1mb_car_stand] [--quiet] [--keys Up --keys-at S --release-at S]
                          [--inject EFF:CH:VOL@SEC ...] [--speed SEC:VALUE ...] [--secs 6] [--poll] [--no-patch]
    snd_test.py compare   WAV EFFECT,VOLUME,T_REQUEST,SECONDS ...      (one effect vs the model render)
    snd_test.py overlap   WAV EFF1,VOL1,T1,EFF2,VOL2,T2,SECONDS       (two-voice proof)
    snd_test.py cost      [--snap ..] [--cfg orig:2 patch:2:15 ...] [--vbls 300] [--fps-vbls 600]
    snd_test.py coldboot  [--machine ste --tos 1.62 --mem 1024] [--record NAME]
    snd_test.py ring      [--snap 1mb_foot_stand] [--vbls 900] [--mhz 8] [--keys Up] --live snd_hz --hz 60   (ring lead / underruns per top-up)
    snd_test.py dur       WAV [--thr 0.08]                                   (onset and end of each sound in a capture)
    mixcheck, record and ring take --live NAME (build/live/NAME.{img,json}: e.g. snd_hz = snd_core + hn_hz) and --hz 50|60
    (60: `w $ff820a $00` at the apply flip).  Work note: work/notes/timing.md.

`mixcheck`: breakpoints on the entry and the end of the mixer; for every tick the 1024-byte ring written by the 68000 is
compared with a Python model of the mixer (same 16.16 stepping, same bank file) -> bit exact or not.
`record`: Hatari's WAV capture (`--sound 50066`, shortcut recsound) of N seconds into work/snd/NAME.wav; effects are injected
into the driver request bytes ($11388+ch, volume word $1138c+2ch) exactly like the game's trigger routine $af0e does;
`--quiet` switches the game's own triggers off; `--speed` pokes the player's object speed word ($aa6).
`compare` / `overlap`: correlate a capture's DMA stream (one sample per 8-sample group of the 50066 Hz capture) with the model.
`cost`: cycles per VBL in the payload ($8e000..$8efff) and in the original driver, plus fps (flips of $ff8203), original vs
patched, with N injected sustained effects (13 = rotor, 11 = engine) at volume VOL (15 = the table-free path).
`coldboot`: boots build/snd_game (made with `huntpatch.py build --only snd_core --samples build/hunter_snd.bin --out
build/snd_game`) on a machine/TOS/RAM, reports marker, flags and payload mode, injects an explosion and records it.
Needs build/hunter_snd.bin (tools/snd_build.py) and build/live/snd.{img,json} (`huntpatch.py live --only snd_core
--samples build/hunter_snd.bin --out build/live/snd`).  Scratch config: HOME=/tmp/hsnd/home_<pid> (a copy of the user's Hatari
config whose szYMCaptureFileName is /tmp/hsnd/cap_<pid>.wav, so concurrent Hatari users do not share /tmp/hatari.wav).
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
from hunter import Hunter, SNAP  # noqa: E402
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))

LIVE = GAME / "build" / "live" / "snd"
HZ = 50                                  # --hz 60: `w $ff820a $00` is added to the live apply (60 Hz refresh)
BANKF = GAME / "build" / "hunter_snd.bin"
PATCH = GAME / "patches" / "snd_core.s"
REALHOME = Path.home()
# one scratch HOME (Hatari config incl. the WAV capture path) and one capture file per process: concurrent runs never share them
HOME = Path(f"/tmp/hsnd/home_{os.getpid()}")
CAP = Path(f"/tmp/hsnd/cap_{os.getpid()}.wav")
atexit.register(lambda: (shutil.rmtree(HOME, ignore_errors=True), CAP.unlink(missing_ok=True)))
BANK, RING, RL = 0x90000, 0x8F800, 1024
SV = 0x8F000


def setup_home() -> None:
    cfg = HOME / ".config" / "hatari"
    cfg.mkdir(parents=True, exist_ok=True)
    src = REALHOME / ".config" / "hatari" / "1040stfm.cfg"
    txt = re.sub(r"(?m)^szYMCaptureFileName.*$", f"szYMCaptureFileName = {CAP}", src.read_text())
    (cfg / "hatari.cfg").write_text(txt)
    nv = REALHOME / ".config" / "hatari" / "hatari.nvram"
    if nv.exists():
        shutil.copy(nv, cfg / "hatari.nvram")


def make(snap: str, machine: str = "ste", sound: bool = True, **kw) -> Hunter:
    setup_home()
    os.environ["HOME"] = str(HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    extra = ["--sound", "50066"] if sound else []
    return Hunter(snapshot=str(SNAP / (snap if snap.endswith(".sav") else snap + ".sav")), machine=machine, extra=extra, **kw)


def pk(h: Hunter, addr: int, n: int, wait: float = 0.6) -> bytes:
    out = h.debug(f"m ${addr:x} {n}", wait)
    got = {}
    for m in re.finditer(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", out, re.M | re.I):
        a = int(m.group(1), 16)
        for i, x in enumerate(m.group(2).split()):
            got[a + i] = int(x, 16)
    return bytes(got.get(addr + i, 0) for i in range(n))


def labels() -> dict[str, int]:
    """Label addresses of the blob (from a vasm listing)."""
    out = Path("/tmp/hsnd/lab.bin")
    lst = Path("/tmp/hsnd/lab.lst")
    subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(out), "-L", str(lst), str(PATCH)], check=True)
    res = {}
    lines = lst.read_text(errors="replace").splitlines()
    for i, ln in enumerate(lines):
        m = re.search(r"^\s*(\d+:)?([0-9A-F]{8})?.*?\d+:\s*([A-Za-z_][\w.]*):", ln)
        if m and m.group(3):
            addr = None
            for j in (i, i + 1, i + 2):
                mm = re.match(r"^\d\d:([0-9A-F]{8})", lines[j])
                if mm:
                    addr = int(mm.group(1), 16)
                    break
            if addr is not None:
                res[m.group(3)] = addr
    return res


def apply_live(h: Hunter, extra_cmds=(), timeout: float = 90, at: int = 0x5FEE) -> None:
    """loadbin the payload image and poke the sites at the next flip."""
    spec = json.loads(Path(str(LIVE) + ".json").read_text())
    cmds = [f"loadbin {LIVE}.img ${spec['img_base']:x}"]
    for s in spec["sites"]:
        cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
    cmds += list(extra_cmds)
    if HZ == 60:
        cmds.append("w $ff820a $00")
    f = h.R / "apply.txt"
    f.write_text("\n".join(cmds) + "\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${at:x} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("live apply")
        time.sleep(0.3)
    time.sleep(0.5)


def inject(h: Hunter, eff: int, ch: int, vol: int) -> None:
    """What the game's trigger routine $af0e does: request byte + volume word of the channel."""
    h.debug(f"w ${0x11388 + ch:x} ${eff:02x}", 0.15)
    h.debug(f"w ${0x1138C + 2 * ch:x} $00 ${vol:02x}", 0.15)


# ---- Python model of the mixer ------------------------------------------------------------------------------
def model_mix(bank: bytes, sv: bytes, nv: int, v_wr: int, n8: int, ring: bytearray) -> tuple[list, int]:
    """Mix n8*8 samples for the voices in `sv` (state block at SV) into `ring`; returns (updated voices, new wr)."""
    vox = []
    for off in (0x40, 0x68):
        ch, mode = sv[off], sv[off + 2]
        base, vt = struct.unpack_from(">II", sv, off + 4)
        idx, frac, incf, inci, end, loop, per = struct.unpack_from(">7H", sv, off + 12)
        vox.append(dict(ch=ch, mode=mode, base=base, vt=vt, idx=idx, frac=frac, incf=incf, inci=inci, end=end, loop=loop))
    act = [v for v in vox if v["ch"] < 0x80]
    assert len(act) == nv, (len(act), nv)
    w = v_wr
    for _ in range(n8 * 8):
        acc = 0
        for v in act:
            s = bank[v["base"] - BANK + v["idx"]]
            k = (v["vt"] - (BANK + 0x1000)) >> 8
            acc += struct.unpack("b", bytes([s if v["mode"] else bank[0x1000 + k * 256 + s]]))[0]
            f = v["frac"] + v["incf"]
            v["idx"] = (v["idx"] + v["inci"] + (f >> 16)) & 0xFFFF
            v["frac"] = f & 0xFFFF
        ring[w] = acc & 0xFF
        w = (w + 1) % RL
    return vox, w


def parse_regs(txt: str) -> dict[str, int]:
    r = {}
    for k, v in re.findall(r"\b([DA][0-7])\s+([0-9A-Fa-f]{8})", txt):
        r[k] = int(v, 16)
    return r


def cmd_mixcheck(a) -> int:
    lab = labels()
    bank = BANKF.read_bytes()
    h = make(a.snap, sound=False)
    try:
        time.sleep(2)
        apply_live(h, ["w $af0e $4e $75", "w $11398 $00 $00 $00", "w $11388 $ff $ff $ff"])
        time.sleep(1.0)
        pre = lab["snd_mix"]
        cf_pre = h.R / "pre.txt"
        cf_pre.write_text("r\nm $8f000 160\n")
        cf_post = h.R / "post.txt"
        cf_post.write_text(f"m $8f000 160\nm ${RING:x} 1024\n")
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b pc = ${pre:x} :trace :file {cf_pre}")
        time.sleep(0.2)
        # the rts of snd_mix is the word right before `mixz:`
        post_pc = lab["mixz"] - 2
        h.cmd(f"hatari-debug b pc = ${post_pc:x} :trace :file {cf_post}")
        time.sleep(0.2)
        start = len(h._logtext())
        # scenario: the --inject requests, in order
        t0 = time.time()
        for spec in a.inject:
            m = re.fullmatch(r"(\d+):(\d+):(\d+)@([\d.]+)", spec)
            while time.time() - t0 < float(m.group(4)):
                time.sleep(0.05)
            inject(h, int(m.group(1)), int(m.group(2)), int(m.group(3)))
        time.sleep(a.ticks / 50 * 2.0 + 1)
        h.debug("b all", 0.3)
        log = h._logtext()[start:]
    finally:
        h.close()
    # pair up hits
    blocks = re.split(r"CPU breakpoint condition\(s\) matched", log)[1:]
    pres, posts = [], []
    for b in blocks:
        if re.search(r"pc = \$%x" % pre, b, re.I) or ("D0 " in b and "m $8f000" in b and "8F800" not in b):
            pres.append(b)
        elif "0008F800" in b or "0008f800" in b.lower():
            posts.append(b)
    n_ok = n_bad = 0
    cover: dict = {}
    for i, (b1, b2) in enumerate(zip(pres, posts)):
        regs = parse_regs(b1)

        def blob(txt, base, n):
            got = {}
            for m in re.finditer(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", txt, re.M | re.I):
                ad = int(m.group(1), 16)
                for k, x in enumerate(m.group(2).split()):
                    got[ad + k] = int(x, 16)
            return bytes(got.get(base + k, 0) for k in range(n))
        sv0 = blob(b1, SV, 160)
        sv1 = blob(b2, SV, 160)
        ring1 = blob(b2, RING, RL)
        n8, nv = regs["D0"] & 0xFFFF, regs["D5"] & 0xFFFF
        wr0 = struct.unpack_from(">H", sv0, 4)[0]
        want = bytearray(RL)
        vox, wr1 = model_mix(bank, sv0, nv, wr0, n8, want)
        span = [(wr0 + k) % RL for k in range(n8 * 8)]
        ok = all(want[p] == ring1[p] for p in span)
        # voice state after
        v_after = []
        for off in (0x40, 0x68):
            v_after.append(struct.unpack_from(">HH", sv1, off + 12))
        mv = [(v["idx"], v["frac"]) for v in vox if v["ch"] < 0x80]
        hv = [v_after[k] for k in range(2) if sv0[0x40 + 0x28 * k] < 0x80]
        ok2 = mv == hv
        n_ok += ok and ok2
        n_bad += not (ok and ok2)
        cover[(nv, tuple(v["mode"] for v in vox if v["ch"] < 0x80))] = cover.get((nv, tuple(v["mode"] for v in vox if v["ch"] < 0x80)), 0) + 1
        if not (ok and ok2) or i < 3:
            print(f"tick {i}: n8={n8} voices={nv} wr={wr0} ring {'OK' if ok else 'DIFF'} voice-state {'OK' if ok2 else 'DIFF'} {mv} {hv}")
    print("coverage (voices, modes 0=table 1=direct): " + ", ".join(f"{k}: {v}" for k, v in sorted(cover.items())))
    print(f"mixcheck: {n_ok} ticks bit-exact, {n_bad} different ({len(pres)} pre / {len(posts)} post hits)")
    return 1 if n_bad or not n_ok else 0


def cmd_record(a) -> int:
    h = make(a.snap, machine=a.machine)
    inj = []
    for s in a.inject or []:
        m = re.fullmatch(r"(\d+):(\d+):(\d+)@([\d.]+)", s)
        inj.append((float(m.group(4)), int(m.group(1)), int(m.group(2)), int(m.group(3))))
    inj.sort()
    try:
        time.sleep(2)
        if not a.no_patch:
            quiet = []
            if a.quiet:        # game triggers off ($af0e = rts), driver channels idle: only injected effects sound
                quiet = ["w $af0e $4e $75", "w $11398 $00 $00 $00", "w $11388 $ff $ff $ff"]
            apply_live(h, quiet)
            time.sleep(1.0)
        elif a.quiet:
            h.debug("w $af0e $4e $75", 0.2)
        if CAP.exists():
            CAP.unlink()
        h.cmd("hatari-shortcut recsound")
        t0 = time.time()
        held = False
        spd_sched = sorted((float(x.split(":")[0]), int(x.split(":")[1])) for x in (a.speed or []))
        cur_speed = None
        for at, eff, ch, vol in inj:
            while time.time() - t0 < at:
                time.sleep(0.05)
            inject(h, eff, ch, vol)
        while time.time() - t0 < a.secs:
            while spd_sched and time.time() - t0 >= spd_sched[0][0]:
                cur_speed = spd_sched.pop(0)[1]
            if cur_speed is not None:
                h.debug(f"w $aa6 $00 ${cur_speed & 0xff:02x}", 0.05)
            if a.keys and not held and time.time() - t0 >= a.keys_at:
                h.hold(*a.keys)
                held = True
            if a.keys and held and a.release_at and time.time() - t0 >= a.release_at:
                h.release(*a.keys)
                a.keys, a.release_at = None, 0
                held = False
            if a.poll:
                sv = pk(h, SV + 0x40, 0x50, 0.25)
                spd = pk(h, 0xAA6, 2, 0.25)
                row = []
                for off in (0, 0x28):
                    ch = sv[off]
                    incf, inci = struct.unpack_from(">HH", sv, off + 16)
                    row.append("-" if ch >= 0x80 else f"ch{ch} inc={(inci * 65536 + incf) / 65536:.4f} per={struct.unpack_from('>H', sv, off + 24)[0]}")
                print(f"{time.time() - t0:5.1f}s speed={struct.unpack('>h', spd)[0]:3d} v0:{row[0]:28s} v1:{row[1]}")
            else:
                time.sleep(0.1)
        h.cmd("hatari-shortcut recsound")
        time.sleep(1.0)
        if a.keys and held:
            h.release(*a.keys)
    finally:
        h.close()
    out = Path(a.out_dir) / f"{a.name}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(CAP, out)
    print("wrote", out)
    return 0


def cmd_cost(a) -> int:
    """Cycles per VBL inside the payload ($8e000..$8efff) and in the original driver ($10fb2..$11656), plus fps, for the
    original game and the patched game with 0/1/2 sustained effects (13 = rotor, 11 = engine) injected.  The game's own
    triggers are switched off ($af0e = rts) in every run so that the runs differ only in the payload and the injected loops."""
    rows = []
    for snap in a.snap:
        for cfg in a.cfg:
            parts = cfg.split(":")
            kind, nv = parts[0], int(parts[1])
            vol = int(parts[2]) if len(parts) > 2 else 15
            h = make(snap, sound=False)
            try:
                time.sleep(2)
                keys = ["Up"] if any(k in snap for k in ("walk", "drive", "turn")) else []
                quiet = ["w $af0e $4e $75", "w $11398 $00 $00 $00", "w $11388 $ff $ff $ff"]
                if kind == "patch":
                    apply_live(h, quiet)
                else:
                    f = h.R / "q.txt"
                    f.write_text("\n".join(quiet) + "\n")
                    st = len(h._logtext())
                    h.cmd(f"hatari-debug b pc = $5fee :trace :once :file {f}")
                    while "Removed CPU breakpoint" not in h._logtext()[st:]:
                        time.sleep(0.3)
                time.sleep(0.5)
                for eff, ch in [(13, 2), (11, 1)][:nv]:
                    inject(h, eff, ch, vol)
                    time.sleep(0.2)
                if keys:
                    h.hold(*keys)
                time.sleep(1.5)
                prof = h.profile_cc(a.vbls)
                fps = h.fps(a.fps_vbls) if a.fps_vbls else {}
                if keys:
                    h.release(*keys)
                tot = sum(c for ad, (c, n) in prof.items())
                nvbl = tot / 160256
                pay = sum(c for ad, (c, n) in prof.items() if 0x8E000 <= ad < 0x8F000)
                drv = sum(c for ad, (c, n) in prof.items() if 0x10FB2 <= ad < 0x11656)
                lab = labels()
                order = sorted((v, k) for k, v in lab.items() if 0x8E000 <= v < 0x8F000 and not k.startswith("."))
                brk = []
                for i, (v, k) in enumerate(order):
                    end = order[i + 1][0] if i + 1 < len(order) else 0x8F000
                    cy = sum(c for ad, (c, n) in prof.items() if v <= ad < end)
                    if cy:
                        brk.append(f"{k}={cy / nvbl:.0f}")
                print("   ", snap, cfg, " ".join(brk))
                rows.append((snap, cfg, pay / nvbl, drv / nvbl, nvbl, fps.get("fps"), fps.get("vbls_per_frame")))
                print(rows[-1], flush=True)
            finally:
                h.close()
    print(f"{'snapshot':18s} {'config':8s} {'payload cyc/VBL':>16s} {'(% of 160256)':>13s} {'orig driver':>12s} {'fps':>6s} {'VBL/frame':>9s}")
    for r in rows:
        print(f"{r[0]:18s} {r[1]:8s} {r[2]:16.0f} {100 * r[2] / 160256:12.1f}% {r[3]:12.0f} {r[5] if r[5] is None else round(r[5], 2)!s:>6s} {r[6] if r[6] is None else round(r[6], 2)!s:>9s}")
    return 0


def load_wav(path: str | Path) -> tuple[np.ndarray, int]:
    w = wave.open(str(path))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, w.getnchannels()).astype(float).mean(axis=1)
    return x, w.getframerate()


def render(bank: bytes, eff: int, vol: int, n: int, inc: int | None = None) -> np.ndarray:
    """The mixer's output for one voice of effect `eff` at game volume `vol` (the Python twin of mix1)."""
    base, end, loop, per, flags, i0 = struct.unpack(">IHHHHI", bank[0x100 + 16 * eff:0x100 + 16 * eff + 16])
    inc = inc or i0
    out = np.zeros(n)
    ph = 0
    for t in range(n):
        idx = ph >> 16
        if idx >= end:
            if not loop:
                break
            ph -= loop << 16
            idx = ph >> 16
        s = bank[base - BANK + idx]
        out[t] = struct.unpack("b", bytes([bank[0x1000 + vol * 256 + s]]))[0]
        ph += inc
    return out


def compare(path, eff: int, vol: int, t_inject: float, dur: float, inc: int | None = None) -> dict:
    """Correlate a Hatari WAV capture (50066 Hz, DMA stream 8x held) with the model render of one effect.
    The onset is the first non-zero sample after t_inject; the DMA stream is taken at one sample per 8-sample group."""
    bank = BANKF.read_bytes()
    x, sr = load_wav(path)
    a = int((t_inject - 0.05) * sr)
    nz = int(np.nonzero(np.abs(x[a:]) > 1)[0][0]) + a
    rate = sr / 8
    n = int(dur * rate)
    ref = render(bank, eff, vol, n, inc)
    best = (0.0, 0, 0.0)
    for ph in range(8):
        y = x[nz - 96 + ph::8][: n + 60]
        for lag in range(0, 24):
            seg = y[lag:lag + n]
            m = min(len(seg), len(ref))
            if m < 100 or np.std(seg[:m]) == 0:
                continue
            r = np.corrcoef(seg[:m], ref[:m])[0, 1]
            if abs(r) > abs(best[0]):
                best = (r, ph * 100 + lag, float((seg[:m] @ ref[:m]) / (ref[:m] @ ref[:m])))
    return dict(effect=eff, vol=vol, onset_s=nz / sr, delay_ms=(nz / sr - t_inject) * 1000, rho=best[0], gain=best[2],
                phase_lag=(best[1] // 100, best[1] % 100 - 12))


def overlap(path, e1: int, v1: int, t1: float, e2: int, v2: int, t2: float, dur: float) -> dict:
    """Two-voice proof. Voice 1 = a loop requested at t1, voice 2 = a one-shot requested at t2 (both in the Hatari capture).
    Model = render(voice1) + render(voice2 shifted by the unknown tick delay, searched).  The capture is compared with the
    model in 0.2 s windows (lag searched +-40 DMA samples per window: Hatari's DMA clock is 6258.5 Hz against the 6258.25
    used to split the 50066 Hz capture, so the alignment slips by one sample every ~4 s; that is not a mixer error)."""
    bank = BANKF.read_bytes()
    x, sr = load_wav(path)
    rate = sr / 8
    a = int((t1 - 0.05) * sr)
    nz = int(np.nonzero(np.abs(x[a:]) > 1)[0][0]) + a
    n = int(dur * rate)
    r1 = render(bank, e1, v1, n)
    t2s = int((t2 - t1) * rate)
    best = (0, None)
    for ph in range(8):
        y = x[nz - 96 + ph::8][: n + 80]
        for lag in range(24):
            seg = y[lag:lag + t2s - 400]
            c = np.corrcoef(seg, r1[:len(seg)])[0, 1]
            if abs(c) > abs(best[0]):
                best = (c, (ph, lag))
    ph, lag = best[1]
    y = x[nz - 96 + ph::8][lag:]
    m1 = t2s - 400
    g = float((y[:m1] @ r1[:m1]) / (r1[:m1] @ r1[:m1]))
    r2 = render(bank, e2, v2, int(3.2 * rate))
    w = int(0.2 * rate)
    bestd = (0, 0)
    for d in range(-int(0.04 * rate), int(0.08 * rate), 1):
        i0 = t2s + d
        L = min(len(r2), int(1.2 * rate))
        mix = r1[i0:i0 + L] + r2[:L]
        c = np.corrcoef(y[i0:i0 + L], mix)[0, 1]
        if abs(c) > abs(bestd[0]):
            bestd = (c, d)
    d = bestd[1]
    k = min(len(r2), n - t2s - d)
    mixes = {"two voices": r1.copy(), "voice 1 only": r1.copy(), "voice 2 only": np.zeros(n)}
    mixes["two voices"][t2s + d:t2s + d + k] += r2[:k]
    mixes["voice 2 only"][t2s + d:t2s + d + k] += r2[:k]
    t_lo = t2s / rate + t1 + d / rate
    t_hi = t_lo + min(len(r2) / rate, 2.4)
    out = dict(delay1_ms=(nz / sr - t1) * 1000, rho_voice1_alone_before_t2=abs(best[0]), gain=g,
               voice2_delay_ms=d / rate * 1000)
    for name, mix in mixes.items():
        vals = []
        for i in range(0, n - w - 100, w // 2):
            tt = i / rate + t1
            if tt < t_lo or tt + 0.2 > t_hi:
                continue
            res = []
            for l in range(-40, 41):
                aa = y[i + l:i + l + w] if i + l >= 0 else None
                if aa is None or len(aa) < w or aa.std() == 0 or mix[i:i + w].std() == 0:
                    continue
                res.append(abs(np.corrcoef(aa, mix[i:i + w])[0, 1]))
            vals.append(max(res) if res else 0.0)
        out[f"rho mean in the overlap, {name}"] = float(np.mean(vals))
        out[f"rho min in the overlap, {name}"] = float(np.min(vals))
    out["overlap_windows"] = len(vals)
    return out


def cmd_overlap(a) -> int:
    e1, v1, t1, e2, v2, t2, d = a.spec.split(",")
    r = overlap(a.wav, int(e1), int(v1), float(t1), int(e2), int(v2), float(t2), float(d))
    for k, v in r.items():
        print(f"  {k:22s} {v:+.4f}" if isinstance(v, float) else f"  {k:22s} {v}")
    return 0


def cmd_compare(a) -> int:
    for spec in a.spec:
        eff, vol, t, d = spec.split(",")
        r = compare(a.wav, int(eff), int(vol), float(t), float(d))
        print(f"effect {r['effect']:2d} vol {r['vol']:2d}: onset {r['onset_s']:.3f} s (+{r['delay_ms']:.0f} ms after the request)  "
              f"|rho| = {abs(r['rho']):.4f} (sign {'-' if r['rho'] < 0 else '+'}), gain {abs(r['gain']):.1f} per 8-bit step")
    return 0


def cmd_coldboot(a) -> int:
    """Cold boot the patched build (build/snd_game, made with `huntpatch.py build --only snd_core --samples
    build/hunter_snd.bin --out build/snd_game`) on MACHINE/TOS/MEM, check marker/flags/payload mode, inject an explosion and
    record the sound.  ste: expect SV mode 2 + DMA samples; st/megast: mode 1 and the original YM sound."""
    import hunter
    from stharness import TOS
    setup_home()
    os.environ["HOME"] = str(HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    orig = hunter.build_hd
    gdir = GAME / "build" / a.game
    hunter.build_hd = lambda img, **k: orig(img, game=gdir, **k)
    h = None
    try:
        h = hunter.Hunter(machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=["--sound", "50066"])
        stage = h._stage
        h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
        if a.machine in ("st", "megast", "tt", "falcon"):
            import huntpatch
            huntpatch.blind_boot(h)            # the reference crops are STE pictures
        else:
            h.boot_to_game()
        mk, fl = h.peek(0x8BFF8, 4), h.peek(0x8BFF0, 4)
        time.sleep(1.0)
        sv = pk(h, SV, 8)
        print(f"BOOT machine={a.machine} tos={a.tos} mem={a.mem}K in_game={h.in_game()} MARKER={mk!r} FLAGS={fl.hex()} "
              f"payload mode={sv[0]} (2 = DMA sound, 1 = original YM) in3d={sv[1]} dma_on={sv[2]}")
        if a.record:
            if CAP.exists():
                CAP.unlink()
            h.cmd("hatari-shortcut recsound")
            t0 = time.time()
            time.sleep(0.5)
            inject(h, 3, 1, 12)
            time.sleep(0.3)
            sv = pk(h, SV, 8)
            print(f"  after the injected explosion: mode={sv[0]} dma_on={sv[2]} $ff8901={pk(h, 0xFF8901, 1).hex()}")
            while time.time() - t0 < a.secs:
                time.sleep(0.1)
            h.cmd("hatari-shortcut recsound")
            time.sleep(1.0)
            out = Path(a.out_dir) / f"{a.record}.wav"
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(CAP, out)
            x, sr = load_wav(out)
            print(f"  wrote {out}: {len(x) / sr:.1f} s, rms {x.std():.0f}, peak {np.abs(x).max():.0f}")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"BOOT FAILED: {e!r}")
        if h:
            try:
                h.shot(str(GAME / "work" / "snd" / f"fail_{a.machine}_{a.mem}.png"))
            except Exception:  # noqa: BLE001
                pass
        return 1
    finally:
        hunter.build_hd = orig
        if h:
            h.close()


def lst_addr(token: str) -> int:
    """Address of the listing line that contains `token` (e.g. a local label `.okp:`) in a vasm listing of the patch."""
    out = Path("/tmp/hsnd/lab2.bin")
    lst = Path("/tmp/hsnd/lab2.lst")
    subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(out), "-L", str(lst), str(PATCH)], check=True)
    for ln in lst.read_text(errors="replace").splitlines():
        m = re.match(r"^\d\d:([0-9A-F]{8})\s+(?:[0-9A-F]+)?\s*\t\s*\d+:\s*" + re.escape(token), ln)
        if m:
            return int(m.group(1), 16)
    raise KeyError(token)


def cmd_ring(a) -> int:
    """Ring health of the mixer at 50 or 60 Hz: at every top-up (`.okp`) the lead (samples the write cursor is ahead of the
    DMA position, D1) and the number of underrun resyncs (the `addi.w #16,d0` path), with two loops and re-injected explosions."""
    okp = lst_addr(".okp:")
    under = okp - 14                                     # addi.w #16,d0 / andi.w / move.w / moveq #16,d1 before `.okp`
    h = make(a.snap, sound=False)
    try:
        time.sleep(2)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        quiet = ["w $af0e $4e $75", "w $11398 $00 $00 $00", "w $11388 $ff $ff $ff"]
        cf = h.R / "lead.txt"
        cf.write_text("r\ne VBL\n")
        cu = h.R / "under.txt"
        cu.write_text("e VBL\n")
        end = h.R / "end.txt"
        end.write_text("b all\n")
        v0 = h.vbl()
        at = v0 + 40
        pre = list(quiet) + ["w $11389 $0b", "w $1138e $00 $0f", "w $1138a $0d", "w $11390 $00 $0f"]   # engine (11) ch1 + rotor (13) ch2 at volume 15
        pre += [f"b pc = ${okp:x} :trace :file {cf}", f"b pc = ${under:x} :trace :file {cu}"]
        # explosions (effect 3, channel 0) every 70 VBL
        inj = []
        for k in range(1, a.vbls // 70):
            f = h.R / f"inj{k}.txt"
            f.write_text("w $11388 $03\nw $1138c $00 $0c\n")
            inj.append(f"b VBL > {at + 70 * k} :trace :once :file {f}")
        pre.append(f"b VBL > {at + a.vbls} :trace :once :file {end}")
        app = h.R / "ring_apply.txt"
        apply_live(h, [])                                # the live image (and 60 Hz) at the next flip; then arm the trace commands
        app.write_text("\n".join(pre + inj) + "\n")
        if len(max(pre + inj, key=len)) > 235:
            raise ValueError("line too long")
        st = len(h._logtext())
        if a.keys:
            h.hold(*a.keys)
        h.cmd(f"hatari-debug b VBL > {v0 + 60} && pc = $5fee :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while h._logtext()[st:].count("Removed CPU breakpoint") < 2 + len(inj):
            if time.time() - t > 600:
                raise TimeoutError(h._logtext()[-1500:])
            time.sleep(0.5)
        time.sleep(0.5)
        log = h._logtext()[st:]
        if a.keys:
            h.release(*a.keys)
    finally:
        h.close()
    leads = []
    for blk in log.split("CPU breakpoint condition(s) matched")[1:]:
        if re.match(r"\s*\d+ times\.\s*pc = \$%x" % okp, blk, re.I):
            m = re.search(r"D1\s+([0-9A-Fa-f]{8})", blk)
            if m:
                leads.append(int(m.group(1), 16) & 0xFFFF)
    ublk = [blk for blk in log.split("CPU breakpoint condition(s) matched")[1:] if re.match(r"\s*\d+ times\.\s*pc = \$%x" % under, blk, re.I)]
    nunder = len(ublk)
    uv = [int(re.search(r"#(\d+) \(dec\)", b).group(1)) - v0 for b in ublk if re.search(r"#(\d+) \(dec\)", b)]
    ticks = len(leads)
    if getattr(a, "debug", False):
        print(ublk[:2])
    if not leads:
        print("RING no top-ups seen\n" + log[-800:])
        return 1
    print(f"RING hz={a.hz} mhz={a.mhz} snap={a.snap} vbl={a.vbls}: top-ups {ticks}, lead before top-up min {min(leads)} max {max(leads)} "
          f"mean {sum(leads) / len(leads):.1f} samples (TARGET 192; 1 VBL = {6258.3 / a.hz:.1f} samples), underrun resyncs {nunder}"
          + (f" at VBL +{uv}" if uv else ""))
    return 0


def cmd_dur(a) -> int:
    """Onset and end of the sound in a Hatari WAV capture of the DMA stream (one sample per 8-sample group of the 50066 Hz capture)."""
    x, sr = load_wav(a.wav)
    y = x[::8] if sr > 40000 else x
    r = sr / 8 if sr > 40000 else sr
    thr = a.thr * np.abs(y).max()
    idx = np.nonzero(np.abs(y) > thr)[0]
    if not len(idx):
        print("DUR silent")
        return 1
    # activity per 10 ms block: runs separated by more than 150 ms of quiet are separate sounds
    blk = int(r * 0.01)
    act = np.array([np.abs(y[i:i + blk]).max() > thr for i in range(0, len(y) - blk, blk)])
    runs, start = [], None
    quiet = 0
    for i, v in enumerate(act):
        if v:
            if start is None:
                start = i
            last = i
            quiet = 0
        elif start is not None:
            quiet += 1
            if quiet > 15:
                runs.append((start * 0.01, (last + 1) * 0.01))
                start = None
    if start is not None:
        runs.append((start * 0.01, (last + 1) * 0.01))
    print(f"DUR {a.wav}: {len(y) / r:.2f} s capture, peak {np.abs(y).max():.0f}; sounds (onset-end s, length s): "
          + ", ".join(f"{s:.2f}-{e:.2f} ({e - s:.2f})" for s, e in runs))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mixcheck")
    m.add_argument("--snap", default="1mb_foot_stand")
    m.add_argument("--ticks", type=int, default=60)
    m.add_argument("--inject", nargs="*", default=["13:2:10@0", "3:1:12@0.6"], help="EFF:CH:VOL@SECONDS (volume 15 = table-free path)")
    r = sub.add_parser("record")
    r.add_argument("name")
    r.add_argument("--snap", default="1mb_foot_stand")
    r.add_argument("--keys", nargs="*")
    r.add_argument("--inject", nargs="*")
    r.add_argument("--quiet", action="store_true", help="disable the game's own effect triggers ($af0e) and idle the driver channels")
    r.add_argument("--keys-at", type=float, default=0.0)
    r.add_argument("--speed", nargs="*", help="poke the player's object speed word ($aa6) from SEC:VALUE pairs, e.g. 1:3 4:9 7:20")
    r.add_argument("--release-at", type=float, default=0.0)
    r.add_argument("--secs", type=float, default=6)
    r.add_argument("--machine", default="ste")
    r.add_argument("--no-patch", action="store_true")
    r.add_argument("--poll", action="store_true", help="print the voice phase increments and the object speed while recording")
    r.add_argument("--out-dir", default=str(GAME / "work" / "snd"))
    cp = sub.add_parser("compare")
    cp.add_argument("wav")
    cp.add_argument("spec", nargs="+", help="EFFECT,VOLUME,T_INJECT,DURATION_S")
    ov = sub.add_parser("overlap")
    ov.add_argument("wav")
    ov.add_argument("spec", help="EFF1,VOL1,T1,EFF2,VOL2,T2,DURATION_S (voice 1 = loop started at T1; voice 2 starts at T2)")
    rg = sub.add_parser("ring")
    rg.add_argument("--snap", default="1mb_foot_stand")
    rg.add_argument("--vbls", type=int, default=900)
    rg.add_argument("--mhz", type=int, default=8)
    rg.add_argument("--debug", action="store_true")
    rg.add_argument("--keys", nargs="*", default=[])
    cb = sub.add_parser("coldboot")
    cb.add_argument("--machine", default="ste")
    cb.add_argument("--tos", default="1.62")
    cb.add_argument("--mem", type=int, default=1024)
    cb.add_argument("--game", default="snd_game")
    cb.add_argument("--record", default=None, help="WAV name (written to work/snd/)")
    cb.add_argument("--secs", type=float, default=6)
    cb.add_argument("--out-dir", default=str(GAME / "work" / "snd"))
    c = sub.add_parser("cost")
    c.add_argument("--snap", nargs="*", default=["1mb_foot_stand"])
    c.add_argument("--cfg", nargs="*", default=["orig:0", "orig:2", "patch:0", "patch:1", "patch:2"], help="KIND:N, KIND orig|patch, N injected loops")
    c.add_argument("--vbls", type=int, default=300)
    c.add_argument("--fps-vbls", type=int, default=0)
    for sp in (m, r, rg):
        sp.add_argument("--live", default=None, help="live patch image under build/live/ (default snd): e.g. snd_hz = snd_core + hn_hz")
        sp.add_argument("--hz", type=int, default=50, choices=(50, 60), help="force the refresh (60: poke $ff820a at the apply flip)")
    dp = sub.add_parser("dur")
    dp.add_argument("wav")
    dp.add_argument("--thr", type=float, default=0.08, help="activity threshold, fraction of the peak of the 6258 Hz stream")
    a = ap.parse_args()
    global LIVE, HZ
    if getattr(a, "live", None):
        LIVE = GAME / "build" / "live" / a.live
    HZ = getattr(a, "hz", 50)
    return {"mixcheck": cmd_mixcheck, "record": cmd_record, "cost": cmd_cost, "compare": cmd_compare, "coldboot": cmd_coldboot, "overlap": cmd_overlap, "ring": cmd_ring, "dur": cmd_dur}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
