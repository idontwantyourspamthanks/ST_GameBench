#!/usr/bin/env python3
"""Campaign gates for the HD and the FLOPPY build, cold boot of the built release; no skip_shop anywhere: every shop is crossed with the real EXIT click (v1.0.1: pointer (0,167)).
   env.sh python3 campgate.py SCENARIO --kind hd|fl --machine ste|megaste|st|megast --mem 2048|4096 [--build DIR] [--tag X] [--src hd|a|b] [--d2b] [--noff]
   Menu items: HD  = ORIGINAL GAME / LOAD FROM HARD DISK (FILES\\MSTRACKS.TRK copy) / LOAD FROM DRIVE A / LOADED CAMPAIGN / BACK;
               FL  = ORIGINAL GAME / LOAD FROM DRIVE A / LOAD FROM DRIVE B / ... (the campaign disk is a 720 KB FAT12 image, msrtrack.py disk)
   scenarios: finish  load the 3-track campaign (--src), race 1..3 through the real shop, ending, title, campaign still selectable (--first-only: race 1 only)
              timeout c3 loaded: race 1 times out (replay of the same custom track), again, the third time-out = game over to the title
              orig    c3 loaded, then ORIGINAL GAME: the stock game
              errors  one session: every error case, then a good load and ORIGINAL GAME
              stock   stock race, no campaign key, for --minutes (default 10)"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cg import *

ap = argparse.ArgumentParser()
ap.add_argument("scenario"); ap.add_argument("--kind", default="hd"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--build"); ap.add_argument("--tag"); ap.add_argument("--camp", default="c3"); ap.add_argument("--src")
ap.add_argument("--first-only", action="store_true"); ap.add_argument("--minutes", type=float, default=10)
ap.add_argument("--d2b", action="store_true", help="floppy: disk 2 in drive B from power-on (two-drive machine)")
ap.add_argument("--sound", action="store_true"); ap.add_argument("--psg", action="store_true"); ap.add_argument("--noff", action="store_true")
a = ap.parse_args()
KIND = a.kind
build = a.build or ("/tmp/msrc2/hd_a" if KIND == "hd" else "/tmp/msrc2/fl_a")
short = f"{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st', 'megast': 'mst'}[a.machine] }{a.mem // 1024}m"
src = a.src or ("hd" if KIND == "hd" else "a")
tag = a.tag or f"{KIND}_{a.scenario}{'_' + src if a.scenario == 'finish' else ''}{'_d2b' if a.d2b else ''}_{short}"
logopen(tag)
LENS = [19472, 19000, 18000]          # $57890 = race length of base levels 0, 3, 5 (c3.trk)
BASES = [0, 3, 5]
STORE = (0x110000, 0x130000)
ITEM = {"hd": {"hd": 1, "a": 2}, "fl": {"a": 1, "b": 2}}[KIND]
sound = a.sound or a.psg
disk_a = Path(build) / "disk_a.st" if KIND == "fl" else None
disk_b = Path(build) / "disk_b.st" if (KIND == "fl" and a.d2b) else None
d2 = Path(build) / "disk_b.st" if (KIND == "fl" and not a.d2b) else None
r = Run(KIND, a.machine, a.mem, tag, build=build, camp_hd=(CAMP / f"{a.camp}.trk") if (KIND == "hd" and a.scenario in ("finish", "timeout", "orig") and src == "hd") else None,
        disk_a=disk_a, disk_b=disk_b, d2=d2, d2_drive="a" if src != "b" else "a", sound=sound, psg=a.psg, strict=a.psg, noff=a.noff)
log(f"== {tag}: {KIND} {MACH[a.machine]} {a.mem // 1024} MB build {build} src {src}")

def start_state(i, res):
    ln, c102c, ptr23c0, pos = res
    check(f"race{i} stream inside the campaign store", STORE[0] <= ptr23c0 < STORE[1], f"$23c0={ptr23c0:#x}")
    check(f"race{i} base level", c102c == BASES[i], f"$102c={c102c:#06x} expect {BASES[i]}")
    check(f"race{i} race length of the base level", ln == LENS[i], f"$57890={ln} expect {LENS[i]}")
    check(f"race{i} position", pos == i, f"POS={pos}")

def goto_item(n):
    for _ in range(8):
        s = r.w(0x100406)
        if s == n: return True
        r.key(0x50 if s < n else 0x48); time.sleep(0.6)
    return r.w(0x100406) == n

def do_load(item, label, wait=90):
    """select main-menu item `item`, Return; wait until loaded or a message (a text on row 20 that is not the LOADING line) shows; returns (ok, seconds, message-row texts)"""
    goto_item(item); texts_start(r)
    r.key(0x1c); v0 = r.vbl(); t0 = time.time(); time.sleep(1)
    vl = None
    while time.time() - t0 < wait:
        if time.time() - t0 > 20: r.ff(True)                         # normal speed first (a good load takes 3-8 s), fast-forward only for the long waits of the error cases
        if r.b(V["loaded"]): vl = r.vbl(); break
        if any(t[1] == 20 and t[2].strip() and "..." not in t[2] and "INSERT" not in t[2] for t in texts_peek(r)): vl = r.vbl(); break
        time.sleep(0.3)
    r.ff(False); time.sleep(1.5); tx = texts_stop(r)
    ok = r.b(V["loaded"]) != 0
    r.shot(label)
    return ok, ((vl or r.vbl()) - v0) / 50.0, [t[2] for t in tx if t[1] == 20]

def prepare_source(which):
    """put the campaign where `which` ('hd' = already in FILES via the overlay; 'a'/'b' = a disk in that drive)"""
    if which in ("a", "b"): r.insert(which, CAMP / f"{a.camp}.st")

def ending(hits, tmo=300):
    """after the last race: SPACE through the ending (fast-forward) until the title routine $723c runs again; the key byte is cleared at that hit.  hits() = counters armed before the races."""
    t0 = time.time(); n = 0
    r.ff(True)
    while time.time() - t0 < tmo:
        time.sleep(1.0); n += 1
        h = hits()
        if h[0x723c]: break
        if n % 4 == 0: r.key(57)
    r.ff(False); time.sleep(3)
    h = hits(); log(f"ENDING hits (shop call $725c, ending $732c, ending picture $75e8, title $723c, new game $7252): {h}")
    return h

def sc_finish():
    r.menu_open(); r.shot("1_main")
    prepare_source(src)
    ok, t, tx = do_load(ITEM[src], "2_after_load", wait=120)
    log(f"LOAD {src}: loaded={ok} {t:.1f}s message-row texts={tx}")
    check("campaign loaded", ok)
    if not ok: return
    cv = r.mem(V["act"], 12)
    check("loaded count", W(cv, 2) == 3, f"count={W(cv, 2)}")
    time.sleep(1); r.shot("3_list"); r.st("list screen")
    hits = r.exec_hits([0x725c, 0x732c, 0x75e8, 0x723c, 0x7252], clear_key_at=(0x723c,))
    r.key(0x1c)
    n = 1 if a.first_only else 3
    res = r.play_races(n, "c")
    for i, x in enumerate(res): start_state(i, x)
    check("all races reached", len(res) == n, f"{len(res)} of {n}")
    check("race over reached", r.b(0x1024) == 0xff)
    log(f"HITS after the races (shop $725c, ending $732c, picture $75e8, title $723c): {hits()}")
    if a.first_only or len(res) < 3: return
    time.sleep(2)
    h = ending(hits)
    check("ending reached ($732c, $75e8)", h[0x732c] >= 1 and h[0x75e8] >= 1)
    check("title reached after the ending ($723c), no new game started by a stray key ($7252 once = the campaign start)", h[0x723c] >= 1 and h[0x7252] == 1, f"{h}")
    r.st("title after the ending")
    cv = r.mem(V["act"], 12)
    check("campaign stays loaded after the ending", cv[0] == 0xff and W(cv, 2) == 3)
    texts_start(r); r.menu_open(); time.sleep(1.5); r.shot("4_menu_after_end")
    tx = texts_stop(r); txs = [t[2] for t in tx]; log("MENU after the ending, texts:", txs[:14])
    check("F10 after the ending shows the loaded campaign again", any("LOADED CAMPAIGN: " in t and "3" in t for t in txs))
    r.key(1); time.sleep(3)                                        # Esc: back to the title
    r.st("title after Esc"); r.shot("5_title")

def sc_timeout():
    r.menu_open(); prepare_source(src); ok, t, tx = do_load(ITEM[src], "1_load"); check("campaign loaded", ok)
    r.key(0x1c)                                                    # play from track 1
    seen = []
    for k in range(3):
        res = r.wait_race(tmo=300, shop=False)
        if res is None: log(f"timeout case {k}: no race start"); r.st("no race"); break
        r.st(f"timeout race {k} start"); r.shot(f"to_race{k}"); seen.append(res)
        r.poke(0x6105, 0x00)
        r.poke(0x10ce, 0x00, 0xfe)                                 # time bar: the next pass crosses $ff = time-out
        t0 = time.time()                                             # normal speed: a replay starts within seconds of the time-out
        while time.time() - t0 < 120 and r.b(0x1024) != 0xff: time.sleep(0.2)
        r.st(f"timeout race {k} over"); r.shot(f"to_over{k}")
        check(f"time-out {k}: the game counted it ($1027 == {k + 1})", r.b(0x1027) == k + 1, f"$1027={r.b(0x1027)} $1024={r.b(0x1024):#04x}")
    if len(seen) >= 2:
        check("replay = the same custom track (same race length, stream pointer, position 0)",
              all(s[0] == seen[0][0] and s[2] == seen[0][2] and s[3] == 0 for s in seen[:2]), f"{[(s[0], hex(s[1]), hex(s[2]), s[3]) for s in seen]}")
    hits = r.exec_hits([0x723c, 0x7252])
    t0 = time.time(); r.ff(True)
    while time.time() - t0 < 150 and hits()[0x723c] == 0:
        time.sleep(1.0)
        if int(time.time() - t0) % 3 == 0: r.key(57)
    r.ff(False); time.sleep(2)
    log("after the third time-out: title hits", hits(), f"$102c={r.w(0x102c):#06x}")
    check("third time-out = game over, back to the title ($723c)", hits()[0x723c] >= 1)
    cv = r.mem(V["act"], 12); check("campaign still loaded after game over", cv[0] == 0xff and W(cv, 2) == 3)

def sc_orig():
    r.menu_open(); prepare_source(src); ok, t, tx = do_load(ITEM[src], "1_load"); check("campaign loaded", ok)
    r.key(14); time.sleep(1.5); r.st("Backspace from the list = main menu, campaign armed")
    r.shot("2_main_after_back")
    goto_item(0); r.key(0x1c); time.sleep(2); r.st("ORIGINAL GAME chosen")
    cv = r.mem(V["act"], 12); check("ORIGINAL GAME clears ACT", cv[0] == 0, f"act={cv[0]:#x}")
    res = r.wait_race(tmo=300)
    check("stock race started", res is not None)
    if res:
        ln, c102c, p23c0, pos = res
        stock = open(G / "originals/MOONSHR/FILES/MS2", "rb").read()[163 * 512:163 * 512 + 16]
        check("stock block at $58c00 (level 0 of the original MS2)", r.mem(0x58c00, 16) == stock)
        check("stock stream pointer inside $58c00 area", 0x58c00 <= p23c0 < 0x5a000, f"$23c0={p23c0:#x}")
        check("stock base level / length", c102c == 0 and ln == 19472, f"$102c={c102c:#x} len={ln}")
        r.st("stock race running")
        r.poke(0x6105, 0x01); time.sleep(15); r.poke(0x6105, 0x00); r.st("stock race driving")

def sc_errors():
    T = CAMP
    blank = r.tmp / "blank.st"; blank.write_bytes(bytes(737280))
    empty = r.tmp / "empty.trk"; empty.write_bytes(b""); big = r.tmp / "big.trk"; big.write_bytes(bytes(200000))
    ver = r.tmp / "bad_ver.trk"; d = bytearray((T / "c3.trk").read_bytes()); d[4] = 9; ver.write_bytes(bytes(d))
    host = r.h.R / "C" / "FILES" / "MSTRACKS.TRK"
    r.menu_open()
    def case(name, item, expect, wait=45, host_file=None, disk=None, drive=None, eject=None):
        if host_file == "none": host.unlink(missing_ok=True)
        elif host_file is not None: host.parent.mkdir(exist_ok=True); shutil.copy(host_file, host)
        if eject: r.eject(eject)
        if disk: r.insert(drive, disk)
        ok, t, tx = do_load(item, f"e_{name}", wait=wait)
        act = r.mem(V["act"], 4)
        log(f"CASE {name}: loaded={ok} {t:.1f}s message-row texts={tx} act={act[0]:#x} loaded={act[1]:#x} count={W(act, 2)}")
        if expect is None:
            check(f"{name}: loads", ok)
            r.key(14); time.sleep(1.5)                                   # Backspace: the list screen back to the main menu
        else:
            check(f"{name}: rejected with a message", (not ok) and any(expect in x for x in tx), f"expect {expect!r}")
            check(f"{name}: campaign not armed", act[0] == 0 and act[1] == 0)
    if KIND == "hd":
        case("nofile", 1, "NOT FOUND", wait=20, host_file="none")
        case("empty_file", 1, "NOT A VALID", wait=20, host_file=empty)
        case("too_big", 1, "TOO BIG", wait=30, host_file=big)
        case("bad_magic", 1, "NOT A VALID", wait=20, host_file=T / "bad_magic.trk")
        case("bad_version", 1, "NOT A VALID", wait=20, host_file=ver)
        case("bad_table", 1, "DAMAGED", wait=20, host_file=T / "bad_table.trk")
        case("bad_crc", 1, "DAMAGED", wait=20, host_file=T / "bad_crc.trk")
        case("bad_short", 1, "NOT A VALID", wait=20, host_file=T / "bad_short.trk")
        case("good_hd", 1, None, wait=40, host_file=T / "c3.trk")
        case("bad_after_good", 1, "DAMAGED", wait=20, host_file=T / "bad_crc.trk")           # a failed load disarms the previous campaign
        case("emptyA", 2, "NO CAMPAIGN DISK", wait=90)
        case("blankdisk", 2, "NO CAMPAIGN DISK", wait=90, disk=blank, drive="a")
        case("corruptdisk", 2, "DAMAGED", wait=90, disk=T / "bad_crc.st", drive="a")
        case("good_drivea", 2, None, wait=60, disk=T / "c3.st", drive="a")
    else:
        # campaign disks in drive A (item 1) and drive B (item 2); drive B of the harness is empty at boot
        case("gamedisk_in_A", 1, "NO CAMPAIGN DISK IN DRIVE A", wait=60)                      # the boot disk (not FAT) as a campaign disk
        case("ejected_A", 1, "NO CAMPAIGN DISK IN DRIVE A", wait=60, eject="a")
        case("emptyB", 2, "NO CAMPAIGN DISK IN DRIVE B", wait=60)
        case("blank_in_A", 1, "NO CAMPAIGN DISK IN DRIVE A", wait=60, disk=blank, drive="a")
        case("corruptdisk_A", 1, "DAMAGED", wait=90, disk=T / "bad_crc.st", drive="a")
        case("corruptdisk_B", 2, "DAMAGED", wait=90, disk=T / "bad_crc.st", drive="b")
        case("good_B", 2, None, wait=60, disk=T / "c3.st", drive="b")
        case("bad_after_good", 1, "DAMAGED", wait=90, disk=T / "bad_crc.st", drive="a")
        case("good_A", 1, None, wait=60, disk=T / "c3.st", drive="a")
    goto_item(0); r.key(0x1c); time.sleep(2)
    res = r.wait_race(tmo=400)
    check("ORIGINAL GAME after the errors: stock race", res is not None and res[2] < 0x110000 and res[0] == 19472, f"{res}")
    r.st("stock race after errors")

def sc_stock():
    r.ff(False)
    res = r.wait_race(tmo=400); check("stock race", res is not None)
    r.st("stock start"); r.poke(0x6105, 0x01)
    v0 = r.vbl(); last = 0
    while r.vbl() - v0 < a.minutes * 3000:
        time.sleep(5)
        v = r.vbl()
        if (v - v0) // 3000 > last:
            last = (v - v0) // 3000; r.st(f"+{last} min"); r.shot(f"min{last}")
        if r.b(0x1024) == 0xff:
            r.poke(0x6105, 0x00); r.st("race over"); r.wait_race(tmo=300); r.poke(0x6105, 0x01)
    r.st("end"); log(f"bus/address error lines: {r.errlines()}")

try:
    r.ff(False)
    if not r.boot_title(): log("BOOT FAILED"); sys.exit(2)
    probe_boot(r)
    if a.scenario == "stock": pass
    {"finish": sc_finish, "timeout": sc_timeout, "orig": sc_orig, "errors": sc_errors, "stock": sc_stock}[a.scenario]()
finally:
    log(f"== {tag} done: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}; bus/address error lines {r.errlines()}")
    r.close()
    if a.psg:
        res = r.h.psg_check(); log("PSGCHECK ok", res.ok, "violations", res.violations, "warnings", res.warnings); log(res.summary)
sys.exit(1 if FAILS else 0)
