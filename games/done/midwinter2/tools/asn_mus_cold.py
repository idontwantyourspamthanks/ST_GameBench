#!/usr/bin/env python3
"""Cold boot of an asn_* build with the MUSIC checks (HD and floppy builds), and the analysis of its WAV capture.

    python3 tools/asn_mus_cold.py run NAME MACHINE TOS MEM_KB (hd|floppy) BUILD_DIR [--intro SECS] [--snap FILE.sav] [--to STAGE] [--no-profile]
    python3 tools/asn_mus_cold.py compare WAV T0 [--secs 40] [--tune 1] [--other 5]

MACHINE ste|megaste|st|tt, TOS 162|206|104|306.  BUILD_DIR = a `mw2patch.py build [--floppy]` output made with MW2_BANK=build/asn_bank.bin.
`run` (results: work/asn_cold/mus_NAME.txt / .json / .wav / _*.png) records Hatari's sound from power-on and walks:
  intro   wait for the game's first tune start (logo), then SECS seconds without a key: the blob's state every few seconds, a 250-VBL profile
  mjk     Space until the M/J/K screen; key M (the game fades the tune out through $b9a, then silences it)
  hall    tune 1 restarted by the hall; PERSONNEL (restart), back, CONTROL map, island, objectives, boss screen (tune 1 keeps playing)
  3d      thumbs up -> the 3D view: the sound-effect tick owns the DMA at 6258 Hz; two effects are requested like the game does
  f5      F5 = the map table: tune 1 again (music tick), 12 s
At every stage: mode / session / DMA / tune / tick counter / $b9a / $5138 / $7626, and the bank in RAM against build/asn_bank.bin (everything but the
state, the channel records and the ring).  YM machines (st, tt): the same walk must show mode 1, the DMA never touched, the YM audible (WAV rms).
`compare`: the capture (50066 Hz, the DMA held 4 samples) against the model render of the tune (tools/asn_music.py render, the blob's exact mixer):
correlation of the two spectrograms (per-band time variation, 41 ms frames) in 5 s segments with a lag search, plus the same against another tune
and against the tune shifted by 1.5 s (negative controls).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

TOSD = ROOT.parent.parent.parent / "tos"
OUT = ROOT / "work" / "asn_cold"
BANKF = ROOT / "build" / "asn_bank.bin"
BANK, SV = 0xBB000, 0xBBE00
MTICK = 0xBF81E                 # the blob's music tick entry (what $806 and so $5138 hold)
DYN = [(0xE00, 0x1800)]         # state, channel records, ring: the only bytes of the bank that change
STAGES = ["intro", "mjk", "hall", "3d", "f5"]


def analyse_rms(x, rate, t0, t1):
    import numpy as np
    seg = x[int(t0 * rate):int(t1 * rate)]
    return float(np.sqrt(np.mean((seg - seg.mean()) ** 2))) if len(seg) else 0.0


def wav_silences(x, rate, t1, win=1.0):
    """Audibility summary of a capture from the tune start `t1` on: seconds with rms > 100 and the silent intervals (>= 2 s).
    (The capture is shorter than the emulated time - Hatari drops samples around debugger pauses - so states are not aligned to it by time.)"""
    n = int(len(x) / rate / win)
    r = [analyse_rms(x, rate, i * win, (i + 1) * win) for i in range(n)]
    i0 = max(0, int(t1 * 0.9 / win))
    quiet, run = [], None
    for i in range(i0, n):
        if r[i] <= 100:
            run = run or [i, i]
            run[1] = i
        elif run:
            quiet.append(run); run = None
    if run:
        quiet.append(run)
    quiet = [(a * win, (b + 1) * win) for a, b in quiet if b - a + 1 >= 2 / win]
    loud = sum(1 for v in r[i0:] if v > 100)
    return (f"{n * win:.0f} s long; from {i0 * win:.0f} s on: {loud} of {n - i0} one-second windows have rms > 100 (max {max(r[i0:], default=0):.0f}); "
            f"silent intervals (rms <= 100, >= 2 s): {[(round(a), round(b)) for a, b in quiet]}")


def spectro(x, n=512, hop=256):
    import numpy as np
    w = np.hanning(n)
    fr = [np.abs(np.fft.rfft(x[i:i + n] * w)) for i in range(0, len(x) - n, hop)]
    s = np.log1p(np.array(fr).T)
    return s - s.mean(axis=1, keepdims=True)          # per band: variation over time


def scorr(a, b):
    import numpy as np
    k = min(a.shape[1], b.shape[1])
    a, b = a[:, :k], b[:, :k]
    return float((a * b).sum() / (np.sqrt((a * a).sum() * (b * b).sum()) + 1e-9))


def model_pcm(tune, secs):
    import numpy as np
    import asn_build
    import asn_music
    t = asn_build.Tables(asn_build.read_mwii(asn_build.ADF))
    bank, info = asn_build.build_bank(t)
    assert bank == BANKF.read_bytes(), "build/asn_bank.bin is not what tools/asn_build.py builds now"
    raw = asn_music.render(t.mem, bank, BANK, info, tune, int(secs * 50.053) + 5, rate=info["rates"][tune], gainset=info["gains"][tune],
                           vt_base=BANK + asn_build.OFF_VT)
    return np.frombuffer(bytes(raw), dtype=np.int8).astype(float), (12516.58 if info["rates"][tune] else 6258.29)


def cmd_compare(a):
    import numpy as np
    import asn_live
    x, rate = asn_live.load_wav(a.wav)
    step = int(round(rate / 12516.58))
    print(f"{a.wav}: {len(x) / rate:.1f} s at {rate} Hz; tune {a.tune} expected from {a.t0:.2f} s; DMA sample = {step} capture samples")
    ref, rr = model_pcm(a.tune, a.secs + 2)
    oth, _ = model_pcm(a.other, a.secs + 2)
    if rr < 12000:
        ref, oth = np.repeat(ref, 2), np.repeat(oth, 2)
    # the capture at the DMA rate (mean of each group of `step`), searched +-2.5 s around T0
    i0 = max(0, int((a.t0 - 2.5) * rate))
    cap = x[i0:i0 + int((a.secs + 6) * rate)]
    cap = cap[:len(cap) // step * step].reshape(-1, step).mean(axis=1)
    cap = cap - cap.mean()
    fs = 12516.58
    # coarse lag: correlation of the 20 ms energy envelopes
    def env(v):
        k = 250
        return np.sqrt((v[:len(v) // k * k].reshape(-1, k) ** 2).mean(axis=1))
    ec, er = env(cap), env(ref[:int(a.secs * fs)])
    best = max(range(0, len(ec) - len(er)), key=lambda L: float(np.corrcoef(ec[L:L + len(er)], er)[0, 1]))      # Pearson: a louder passage (the boot stub's YM tune) must not win
    lag0 = best * 250
    print(f"coarse onset of the tune in the capture: {i0 / rate + lag0 / fs:.2f} s")
    seg = int(5 * fs)
    rows = []
    for s in range(0, int(a.secs * fs) - seg + 1, seg):
        R = spectro(ref[s:s + seg])
        O = spectro(oth[s:s + seg])
        bestc, bestl = -2, 0
        for L in range(lag0 + s - 1500, lag0 + s + 1501, 64):
            if L < 0 or L + seg > len(cap):
                continue
            c = scorr(spectro(cap[L:L + seg]), R)
            if c > bestc:
                bestc, bestl = c, L
        C = spectro(cap[bestl:bestl + seg])
        sh = bestl + int(1.5 * fs)
        rows.append((s / fs, bestc, (bestl - lag0 - s) / fs * 1000, scorr(C, O), scorr(spectro(cap[sh:sh + seg]), R) if sh + seg <= len(cap) else float("nan")))
    print("segment   rho(model tune %d)   lag ms   rho(model tune %d)   rho(capture shifted 1.5 s)" % (a.tune, a.other))
    for t0, c, l, o, sft in rows:
        print(f"{t0:5.1f} s        {c:6.3f}        {l:+6.1f}        {o:6.3f}               {sft:6.3f}")
    m = [r[1] for r in rows]
    print(f"mean rho {np.mean(m):.3f} (min {min(m):.3f}); other tune {np.mean([r[3] for r in rows]):.3f}; shifted {np.nanmean([r[4] for r in rows]):.3f}")


def cmd_run(a):
    import asn_live
    from mw2harness import Hatari
    name, machine, tos, mem, media, bdir = a.name, a.machine, a.tos, a.mem, a.media, a.build
    TOS = {"162": TOSD / "TOS_1_62.img", "206": TOSD / "TOS_2_06.img", "104": TOSD / "TOS_1_04.img", "306": TOSD / "TOS_3_06_uk.img"}
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"cell": name, "log": [], "states": []}
    bank = BANKF.read_bytes()

    def L(*x):
        s = " ".join(str(v) for v in x)
        res["log"].append(s)
        print(s, flush=True)

    asn_live.setup_home()
    os.environ["HOME"] = str(asn_live.HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    extra = ["--sound", "50066"]
    if machine == "tt":
        extra += ["--mmu", "true"]
    dma_machine = machine in ("ste", "megaste")
    h = None
    last = STAGES.index(a.to)
    try:
        if media == "hd":
            h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=TOS[tos], game_dir=ROOT / bdir, extra=extra)
        else:
            d = ROOT / bdir
            scratch = Path(f"/tmp/fl/mus_{name}")
            shutil.rmtree(scratch, ignore_errors=True)
            scratch.mkdir(parents=True)
            for src, dst in (("FFA_boot.st", "A.st"), ("FFB_graphics.st", "B.st")):
                shutil.copy(d / src, scratch / dst)
            shutil.copy(ROOT / "work/disk_overlay/FILES/FFD", scratch / "D.st")
            (scratch / "empty").mkdir()
            h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=TOS[tos], game_dir=scratch / "empty",
                       extra=["--disk-a", str(scratch / "A.st"), "--disk-b", str(scratch / "D.st")] + extra)
        if asn_live.CAP.exists():
            asn_live.CAP.unlink()
        h.cmd("hatari-shortcut recsound")
        v0 = h.vbl()
        tw0 = time.time()

        def now():
            """Seconds of emulated time since the capture started."""
            return (h.vbl() - v0) / 50.053

        def state(tag):
            sv = asn_live.pk(h, SV, 0x18, 0.3)
            tick = struct.unpack(">I", asn_live.pk(h, SV + 0xD0, 4, 0.3))[0]
            lo = asn_live.pk(h, 0xB96, 14, 0.3)
            g = dict(tag=tag, t=round(now(), 2), mode=sv[0], act=sv[1], dma=sv[2], mus=sv[0x12], rate=sv[0x14], tick=tick,
                     p5138=asn_live.pk(h, 0x5138, 4, 0.3).hex(), t7626=asn_live.pk(h, 0x7626, 2, 0.3).hex(), b96=lo[:4].hex(), b9a=lo[4], ba2=lo[12:14].hex(),
                     ff8901=asn_live.pk(h, 0xFF8901, 1, 0.3).hex(), ff8921=asn_live.pk(h, 0xFF8921, 1, 0.3).hex())
            res["states"].append(g)
            L(f"[{tag:11s}] t={g['t']:7.2f}s mode {g['mode']} session {g['act']} dma {g['dma']:3d} tune {g['mus']:2d} rate {g['rate']} tick {g['tick']:5d} "
              f"$b96={g['b96']} $b9a={g['b9a']:2d} $ba2={g['ba2']} $7626={g['t7626']} $5138={g['p5138']} $ff8901={g['ff8901']} $ff8921={g['ff8921']}")
            return g

        def bankcheck(tag):
            p = h.R / "bk.bin"
            if p.exists():
                p.unlink()
            h.debug(f"savebin {p} ${BANK:x} ${len(bank):x}", 4.0)
            ram = p.read_bytes()
            bad = [i for i in range(len(bank)) if ram[i] != bank[i] and not any(x <= i < y for x, y in DYN)]
            L(f"[{tag:11s}] bank ${BANK:x}-${BANK + len(bank):x} in RAM vs build/asn_bank.bin: {len(bad)} bytes differ outside state/records/ring"
              + (f" (first {[hex(BANK + i) for i in bad[:6]]})" if bad else ""))
            res.setdefault("bank", {})[tag] = len(bad)

        def cost(tag, vbls=250):
            if a.no_profile:
                return
            prof = h.profile(vbls)
            tot = sum(c for _, c in prof)
            blob = sum(c for ad, c in prof if 0xBF800 <= ad < 0xC1000)
            ym = sum(c for ad, c in prof if 0xC4C <= ad < 0x123E)
            L(f"[{tag:11s}] profile {vbls} VBL: blob {blob / vbls:.0f} cycles/VBL = {100 * blob / vbls / 160256:.1f} % of a 50 Hz frame; YM driver {ym / vbls:.0f}/VBL; "
              f"everything profiled {tot / vbls:.0f}/VBL")
            res.setdefault("cost", {})[tag] = dict(blob=blob / vbls, ym=ym / vbls, total=tot / vbls)

        def shot(tag):
            try:
                h.shot(OUT / f"mus_{name}_{tag}.png")
            except Exception as e:
                L("shot failed", e)

        # ---- intro: the game's first tune start --------------------------------------------------------------------
        ins = ROOT / "work/floppy_tests/ref_insert_graphics.png"
        swapped = media == "hd"
        started = None
        t0 = time.time()
        while time.time() - t0 < 420 and (started is None or not swapped):
            time.sleep(1.5)
            p = asn_live.pk(h, 0x5138, 4, 0.3)
            if started is None and int.from_bytes(p, "big") in (MTICK, 0xD0E) and int.from_bytes(asn_live.pk(h, 0x7626, 2, 0.3), "big") == 1:
                started = now()
                L(f"the game started tune 1 (its tick pointer $5138 = {p.hex()}) about {started:.1f} s after the capture start (wall {time.time() - tw0:.0f} s)")
                state("logo")
                res["tune_t0"] = started
                shot("logo")
            if not swapped:
                from PIL import Image, ImageChops, ImageStat
                cur = Image.open(h.shot()).convert("RGB").crop((280, 360, 560, 420))
                dd = ImageChops.difference(cur, Image.open(ins).convert("RGB").crop((280, 360, 560, 420)))
                if sum(ImageStat.Stat(dd).mean) / 3 < 0.3:
                    L(f"insert-graphics prompt at {now():.1f} s")
                    state("fl-prompt")
                    h.cmd(f"hatari-option --disk-a {scratch / 'B.st'}")
                    swapped = True
                    time.sleep(2)
        if started is None:
            raise RuntimeError("the game never started tune 1")
        L("MWPO:", h.debug("m $b2ff8 4").strip().splitlines()[-1])
        L("vector table $806:", asn_live.pk(h, 0x806, 12).hex(), "(asn_mus: 000bf81e 000bf824 00000c4c)")
        if media == "hd":
            tend = started + a.intro
            k = 0
            while now() < tend:
                time.sleep(4)
                k += 1
                g = state(f"intro{k}")
                if k in (2, 6, 10):
                    shot(f"intro{k}")
            cost("intro")
            bankcheck("intro")
        if last >= 1:
            ref = ROOT / "work" / "ref" / "mode_select.png"
            for _ in range(60):
                h.cmd("hatari-event keypress 57")
                time.sleep(5)
                if h.screen_matches(ref, (280, 350, 560, 420)):
                    break
            else:
                raise RuntimeError("never reached the M/J/K screen")
            state("mjk")
            shot("mjk")
            cost("mjk")
            bankcheck("mjk")
            if media != "hd":
                h.debug("w $2c574 $60 $02")                  # TEST-ONLY security-check bypass of the floppy test cells (work/floppy_tests/run_cell.py)
            for _ in range(5):
                time.sleep(3)
                h.cmd("hatari-event keypress 50")
                time.sleep(1.5)
                state("M-key")
                time.sleep(3.5)
                if not h.screen_matches(ref, (280, 350, 560, 420)):
                    break
            else:
                raise RuntimeError("M/J/K key not accepted")
            for i in range(3):
                time.sleep(2.5)
                state(f"fade{i}")
        if last >= 2:
            if media != "hd":
                from PIL import Image, ImageChops, ImageStat
                FT = ROOT / "work/floppy_tests"

                def sdiff(refp, box):
                    cur = Image.open(h.shot()).convert("RGB").crop(box)
                    dd = ImageChops.difference(cur, Image.open(refp).convert("RGB").crop(box))
                    return sum(ImageStat.Stat(dd).mean) / 3

                def wait_match(target, timeout):
                    t1 = time.time()
                    while time.time() - t1 < timeout:
                        if sdiff(*target) < 4:
                            return True
                        time.sleep(3)
                    return False

                HALL = (FT / "ref_hall.png", (96, 350, 736, 458))
                PERS = (FT / "ref_personnel.png", (96, 100, 330, 350))
                MAP = (FT / "ref_map.png", (96, 300, 560, 458))

                def step(point, target, timeout=40):
                    for _ in range(4):
                        h.goto(*point)
                        h.click()
                        if wait_match(target, timeout):
                            return
                    raise RuntimeError(f"click at {point} never produced the expected screen")

                if not wait_match(HALL, 120):
                    raise RuntimeError("never saw the HQ hall")
                state("hall")
                cost("hall")
                step((554, 105), PERS)
                state("personnel")
                step((389, 140), HALL)
                state("hall2")
                step((414, 185), MAP, timeout=100)
                time.sleep(25)
                state("map")
            else:
                time.sleep(6)
                state("hall")
                shot("hall")
                cost("hall")
                bankcheck("hall")
                h.goto(554, 105); h.click(); time.sleep(15)
                state("personnel")
                h.goto(389, 140); h.click(); time.sleep(12)
                state("hall2")
                h.goto(414, 185); h.click(); time.sleep(25)
                state("map")
                shot("map")
            cost("map")
            bankcheck("map")
            h.goto(150, 280); h.key("space"); time.sleep(18)
            state("island")
            h.goto(230, 410); h.click(); time.sleep(15)
            state("objectives")
            boss = ROOT / "work/ref/boss_thumbs.png"
            for _ in range(6):
                h.goto(140, 415); h.click(); time.sleep(8)
                if h.screen_matches(boss, (590, 60, 740, 125)):
                    break
            else:
                raise RuntimeError("never reached the boss screen")
            state("boss")
            bankcheck("boss")
        if last >= 3:
            h.goto(625, 92); h.click(); time.sleep(40)
            for _ in range(12):
                if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2:
                    break
                time.sleep(5)
            else:
                raise RuntimeError(f"no 3D view ($6220={h.peekw(0x6220):#x}, $700a={h.peekw(0x700A):#x})")
            for _ in range(40):                           # floppy: the mission is still loading when $6220/$700a already look like the 3D view (the helicopter preview)
                if int.from_bytes(asn_live.pk(h, 0x5138, 4, 0.3), "big") == 0x18F92:
                    break
                time.sleep(5)
            else:
                raise RuntimeError("the 3D game's sound tick ($18f92) never took over $5138")
            time.sleep(15)
            h.center()
            state("3d")
            shot("3d")
            for sid in (2, 4):
                asn_live.request(h, sid)
                time.sleep(0.4)
                g = state(f"3d-sfx{sid}")
                if dma_machine:
                    L(f"   voices after the request of effect {sid}:", [(v["vol"] >> 8, v["per"], v["cnt"]) for v in asn_live.voices(h)])
                time.sleep(2.0)
            cost("3d")
            bankcheck("3d")
            if a.snap:
                h.savemem(a.snap)
                L("snapshot", a.snap)
        if last >= 4:
            h.key("F5"); time.sleep(8)
            state("f5")
            shot("f5")
            time.sleep(6)
            state("f5+6s")
            cost("f5")
            bankcheck("f5")
        h.cmd("hatari-shortcut recsound")
        time.sleep(1.0)
        wavp = OUT / f"mus_{name}.wav"
        wavx = None
        if asn_live.CAP.exists():
            shutil.copy(asn_live.CAP, wavp)
            x, rate = asn_live.load_wav(wavp)
            wavx = (x, rate)
            t1 = res["tune_t0"]
            L(f"wav {wavp}: {len(x) / rate:.1f} s; rms before the game's tune (boot stub) {analyse_rms(x, rate, max(0, t1 - 6), t1 - 1):.0f}, "
              f"first 30 s of the tune {analyse_rms(x, rate, t1 + 1, t1 + 30):.0f}")
        # ---- verdict lines ---------------------------------------------------------------------------------------------
        st = res["states"]
        if dma_machine:
            mus = [g for g in st if g["tag"].startswith(("logo", "intro", "mjk", "hall", "personnel", "map", "island", "objectives", "boss", "f5"))]
            L(f"DMA machine: mode 2 at every stage {all(g['mode'] == 2 for g in st)}; music stages with a DMA tune {sum(1 for g in mus if g['mus'])}/{len(mus)}, "
              f"session 2 {sum(1 for g in mus if g['act'] == 2)}/{len(mus)}, $5138 = music tick {sum(1 for g in mus if g['p5138'] == '%08x' % MTICK)}/{len(mus)}")
        else:
            L(f"YM machine: mode 1 at every stage {all(g['mode'] == 1 for g in st)}; DMA tune never set {all(g['mus'] == 0 for g in st)}; "
              f"$ff8901 never started ({'00 or ff (no DMA hardware: the bus answers ff)' if machine == 'st' else '00'}) "
              f"{all(g['ff8901'] in (('00', 'ff') if machine == 'st' else ('00',)) for g in st)}; blob DMA flag never set {all(g['dma'] == 0 for g in st)}")
            if wavx:
                L("YM machine: WAV " + wav_silences(*wavx, res["tune_t0"]))
        L("bank checks:", res.get("bank"))
    except Exception as e:
        L("EXC", repr(e))
        L(traceback.format_exc())
        try:
            h.shot(OUT / f"mus_{name}_exc.png")
        except Exception:
            pass
    finally:
        if h:
            h.close()
        (OUT / f"mus_{name}.json").write_text(json.dumps(res, indent=1, default=str))
        (OUT / f"mus_{name}.txt").write_text("\n".join(res["log"]) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("name")
    r.add_argument("machine")
    r.add_argument("tos")
    r.add_argument("mem")
    r.add_argument("media", choices=["hd", "floppy"])
    r.add_argument("build")
    r.add_argument("--intro", type=float, default=44.0, help="seconds of the intro left alone after the tune start (HD)")
    r.add_argument("--snap", default=None, help="save a snapshot at the 3D view")
    r.add_argument("--to", default="f5", choices=STAGES)
    r.add_argument("--no-profile", action="store_true", help="skip the 250-VBL CPU profiles (Hatari's profiler gives no data / never returns on the Mega STE)")
    c = sub.add_parser("compare")
    c.add_argument("wav")
    c.add_argument("t0", type=float)
    c.add_argument("--secs", type=float, default=40.0)
    c.add_argument("--tune", type=int, default=1)
    c.add_argument("--other", type=int, default=5)
    a = ap.parse_args()
    {"run": cmd_run, "compare": cmd_compare}[a.cmd](a)


if __name__ == "__main__":
    main()
