#!/usr/bin/env python3
"""Gates for the Powermonger STE DMA sound patches (snd_core snd_start snd_stop snd_setup; work/notes/snd.md).

    python3 tools/pmsnd.py live [--mode 0|1]                       # build/live/snd.{img,json} (pmpatch.py live, STE flags)
    python3 tools/pmsnd.py cost  SNAP MHZ VBLS [--orig] [--mode M]  # cycles/VBL by region while a sample plays + fps
    python3 tools/pmsnd.py wav   NAME EFFECT SECS [--orig] [--mode M] [--st] [--loop]   # Hatari WAV capture of one injected effect
    python3 tools/pmsnd.py cmp   A.wav B.wav                        # onset-aligned comparison of two captures
    python3 tools/pmsnd.py pairs                                    # (chunk, rate) statistics + pitch error of the direct-DMA alternative

The effect is injected by writing the sequencer state exactly as $1b978 does ($2cba2 sequence pointer, $2c996 step 0, $2c994 loop,
$2c992 active) at a loop-top stop, in the original and the patched run alike.  A patch is applied to the snapshot live at a loop-top
stop: loadbin of the payload image, the site bytes, then `r pc=$d0010` (snd_live: Microwire setup, then back to $12fd8).
"""
from __future__ import annotations

import argparse
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
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from pm import PM, SNAP  # noqa: E402

TMP = Path("/tmp/psnd")
HOME = TMP / "home"
CAP = TMP / "cap.wav"
LIVE = GAME / "build" / "live" / "snd"
OUT = GAME / "work" / "snd"
LOOPTOP = 0x12FD8
SEQTAB, CHTAB = 0x2C9A0, 0x2CBA6
STATE = 0xD0E00
SNDNAMES = ["snd_core", "snd_start", "snd_stop", "snd_setup"]


def setup_home() -> None:
    cfg = HOME / ".config" / "hatari"
    cfg.mkdir(parents=True, exist_ok=True)
    src = Path.home() / ".config" / "hatari" / "hatari.cfg"
    txt = re.sub(r"(?m)^szYMCaptureFileName.*$", f"szYMCaptureFileName = {CAP}", src.read_text())
    (cfg / "hatari.cfg").write_text(txt)
    nv = Path.home() / ".config" / "hatari" / "hatari.nvram"
    if nv.exists():
        shutil.copy(nv, cfg / "hatari.nvram")


def make(snap: str | None, machine: str = "ste", **kw) -> PM:
    """A PM (restored snapshot or cold boot) with WAV capture possible: `--sound 50066`, dummy SDL audio, private YM capture path."""
    TMP.mkdir(exist_ok=True)
    setup_home()
    os.environ["HOME"] = str(HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    extra = ["--sound", "50066"] + kw.pop("extra", [])
    if snap:
        return PM(snapshot=str(SNAP / (snap if snap.endswith(".sav") else snap + ".sav")), machine=machine, extra=extra, **kw)
    return PM(machine=machine, extra=extra, **kw)


def build_live(ste: bool = True) -> str:
    TMP.mkdir(exist_ok=True)
    LIVE.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(HERE / "pmpatch.py"), "live", "--only", *SNDNAMES, "--out", str(LIVE)] + ([] if ste else ["--no-ste"])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    shutil.copy(str(LIVE) + ".img", TMP / "live.img")
    return str(LIVE)


def at_loop(h: PM, cmds: list[str], timeout: float = 120) -> None:
    """Run debugger commands at the next loop top ($12fd8)."""
    f = h.R / "atloop.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${LOOPTOP:x} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("loop-top breakpoint never fired")
        time.sleep(0.3)
    time.sleep(0.4)


def apply_patch(h: PM, patched: bool, mode: int = 0, extra: list[str] | None = None) -> None:
    cmds = list(extra or [])
    if patched:
        spec = json.loads(Path(str(LIVE) + ".json").read_text())
        cmds.append(f"loadbin {TMP / 'live.img'} ${spec['img_base']:x}")
        for s in spec["sites"]:
            cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
        if mode:
            cmds.append(f"w ${STATE + 1:x} $01")
        cmds.append(f"r pc=${0xD0010:x}")          # last: snd_live runs the setup and returns to the loop top
    else:
        cmds.append("e VBL")
    at_loop(h, cmds)
    time.sleep(0.5)


def seq_ptr(ram: bytes, eff: int) -> int:
    return struct.unpack(">I", ram[SEQTAB + 4 * (eff - 1): SEQTAB + 4 * eff])[0]


def trigger_cmds(ptr: int, loop: bool = False) -> list[str]:
    b = struct.pack(">I", ptr)
    return ["w $2c992 $00", f"w $2cba2 {' '.join(f'${x:02x}' for x in b)}", "w $2c996 $00 $00", f"w $2c994 ${1 if loop else 0:02x}",
            "w $2c992 $01"]


