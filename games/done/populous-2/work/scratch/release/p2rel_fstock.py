"""Release cell: cold boot a default-set build (HD folder or 720K floppy), measure turns/s, scan the log, tooltip shot, optional Falcon sound proof."""
import argparse, re, shutil, sys, time
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2, HOME
from stharness import TOS
import p2tick as TK
from PIL import Image, ImageChops

ap = argparse.ArgumentParser()
ap.add_argument("--media", default="hd"); ap.add_argument("--machine", default="ste"); ap.add_argument("--tos", default=None)
ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--clocks", type=int, nargs="*", default=[0])
ap.add_argument("--hz", type=int, nargs="*", default=[]); ap.add_argument("--tag", required=True)
ap.add_argument("--vbls", type=int, default=1500); ap.add_argument("--sound", action="store_true"); ap.add_argument("--force8007", default="")
ap.add_argument("--extra", default="")
a = ap.parse_args()
BAD = re.compile(r"bus error|address error|exception [23] |halt|double|illegal", re.I)
extra = (["--mmu", "true"] if a.machine == "tt" else []) + a.extra.split()
kw = dict(machine=a.machine, memsize_kb=a.mem)
if a.tos: kw["tos"] = TOS[a.tos]
if a.media == "hd":
    kw.update(game_dir=G / "build/Pop2Release")
else:
    st = Path(f"/tmp/p2rel_{a.tag}.st"); shutil.copy(G / "build/Pop2ReleaseFstock/Populous2_boot.st", st)
    kw.update(game_dir=G / "build/Pop2ReleaseFstock", files=[], autorun="")
    extra += ["--disk-a", str(st)]
h = Populous2(extra=extra, **kw)
shots = G / "work/shots"
def rd(a_, n): return TK.rdb(h, a_, n)
try:
    t0 = time.time(); ok = h.boot_to_game()
    sync = rd(0xFF820A, 1)[0]
    print(f"CELL {a.tag}: media={a.media} {a.machine} TOS {a.tos or 'default'} {a.mem} KB; boot {time.time()-t0:.0f}s in_play={ok} marker={h.marker()!r} $22f14={rd(0x22f14,6).hex()} sync=${sync:02x} ({TK.sync_hz(sync)} Hz) turn={h.peekw(h.TURN)}", flush=True)
    ex = TK.counters(True)
    for hz in (a.hz or [TK.sync_hz(sync)]):
        cur = TK.sync_hz(rd(0xFF820A, 1)[0])
        if hz != cur:
            h.debug("w $ff820a $%02x" % (0 if hz == 60 else 2), 0.5); time.sleep(1.0)
        for mhz in a.clocks:
            if mhz: h.set_cpuclock(mhz)
            time.sleep(1.0); h.cmd("hatari-option --fast-forward on")
            s0 = TK.sample_at(h, h.vbl() + 60, ex); s1 = TK.sample_at(h, s0["VBL"] + a.vbls * hz // 50, ex)
            h.cmd("hatari-option --fast-forward off")
            cpu = mhz or {"st": 8, "ste": 8, "megaste": 16, "tt": 32, "falcon": 16}[a.machine]
            TK.report(f"{a.tag} {mhz or 'default'} MHz {hz} Hz", s0, s1, ex, hz, True, cpu_mhz=cpu)
    # tooltip: hover the earth category icon (and a strip icon), compare with a no-hover shot
    time.sleep(1)
    imgs = {}
    for name, (x, y) in (("none", (160, 100)), ("cat2", (91, 161)), ("strip4", (253, 180))):
        h.goto(HOME[0] + 2 * x, HOME[1] + 2 * y, HOME); time.sleep(2.5)
        p = shots / f"rel_{a.tag}_{name}.png"; h.shot(str(p)); imgs[name] = Image.open(p).convert("RGB")
    for n in ("cat2", "strip4"):
        bb = ImageChops.difference(imgs["none"], imgs[n]).getbbox()
        print(f"tooltip {n}: diff vs none bbox {bb}; shot rel_{a.tag}_{n}.png")
    print(f"pointer {h.peekw(0x393FA)},{h.peekw(0x393FC)} turn {h.peekw(h.TURN)}")
    if a.sound:
        print(f"SOUND: $2aa74 = {h.peekl(0x2aa74):#010x} {h.peekl(0x2aa78):#010x} (jsr {0x4eb90008:#x}1080 expected: 4eb90008 108 04e71); $134={h.peekl(0x134):#x}")
        h.dump  # exists
        if a.force8007:
            h.debug("w $f0000 $3f $00 $2f $01 $2f $08 $13 $fc $00 $" + a.force8007 + " $ff $ff $80 $07 $4e $f9 $00 $02 $aa $54", 0.5)
            h.debug("w $2aa4e $4e $f9 $00 $0f $00 $00", 0.5)
            print(f"forced: handler entry {h.peekl(0x2aa4e):#x}; every IRQ does CPU write $ff8007:=${a.force8007}")
        h.debug("b all", 0.3)
        h.cmd("hatari-debug b pc = $81080 :trace :once"); time.sleep(0.4)
        h.cmd("hatari-debug b pc = $2aa4e :trace :once"); time.sleep(0.4)
        mark = len(h._logtext())
        # natural samples: effect clicks on the map (raise land / earthquake etc.), several rounds
        for rnd in range(6):
            h.key("F3", 0.3); time.sleep(0.5)
            h.goto(HOME[0] + 2 * 160, HOME[1] + 2 * (100 + rnd * 8), HOME); h.click(hold=0.4); time.sleep(2.0)
            fired = [l for l in h._logtext()[mark:].splitlines() if "matched" in l]
            print(f"round {rnd}: matched breakpoints so far: {len(fired)}", flush=True)
            if len(fired) >= 2: break
        print("matched:", *[l for l in h._logtext()[mark:].splitlines() if "matched" in l], sep="\n  ")
        print(f"after: $2aa74 = {h.peekl(0x2aa74):#010x}; turn {h.peekw(h.TURN)}; in_play {h.in_play()}; $2b60b..e = {rd(0x2b60a,6).hex()}")
        h.shot(str(shots / f"rel_{a.tag}_sound.png"))
    log = h._logtext()
    allb = [l for l in log.splitlines() if BAD.search(l)]
    probe = [l for l in allb if re.search(r"ffff8e21|ffff8924", l) and re.search(r"PC=\$1[0-9a-f]{4}", l) or re.search(r"ffff8a28.*PC=\$8432", l)]     # PP's TT-register probe, same in the stock game (PC $13968 there)
    bad = [l for l in allb if l not in probe]
    print(f"known probe lines (PP's $ffff8e21/$ffff8924 reads from RUNME PC $1b9xx = stock $139xx; pop2_spr's bus-error-safe blitter probe write $ffff8a28 at PC $8432x on an ST): {len(probe)}")
    print(f"LOG: {len(log.splitlines())} lines; bus/address-error/halt lines: {len(bad)}"); print("\n".join(bad[:8]))
    print(f"RESULT {a.tag}: ok={ok} marker={h.marker()!r} errors={len(bad)}")
except Exception as e:
    lg = h._logtext()
    print('EXCEPTION', repr(e)); print('LOG TAIL:'); print(chr(10).join(lg.splitlines()[-12:]))
    print('BUS/HALT LINES:', *[l for l in lg.splitlines() if BAD.search(l)][:8], sep=chr(10))
finally:
    h.close()
