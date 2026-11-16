#!/usr/bin/env python3
"""Live (Hatari) tests of the asn_* STE DMA sound patches on the Midwinter 2 snapshots and cold boots.

    asn_live.py record NAME [--snap raid_jeep_dhafra] [--machine ste] [--secs 8] [--quiet] [--inject ID@SEC ...] [--sustain ID@SEC]
                           [--level N@SEC] [--live build/live/asn] [--no-patch] [--poll]
    asn_live.py cost  [--snap ..] [--vbls 300] [--inject ID@SEC ...]       cycles per VBL in the blob ($bf800-$c0fff) + the YM tick, fps
    asn_live.py analyse WAV [--thr 0.02]                                  onset / end / RMS of each sound in a capture

`record`: Hatari's WAV capture (`--sound 50066`, shortcut recsound) into work/snd/NAME.wav (git-ignored: Amiga sample material).  The effects
are requested exactly like the game does: the request word `$6862` = sound id * 6 (the game's `move.w #n,$6862.w`), the sustained sound
`$686c` (via `$18eec`'s variable), the engine level `$19218`.  `--quiet` makes the game's own engine request (`$18eec`) a no-op.
Scratch config: HOME=/tmp/asn/home_<pid> (copy of the user's Hatari config with its own WAV capture file).
"""
from __future__ import annotations

import argparse
import atexit
import json
import os
import re
import shutil
import struct
import sys
import time
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari  # noqa: E402

SNAP = ROOT / "work" / "snapshots"
HOME = Path(f"/tmp/asn/home_{os.getpid()}")
CAP = Path(f"/tmp/asn/cap_{os.getpid()}.wav")
atexit.register(lambda: (shutil.rmtree(HOME, ignore_errors=True), CAP.unlink(missing_ok=True)))
SV, BANK, RING = 0xBBE00, 0xBB000, 0xBC000
FLIP = 0x26E98


def setup_home():
    cfg = HOME / ".config" / "hatari"
    cfg.mkdir(parents=True, exist_ok=True)
    src = Path.home() / ".config" / "hatari" / "1040stfm.cfg"
    txt = re.sub(r"(?m)^szYMCaptureFileName.*$", f"szYMCaptureFileName = {CAP}", src.read_text())
    (cfg / "hatari.cfg").write_text(txt)
    nv = Path.home() / ".config" / "hatari" / "hatari.nvram"
    if nv.exists():
        shutil.copy(nv, cfg / "hatari.nvram")