def load_ram(name: str = "map_idle") -> bytes:
    return (GAME / "work" / "dumps" / f"{name}.bin").read_bytes()


# ---- cost ---------------------------------------------------------------------------------------------------------------
PROF = re.compile(r"\$([0-9A-Fa-f]+)\s+(.*?)\s+[\d.]+% \((\d+), (\d+),")


def region_cycles(path: Path) -> dict:
    rows = {}
    for ln in path.read_text().splitlines():
        m = PROF.match(ln)
        if m:
            rows[int(m.group(1), 16)] = (int(m.group(3)), int(m.group(4)))
    tot = sum(c for _, c in rows.values())

    def rng(lo, hi):
        return sum(c for a, (_, c) in rows.items() if lo <= a < hi)

    def cnt(a):
        return rows.get(a, (0, 0))[0]
    return {"total": tot, "irq_1af32": rng(0x1AF32, 0x1AF86), "payload": rng(0xD0000, 0xD1000), "vbl_handler_runs": cnt(0x1282),
            "irq_runs": cnt(0x1AF32), "start_runs": cnt(0xD0004), "tick_runs": cnt(0xD0000)}


def cmd_cost(a) -> None:
    live = build_live()
    h = make(a.snap)
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        apply_patch(h, not a.orig, a.mode)
        time.sleep(1.0)
        OUT.mkdir(parents=True, exist_ok=True)
        tag = f"{a.snap}_{a.mhz}_{'orig' if a.orig else 'dma' + str(a.mode)}"
        p = OUT / f"prof_{tag}.txt"
        frames = h.profile_save(a.vbls, str(p))
        r = region_cycles(p)
        v = max(1, r["vbl_handler_runs"])
        busy = h.peekw(0x2C992)
        print(f"{tag}: {frames} VBL in the profile, total {r['total']} cycles; sequence active word {busy:#x}")
        print(f"  timer-A IRQ $1af32-$1af85: {r['irq_1af32']} cycles ({r['irq_runs']} IRQs) = {r['irq_1af32'] / v:.0f} cycles/VBL = "
              f"{100 * r['irq_1af32'] / r['total']:.2f} % of the CPU")
        print(f"  payload $d0000-$d0fff:    {r['payload']} cycles = {r['payload'] / v:.0f} cycles/VBL = {100 * r['payload'] / r['total']:.2f} % "
              f"(start calls {r['start_runs']}, tick calls {r['tick_runs']})")
        f = h.fps(a.fps_vbls)
        print(f"  fps over {a.fps_vbls} VBL: {f['flips']} flips = {f['fps']:.2f} fps ({f['vbls_per_frame']} VBL/frame)")
    finally:
        h.close()


# ---- WAV capture ---------------------------------------------------------------------------------------------------------
def cmd_wav(a) -> None:
    build_live(not a.st)
    ram = load_ram()
    h = make(a.snap, machine="ste")
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        # silence first: the snapshot's long sequence is cut (its in-flight chunk ends by itself)
        apply_patch(h, not a.orig, a.mode, extra=["w $2c992 $00"])
        time.sleep(2.0)
        if CAP.exists():
            CAP.unlink()
        h.cmd("hatari-shortcut recsound")
        time.sleep(0.5)
        t0 = time.time()
        at_loop(h, trigger_cmds(seq_ptr(ram, a.effect), a.loop))
        while time.time() - t0 < a.secs:
            time.sleep(0.1)
        h.cmd("hatari-shortcut recsound")
        time.sleep(1.0)
        flags = h.peekl(0xB87F0)
        st = [h.peekw(0x2C992), h.peekw(0x2C996)]
        print(f"  state after: $2c992 {st[0]:#x} step {st[1]}, FLAGS {flags:#x}")
    finally:
        h.close()
    out = OUT / f"{a.name}.wav"
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(CAP, out)
    x, sr = load_wav(out)
    print(f"wrote {out}: {len(x) / sr:.2f} s at {sr} Hz, rms {np.sqrt(np.mean(x ** 2)):.1f}, peak {np.abs(x).max():.0f}")


def load_wav(path) -> tuple[np.ndarray, int]:
    w = wave.open(str(path))
    n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
    x = np.frombuffer(w.readframes(n), dtype="<i2").astype(float)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def onset_end(x: np.ndarray, sr: int, thr: float = 0.08):
    """Start and end (samples) of the sound: the smoothed |x - median| above thr * its peak."""
    y = np.abs(x - np.median(x))
    k = int(sr * 0.004)
    e = np.convolve(y, np.ones(k) / k, mode="same")
    pk = e.max()
    idx = np.where(e > thr * pk)[0]
    return (int(idx[0]), int(idx[-1])) if len(idx) else (0, 0)


