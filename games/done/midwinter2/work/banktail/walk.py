#!/usr/bin/env python3
"""Cold-boot walk with a bank-in-RAM check at every checkpoint (work/notes/banktail.md).  Own workdir /tmp/mw2tail/<name>, private HOME.

    python3 work/banktail/walk.py NAME MACHINE TOS MEM_KB hd|floppy BUILD [--clk 16] [--to logo|mjk|hall|map|3d] [--fx 17,19,24,2] [--intro SECS] [--auto DIR]

HD:      BUILD = unzipped release dir (RUNME.TOS, FILES/ASNBANK.BIN ...).  --auto DIR: files copied to C:\\AUTO (TSR test).
Floppy:  BUILD = dir with FFA_boot.st FFB_graphics.st (A: boot, swap to B: at the Insert-Graphics prompt, D: = campaign).
Checks: header-watch (the end of the bank load) -> dump; HAGA swap-area record ($f8094 start / $f8098 count / ...) ; dump at logo, intro, mjk, hall, map, 3d.
--fx: at the 3D view request each effect id (request word $6862 = id*6) while Hatari records the WAV; WAV kept in the workdir (cap.wav) + copied to work/banktail/out/.
"""
import argparse, json, re, shutil, struct, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bt
from bt import ROOT, BANKF, BANK, T
import asn_live            # pk / request / voices / load_wav only (setup_home is NOT called: private HOME is bt's)

ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("machine"); ap.add_argument("tos"); ap.add_argument("mem")
ap.add_argument("media", choices=["hd", "floppy"]); ap.add_argument("build")
ap.add_argument("--clk", type=int, default=0)
ap.add_argument("--to", default="3d", choices=["logo", "mjk", "hall", "map", "3d"])
ap.add_argument("--fx", default="")
ap.add_argument("--intro", type=float, default=20.0)
ap.add_argument("--auto", default=None)
ap.add_argument("--wrap", default=None, help="KEEP_HEX: start the real RUNME behind a wrapper that keeps KEEP bytes resident (a driver stand-in), see mkwrap.py")
ap.add_argument("--snap", default=None)
ap.add_argument("--wav", type=float, default=0.0, help="record this many seconds of sound at the intro stage; prints rms and the DMA control register")
a = ap.parse_args()
OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)
LOG = []
def L(*x):
    s = " ".join(str(v) for v in x); LOG.append(s); print(s, flush=True)

