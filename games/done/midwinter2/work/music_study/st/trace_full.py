#!/usr/bin/env python3
"""Cold boot of the ORIGINAL HD build to the 3D view (boot_to_game steps) with PC breakpoints on the music API and a polled timeline.
   usage: trace_full.py OUTDIR [--machine ste] [--game DIR] [--floppy-dir DIR]"""
import sys, time, re, os, shutil, threading
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
gd = Path(sys.argv[sys.argv.index("--game") + 1]) if "--game" in sys.argv else ROOT
machine = sys.argv[sys.argv.index("--machine") + 1] if "--machine" in sys.argv else "ste"
os.environ["SDL_AUDIODRIVER"] = "dummy"
BPS = {
    "ym_start_c6c": 0xc6c, "ym_stop_c4c": 0xc4c, "stop_5032": 0x33870, "stop_restore_502c": 0x338c2,
    "start_tune": 0x321fe, "setvec_3225c": 0x3225c, "setvec_32288": 0x32288, "setvec_32322": 0x32322,
    "fade_start_3238e": 0x3238e, "fadeout_322d6": 0x322d6, "sfx_init_18e32": 0x18e32, "tick_restore_338c6": 0x338c6,
    "once_end_e78": 0xe78, "tune9_32186": 0x32186, "tune_deferred_3234a": 0x3234a, "mute_toggle_26376": 0x26376,
}
h = Hatari(snapshot=None, memsize_kb=1024, machine=machine, game_dir=gd)
lock = threading.Lock()
_dbg = h.debug
def dbg(s, wait=0.8):
    with lock:
        return _dbg(s, wait)
h.debug = dbg
slock = threading.Lock()
_shot = h.shot
def shot(*a, **k):
    with slock:
        return _shot(*a, **k)
h.shot = shot
t0 = time.time()
stop = False
tl = open(out / "timeline.txt", "w")
def parse_mem(txt):
    got = {}
    for m in re.finditer(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", txt, re.M | re.I):
        a = int(m.group(1), 16)
        for i, x in enumerate(m.group(2).split()):
            got[a + i] = x
    return got
def rd(got, addr, n):
    return ''.join(got.get(addr + i, '??') for i in range(n))
def poll():
    k = 0
    while not stop:
        try:
            with lock:
                n = len(h._logtext())
                for c in ["e VBL", "m $5138 8", "m $7626 22", "m $b96 16", "m $c44 2", "m $757c 2", "m $700a 2", "m $f92a 2", "m $6220 2", "m $6876 2"]:
                    h.cmd("hatari-debug " + c)
                time.sleep(1.2)
                txt = h._logtext()[n:]
            v = re.search(r"#(\d+) \(dec\)", txt)
            g = parse_mem(txt)
            tl.write(f"t={time.time()-t0:6.1f} VBL={v.group(1) if v else '?':>6} 5138={rd(g,0x5138,4)} 513c={rd(g,0x513c,4)} 7626={rd(g,0x7626,2)} 7628={rd(g,0x7628,2)} 762a={rd(g,0x762a,2)} 762c={rd(g,0x762c,2)} 763a={rd(g,0x763a,2)} 763c={rd(g,0x763c,2)} b96={rd(g,0xb96,4)} b9a={rd(g,0xb9a,2)} b9c={rd(g,0xb9c,4)} ba0={rd(g,0xba0,2)} ba2={rd(g,0xba2,2)} c44={rd(g,0xc44,2)} 757c={rd(g,0x757c,2)} 700a={rd(g,0x700a,2)} f92a={rd(g,0xf92a,2)} 6220={rd(g,0x6220,2)} 6876={rd(g,0x6876,2)}\n"); tl.flush()
            k += 1
            if k % 8 == 0:
                try: shutil.copy(h.shot(), out / f"s{int(time.time()-t0):04d}.png")
                except Exception as e: pass
        except Exception as e:
            tl.write(f"poll error {e}\n")
        time.sleep(0.5)
try:
    for name, a in BPS.items():
        f = h.R / f"bp_{name}.txt"
        f.write_text("e VBL\nr\nm a7 16\nm $7626 2\nm $b96 4\nm $757c 2\nm $700a 2\n")
        h.cmd(f"hatari-debug b pc = ${a:x} :trace :file {f}")
        time.sleep(0.2)
    th = threading.Thread(target=poll, daemon=True); th.start()
    try:
        h.boot_to_game("M")
    except Exception as e:
        print("boot_to_game:", e)
    time.sleep(10)
    stop = True; time.sleep(3)
    shutil.copy(h.logpath, out / "hatari_log.txt")
finally:
    h.close()
