#!/usr/bin/env python3
"""DMA-sound gate helper for snd_* (port of master's tools/pmsnd.py `wav` / `cmp`; notes: work/notes/RESULTS_stage04b.md).

    python3 tools/wwsnd.py wav --disk build/X/floppy.st --workdir DIR --effect 47 --secs 3 --out /tmp/e47_dma.wav [--machine ste --tos 1.62 --mem 1024]
    python3 tools/wwsnd.py cmp A.wav B.wav

`wav`: cold boot of a BUILT floppy to the map view with emulated sound ON (--sound 50066, dummy SDL audio: nothing reaches the host speakers), the sequencer is stopped, then at a main-loop top
the debugger starts the game's sound effect EFFECT exactly as the game does ($2d9c2 = sequence pointer from the table $2d7c0, step $2d7b6 = 0, loop $2d7b4, active $2d7b2 = 1; WW1 addresses =
master's + $e20, checked against the sequencer $1c4de) while Hatari records the sound output (`hatari-shortcut recsound`).  Prints rms / peak / duration of the capture and the state words.
`cmp`: onset-aligned comparison (normalised correlation, 3 kHz low-pass) of two captures: the original YM player (build without snd_*) vs the DMA player (build with snd_*).
"""
from __future__ import annotations
import argparse
import shutil
import struct
import sys
import time
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402

SEQTAB, ACTIVE, LOOP, STEP, SEQPTR = 0x2D7C0, 0x2D7B2, 0x2D7B4, 0x2D7B6, 0x2D9C2
LOOPTOP = 0x13D58


def load_wav(path):
    w = wave.open(str(path))
    n, ch, sr = w.getnframes(), w.getnchannels(), w.getframerate()
    x = np.frombuffer(w.readframes(n), dtype="<i2").astype(float)
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def onset_end(x, sr, thr=0.08):
    y = np.abs(x - np.median(x))
    k = int(sr * 0.004)
    e = np.convolve(y, np.ones(k) / k, mode="same")
    pk = e.max()
    idx = np.where(e > thr * pk)[0]
    return (int(idx[0]), int(idx[-1])) if len(idx) else (0, 0)


def cmd_cmp(a):
    xa, sra = load_wav(a.a)
    xb, srb = load_wav(a.b)
    sa, ea = onset_end(xa, sra)
    sb, eb = onset_end(xb, srb)
    print(f"A {a.a}: onset {sa / sra:.3f} s end {ea / sra:.3f} s (dur {(ea - sa) / sra:.3f}), rms {np.std(xa[sa:ea]):.0f}")
    print(f"B {a.b}: onset {sb / srb:.3f} s end {eb / srb:.3f} s (dur {(eb - sb) / srb:.3f}), rms {np.std(xb[sb:eb]):.0f}")
    n = min(ea - sa, eb - sb)
    k = 9
    lp = lambda v: np.convolve(v - np.mean(v), np.ones(k) / k, mode="same")
    ya, yb = lp(xa[sa:sa + n]), lp(xb[sb:sb + n])
    best = (0.0, 0)
    for lag in range(-int(0.05 * sra), int(0.05 * sra) + 1):
        u, v = (ya[lag:], yb[:len(yb) - lag]) if lag >= 0 else (ya[:len(ya) + lag], yb[-lag:])
        m = min(len(u), len(v))
        if m < sra // 10:
            continue
        r = float(np.corrcoef(u[:m], v[:m])[0, 1])
        if abs(r) > abs(best[0]):
            best = (r, lag)
    print(f"CMP rho = {best[0]:+.4f} at lag {best[1] / sra * 1000:+.1f} ms (|lag| <= 50 ms, LP 9 taps); durations {(ea - sa) / sra:.3f} / {(eb - sb) / srb:.3f} s; rms {np.std(xa[sa:ea]):.0f} / {np.std(xb[sb:eb]):.0f}")
    return 0 if abs(best[0]) > 0.8 else 2


def cmd_wav(a):
    out = Path(a.out)
    cap = Path(a.workdir) / "cap.wav"
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=a.mem, sound=True, ymwav=str(cap))
    try:
        h.boot_to_map(noprot=True, swap=False, log=lambda s: print("  " + s, flush=True))
        time.sleep(3)
        flags = h.peekl(0x76718)
        h.debug(f"w ${ACTIVE:x} $00", 0.5)
        time.sleep(2.0)
        ram = h.ram(SEQTAB, 4 * 56)
        ptr = struct.unpack(">I", ram[4 * (a.effect - 1):4 * a.effect])[0]
        print(f"  FLAGS ${flags:x}, effect {a.effect} sequence pointer ${ptr:x}", flush=True)
        cmds = ["w $%x $00" % ACTIVE, "w $%x %s" % (SEQPTR, " ".join(f"${x:02x}" for x in struct.pack(">I", ptr))), "w $%x $00 $00" % STEP,
                "w $%x $%02x" % (LOOP, 1 if a.loop else 0), "w $%x $01" % ACTIVE]
        (h.R / "trig.txt").write_text("\n".join(cmds) + "\n")
        cap.unlink(missing_ok=True)
        h.cmd("hatari-shortcut recsound")
        time.sleep(0.5)
        t0 = time.time()
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b pc = ${LOOPTOP:x} :trace :once :file {h.R / 'trig.txt'}")
        while time.time() - t0 < a.secs:
            time.sleep(0.1)
        h.cmd("hatari-shortcut recsound")
        time.sleep(1.0)
        st = [h.peekw(ACTIVE), h.peekw(STEP)]
        print(f"  state after: active ${st[0]:x}, step {st[1]}, FLAGS ${h.peekl(0x76718):x}", flush=True)
    finally:
        h.close()
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(cap, out)
    x, sr = load_wav(out)
    s, e = onset_end(x, sr)
    print(f"WAV {out}: {len(x) / sr:.2f} s at {sr} Hz, sound {s / sr:.2f}-{e / sr:.2f} s, rms {np.std(x[s:e + 1]):.1f}, peak {np.abs(x - np.median(x)).max():.0f}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("wav")
    w.add_argument("--disk", required=True)
    w.add_argument("--workdir", required=True)
    w.add_argument("--effect", type=int, default=47)
    w.add_argument("--secs", type=float, default=3.0)
    w.add_argument("--out", required=True)
    w.add_argument("--machine", default="ste")
    w.add_argument("--tos", default="1.62")
    w.add_argument("--mem", type=int, default=1024)
    w.add_argument("--loop", action="store_true")
    c = sub.add_parser("cmp")
    c.add_argument("a")
    c.add_argument("b")
    a = ap.parse_args()
    return {"wav": cmd_wav, "cmp": cmd_cmp}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
