"""Effect capture + ring-lead measurement inside a booted cell (used by cell.py --fx / --ring).

fx_pass: game triggers off (`$af0e = rts`), channels idle; every effect id 0..20 is injected on channel 0 (volume 12) like the game's trigger
does (request byte `$11388+ch`, volume word `$1138c+2ch`), Hatari's WAV capture runs over the whole pass; the DMA registers, SV state and
the voice table are read after each request; the WAV is cut into the request windows and analysed (rms, spectral centroid, energy > 1.5 kHz,
onset delay, length, DMA state after the end).  ring_pass: lead of the write cursor over the DMA position at every top-up and underrun resyncs
(breakpoints `.okp` and the resync path of snd_core.s, like snd_test.py `ring`), with two loops and re-injected explosions.
"""
from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import time
import wave
from pathlib import Path

import numpy as np

import ac
from ac import SV, T

QUIET = ["w $af0e $4e $75", "w $11398 $00 $00 $00", "w $11388 $ff $ff $ff"]
NFX = 21


def load_wav(path):
    w = wave.open(str(path))
    x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").reshape(-1, w.getnchannels()).astype(float).mean(axis=1)
    return x, w.getframerate()


def inject(h, eff, ch, vol):
    h.debug(f"w ${0x11388 + ch:x} ${eff:02x}", 0.1)
    h.debug(f"w ${0x1138C + 2 * ch:x} $00 ${vol:02x}", 0.1)


def idle(h):
    for c in QUIET[1:]:
        h.debug(c, 0.1)


def feats(seg: np.ndarray, sr: int) -> dict:
    if len(seg) < 256:
        return dict(rms=0.0, centroid=0.0, hi=0.0, peak=0.0)
    s = seg - seg.mean()
    sp = np.abs(np.fft.rfft(s * np.hanning(len(s)))) ** 2
    fr = np.fft.rfftfreq(len(s), 1 / sr)
    m = (fr > 20) & (fr < 3200)           # the DMA stream is 6258 Hz: 8 x held in the 50066 Hz capture, band-limit to its Nyquist
    tot = sp[m].sum() + 1e-9
    return dict(rms=float(s.std()), centroid=float((fr[m] * sp[m]).sum() / tot), hi=float(sp[m & (fr > 1500)].sum() / tot), peak=float(np.abs(s).max()))