def cmd_cmp(a) -> None:
    xa, sra = load_wav(a.a)
    xb, srb = load_wav(a.b)
    assert sra == srb
    sa, ea = onset_end(xa, sra)
    sb, eb = onset_end(xb, srb)
    print(f"A {a.a}: onset {sa / sra:.3f} s end {ea / sra:.3f} s (dur {(ea - sa) / sra:.3f}), rms {np.std(xa[sa:ea]):.0f}")
    print(f"B {a.b}: onset {sb / srb:.3f} s end {eb / srb:.3f} s (dur {(eb - sb) / srb:.3f}), rms {np.std(xb[sb:eb]):.0f}")
    n = min(ea - sa, eb - sb)
    # remove DC, band-limit both to <3 kHz by a moving average (the DMA mixer path and the YM path differ in HF noise)
    k = 9

    def lp(v):
        v = v - np.mean(v)
        return np.convolve(v, np.ones(k) / k, mode="same")
    ya, yb = lp(xa[sa:sa + n]), lp(xb[sb:sb + n])
    best = (0.0, 0)
    for lag in range(-int(0.05 * sra), int(0.05 * sra) + 1, 1):
        if lag >= 0:
            u, v = ya[lag:], yb[:len(yb) - lag]
        else:
            u, v = ya[:len(ya) + lag], yb[-lag:]
        m = min(len(u), len(v))
        if m < sra // 10:
            continue
        r = float(np.corrcoef(u[:m], v[:m])[0, 1])
        if abs(r) > abs(best[0]):
            best = (r, lag)
    print(f"  best normalised correlation rho = {best[0]:+.4f} at lag {best[1] / sra * 1000:+.1f} ms (|lag| <= 50 ms, LP 9 taps)")
    # per-200 ms windows at that lag
    lag = best[1]
    w = int(0.2 * sra)
    rs = []
    for i in range(0, n - w - abs(lag), w):
        u = ya[i + max(lag, 0): i + max(lag, 0) + w]
        v = yb[i + max(-lag, 0): i + max(-lag, 0) + w]
        if np.std(u) > 1 and np.std(v) > 1:
            rs.append(abs(float(np.corrcoef(u, v)[0, 1])))
    if rs:
        print(f"  200 ms windows: mean |rho| {np.mean(rs):.3f}, min {np.min(rs):.3f}, n={len(rs)}")
    # spectral centroid
    for nm, x, s, e in (("A", xa, sa, ea), ("B", xb, sb, eb)):
        seg = x[s:e] - np.mean(x[s:e])
        sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
        fr = np.fft.rfftfreq(len(seg), 1 / sra)
        print(f"  {nm} spectral centroid {np.sum(fr * sp) / np.sum(sp):.0f} Hz, energy > 3.1 kHz {100 * np.sum(sp[fr > 3100] ** 2) / np.sum(sp ** 2):.1f} %")


