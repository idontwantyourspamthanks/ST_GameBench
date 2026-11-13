"""Level-change cells: python3 cell_level.py --tag X [--media hd|acsi] [--machine ste] [--tos ..] [--mem ..] [--build DIR]
 1. cold boot to the first battle and SAVE immediately after the world loaded (no settling time);
 2. LOAD it, then at once QUIT MAP -> main menu -> CONQUEST GAME -> PROCEED (a new world loads through PP's data stub $140, counted);
 3. SAVE immediately after that second world loaded; LOAD the first save into it;
 4. RESTART MAP right after a LOAD.
Every step compares RAM against the file / dump."""
import argparse, hashlib, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--media", default="hd"); ap.add_argument("--build", default="build/Pop2Save")
ap.add_argument("--machine", default="ste"); ap.add_argument("--tos", default=None); ap.add_argument("--mem", type=int, default=2048)
a = ap.parse_args()
P = lambda *x: print(*x, flush=True)
OUT = SD / f"out_{a.tag}"; OUT.mkdir(exist_ok=True)
h, info = make(a.media, a.build, a.machine, a.tos, a.mem, a.tag)


def fbytes(n):
    if a.media == "hd":
        p = hdfile(h, n); return p.read_bytes() if p.exists() else None
    for _ in range(14):
        b = imgfile(info["img"], n)
        if b is not None and len(b) == SIZE:
            return b
        time.sleep(2.5)
    return b


def save(nm, dump):
    arm(h, 0x80300, OUT / dump, "&& d0 = 1", tag=dump)
    assert open_req(h); choose(h, "save"); name(h, nm); confirm(h)
    ok = waitfile(OUT / dump); r = wait_running(h, 90)
    return ok, r, ((OUT / dump).read_bytes() if ok else b"")


def load(nm, dump):
    arm(h, 0x2cc5e, OUT / dump, tag=dump)
    assert open_req(h); choose(h, "load"); name(h, nm); confirm(h)
    ok = waitfile(OUT / dump, 60); r = wait_running(h, 90)
    return ok, r, ((OUT / dump).read_bytes() if ok else b"")


def loads_so_far():
    return max([int(x) for x in re.findall(r"matched (\d+) times\.\s+pc = \$140", h._logtext())] or [0])


def newgame():
    """QUIT MAP -> main menu -> CONQUEST GAME -> PROCEED (the noquest build skips the manual question)"""
    assert open_req(h); h._click(535, 194, 14)
    t0 = time.time()
    while time.time() - t0 < 60 and h.peekl(0x70) != 0x18FA:
        time.sleep(1)
    time.sleep(3)
    h._click(384, 258, 8); h._click(216, 448, 12)
    return h.in_play()


try:
    t0 = time.time(); ok = h.boot_to_game()
    h.cmd("hatari-debug b pc = $140 :trace"); time.sleep(0.5)
    P(f"CELL {a.tag}: {info} boot {time.time()-t0:.0f}s in_play={ok} marker={h.marker()!r} turn={turn(h)} $148={h.peekw(0x148)}")
    # 1. save straight after the world loaded
    ok1, r1, A1 = save("lv1", "A1.bin")
    f = fbytes("LV1.GAM")
    P(f"1. SAVE right after the load: dump={ok1} back_in_play={r1} turn_in_dump={int.from_bytes(A1[0x16c:0x16e],'big') if A1 else None}; file == RAM at write: {f == A1}")
    # 2. LOAD then immediately a level change
    okb, rb, B1 = load("lv1", "B1.bin")
    P(f"2a. LOAD lv1: dump={okb} RAM == saved: {B1 == A1} running={rb} turn={turn(h)}")
    n0 = loads_so_far()
    t0 = time.time(); ng = newgame()
    P(f"2b. QUIT MAP right after the LOAD -> new conquest world: in_play={ng} turn={turn(h)} marker={h.marker()!r} ({time.time()-t0:.0f}s); PP data-stub calls ($140) during the change: {loads_so_far() - n0} (total {loads_so_far()})")
    # 3. save straight after the 2nd world loaded
    ok2, r2, A2 = save("lv2", "A2.bin")
    f2 = fbytes("LV2.GAM")
    P(f"3a. SAVE right after the second world loaded: dump={ok2} back_in_play={r2}; file == RAM at write: {f2 == A2}; differs from the first world's save: {A2 != A1}")
    okb, rb, B2 = load("lv1", "B2.bin")
    P(f"3b. LOAD lv1 (world 1) into world 2's session: RAM == saved: {B2 == A1} running={rb} turn={turn(h)}")
    # 4. RESTART MAP right after a LOAD
    n1 = loads_so_far()
    assert open_req(h); h._click(318, 194, 12)       # RESTART MAP -> the battle settings screen of the game; PROCEED starts the world again
    t0 = time.time()
    while time.time() - t0 < 60 and h.peekl(0x70) != 0x18FA:
        time.sleep(1)
    h._click(216, 448, 12)
    P(f"4. RESTART MAP right after the LOAD: running={wait_running(h, 60)} turn={turn(h)} in_play={h.in_play()}; $140 calls: {loads_so_far() - n1}")
    ok3, r3, A3 = save("lv3", "A3.bin")
    P(f"   SAVE after the restart: dump={ok3} running={r3}; file == RAM: {fbytes('LV3.GAM') == A3}")
    bad = logbad(h); P(f"LOG errors: {len(bad)}"); [P("  ", l) for l in bad[:6]]
    allok = ok1 and r1 and f == A1 and B1 == A1 and ng and ok2 and f2 == A2 and B2 == A1 and ok3
    P(f"RESULT {a.tag}: {'PASS' if allok else 'CHECK'}")
except Exception as e:
    import traceback; traceback.print_exc(); P("EXCEPTION", repr(e))
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}.log")
    h.close()
