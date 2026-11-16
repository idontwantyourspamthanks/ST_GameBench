#!/usr/bin/env python3
"""Cold boot of an asn_* build to the Lobos 3D view, with the sound group's checks (HD and floppy builds).

    python3 tools/asn_cold.py NAME MACHINE TOS MEM_KB (hd|floppy) BUILD_DIR [--set SET] [--no-sound] [--hz60]

MACHINE ste|megaste|st, TOS 162|206|104.  BUILD_DIR = build/asn_hd (RUNME.TOS...) or build/asn_fl (FFA_boot.st ...), made with
`MW2_BANK=build/asn_bank.bin python3 tools/mw2patch.py build ...` (see work/notes/amiga_sound.md).
Checks (results in work/asn_cold/NAME.json + .txt):
  - at the 3D view: marker MWPO, $6220 = $d, $700a = 2; the bank (its whole length from $BB000 minus the state / channel records / ring, `$BBE00-$BC7FF`;
    the blob is part of it at $BF800) in RAM equals the built image (bank survived every screen: M/J/K, hall, map, 3D view); mode byte SV+0 (2 = DMA sound, 1 = YM);
  - sound: effects requested like the game does (`$6862` = id * 6) while Hatari records a WAV (--sound 50066 + recsound); on mode 2 the DMA registers
    $ff8901.. are read back; on mode 1 the YM must produce the sound (WAV rms) and the DMA must stay off;
  - the natural engine request of the game (the helicopter's `$686c`) and one natural weapon fire (`$6872` pulse) with the ids seen at `$6862`.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import asn_live
from mw2harness import Hatari

TOSD = ROOT.parent.parent.parent / "tos"
TOS = {"162": TOSD / "TOS_1_62.img", "206": TOSD / "TOS_2_06.img", "104": TOSD / "TOS_1_04.img"}
OUT = ROOT / "work" / "asn_cold"
SV, BANK = 0xBBE00, 0xBB000
RING = 0xBC000


def main():
    a = sys.argv[1:]
    name, machine, tos, mem, media, bdir = a[:6]
    opts = a[6:]
    sound = "--no-sound" not in opts
    hz60 = "--hz60" in opts
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"cell": name, "log": []}
    txt = OUT / f"{name}.txt"

    def L(*x):
        s = " ".join(str(v) for v in x)
        res["log"].append(s)
        print(s, flush=True)

    os.environ["MW2_BANK"] = str(ROOT / "build" / "asn_bank.bin")
    import mw2patch as M
    bank = (ROOT / "build" / "asn_bank.bin").read_bytes()
    bank_len = int.from_bytes(bank[12:16], "big")
    h = None
    asn_live.setup_home()
    os.environ["HOME"] = str(asn_live.HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    extra = ["--sound", "50066"] if sound else []
    tt = machine == "tt"
    if tt:                                     # TT: its TOS and the MMU (as work/jagpad/cold.py), slower start
        sys.path.insert(0, str(ROOT.parent.parent.parent / "tools"))
        from stharness import MACHINE_TOS
        TOS["tt"] = MACHINE_TOS["tt"] if Path(MACHINE_TOS["tt"]).exists() else TOSD / "TOS_3_05_us.img"
        tos = "tt"
        extra += ["--mmu", "true"]
    try:
        if media == "hd":
            h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=TOS[tos], game_dir=ROOT / bdir, extra=extra)
            time.sleep(70 if tt else 25)
            ref = ROOT / "work" / "ref" / "mode_select.png"
            for _ in range(60):
                h.cmd("hatari-event keypress 57")
                time.sleep(5)
                if h.screen_matches(ref, (280, 350, 560, 420)):
                    break
            else:
                raise RuntimeError("never reached the M/J/K screen")
            L("M/J/K reached; MWPO", h.debug("m $b2ff8 4").strip().splitlines()[-1])
            for _ in range(5):
                time.sleep(3)
                h.cmd("hatari-event keypress 50")
                time.sleep(5)
                if not h.screen_matches(ref, (280, 350, 560, 420)):
                    break
            else:
                raise RuntimeError("M/J/K key not accepted")
            time.sleep(4)
        else:
            d = ROOT / bdir
            scratch = Path(f"/tmp/fl/run_{name}")
            shutil.rmtree(scratch, ignore_errors=True)
            scratch.mkdir(parents=True)
            for src, dst in (("FFA_boot.st", "A.st"), ("FFB_graphics.st", "B.st")):
                shutil.copy(d / src, scratch / dst)
            shutil.copy(ROOT / "work/disk_overlay/FILES/FFD", scratch / "D.st")
            empty = scratch / "empty"
            empty.mkdir()
            h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=TOS[tos], game_dir=empty,
                       extra=["--disk-a", str(scratch / "A.st"), "--disk-b", str(scratch / "D.st")] + extra)
            from PIL import Image, ImageChops, ImageStat

            def sdiff(refp, box):
                cur = Image.open(h.shot()).convert("RGB").crop(box)
                dd = ImageChops.difference(cur, Image.open(refp).convert("RGB").crop(box))
                return sum(ImageStat.Stat(dd).mean) / 3

            ins = ROOT / "work/floppy_tests/ref_insert_graphics.png"
            box = (280, 360, 560, 420)
            t0 = time.time()
            while time.time() - t0 < 360:
                time.sleep(4)
                if sdiff(ins, box) < 0.3:
                    break
            else:
                raise RuntimeError("never saw the Insert Graphics Disk prompt")
            L("insert-graphics prompt after %.0f s" % (time.time() - t0))
            h.cmd(f"hatari-option --disk-a {scratch / 'B.st'}")
            time.sleep(2)
            ref = ROOT / "work/ref/mode_select.png"
            for i in range(40):
                h.cmd("hatari-event keypress 57")
                time.sleep(5)
                if h.screen_matches(ref, (280, 350, 560, 420)):
                    break
            else:
                raise RuntimeError("never reached the M/J/K screen")
            L("M/J/K reached; MWPO", h.debug("m $b2ff8 4").strip().splitlines()[-1])
            h.debug("w $2c574 $60 $02")                      # TEST-ONLY security-check bypass of the floppy test cells (work/floppy_tests/run_cell.py)
            for _ in range(5):
                time.sleep(3)
                h.cmd("hatari-event keypress 50")
                time.sleep(5)
                if not h.screen_matches(ref, (280, 350, 560, 420)):
                    break
            FT = ROOT / "work/floppy_tests"

            def wait_match(target, timeout):
                t0 = time.time()
                while time.time() - t0 < timeout:
                    if sdiff(*target) < 4:
                        return True
                    time.sleep(3)
                return False

            HALL = (FT / "ref_hall.png", (96, 350, 736, 458))
            PERS = (FT / "ref_personnel.png", (96, 100, 330, 350))
            MAP = (FT / "ref_map.png", (96, 300, 560, 458))

            def step(point, target, timeout=40):
                for attempt in range(4):
                    h.goto(*point)
                    h.click()
                    if wait_match(target, timeout):
                        return attempt
                raise RuntimeError(f"click at {point} never produced the expected screen")

            if not wait_match(HALL, 120):
                raise RuntimeError("never saw the HQ hall")
            step((554, 105), PERS)
            step((389, 140), HALL)
            step((414, 185), MAP, timeout=100)
            time.sleep(25)
        # ---- map -> boss screen -> 3D view (shared) -------------------------------------------------------------
        if media == "hd":
            h.goto(554, 105); h.click(); time.sleep(15)
            h.goto(389, 140); h.click(); time.sleep(12)
            h.goto(414, 185); h.click(); time.sleep(25)
        h.goto(150, 280); h.key("space"); time.sleep(18)
        h.goto(230, 410); h.click(); time.sleep(15)
        boss = ROOT / "work/ref/boss_thumbs.png"
        for _ in range(6):
            h.goto(140, 415); h.click(); time.sleep(8)
            if h.screen_matches(boss, (590, 60, 740, 125)):
                break
        else:
            raise RuntimeError("never reached the boss screen")
        h.goto(625, 92); h.click(); time.sleep(40)
        for _ in range(12):
            if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2:
                break
            time.sleep(5)
        else:
            raise RuntimeError(f"no 3D view ($6220={h.peekw(0x6220):#x}, $700a={h.peekw(0x700A):#x})")
        if "--watch" in opts:      # how soon after the 3D view does the tick hook ($18f92) hold the jmp?
            t0w = time.time()
            for _ in range(24):
                b = asn_live.pk(h, 0x18F92, 6, 0.3)
                sv = asn_live.pk(h, SV, 3, 0.3)
                L(f"watch +{time.time() - t0w:5.1f}s $18f92 = {b.hex()}  SV mode/act/dma = {sv.hex()}  $5138 = {asn_live.pk(h, 0x5138, 4, 0.3).hex()}")
                time.sleep(1.0)
        time.sleep(20)
        h.center()
        h.shot(OUT / f"{name}_3d.png")
        L("3D view: $6220=%x $700a=%x" % (h.peekw(0x6220), h.peekw(0x700A)))
        L("MWPO:", h.debug("m $b2ff8 4").strip().splitlines()[-1])
        if hz60:
            h.debug("w $ff820a $00")
            L("60 Hz sync set")
        # ---- bank + code window equal the built image ------------------------------------------------------------
        sets = None
        if "--set" in opts:
            sets = opts[opts.index("--set") + 1]
        p = h.R / "asn_ram.bin"
        if p.exists():
            p.unlink()
        h.debug(f"savebin {p} 0xbb000 ${len(bank):x}", 4.0)
        ram = p.read_bytes()
        dyn = [(SV - BANK, RING - BANK + 2048)]          # state, music channel records, ring
        bad = [i for i in range(bank_len) if ram[i] != bank[i] and not any(a0 <= i < a1 for a0, a1 in dyn)]
        L(f"bank $BB000-${BANK + bank_len:x}: {len(bad)} bytes differ from asn_bank.bin outside the state/ring" + (f" (first {[hex(BANK + i) for i in bad[:6]]})" if bad else ""))
        mode = ram[SV - BANK]
        L(f"SV mode byte = {mode} (2 = DMA sound, 1 = YM)  act={ram[SV - BANK + 1]} dma={ram[SV - BANK + 2]}")
        res["mode"] = mode
        # ---- the sound tests ------------------------------------------------------------------------------------
        if sound:
            if asn_live.CAP.exists():
                asn_live.CAP.unlink()
            h.cmd("hatari-shortcut recsound")
            t0 = time.time()
            log = []
            # natural engine (helicopter) for 3 s, then ids requested like the game's fire code does
            time.sleep(3)
            vs = asn_live.voices(h) if mode == 2 else None
            L("voices after 3 s of natural engine:", vs)
            seq = [(5.0, 2), (8.0, 4), (11.0, 12), (14.0, 40)]
            for at, sid in seq:
                while time.time() - t0 < at:
                    time.sleep(0.1)
                asn_live.request(h, sid)
                log.append((round(time.time() - t0, 2), sid))
            # a natural weapon fire: pulse the fire level $6872 (the game's own fire code writes `$6862` itself); the blob consumes the request within one VBL,
            # so the sound is identified from the voices' effect record offsets (V_REC) while it plays
            while time.time() - t0 < 17:
                time.sleep(0.1)
            import asn_build
            tb = asn_build.Tables(asn_build.read_mwii(asn_build.ADF))
            first = {}
            for sid, row in enumerate(tb.rows):
                for ch, w in enumerate(row):
                    if w != 0xFFFF:
                        first[(ch, tb.seq_word(w))] = sid
            h.debug("w $6872 $ff $ff", 0.1)
            seen = []
            for _ in range(10):
                if mode == 2:
                    for c, v in enumerate(asn_live.voices(h)):
                        if v["cnt"] and (c, v["rec"]) in first:
                            seen.append((c, v["rec"], first[(c, v["rec"])]))
                time.sleep(0.1)
            h.debug("w $6872 $00 $00", 0.1)
            L("fire pulse: (voice, record, sound id) seen:", sorted(set(seen)))
            while time.time() - t0 < 24:
                time.sleep(0.1)
            h.cmd("hatari-shortcut recsound")
            time.sleep(1.0)
            regs = h.debug("m $ff8901 1", 0.4)
            sv = asn_live.pk(h, SV, 4)
            L(f"SV after the test: mode {sv[0]} act {sv[1]} dma {sv[2]}")
            L("requested:", log)
            L("DMA control reg:", re.findall(r"FF8901:\s+(\S+)", regs, re.I), "(mode 2: 03 while a sound is playing, 00 when silent)")
            wavp = OUT / f"{name}.wav"
            if asn_live.CAP.exists():
                shutil.copy(asn_live.CAP, wavp)
                L("wav", wavp)
        # ---- cost: cycles in the blob per VBL ------------------------------------------------------------------
        if "--cost" in opts:
            prof = h.profile(250)
            tot = sum(c for _, c in prof)
            blob = sum(c for ad, c in prof if 0xBF800 <= ad < 0xC1000)
            L(f"profile 250 VBL: total {tot}, blob {blob} ({blob / 250:.0f}/VBL)")
    except Exception as e:
        L("EXC", repr(e))
        L(traceback.format_exc())
        try:
            h.shot(OUT / f"{name}_exc.png")
        except Exception:
            pass
    finally:
        if h:
            res["workdir"] = str(h.R)
            h.close()
        (OUT / f"{name}.json").write_text(json.dumps(res, indent=1, default=str))
        txt.write_text("\n".join(res["log"]) + "\n")


if __name__ == "__main__":
    main()