bank = BANKF.read_bytes()
STAGES = ["logo", "mjk", "hall", "map", "3d"]
last = STAGES.index(a.to)
h = None
res = {"cell": a.name, "checks": {}}
try:
    if a.media == "hd":
        g = T / f"{a.name}_game"
        shutil.rmtree(g, ignore_errors=True); shutil.copytree(a.build, g, ignore=shutil.ignore_patterns("work"))
        shutil.copytree(ROOT / "work" / "disk_overlay", g / "work" / "disk_overlay")      # the created campaign disk (FILES\FFD): without it the game asks for the campaign disk at the boss screen
        if a.wrap:
            import subprocess
            shutil.move(g / "RUNME.TOS", g / "FILES" / "RUNME2.TOS")
            subprocess.run([sys.executable, str(Path(__file__).parent / "mkwrap.py"), str(g / "RUNME.TOS"), a.wrap], check=True)
        if a.auto:
            (g / "work" / "disk_overlay" / "AUTO").mkdir(exist_ok=True)         # mw2harness copies only named files of the game dir, plus work/disk_overlay (-> C:\AUTO)
            for f in Path(a.auto).iterdir(): shutil.copy(f, g / "work" / "disk_overlay" / "AUTO" / f.name)
        gdir = g
        h = bt.start(a.name, a.machine, a.tos, a.mem, game=gdir)
    else:
        d = Path(a.build)
        scratch = T / f"{a.name}_fl"
        shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
        for src, dst in (("FFA_boot.st", "A.st"), ("FFB_graphics.st", "B.st")): shutil.copy(d / src, scratch / dst)
        shutil.copy(ROOT / "work/disk_overlay/FILES/FFD", scratch / "D.st")
        (scratch / "empty").mkdir()
        h = bt.start(a.name, a.machine, a.tos, a.mem, game=scratch / "empty", extra=["--disk-a", str(scratch / "A.st"), "--disk-b", str(scratch / "D.st")])
    if a.clk: h.set_cpuclock(a.clk)
    R = h.R
    v0 = h.vbl()
    now = lambda: (h.vbl() - v0) / 50.053
    pk = lambda ad, n: asn_live.pk(h, ad, n, 0.3)

    def chk(tag, quiet=False):
        bad, ram = bt.dump_bank(h, tag)
        s = bt.summ(bad)
        L(f"[{tag:10s}] vbl {h.vbl()} bank ${BANK:x}-${BANK+len(bank):x} vs build/asn_bank.bin: {s}")
        ps = int.from_bytes(pk(0x42E, 4), "big")
        sw = pk(ps - 0x8000 + 0x94, 12)            # HAGA sits at phystop-$8000 ($f8000 on 1 MB): its swap-area record (start, count, ...)
        L(f"[{tag:10s}] phystop ${ps:x}, HAGA record ${ps - 0x8000 + 0x94:x}: start ${int.from_bytes(sw[:4],'big'):x} count {int.from_bytes(sw[4:6],'big')} (words $f8098) $f809c ${int.from_bytes(sw[8:12],'big'):x}")
        top = R / f"top_{tag}.bin"
        if top.exists(): top.unlink()
        h.debug(f"savebin {top} $f8000 $8000", 1.5)
        tb = top.read_bytes() if top.exists() else b""
        if tb:
            hi = tb[0x3488:]          # $fb488-$fffff
            nz = [i for i, x in enumerate(hi) if x]
            L(f"[{tag:10s}] $fb488-$fffff ({len(hi)} B above HAGA): {len(nz)} nonzero bytes" + (f", first ${0xfb488 + nz[0]:x} last ${0xfb488 + nz[-1]:x}" if nz else "") + f", md5 {__import__('hashlib').md5(hi).hexdigest()[:8]}")
        svb = pk(0xBBE00, 3); p5 = pk(0x5138, 4)
        L(f"[{tag:10s}] SV mode/act/dma = {svb.hex()} (2 = DMA sound, 1 = YM), $5138 = {p5.hex()} (bf81e = music tick, d0e = YM driver), canary @bank end: {ram[-4:] if len(ram) == len(bank) else '?'}")
        res["checks"][tag] = dict(n=len(bad), first=(BANK + bad[0]) if bad else None, last=(BANK + bad[-1]) if bad else None)
        if bad and not quiet:
            p = R / f"bk_{tag}.bin"
            OUT.joinpath(f"{a.name}_{tag}_tail.bin").write_bytes(ram[bad[0]:bad[-1] + 1])
        return bad

    # --- the end of the bank load: change-watch on the header (HD: load by the RUNME splice; floppy: the payload copy) -----------------
    fe = R / "fe.txt"; fx = R / "fx.txt"
    fe.write_text(f"e VBL\nr\nsavebin {R}/bk_prehaga.bin ${BANK:x} ${len(bank):x}\n")
    fx.write_text(f"e VBL\nr\nsavebin {R}/bk_posthaga.bin ${BANK:x} ${len(bank):x}\n")
    h.cmd(f"hatari-debug b pc = $fb1f0 :trace :once :file {fe}")
    time.sleep(0.3)
    h.cmd(f"hatari-debug b pc = $fb204 :trace :once :file {fx}")
    # --- first logo: tune start ------------------------------------------------------------------------------------------------------
    swapped = a.media == "hd"
    started = None
    t0 = time.time()
    ins = ROOT / "work/floppy_tests/ref_insert_graphics.png"
    while time.time() - t0 < 600 and (started is None or not swapped):
        time.sleep(1.5)
        p = asn_live.pk(h, 0x5138, 4, 0.3)
        if started is None and int.from_bytes(p, "big") in (0xBF81E, 0xD0E) and int.from_bytes(asn_live.pk(h, 0x7626, 2, 0.3), "big") == 1:
            started = now(); L(f"tune 1 started ($5138={p.hex()}) at {started:.1f} s emulated")
        if not swapped:
            from PIL import Image, ImageChops, ImageStat
            cur = Image.open(h.shot()).convert("RGB").crop((280, 360, 560, 420))
            dd = ImageChops.difference(cur, Image.open(ins).convert("RGB").crop((280, 360, 560, 420)))
            if sum(ImageStat.Stat(dd).mean) / 3 < 0.3:
                L(f"insert-graphics prompt at {now():.1f} s")
                h.cmd(f"hatari-option --disk-a {scratch / 'B.st'}"); swapped = True; time.sleep(2)
    if started is None: raise RuntimeError("tune 1 never started")
    for tag in ("prehaga", "posthaga"):
        ld = R / f"bk_{tag}.bin"
        if ld.exists():
            bad = bt.diff(ld.read_bytes(), bank)
            L(f"[{tag:10s}] bank dumped at the HAGA copy loop ({'entry $fb1f0' if tag == 'prehaga' else 'exit $fb204'}): {bt.summ(bad)}")
            res["checks"][tag] = dict(n=len(bad))
        else:
            L(f"[{tag:10s}] breakpoint never fired")
    L("debugger lines of the HAGA breakpoints:", [l.strip() for l in h.logpath.read_text(errors='replace').splitlines() if l.startswith(('= %', '  A4', '  A6', '  A7'))][:12])
    chk("logo")
    L("$ff8e21 (Mega STE speed/cache register):", pk(0xFF8E21, 1).hex(), "| status:", [l for l in h.logpath.read_text(errors='replace').splitlines() if 'MHz' in l][:2])
    L("vector table $806:", pk(0x806, 12).hex())
    tend = started + a.intro
    while now() < tend: time.sleep(3)
    chk("intro")
    if a.wav:
        cap = R / "cap.wav"
        if cap.exists(): cap.unlink()
        h.cmd("hatari-shortcut recsound"); time.sleep(a.wav); h.cmd("hatari-shortcut recsound"); time.sleep(1.5)
        L("$ff8901 (DMA sound control; 03 = playing, 00 = off, ff = no DMA hardware):", pk(0xFF8901, 1).hex(), " $ff8921:", pk(0xFF8921, 1).hex())
        if cap.exists():
            import numpy as np
            shutil.copy(cap, OUT / f"{a.name}_intro.wav")
            x, r = asn_live.load_wav(cap)
            seg = [float(np.sqrt(np.mean((x[int(i * r):int((i + 1) * r)] - x[int(i * r):int((i + 1) * r)].mean()) ** 2))) for i in range(int(len(x) / r))]
            L(f"intro WAV {len(x)/r:.1f} s: rms per second {[int(v) for v in seg]}")
    if last >= 1:
        ref = ROOT / "work" / "ref" / "mode_select.png"
        for _ in range(60):
            h.cmd("hatari-event keypress 57"); time.sleep(5)
            if h.screen_matches(ref, (280, 350, 560, 420)): break
        else: raise RuntimeError("never reached the M/J/K screen")
        chk("mjk")
        if a.media != "hd": h.debug("w $2c574 $60 $02")
        for _ in range(5):
            time.sleep(3); h.cmd("hatari-event keypress 50"); time.sleep(5)
            if not h.screen_matches(ref, (280, 350, 560, 420)): break
        else: raise RuntimeError("M/J/K key not accepted")
        time.sleep(4)
    if last >= 2:
        if a.media == "hd":
            time.sleep(6)
        else:
            from PIL import Image, ImageChops, ImageStat
            FT = ROOT / "work/floppy_tests"
            def sdiff(refp, box):
                cur = Image.open(h.shot()).convert("RGB").crop(box)
                dd = ImageChops.difference(cur, Image.open(refp).convert("RGB").crop(box))
                return sum(ImageStat.Stat(dd).mean) / 3
            def wait_match(target, timeout):
                t1 = time.time()
                while time.time() - t1 < timeout:
                    if sdiff(*target) < 4: return True
                    time.sleep(3)
                return False
            HALL = (FT / "ref_hall.png", (96, 350, 736, 458)); PERS = (FT / "ref_personnel.png", (96, 100, 330, 350)); MAP = (FT / "ref_map.png", (96, 300, 560, 458))
            def step(point, target, timeout=40):
                for _ in range(4):
                    h.goto(*point); h.click()
                    if wait_match(target, timeout): return
                raise RuntimeError(f"click at {point} never produced the expected screen")
            if not wait_match(HALL, 120): raise RuntimeError("never saw the HQ hall")
        chk("hall")
        if a.media == "hd":
            h.goto(554, 105); h.click(); time.sleep(15)
            h.goto(389, 140); h.click(); time.sleep(12)
            h.goto(414, 185); h.click(); time.sleep(25)
        else:
            step((554, 105), PERS); step((389, 140), HALL); step((414, 185), MAP, timeout=100); time.sleep(25)
    if last >= 3:
        chk("map")
    if last >= 4:
        h.goto(150, 280); h.key("space"); time.sleep(18)
        h.goto(230, 410); h.click(); time.sleep(15)
        boss = ROOT / "work/ref/boss_thumbs.png"
        ok = False
        for i in range(6):
            h.goto(140, 415); h.click(); time.sleep(8)
            h.shot(OUT / f"{a.name}_boss{i}.png")
            if h.screen_matches(boss, (590, 60, 740, 125)): ok = True; break
        L("boss screen matched:", ok)
        chk("boss")
        h.goto(625, 92); h.click(); time.sleep(40)
        for _ in range(12):
            if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2: break
            time.sleep(5)
        else: raise RuntimeError(f"no 3D view ($6220={h.peekw(0x6220):#x}, $700a={h.peekw(0x700A):#x})")
        for _ in range(40):
            if int.from_bytes(asn_live.pk(h, 0x5138, 4, 0.3), "big") == 0x18F92: break
            time.sleep(5)
        else: raise RuntimeError("$18f92 never took over $5138")
        time.sleep(15); h.center()
        h.shot(OUT / f"{a.name}_3d.png")
        bad3 = chk("3d")
        sv = pk(0xBBE00, 3); L(f"SV mode/act/dma = {sv.hex()}")
        if a.snap: h.savemem(a.snap); L("snapshot", a.snap)
        if a.fx:
            ids = [int(x) for x in a.fx.split(",")]
            cap = R / "cap.wav"
            h.debug("w $18eec $4e $75", 0.2); h.debug("w $686c $ff $ff", 0.2)    # the helicopter's own engine request off (asn_live --quiet): the capture holds the requested effects only
            time.sleep(10)
            if cap.exists(): cap.unlink()
            h.cmd("hatari-shortcut recsound"); time.sleep(0.5)       # starts the WAV capture here
            tstart = time.time(); log = []
            time.sleep(3)
            for sid in ids:
                asn_live.request(h, sid)
                e = time.time() - tstart
                vs = asn_live.voices(h)
                L(f"effect {sid} requested at wall {e:.1f}s; voices (cnt, smp, ln): {[(v['cnt'], hex(v['smp']), v['ln']) for v in vs if v['cnt']]}")
                log.append((sid, round(e, 2)))
                time.sleep(10)
            h.cmd("hatari-shortcut recsound"); time.sleep(1.5)
            L("requested:", log)
            if cap.exists():
                shutil.copy(cap, OUT / f"{a.name}_fx.wav"); L("wav", OUT / f"{a.name}_fx.wav", cap.stat().st_size)
            res["fx"] = log
    L("DONE", a.name)
except Exception as e:
    L("EXC", repr(e)); L(traceback.format_exc())
    try: h.shot(OUT / f"{a.name}_exc.png")
    except Exception: pass
finally:
    if h:
        h.close()
    (OUT / f"{a.name}.txt").write_text("\n".join(LOG) + "\n")
    (OUT / f"{a.name}.json").write_text(json.dumps(res, indent=1, default=str))