def make(snap: str | None, machine="ste", mem=1024, sound=True, game_dir=None, tos=None, **kw) -> Hatari:
    setup_home()
    os.environ["HOME"] = str(HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    extra = ["--sound", "50066"] if sound else []
    if machine == "tt":                      # TT: its TOS and the MMU, as the other TT snapshot runs of this project
        sys.path.insert(0, str(ROOT.parent.parent.parent / "tools"))
        from stharness import MACHINE_TOS
        tos = tos or MACHINE_TOS["tt"]
        extra += ["--mmu", "true"]
    args = dict(snapshot=str(SNAP / (snap + ".sav")) if snap else None, machine=machine, memsize_kb=mem, extra=extra)
    if game_dir:
        args["game_dir"] = Path(game_dir)
    if tos:
        args["tos"] = Path(tos)
    return Hatari(**args, **kw)


def pk(h: Hatari, addr: int, n: int, wait: float = 0.6) -> bytes:
    out = h.debug(f"m ${addr:x} {n}", wait)
    got = {}
    for m in re.finditer(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", out, re.M | re.I):
        a = int(m.group(1), 16)
        for i, x in enumerate(m.group(2).split()):
            got[a + i] = int(x, 16)
    return bytes(got.get(addr + i, 0) for i in range(n))


def apply_live(h: Hatari, live: str, extra_cmds=(), timeout=120):
    spec = json.loads(Path(live + ".json").read_text())
    cmds = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
    for s in spec["sites"]:
        cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
    cmds += list(extra_cmds)
    f = h.R / "apply.txt"
    f.write_text("\n".join(cmds) + "\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("live apply")
        time.sleep(0.3)
    time.sleep(0.5)


def request(h: Hatari, sid: int):
    h.debug(f"w $6862 $00 ${sid * 6:02x}", 0.1)


def sustain(h: Hatari, sid: int):
    h.debug(f"w $686c $00 ${sid * 6:02x}", 0.1)


def parse_sched(items):
    out = []
    for s in items or []:
        m = re.fullmatch(r"(\d+)@([\d.]+)", s)
        out.append((float(m.group(2)), int(m.group(1))))
    return sorted(out)


def voices(h: Hatari):
    raw = pk(h, SV + 0x40, 128, 0.35)
    res = []
    for c in range(4):
        f = struct.unpack_from(">8H", raw, c * 32)
        smp, ln, idx, frac, incf, inci = struct.unpack_from(">IHHHHH", raw, c * 32 + 0x10)
        s = lambda x: x - 65536 if x & 0x8000 else x
        res.append(dict(vol=s(f[0]), per=s(f[2]), cnt=s(f[4]), rec=s(f[5]), grp=s(f[7]), smp=smp, ln=ln, idx=idx, inc=(inci * 65536 + incf) / 65536))
    return res


def cmd_record(a):
    h = make(a.snap, machine=a.machine, mem=a.mem)
    try:
        time.sleep(2)
        quiet = []
        if a.quiet:
            quiet = ["w $18eec $4e $75", "w $686c $ff $ff"]
        if a.hz60:
            quiet.append("w $ff820a $00")       # 60 Hz refresh: the VBL runs 20 % faster
        if not a.no_patch:
            apply_live(h, a.live, quiet)
            time.sleep(1.0)
        elif a.quiet:
            h.debug("w $18eec $4e $75", 0.2)
        inj, sus, lvl = parse_sched(a.inject), parse_sched(a.sustain), parse_sched(a.level)
        if CAP.exists():
            CAP.unlink()
        h.cmd("hatari-shortcut recsound")
        t0 = time.time()
        events = sorted([(t, "req", s) for t, s in inj] + [(t, "sus", s) for t, s in sus] + [(t, "lvl", s) for t, s in lvl])
        log = []
        while time.time() - t0 < a.secs:
            while events and time.time() - t0 >= events[0][0]:
                t, kind, v = events.pop(0)
                if kind == "req":
                    request(h, v)
                elif kind == "sus":
                    sustain(h, v)
                else:
                    h.debug(f"w $19218 $00 ${v:02x}", 0.1)
                log.append((round(time.time() - t0, 2), kind, v))
            if a.poll:
                vs = voices(h)
                print(f"{time.time() - t0:5.1f}s", " | ".join(f"c{c}: vol{v['vol'] >> 8:3d} per{v['per']:5d} cnt{v['cnt']:4d} inc{v['inc']:.3f}" for c, v in enumerate(vs)))
            else:
                time.sleep(0.1)
        h.cmd("hatari-shortcut recsound")
        time.sleep(1.0)
        regs = h.debug("m $ff8901 1", 0.4)
        print("injected:", log)
        print("DMA control:", re.findall(r"FF8901:\s+(\S+)", regs, re.I))
    finally:
        h.close()
    out = ROOT / "work" / "snd" / f"{a.name}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(CAP, out)
    print("wrote", out)
    return 0


def load_wav(path):
    import numpy as np
    with wave.open(str(path), "rb") as w:
        n, ch, sw, rate = w.getnframes(), w.getnchannels(), w.getsampwidth(), w.getframerate()
        raw = w.readframes(n)
    x = np.frombuffer(raw, dtype="<i2" if sw == 2 else "u1").astype(float)
    if ch == 2:
        x = x.reshape(-1, 2).mean(axis=1)
    return x, rate


def cmd_analyse(a):
    import numpy as np
    x, rate = load_wav(a.wav)
    win = int(rate * 0.05)
    n = len(x) // win
    r = np.array([np.sqrt(np.mean((x[i * win:(i + 1) * win] - x[i * win:(i + 1) * win].mean()) ** 2)) for i in range(n)])
    thr = a.thr * (r.max() if r.max() else 1)
    on = r > thr
    print(f"{a.wav}: {len(x) / rate:.2f} s at {rate} Hz, rms max {r.max():.1f}")
    i = 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            print(f"  sound {i * 0.05:5.2f}s - {j * 0.05:5.2f}s   rms peak {r[i:j].max():7.1f}  mean {r[i:j].mean():7.1f}")
            i = j
        else:
            i += 1


def cmd_compare(a):
    """Correlate the DMA stream of a capture (one sample per 8-sample group of the 50066 Hz capture) with the model render of
    sound ID (tools/asn_model.py, same driver, 6258 Hz) requested at T seconds (level LVL)."""
    import numpy as np
    import asn_build
    import asn_model
    t = asn_build.Tables(asn_build.read_mwii(asn_build.ADF))
    x, rate = load_wav(a.wav)
    for spec in a.spec:
        sid, t0, secs = spec.split(",")
        sid, t0, secs = int(sid), float(t0), float(secs)
        ref = asn_model.render_sound(t, sid, secs=secs, level=a.level).astype(float)
        best = (0, -1, 0)
        i0 = int(max(0, (t0 - 0.2) * rate))
        seg = x[i0:i0 + int((secs + 0.6) * rate)]
        for ph in range(8):
            d = seg[ph::8]
            d = d - d.mean()
            n = min(len(ref), len(d))
            r = ref[:n] - ref[:n].mean()
            # search onset lag 0..0.3 s
            for lag in range(0, int(0.3 * 6258), 2):
                m_ = min(len(r), len(d) - lag)
                if m_ < 200:
                    continue
                dd, rr = d[lag:lag + m_], r[:m_]
                c = float(np.dot(dd, rr) / (np.linalg.norm(dd) * np.linalg.norm(rr) + 1e-9))
                if abs(c) > abs(best[0]):
                    best = (c, lag, ph)
        print(f"sound {sid:2d}: onset {1000 * ((i0 / rate) + best[1] / 6258 - t0):+6.0f} ms after request, |rho| {abs(best[0]):.4f} (phase {best[2]}, sign {'-' if best[0] < 0 else '+'})")


def cmd_mcompare(a):
    """Music capture (50066 Hz, the DMA held 4 samples) against the model render (asn_music.render, the blob's exact mixer): correlation of
    the spectrograms (asn_mus_cold.spectro/scorr) per SEG (5) s segment. The lag of each segment is searched +-WIN s around the lag of the
    previous one (the first: around T0), so VBL stalls of the game (the tune loses time) are followed. Controls: another tune, and
    the capture shifted 1.5 s."""
    import numpy as np
    import asn_mus_cold as mc
    x, rate = load_wav(a.wav)
    step = int(round(rate / 12516.58))
    fs = 12516.58
    ref, rr = mc.model_pcm(a.tune, a.secs + 2)
    oth, _ = mc.model_pcm(a.other, a.secs + 2)
    if rr < 12000:
        ref, oth = np.repeat(ref, 2), np.repeat(oth, 2)
    i0 = max(0, int((a.t0 - a.win - 1) * rate))
    cap = x[i0:i0 + int((a.secs + 2 * a.win + 4) * rate)]
    cap = cap[:len(cap) // step * step].reshape(-1, step).mean(axis=1)
    cap = cap - cap.mean()
    base = int(round((a.t0 - i0 / rate) * fs))          # DMA-rate index of the expected onset in `cap`
    seg, hop, win = int(a.seg * fs), 256, int(a.win * fs)
    print(f"{a.wav}: {len(x) / rate:.1f} s at {rate} Hz; tune {a.tune} expected from {a.t0:.2f} s; lag window +-{a.win} s, followed")
    rows, prev = [], base
    for s in range(0, int(a.secs * fs) - seg + 1, seg):
        R, O = mc.spectro(ref[s:s + seg]), mc.spectro(oth[s:s + seg])
        bestc, bestl = -2.0, prev
        centre = prev + s                                    # `prev` = offset of the tune start found for the previous segment
        for L in range(centre - win, centre + win + 1, hop):  # coarse: 256 samples = 20 ms
            if L < 0 or L + seg > len(cap):
                continue
            c = mc.scorr(mc.spectro(cap[L:L + seg]), R)
            if c > bestc:
                bestc, bestl = c, L
        for L in range(bestl - 224, bestl + 225, 32):       # fine
            if L < 0 or L + seg > len(cap):
                continue
            c = mc.scorr(mc.spectro(cap[L:L + seg]), R)
            if c > bestc:
                bestc, bestl = c, L
        sh = bestl + int(1.5 * fs)
        rows.append((s / fs, bestc, (bestl - s - base) / fs * 1000, mc.scorr(mc.spectro(cap[bestl:bestl + seg]), O),
                     mc.scorr(mc.spectro(cap[sh:sh + seg]), R) if sh + seg <= len(cap) else float("nan")))
        prev = bestl - s
    print("segment   rho(model tune %d)   offset ms vs T0   rho(model tune %d)   rho(capture shifted 1.5 s)" % (a.tune, a.other))
    for t0, c, l, o, sft in rows:
        print(f"{t0:5.1f} s        {c:6.3f}        {l:+8.1f}        {o:6.3f}               {sft:6.3f}")
    m = [r[1] for r in rows]
    print(f"mean rho {np.mean(m):.3f} (min {min(m):.3f}); other tune {np.mean([r[3] for r in rows]):.3f}; shifted {np.nanmean([r[4] for r in rows]):.3f}")


def cmd_cost(a):
    h = make(a.snap, machine=a.machine, mem=a.mem, sound=False)
    try:
        time.sleep(2)
        if a.live:
            apply_live(h, a.live, ["w $18eec $4e $75", "w $686c $ff $ff"] if a.quiet else [])
        elif a.quiet:
            h.debug("w $18eec $4e $75", 0.2)
            h.debug("w $686c $ff $ff", 0.2)
        time.sleep(1.0)
        for sid in a.sustain or []:        # a sustained sound: the idle re-request of $686c keeps it going
            sustain(h, sid)
        time.sleep(0.5)
        for sid in a.trigger or []:
            request(h, sid)
        time.sleep(1.0)
        prof = h.profile(a.vbls)
        tot = sum(c for _, c in prof)
        blob = sum(c for ad, c in prof if 0xBF800 <= ad < 0xC1000)
        ym = sum(c for ad, c in prof if 0x18f92 <= ad < 0x19200 or 0x682c <= ad < 0x6900)
        print(f"{a.snap} live={bool(a.live)} sustain={a.sustain}: {a.vbls} VBL: total {tot} cycles ({tot / a.vbls:.0f} per VBL), blob {blob} ({blob / a.vbls:.0f} per VBL = "
              f"{100 * blob / tot:.2f} %), YM tick {ym} ({ym / a.vbls:.0f} per VBL)")
        f = h.fps(a.fps_vbls)
        print("fps:", f)
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("name")
    r.add_argument("--snap", default="raid_jeep_dhafra")
    r.add_argument("--machine", default="ste")
    r.add_argument("--mem", type=int, default=1024)
    r.add_argument("--secs", type=float, default=8)
    r.add_argument("--quiet", action="store_true")
    r.add_argument("--inject", nargs="*")
    r.add_argument("--sustain", nargs="*")
    r.add_argument("--level", nargs="*")
    r.add_argument("--live", default=str(ROOT / "build" / "live" / "asn"))
    r.add_argument("--no-patch", action="store_true")
    r.add_argument("--poll", action="store_true")
    r.add_argument("--hz60", action="store_true")
    an = sub.add_parser("analyse")
    an.add_argument("wav")
    an.add_argument("--thr", type=float, default=0.05)
    cp = sub.add_parser("compare")
    cp.add_argument("wav")
    cp.add_argument("spec", nargs="+", help="ID,T_REQUEST,SECONDS")
    cp.add_argument("--level", type=int, default=7)
    c = sub.add_parser("cost")
    c.add_argument("--snap", default="raid_jeep_dhafra")
    c.add_argument("--machine", default="ste")
    c.add_argument("--mem", type=int, default=1024)
    c.add_argument("--vbls", type=int, default=300)
    c.add_argument("--fps-vbls", type=int, default=600)
    c.add_argument("--live", default=None)
    c.add_argument("--quiet", action="store_true")
    c.add_argument("--sustain", nargs="*", type=int)
    c.add_argument("--trigger", nargs="*", type=int)
    mc = sub.add_parser("mcompare", help="music capture vs the model render of a tune, lag followed per 5 s segment")
    mc.add_argument("wav")
    mc.add_argument("t0", type=float, help="expected onset of the tune in the capture, s")
    mc.add_argument("--secs", type=float, default=40)
    mc.add_argument("--tune", type=int, default=1)
    mc.add_argument("--other", type=int, default=5)
    mc.add_argument("--seg", type=float, default=5, help="segment length, s")
    mc.add_argument("--win", type=float, default=1.5, help="lag search +- this many s around the previous segment's lag")
    a = ap.parse_args()
    {"record": cmd_record, "analyse": cmd_analyse, "cost": cmd_cost, "compare": cmd_compare, "mcompare": cmd_mcompare}[a.cmd](a)


if __name__ == "__main__":
    main()
