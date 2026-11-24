#!/usr/bin/env python3
"""HD campaign gates from a cold-booted title memstate of the full build (b3; the gate is real: the trampoline applied the sites).
   env.sh python3 gate.py SCENARIO --machine ste --mem 2048 [--tag X]
   scenarios: finish (HD c3: tracks 1..3 to the BAR, ending, title, campaign still selectable) | drivea (c3.st: same, from drive A, first track only unless --full)
              errors (missing HD file, corrupt files, empty drive A, bad disk: messages + recovery) | timeout (replay of the same custom track) | stock (10 min stock race)"""
import argparse, sys, time, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cplib import *
ap = argparse.ArgumentParser()
ap.add_argument("scenario"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--tos")
ap.add_argument("--snap"); ap.add_argument("--tag"); ap.add_argument("--build", default="b5"); ap.add_argument("--camp", default="c3"); ap.add_argument("--full", action="store_true")
ap.add_argument("--minutes", type=float, default=10)
a = ap.parse_args()
short = {(m, k): f"{n}{k // 1024}m" for m, n in (("ste", "ste"), ("megaste", "mste"), ("st", "st"), ("megast", "mst")) for k in (2048, 4096)}[(a.machine, a.mem)]
tag = a.tag or f"{a.scenario}_{short}"
snap = a.snap or str(HERE / f"snap/b5_{short}.sav")
camp = HERE / "camp"
V = dict(act=0xb8e00, loaded=0xb8e01, count=0xb8e02, pos=0xb8e04, start=0xb8e06, ptr=0xb8e08)
def new(src="hd", file=None, disk=None):
    gd = HERE / f"run_{tag}"; shutil.rmtree(gd, ignore_errors=True); shutil.copytree(HERE / a.build, gd)
    if file: shutil.copy(camp / file, gd / "FILES" / "MSTRACKS.TRK")
    extra = ["--disk-a", str(camp / disk)] if disk else []
    m = Moonshine(snapshot=snap, game_dir=str(gd), machine=a.machine, memsize_kb=a.mem, extra=extra, **({"tos": TOS[a.tos]} if a.tos else {}))
    if disk:                                              # a memstate restore forgets --disk-a: insert the disk at run time
        time.sleep(2); m.cmd(f"hatari-option --disk-a {camp / disk}"); time.sleep(3)
    return m
def skip_shop(m):
    """v1.0's spare parts store has a frozen mouse pointer (ta_nomouse, reported to the lead): skip `jsr $16718` at $725c by a debugger breakpoint that sets pc = $7262."""
    f = m.R / "skipshop.txt"; f.write_text("r pc=$7262\n")
    m.cmd(f"hatari-debug b pc = $725c :trace :file {f}"); time.sleep(0.3)
h = None
def shot(n): return h.shot(str(HERE / f"snap/{tag}_{n}.png"))
def st(t):
    b = mem(h, 0xb8e00, 12)
    log(f"[{t}] vbl={h.vbl()} act={b[0]:#x} loaded={b[1]:#x} count={W(b,2)} start={W(b,6)} ptr={L(b,8):#x} $102c={W(mem(h,0x102c,2)):#06x} len57890={W(mem(h,0x57890,2))} "
        f"$23c0={L(mem(h,0x23c0,4)):#x} $1024={mem(h,0x1024,1).hex()} $100e={W(mem(h,0x100e,2))} $5ff8={W(mem(h,0x5ff8,2))} $1021={mem(h,0x1021,1).hex()}")
def menu_open():
    h.keypress(0x44); time.sleep(3)
def downs(n):
    for _ in range(n): h.keypress(0x50); time.sleep(0.5)
def load_from(n_down, wait=40, label=""):
    """F10 menu: Down x n_down, Return; waits for loaded (or the end of the load); returns (loaded, seconds)."""
    downs(n_down); h.keypress(0x1c); t0 = time.time(); time.sleep(2); shot(f"{label}loading")
    while time.time() - t0 < wait:
        if mem(h, V["loaded"], 1)[0]: break
        # the main screen redraws with a message when the load fails: detect by the menu variable M_MSG ($10040a) becoming non-zero
        if L(mem(h, 0x10040a, 4)): break
        time.sleep(1)
    return mem(h, V["loaded"], 1)[0] != 0, time.time() - t0
def click_exit():
    """real shop exit (v1.0.1): pin the pointer to the top-left, move down (the shop clamps y <= 167 = the EXIT hotspot at x = 0), click."""
    for _ in range(8): h.cmd("hatari-event mousemove -100 -80"); time.sleep(0.05)
    time.sleep(0.3)
    for _ in range(10): h.cmd("hatari-event mousemove 0 20"); time.sleep(0.05)
    time.sleep(0.3); h.cmd("hatari-event leftdown"); time.sleep(0.3); h.cmd("hatari-event leftup"); time.sleep(0.3)
def click_at(x, y):
    """ST pixel (x, y): pin the pointer into the top-left corner, move by (x, y) in emulated pixels, click (Hatari events, deterministic)."""
    for _ in range(8): h.cmd("hatari-event mousemove -100 -80"); time.sleep(0.05)
    time.sleep(0.3)
    for _ in range(10): h.cmd(f"hatari-event mousemove {x // 10} {y // 10}"); time.sleep(0.05)
    time.sleep(0.3); h.cmd("hatari-event leftdown"); time.sleep(0.3); h.cmd("hatari-event leftup"); time.sleep(0.3)
def race_up():
    return L(mem(h, 0x23c0, 4)) != 0 and W(mem(h, 0x100e, 2)) > 30 and mem(h, 0x1024, 1)[0] == 0
def run_races(n, label, tmo=900, press=True):
    """Press SPACE through the screens, drive (joystick up) in every race; log each race start / over; returns list of (len57890, $102c at start, $23c0 at start)."""
    out = []; t0 = time.time(); inrace = False
    while (len(out) < n or inrace) and time.time() - t0 < tmo:
        time.sleep(4)
        up = race_up() and mem(h, 0x1024, 1)[0] == 0
        if up and not inrace:
            inrace = True; h.debug("w $6105 $01", 0.3); st(f"{label} race {len(out)} start"); shot(f"{label}_race{len(out)}")
            out.append((W(mem(h, 0x57890, 2)), W(mem(h, 0x102c, 2)), L(mem(h, 0x23c0, 4)), W(mem(h, V["pos"], 2))))
        elif mem(h, 0x1024, 1)[0] == 0xff and inrace:
            inrace = False; h.debug("w $6105 $00", 0.3); st(f"{label} race {len(out)-1} over"); shot(f"{label}_over{len(out)-1}")
        elif press and mem(h, 0x1024, 1)[0] == 0xff and len(out) < n:
            click_exit(); h.keypress(57)
        elif press and not up:
            h.keypress(57)
    return out

def after_ending_to_title(tmo=240):
    """SPACE every 5 s through the ending until the game's title routine $73e6 runs again (breakpoint count), then stop pressing keys."""
    h.cmd("hatari-debug b pc = $73e6 :trace"); time.sleep(1.0); n0 = len(h._logtext())
    t0 = time.time(); n = 0; seen = False
    while time.time() - t0 < tmo:
        if "pc = $73e6" in h._logtext()[n0:]:
            seen = True; break
        time.sleep(2.5); n += 1
        if n % 2 == 0: h.keypress(57)
        if n % 6 == 0: shot(f"end{n:02d}")
    h.debug("b all", 0.3)
    pass
    time.sleep(6)
    log("title reached after the ending:", seen, f"{time.time()-t0:.0f}s"); st("after ending (title)")

def sc_finish():
    global h
    h = new(file=f"{a.camp}.trk"); time.sleep(2)
    menu_open(); shot("1_main")
    ok, t = load_from(1, label="hd_"); log("HD load:", ok, f"{t:.1f}s"); time.sleep(1.5); shot("2_list")
    h.keypress(0x1c)
    n = 3 if a.camp == "c3" else 1
    res = run_races(n, "hd")
    log("RACES (len57890, $102c, $23c0, POS):", [(r[0], hex(r[1]), hex(r[2]), r[3]) for r in res])
    if a.camp == "c3":
        # 3rd race over -> ending -> title
        time.sleep(10); after_ending_to_title()
        menu_open(); shot("3_menu_after_end"); st("menu after the ending")
        h.keypress(1)   # Esc back to the title
        time.sleep(3); st("title after Esc"); shot("4_title")

def sc_timeout():
    global h
    h = new(file=f"{a.camp}.trk"); time.sleep(2)
    menu_open(); load_from(1); time.sleep(1.5); h.keypress(0x1c)
    t0 = time.time(); starts = []
    poked = False
    while time.time() - t0 < 600 and len(starts) < 2:
        time.sleep(4)
        if race_up() and mem(h, 0x1024, 1)[0] == 0:
            if not starts or (poked and starts and W(mem(h, 0x100e, 2)) < 120 and len(starts) == 1):
                h.debug("w $6105 $00", 0.3)
                st(f"race start {len(starts)}"); shot(f"race{len(starts)}")
                starts.append((W(mem(h, 0x57890, 2)), W(mem(h, 0x102c, 2)), L(mem(h, 0x23c0, 4)), W(mem(h, V["pos"], 2))))
                if len(starts) == 1:
                    h.debug("w $10ce $00 $fe", 0.3); poked = True      # time bar nearly full: the next passes run out of time
        elif not race_up():
            h.keypress(57)
    log("STARTS (len, $102c, $23c0, POS):", [(r[0], hex(r[1]), hex(r[2]), r[3]) for r in starts])
    time.sleep(2); st("end"); 

def sc_stock():
    global h
    h = new(); time.sleep(2)
    h.keypress(57)
    t0 = time.time(); v0 = None; last = 0
    while True:
        time.sleep(5)
        v = h.vbl()
        if race_up():
            if v0 is None:
                v0 = v; h.debug("w $6105 $01", 0.3); st("race start")
            if (v - v0) // 3000 > last:
                last = (v - v0) // 3000; st(f"+{(v - v0)/3000:.0f} min/10 (vbl {v - v0})"); shot(f"min{last}")
            if mem(h, 0x1024, 1)[0] == 0xff:
                h.debug("w $6105 $00", 0.3)
        else:
            h.keypress(57); h.debug("w $6105 $00", 0.3)
        if v0 is not None and v - v0 > a.minutes * 3000:
            break
    st("end of the run")

def sc_errors():
    global h
    def one(name, file, disk, n_down, wait, expect):
        global h
        h = new(file=file, disk=disk); time.sleep(2)
        menu_open(); ok, t = load_from(n_down, wait=wait, label=name + "_")
        time.sleep(1.0); shot(f"{name}_msg"); log(f"CASE {name}: loaded={ok} after {t:.1f}s (expect: {expect})")
        # recovery: back to 'Original game' (selection retained), Return starts the stock game
        for _ in range(n_down): h.keypress(0x48); time.sleep(0.5)
        h.keypress(0x1c)
        res = run_races(1, name + "_orig", tmo=300)
        log(f"CASE {name}: recovery race (len57890, $102c, $23c0, POS) = {[(r[0], hex(r[1]), hex(r[2]), r[3]) for r in res]} (stock: 19472, 0, $58c1x, 0)")
        h.close(); h = None
    one("nofile", None, None, 1, 6, "message NOT FOUND, stock recovery")
    for n in ("bad_crc", "bad_magic", "bad_table", "bad_short"):
        one(n, f"{n}.trk", None, 1, 8, "message damaged/invalid")
    one("emptyA", None, None, 2, 60, "message NO CAMPAIGN DISK after ~17 s")
    one("baddisk", None, "bad_crc.st", 2, 40, "message damaged (CRC)")

def sc_drivea():
    global h
    h = new(disk=f"{a.camp}.st"); time.sleep(2)
    menu_open(); ok, t = load_from(2, wait=60, label="a_"); log("drive A load:", ok, f"{t:.1f}s"); time.sleep(1.5); shot("2_list")
    h.keypress(0x1c)
    n = 3 if (a.camp == "c3" and a.full) else 1
    res = run_races(n, "a"); log("RACES (len57890, $102c, $23c0, POS):", [(r[0], hex(r[1]), hex(r[2]), r[3]) for r in res])

def sc_orig():
    global h
    h = new(file="c3.trk"); time.sleep(2)
    menu_open(); ok, t = load_from(1); log("loaded", ok); time.sleep(1.5); st("campaign loaded (list screen)")
    h.keypress(14); time.sleep(1.5); shot("1_main_after_esc"); st("Esc from the list = main menu, campaign still armed")
    h.keypress(0x1c)                  # the selection is on ORIGINAL GAME after Backspace from the list: Return
    time.sleep(2); st("ORIGINAL GAME chosen")
    res = run_races(1, "orig", tmo=300)
    st("stock race running")
    stock = open(HERE.parent.parent / "originals/MOONSHR/FILES/MS2", "rb").read()[163 * 512:163 * 512 + 16]
    log("RACE (len57890, $102c, $23c0, POS):", [(r[0], hex(r[1]), hex(r[2]), r[3]) for r in res])
    log("$58c00 =", mem(h, 0x58c00, 16).hex(), " stock level 0 block head =", stock.hex(), "->", "IDENTICAL" if mem(h, 0x58c00, 16) == stock else "DIFFERENT")
try:
    {"orig": sc_orig, "finish": sc_finish, "timeout": sc_timeout, "stock": sc_stock, "errors": sc_errors, "drivea": sc_drivea}[a.scenario]()
finally:
    if h: h.close()
