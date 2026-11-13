"""ICS floppy release cell: cold boot a built ICS floppy, check marker/payload, measure turns/s, scan the log, tooltip shots, optional in-game save+load.
   python3 cell.py --disk build/ics/Populous2_lowram.st --machine ste --tos 1.62 --mem 512 --tag ste512 [--clocks 8 16] [--hz 50 60] [--saveload]"""
import argparse, re, shutil, sys, time, json
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools", str(G / "work/scratch/disks")]
from populous2 import Populous2, HOME
from stharness import TOS
import p2tick as TK
from PIL import Image, ImageChops

ap = argparse.ArgumentParser()
ap.add_argument("--disk", default="build/ics/Populous2_lowram.st"); ap.add_argument("--machine", default="ste"); ap.add_argument("--tos", default=None)
ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--clocks", type=int, nargs="*", default=[0])
ap.add_argument("--hz", type=int, nargs="*", default=[]); ap.add_argument("--tag", required=True)
ap.add_argument("--vbls", type=int, default=1500); ap.add_argument("--saveload", action="store_true"); ap.add_argument("--extra", default="")
ap.add_argument("--noboot", action="store_true")
a = ap.parse_args()
BAD = re.compile(r"bus error|address error|exception [23] |halt|double|illegal", re.I)
extra = (["--mmu", "true"] if a.machine == "tt" else []) + a.extra.split()
disk = Path(a.disk); disk = disk if disk.is_absolute() else G / disk
st = Path(f"/tmp/ics_{a.tag}_a.st"); shutil.copy(disk, st)
empty = G / "work/scratch/disks/emptyC"; empty.mkdir(exist_ok=True)
extra += ["--disk-a", str(st), "--protect-floppy", "off"]
kw = dict(machine=a.machine, memsize_kb=a.mem, game_dir=empty, autorun=None)
if a.tos: kw["tos"] = TOS[a.tos]
lowram = (a.mem < 1024)
liveinfo = json.loads((G / f"build/live/ics_{'low' if lowram else 'full'}.json").read_text())
PBTICK = liveinfo.get("pb", {}).get("pop2_tick", 0x80000)
TK.D = PBTICK + 0x2800
h = Populous2(extra=extra, **kw)
h.tag = 'ics_' + a.tag; h.cp = st
shots = G / "work/shots"
def rd(a_, n): return TK.rdb(h, a_, n)
try:
    t0 = time.time(); ok = h.boot_to_game()
    sync = rd(0xFF820A, 1)[0]
    tick_hook = rd(0x22f14, 6).hex()
    print(f"CELL {a.tag}: ICS floppy {a.machine} TOS {a.tos or 'default'} {a.mem} KB ({'lowram' if lowram else 'full'} layout); boot {time.time()-t0:.0f}s in_play={ok} marker={h.marker()!r} $22f14={tick_hook} (expect 4ef9{PBTICK+0x2000:08x}) sync=${sync:02x} ({TK.sync_hz(sync)} Hz) turn={h.peekw(h.TURN)}", flush=True)
    # payload intact: dump the image range and compare with the live image of the same layout
    img = (G / f"build/live/ics_{'low' if lowram else 'full'}.img").read_bytes()
    base = liveinfo["img_base"]; dp = h.R / "pl.bin"
    h.dump(str(dp), base, len(img))
    for _ in range(40):
        if dp.exists() and dp.stat().st_size == len(img): break
        time.sleep(1)
    time.sleep(1); got = dp.read_bytes()
    # the tick control block D+$0.. changes at run time, as do the data blocks; compare the CODE bytes only (the nonzero bytes of the image)
    diff = [i for i in range(len(img)) if img[i] and got[i] != img[i]]
    print(f"payload ${base:x}+{len(img)}: {len([x for x in img if x])} non-zero image bytes, {len(diff)} differ in RAM" + (f" first at +${diff[0]:x}" if diff else ""))
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
    time.sleep(1)
    imgs = {}
    for name, (x, y) in (("none", (160, 100)), ("cat2", (91, 161)), ("strip4", (253, 180))):
        h.goto(HOME[0] + 2 * x, HOME[1] + 2 * y, HOME); time.sleep(2.5)
        p = shots / f"ics_{a.tag}_{name}.png"; h.shot(str(p)); imgs[name] = Image.open(p).convert("RGB")
    for n in ("cat2", "strip4"):
        bb = ImageChops.difference(imgs["none"], imgs[n]).getbbox()
        print(f"tooltip {n}: diff vs none bbox {bb}; shot ics_{a.tag}_{n}.png")
    print(f"pointer {h.peekw(0x393FA)},{h.peekw(0x393FC)} turn {h.peekw(h.TURN)}")
    mk = h.marker()
    if a.saveload:
        from dl import save_load
        r = save_load(h, 'T1'); print("SAVELOAD", r, flush=True)
        h.shot(str(shots / f"ics_{a.tag}_afterload.png"))
        h.cmd('hatari-shortcut quit'); time.sleep(4)        # Hatari writes the floppy image on exit
        sp = __import__('subprocess')
        d = sp.run(['mdir', '-i', str(st), '::'], capture_output=True, text=True).stdout.strip().splitlines()
        print("disk after save:", d[-2:], "; GAM files", [l for l in d if 'GAM' in l])
        print("fsck.fat -n:", sp.run(['fsck.fat', '-n', str(st)], capture_output=True, text=True).stdout.strip().splitlines()[-1])
    log = h._logtext()
    allb = [l for l in log.splitlines() if BAD.search(l)]
    probe = [l for l in allb if re.search(r"ffff8e21|ffff8924", l) and re.search(r"PC=\$1[0-9a-f]{4}", l) or re.search(r"ffff8a28", l)]
    bad = [l for l in allb if l not in probe]
    print(f"known hardware-probe lines (the game's $ffff8e21/$ffff8924 reads at PC $13968/$139xx; pop2_spr's blitter probe $ffff8a28 on an ST): {len(probe)}")
    print(f"LOG: {len(log.splitlines())} lines; bus/address-error/halt lines: {len(bad)}"); print("\n".join(bad[:8]))
    print(f"RESULT {a.tag}: ok={ok} marker={mk!r} errors={len(bad)}")
except Exception as e:
    import traceback; traceback.print_exc()
    lg = h._logtext()
    print('EXCEPTION', repr(e)); print('LOG TAIL:'); print(chr(10).join(lg.splitlines()[-12:]))
    print('BUS/HALT LINES:', *[l for l in lg.splitlines() if BAD.search(l)][:8], sep=chr(10))
finally:
    shutil.copy(h.logpath, G/'work/gates'/f'ics_{a.tag}.log')
    h.close()