# ---- cold boot -------------------------------------------------------------------------------------------------------------
def cmd_boot(a) -> None:
    """Cold boot of a built floppy image to the 3D view, then: marker/flags, the sequencer state, DMA state, a WAV of the game's own
    sound (the ambient loop starts with the view) and, if nothing plays, an injected effect."""
    import pmpatch
    from pm import TOS
    TMP.mkdir(exist_ok=True)
    setup_home()
    os.environ["HOME"] = str(HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    h = pmpatch.make_pm(Path(a.disk), None, machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=["--sound", "50066"])
    try:
        t = time.time()
        h.boot_to_game()
        print(f"boot to the 3D view in {time.time() - t:.0f} s")
        mk = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
        print(f"MARKER={mk!r} FLAGS={h.peekl(pmpatch.FLAGS):#x}")
        rows = []
        for _ in range(3):
            rows.append((h.peekw(0x2C992), h.peekw(0x2C996), h.peekw(0x2C998), h.peekw(0x2C99A), h.peekw(0xFF8900), h.peekw(STATE)))
            time.sleep(1.0)
        print("(active, step, chunk, d, $ff8900, SV busy/mode) samples:", [tuple(f"{v:#x}" for v in r) for r in rows])
        if CAP.exists():
            CAP.unlink()
        h.cmd("hatari-shortcut recsound")
        time.sleep(a.secs)
        h.cmd("hatari-shortcut recsound")
        time.sleep(1.0)
        x, sr = load_wav(CAP)
        out = OUT / f"{a.name}.wav"
        OUT.mkdir(parents=True, exist_ok=True)
        shutil.copy(CAP, out)
        print(f"wrote {out}: {len(x) / sr:.2f} s, rms {np.std(x):.1f}, peak {np.abs(x - np.median(x)).max():.0f}")
        v0 = h.vbl()
        steps = h.peekw(0x2C996)
        time.sleep(2)
        print(f"sequence step {steps} -> {h.peekw(0x2C996)} in 2 s, VBL {v0} -> {h.vbl()}")
        h.shot(str(OUT / f"{a.name}.png"))
    finally:
        h.close()


# ---- statistics ----------------------------------------------------------------------------------------------------------
def cmd_pairs(a) -> None:
    d = load_ram()
    l = lambda o: struct.unpack(">I", d[o:o + 4])[0]
    ch = []
    for i in range(58):
        p, _, n = struct.unpack(">3I", d[CHTAB + 12 * i: CHTAB + 12 * i + 12])
        if i == 57:
            n = 0x6F304 - p
        ch.append((p, n))
    seqs = [l(SEQTAB + 4 * k) for k in range(56)]
    ends = seqs[1:] + [ch[0][0]]
    use = {}
    for s, e in zip(seqs, ends):
        b = d[s:e]
        for i in range(0, len(b) - 1, 2):
            c, r = b[i], b[i + 1]
            if c == 0xFF:
                break
            r = r or 256
            use[(c, r)] = use.get((c, r), 0) + 1
    tot_t = sum(ch[c][1] / (614400 / r) * k for (c, r), k in use.items())
    print(f"{len(use)} distinct (chunk, d) pairs; {sum(use.values())} steps in all sequences")
    for dst in (6258.29, 12516.58, 25033.16):
        mem = sum(ch[c][1] * dst / (614400 / r) for (c, r) in use)
        print(f"  all pairs pre-resampled to {dst:.0f} Hz: {mem / 1024:.0f} KB")
    # direct DMA at the nearest rate: pitch error (log distance) per use, weighted by playing time
    rates = [6258.29, 12516.58, 25033.16, 50066.3]
    err, wt, byrate = [], [], {}
    for (c, r), k in use.items():
        src = 614400 / r
        near = min(rates, key=lambda q: abs(np.log(q / src)))
        dur = ch[c][1] / src * k
        e = 1200 * np.log2(near / src)                   # cents the DMA plays the sample too high (+) / low (-)
        err.append(e)
        wt.append(dur)
        byrate[near] = byrate.get(near, 0) + dur
    err, wt = np.array(err), np.array(wt)
    print(f"direct DMA at the nearest of 6258/12517/25033/50066: time-weighted pitch error mean {np.average(err, weights=wt):+.0f} cents, "
          f"mean |err| {np.average(np.abs(err), weights=wt):.0f} cents, max {np.abs(err).max():.0f} cents; playing-time share by DMA rate "
          f"{ {int(k): round(100 * v / sum(byrate.values())) for k, v in byrate.items()} } %")
    thr = [(100, 'under 100 cents'), (300, 'under 300 cents'), (600, 'under 600 cents')]
    for t, nm in thr:
        print(f"  share of playing time with |pitch error| < {t} cents: {100 * wt[np.abs(err) < t].sum() / wt.sum():.0f} %")
    # source rate histogram
    srcs = np.array([614400 / r for (c, r) in use])
    print(f"source rates {srcs.min():.0f}..{srcs.max():.0f} Hz; time-weighted median {np.median(np.repeat(srcs, np.maximum(1, (wt * 10).astype(int)))):.0f} Hz")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("live")
    p.add_argument("--mode", type=int, default=0)
    p = sub.add_parser("cost")
    p.add_argument("snap")
    p.add_argument("mhz", type=int)
    p.add_argument("vbls", type=int)
    p.add_argument("--orig", action="store_true")
    p.add_argument("--mode", type=int, default=0)
    p.add_argument("--fps-vbls", type=int, default=400)
    p = sub.add_parser("wav")
    p.add_argument("name")
    p.add_argument("effect", type=int)
    p.add_argument("secs", type=float)
    p.add_argument("--snap", default="map_idle")
    p.add_argument("--mhz", type=int, default=8)
    p.add_argument("--orig", action="store_true")
    p.add_argument("--mode", type=int, default=0)
    p.add_argument("--st", action="store_true", help="patched, but FLAGS = plain ST (bit0 clear): the YM path of the patch")
    p.add_argument("--loop", action="store_true")
    p = sub.add_parser("cmp")
    p.add_argument("a")
    p.add_argument("b")
    sub.add_parser("pairs")
    p = sub.add_parser("boot")
    p.add_argument("name")
    p.add_argument("--disk", required=True)
    p.add_argument("--machine", default="ste")
    p.add_argument("--tos", default="1.62")
    p.add_argument("--mem", type=int, default=1024)
    p.add_argument("--secs", type=float, default=8)
    a = ap.parse_args()
    {"live": lambda a: print(build_live()), "cost": cmd_cost, "wav": cmd_wav, "cmp": cmd_cmp, "pairs": cmd_pairs, "boot": cmd_boot}[a.cmd](a)


if __name__ == "__main__":
    main()