def fx_pass(c, a, vol=12, win=3.0, gap=1.2):
    h, L = c.h, c.L
    ac_dma = lambda: (ac.pk(h, 0xFF8901, 1, 0.3).hex(), ac.pk(h, 0xFF8921, 1, 0.3).hex())  # noqa: E731
    for q in QUIET:
        h.debug(q, 0.2)
    time.sleep(1.0)
    cap = c.cap
    cap.unlink(missing_ok=True)
    h.cmd("hatari-shortcut recsound")
    t0 = time.time()
    time.sleep(0.5)
    reqs = []
    for e in range(NFX):
        t = time.time() - t0
        inject(h, e, 0, vol)
        time.sleep(0.5)
        dma = ac_dma()
        sv = ac.pk(h, SV, 8, 0.3)
        v0 = ac.pk(h, SV + 0x40, 0x28, 0.3)
        incf, inci = struct.unpack_from(">HH", v0, 16)
        reqs.append(dict(e=e, t=t, dma_ctl=dma[0], dma_rate=dma[1], mode=sv[0], in3d=sv[1], dmaflag=sv[2],
                         voice_ch=v0[0], inc=(inci * 65536 + incf) / 65536))
        while time.time() - t0 < t + win:
            time.sleep(0.05)
        idle(h)
        time.sleep(gap - 0.3)
        sv = ac.pk(h, SV, 8, 0.3)
        reqs[-1]["dma_after"] = (ac_dma()[0], sv[2])
    h.cmd("hatari-shortcut recsound")
    time.sleep(1.5)
    wall = time.time() - t0
    if not cap.exists():
        L("fx: no WAV captured")
        return
    x, sr = load_wav(cap)
    ratio = (len(x) / sr) / wall
    keep = T / "keep"
    keep.mkdir(exist_ok=True)
    shutil.copy(cap, keep / f"{c.a.name}_fx.wav")
    L(f"fx: WAV {len(x) / sr:.1f} s at {sr} Hz for {wall:.1f} s wall (emulation/real = {ratio:.3f}); DMA ctl/rate after each request below")
    rows = []
    env = np.array([np.abs(x[i:i + 500] - np.median(x[i:i + 500])).max() for i in range(0, len(x) - 500, 500)])   # 10 ms envelope
    thr = 0.05 * env.max()
    act = env > thr
    bursts, cur, quiet = [], None, 0
    for i, v in enumerate(act):
        if v:
            if cur is None:
                cur = [i, i]
            cur[1] = i
            quiet = 0
        elif cur is not None:
            quiet += 1
            if quiet > 25:
                bursts.append(tuple(cur))
                cur = None
    if cur is not None:
        bursts.append(tuple(cur))
    L(f"fx: {len(bursts)} bursts for {len(reqs)} requests (burst-aligned windows when equal, else time windows)")
    for k, r in enumerate(reqs):
        if len(bursts) == len(reqs):
            b0, b1 = bursts[k]
            seg = x[b0 * 500:(b1 + 1) * 500]
            r["onset_ms"], r["len_ms"] = None, (b1 - b0 + 1) * 10.0
        else:
            s0 = r["t"] * ratio
            seg = x[int(s0 * sr):int((s0 + win) * sr)]
            r["len_ms"] = None
        f = feats(seg, sr)
        r.update(f)
        rows.append(r)
        L(f"  fx e={r['e']:2d} rms={f['rms']:7.1f} peak={f['peak']:7.0f} centroid={f['centroid']:6.0f} Hz hi(>1.5k)={100 * f['hi']:4.1f}% len={r['len_ms']} ms | ctl={r['dma_ctl']} rate={r['dma_rate']} mode={r['mode']} dmaflag={r['dmaflag']} vox0ch={r['voice_ch']} inc={r['inc']:.4f} after={r['dma_after']}")
    json.dump(rows, open(c.wd / "fx.json", "w"))
    shutil.copy(c.wd / "fx.json", ac.HERE / "out" / f"{c.a.name}_fx.json")


def lst_addr(token):
    out, lst = T / "lab" / "snd.bin", T / "lab" / "snd.lst"
    subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(out), "-L", str(lst), str(ac.GAME / "patches" / "snd_core.s")], check=True)
    for ln in lst.read_text(errors="replace").splitlines():
        m = re.match(r"^\d\d:([0-9A-F]{8})\s+(?:[0-9A-F]+)?\s*\t\s*\d+:\s*" + re.escape(token), ln)
        if m:
            return int(m.group(1), 16)
    raise KeyError(token)


def ring_pass(c, a):
    """Lead of the write cursor before each top-up and underrun resyncs, 2 sustained loops + an explosion every 70 VBL."""
    h, L = c.h, c.L
    okp = lst_addr(".okp:")
    under = okp - 14
    vbls = int(a.ring * 50)
    quiet = list(QUIET)
    cf = c.wd / "lead.txt"
    cf.write_text("r\ne VBL\n")
    cu = c.wd / "under.txt"
    cu.write_text("e VBL\n")
    end = c.wd / "end.txt"
    end.write_text("b all\n")
    v0 = h.vbl()
    at = v0 + 40
    pre = list(quiet) + ["w $11389 $0b", "w $1138e $00 $0f", "w $1138a $0d", "w $11390 $00 $0f"]
    pre += [f"b pc = ${okp:x} :trace :file {cf}", f"b pc = ${under:x} :trace :file {cu}"]
    inj = []
    for k in range(1, min(vbls // 70, 11)):         # Hatari's debugger holds at most 16 conditional breakpoints (17 = memory corruption, Hatari dies)
        f = c.wd / f"inj{k}.txt"
        f.write_text("w $11388 $03\nw $1138c $00 $0c\n")
        inj.append(f"b VBL > {at + 70 * k} :trace :once :file {f}")
    pre.append(f"b VBL > {at + vbls} :trace :once :file {end}")
    app = c.wd / "ring_apply.txt"
    app.write_text("\n".join(pre + inj) + "\n")
    if len(max(pre + inj, key=len)) > 235:
        raise ValueError("line too long")
    st = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v0 + 20} :trace :once :file {app}")
    t = time.time()
    while h._logtext()[st:].count("Removed CPU breakpoint") < 2 + len(inj):
        if time.time() - t > 900:
            raise TimeoutError(h._logtext()[-1500:])
        time.sleep(1.0)
    time.sleep(0.5)
    log = h._logtext()[st:]
    h.debug("b all", 0.3)
    for q in QUIET[1:]:
        h.debug(q, 0.1)
    leads = []
    for blk in log.split("CPU breakpoint condition(s) matched")[1:]:
        if re.match(r"\s*\d+ times\.\s*pc = \$%x" % okp, blk, re.I):
            m = re.search(r"D1\s+([0-9A-Fa-f]{8})", blk)
            if m:
                leads.append(int(m.group(1), 16) & 0xFFFF)
    ublk = [b for b in log.split("CPU breakpoint condition(s) matched")[1:] if re.match(r"\s*\d+ times\.\s*pc = \$%x" % under, b, re.I)]
    uv = [int(re.search(r"#(\d+) \(dec\)", b).group(1)) - v0 for b in ublk if re.search(r"#(\d+) \(dec\)", b)]
    if not leads:
        L("RING no top-ups seen\n" + log[-600:])
        return
    arr = np.array(leads)
    L(f"RING {a.name}: {vbls} VBL, top-ups {len(leads)}, lead before top-up min {arr.min()} p5 {int(np.percentile(arr, 5))} median {int(np.median(arr))} max {arr.max()} samples "
      f"(TARGET 192, 1 VBL = 125 samples), underrun resyncs {len(ublk)}" + (f" at VBL +{uv[:20]}" if uv else ""))
    (c.wd / "ring_leads.json").write_text(json.dumps(leads))
    shutil.copy(c.wd / "ring_leads.json", ac.HERE / "out" / f"{c.a.name}_ringleads.json")


def voice_pass(c, a, secs=10.0):
    """Three channels at once: engine loop (11, ch0) + rotor loop (13, ch1) at volume 15 and a one-shot (effect 6) re-triggered on ch2 about
    every 0.5 s.  The mixer has 2 voices: which channels hold a voice at each poll (SV voice slots at SV+$40 / SV+$68, byte 0 = channel, $ff = free)."""
    h, L = c.h, c.L
    for q in QUIET:
        h.debug(q, 0.2)
    time.sleep(1.0)
    inject(h, 11, 0, 15)
    inject(h, 13, 1, 15)
    rows = []
    t0 = time.time()
    n = 0
    while time.time() - t0 < secs:
        if n % 2 == 0:
            inject(h, 6, 2, 14)
        sv = ac.pk(h, SV + 0x40, 0x30, 0.3)
        rows.append((sv[0], sv[0x28]))
        n += 1
    idle(h)
    tot = len(rows)
    has = lambda ch: sum(1 for r in rows if ch in r) / tot  # noqa: E731
    L(f"VOICES {c.a.name}: {tot} polls over {secs:.0f} s, engine(ch0) voiced {100 * has(0):.0f} %, rotor(ch1) voiced {100 * has(1):.0f} %, one-shot(ch2) voiced {100 * has(2):.0f} %, "
      f"both loops voiced together {100 * sum(1 for r in rows if 0 in r and 1 in r) / tot:.0f} %; raw (voice0 ch, voice1 ch): {rows}")


def run(c, a):
    if getattr(a, "voices", False):
        try:
            voice_pass(c, a)
        except Exception as e:  # noqa: BLE001
            c.L(f"voice pass FAILED: {e!r}")
    if a.fx:
        try:
            fx_pass(c, a)
        except Exception as e:  # noqa: BLE001
            c.L(f"fx pass FAILED: {e!r}")
    if a.ring:
        try:
            ring_pass(c, a)
        except Exception as e:  # noqa: BLE001
            c.L(f"ring pass FAILED: {e!r}")
