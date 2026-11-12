#!/usr/bin/env python3
"""Phantom-click investigation (work/notes/phantom_click.md): a cold boot the way a user plays it, with a per-pass log of the click latches,
the key latch (qol_keys PEND / ANY), the selected command and the captain's job / order target, from the moment the map view starts.

    python3 tools/pmphantom.py --disk build/phantom/floppy/powermonger.st --name Ryan --out /tmp/ph/a
    python3 tools/pmphantom.py --vhd dist/AtariST_enhanced_games_2026-11-11.vhd --name Ryan --out /tmp/ph/b      # PMBOOT, P

Cold boot like `pm.boot_to_game`, but the stages are separate so that the logger can be armed before the island click, and the VHD flow
(HDDRIVER, AUTO\\PMBOOT.PRG, key P) is the user's.  The logger is a breakpoint at the pass hook site $130fc (`jsr $7202` in the original,
`jsr $cf830` with qol_keys): every pass it dumps the words below with the debugger's `m`.  RAM map (qol.md, tooltip.md, notes):
  $2df70.l pass / tick counter    $2df74.w click stamp     $2df8e/$2df90 click position    $2df92/$2df94 pointer    $2df96 left latch
  $2df98 right latch    $2df9e right held    $57fd4 selected command    $57ffe selected captain    captain record $51538 + $4c + sel * $13c
  (word +0 = job: 5 Going To, 6 In Camp, ...; word -$c = the captain's person record offset from $51b66, +$14/+$16 = target x/z)
  qol_keys data $cd460: ANY $cd4a2, REP $cd49e, PEND $cd4a4 (128 B by scan code).
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
BENCH = GAME.parent.parent.parent
sys.path[:0] = [str(BENCH / "tools"), str(HERE)]
import pm  # noqa: E402
from pm import TOS, PM  # noqa: E402

PASS_SITE = 0x130FC

DUMP = [
    ("e VBL", None),
    ("m $2df70 4", "iter"),
    ("m $2df74 2", "stamp"),
    ("m $2df8e 8", "clickxy_ptr"),
    ("m $2df96 8", "latches"),
    ("m $2df9e 2", "held"),
    ("m $57fd4 2", "cmd"),
    ("m $57ffe 2", "sel"),
    ("m $516c0 2", "job"),
    ("m $516b4 2", "poff"),
    ("m $7a36 2", "win"),
    ("m $d03e 2", "typing"),
    ("m $cd49e 2", "REP"),
    ("m $cd4a2 2", "ANY"),
    ("m $cd4a4 128", "PEND"),
]


def make_vhd_pm(vhd: Path, machine="ste", tos="1.62", mem=1024, extra=()):
    """The user's start: an ACSI disk (HDDRIVER boots from the partition loader, AUTO\\PMBOOT.PRG asks P), no floppy, no GEMDOS folder."""
    class HDPM(PM):
        def __init__(self):
            R = Path(tempfile.mkdtemp(prefix="strun-"))
            home = R / "home"
            (home / ".config/hatari").mkdir(parents=True, exist_ok=True)
            txt = (Path.home() / ".config/hatari/hatari.cfg").read_text()
            txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
            (home / ".config/hatari/hatari.cfg").write_text(txt)
            img = R / "disk.vhd"
            shutil.copy(vhd, img)
            old = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            try:
                pm.Hatari.__init__(self, game_dir=GAME, workdir=str(R), machine=machine, tos=TOS[tos], memsize_kb=mem, files=[],
                                   overlay=Path("/nonexistent"), autorun=None,
                                   extra=["--gemdos-drive", "skip", "--acsi", f"0={img}", *extra])
            finally:
                os.environ["HOME"] = old
            self.state = R / "state.sav"
    return HDPM()


def make_floppy_pm(disk: Path, machine="ste", tos="1.62", mem=1024, extra=()):
    return PM(disk=disk, machine=machine, tos=TOS[tos], memsize_kb=mem, extra=list(extra))


def parse_dump(text: str):
    """Group the log of the pass logger into one dict per hit: label -> list of byte values / the VBL."""
    hits = []
    cur = None
    for ln in text.splitlines():
        if "CPU breakpoint condition(s) matched" in ln:
            cur = {"labels": []}
            hits.append(cur)
            continue
        if cur is None:
            continue
        m = re.match(r"^> (m \$[0-9a-f]+ \$?[0-9a-f]+|e VBL)", ln)
        if m:
            cur["labels"].append([m.group(1), []])
            continue
        m = re.match(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", ln)
        if m and cur["labels"]:
            cur["labels"][-1][1].extend(int(b, 16) for b in m.group(2).split())
            continue
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur["labels"] and cur["labels"][-1][0] == "e VBL":
            cur["labels"][-1][1].append(int(m.group(1)))
    return hits


def boot_user(h, vhd: bool, name: str, skip: str = "space", log=print, hold_island: float = 0.2, pre_island=None, post_island=None,
              pre_name=None, t_name=400):
    """Cold boot -> map view the way a user does it; returns the monotonic times of the stages."""
    t0 = time.time()
    st = {}

    def stamp(s):
        st[s] = time.time() - t0
        log(f"[{time.time() - t0:5.0f}s vbl {h.vbl()}] {s}")

    if vhd:
        time.sleep(8)               # HDDRIVER + the AUTO folder: PMBOOT's prompt waits 3 s
        h.key("p")
        stamp("P pressed")
        time.sleep(7)
    else:
        time.sleep(15)
    if not h.wait_gate("name", t_name, 4.0, act=(lambda: h.key(skip)) if skip else None):
        raise RuntimeError("name prompt not reached")
    stamp("name prompt")
    time.sleep(1.0)
    if pre_name:
        pre_name(h)
    for ch in name:
        h.key(ch)
        time.sleep(0.25)
    h.key("Return")
    if not h.wait_gate("options", 40, 2.0):
        raise RuntimeError("option screen not reached")
    stamp("option screen")
    h.click_st(*pm.START_NEW_XY, wait=2.0)
    if not h.wait_gate("chart", 60, 2.0):
        raise RuntimeError("territory chart not reached")
    stamp("territory chart")
    removed = h.protection_removed()
    if pre_island:
        pre_island(h)
    h.goto_st(*pm.ISLAND_XY)
    h.click(hold=hold_island)
    stamp("island clicked")
    if post_island:
        post_island(h)
    t1 = time.time()
    if not removed:         # the original: the copy-protection question, answered from RAM as pm.boot_to_game does
        if not h.wait_gate("prot", 120, 3.0):
            raise RuntimeError("protection question not reached")
        stamp("protection question")
        typ, ans = h.protection_answer()
        digits = [(ans // 1000) % 10, (ans // 100) % 10, (ans // 10) % 10, ans % 10]
        for x, n in zip(pm.PROT_DIGIT_X, digits):
            if n:
                h.goto_st(x, pm.PROT_UP_Y)
                for _ in range(n):
                    h.click(hold=0.15)
                    time.sleep(0.4)
        stamp(f"protection answer type {typ} value {ans}")
        h.click_st(*pm.PROT_OK_XY, wait=2.0)
    while not h.at("game"):
        if time.time() - t1 > 300:
            raise RuntimeError("3D map view not reached")
        time.sleep(1.0)
    stamp("3D map view (HUD on screen)")
    return st


def arm_logger(h, name="pass.txt", site=PASS_SITE):
    f = h.R / name
    f.write_text("\n".join(c for c, _ in DUMP) + "\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${site:x} :trace :file {f}")
    time.sleep(0.5)
    return f


PEOPLE, PEOPLE_N, STRIDE = 0x51B66, 512, 0x32
CAPT, CAPT_STRIDE, CAPT_OFF = 0x51538, 0x13C, 0x4C
REGION, REGION_LEN = 0x4E000, 0xA000


def rw(d, a):
    return int.from_bytes(d[a - REGION:a - REGION + 2], "big")


def analyze(snaps, r0=1100):
    """snaps = [(label, dump of $4e000..$57fff)].  Captain = record $57ffe (read from the first dump's neighbour is not possible: the word
    sits above the region, so it is passed as the global SEL below).  Army = live people within r0 world units (max of |dx|, |dz|) of the
    captain in the FIRST dump; for every dump: captain x/z, job, target bytes, army size within r0 of the CAPTAIN and of the START position."""
    sel = analyze.sel
    a3 = CAPT + CAPT_OFF + sel * CAPT_STRIDE
    out = []
    first = snaps[0][1]
    po = rw(first, a3 - 0xC)
    cp = PEOPLE + po
    cx0, cz0 = rw(first, cp + 8), rw(first, cp + 10)
    army = []
    for i in range(PEOPLE_N):
        p = PEOPLE + i * STRIDE
        if first[p + 5 - REGION] and 0 < first[p + 5 - REGION] < 0x80 and PEOPLE + i * STRIDE != cp:
            x, z = rw(first, p + 8), rw(first, p + 10)
            if max(abs(x - cx0), abs(z - cz0)) <= r0:
                army.append(i)
    out.append(f"captain person ${cp:x} start x,z = ({cx0},{cz0}); army = {len(army)} live people within {r0} units at the first dump")
    for label, d in snaps:
        job = rw(d, a3)
        po = rw(d, a3 - 0xC)
        cp = PEOPLE + po
        cx, cz = rw(d, cp + 8), rw(d, cp + 10)
        tx, tz = d[cp + 0x14 - REGION], d[cp + 0x16 - REGION]
        near_c = near_s = ring = 0
        far = 0
        rad = []
        for i in army:
            p = PEOPLE + i * STRIDE
            x, z = rw(d, p + 8), rw(d, p + 10)
            ring += d[p + 6 - REGION] == 0x0E       # person state $0e: the formation around the castle (protection.md: state $0e is also the one the check hooks)
            rad.append(max(abs(x - cx), abs(z - cz)))
            near_c += max(abs(x - cx), abs(z - cz)) <= r0
            near_s += max(abs(x - cx0), abs(z - cz0)) <= r0
            far = max(far, max(abs(x - cx0), abs(z - cz0)))
        out.append(f"{label:>10}: job {job:2d} captain ({cx:5d},{cz:5d}) moved {max(abs(cx - cx0), abs(cz - cz0)):5d}  target bytes ({tx:3d},{tz:3d})  "
                   f"army {len(army)}: state $0e {ring:2d}, distance to the captain min {min(rad)} max {max(rad)}, farthest from the start {far}")
    return out


analyze.sel = 1


SC = {"A": 0x1E, "D": 0x20, "E": 0x12, "F": 0x21, "G": 0x22, "H": 0x23, "I": 0x17, "L": 0x26, "M": 0x32, "N": 0x31, "O": 0x18, "Q": 0x10,
      "R": 0x13, "S": 0x1F, "T": 0x14, "X": 0x2D, "Y": 0x15, "1": 2, "2": 3, "3": 4}       # qol_keys KT scan codes


def key_latch_dump(h, out: Path):
    ptxt = h.debug("m $cd460 66", 0.6) + h.debug("m $cd4a2 2", 0.4) + h.debug("m $cd4a4 128", 0.6)
    (out / "key_latch_at_chart.txt").write_text(ptxt)
    print("key latch (qol_keys data $cd460 / ANY $cd4a2 / PEND $cd4a4) at the chart, before the island click:")
    print("\n".join(l for l in ptxt.splitlines() if re.match(r"^[0-9A-F]{8}:", l)))


def arm_all(h, marks):
    """Pass logger + a one-shot dump of the world tables at the first pass; marks['log0'] = log offset."""
    arm_logger(h)
    first = h.R / "first.txt"
    first.write_text(f"savebin {h.R / 'first.bin'} ${REGION:x} ${REGION_LEN:x}\n")
    h.cmd(f"hatari-debug b pc = ${PASS_SITE:x} && ($2df70).l < 3 :trace :once :file {first}")
    time.sleep(0.5)
    marks["log0"] = len(h._logtext())


def capture(h, out: Path, marks: dict, secs: float, step: float):
    """From the moment the map is up: world dumps + screenshots for `secs`, then the analysis."""
    t0 = time.time()
    snaps = []
    i = 0
    while time.time() - t0 < secs:
        try:
            snaps.append((f"t+{time.time() - t0:4.1f}s", h.ram(REGION, REGION_LEN)))
            h.shot(str(out / f"shot_{i:02d}.png"))
        except Exception as e:      # noqa: BLE001
            print("capture failed:", e)
        i += 1
        time.sleep(step)
    h.debug("b all", 0.5)
    sel = h.peekw(0x57FFE)
    analyze.sel = sel
    first = h.R / "first.bin"
    if first.exists():
        snaps.insert(0, ("pass 1", first.read_bytes()))
    (out / "passes.log").write_text(h._logtext()[marks["log0"]:])
    for lbl, d in snaps:
        (out / f"dump_{lbl.replace(' ', '_').replace('+', 'p')}.bin").write_bytes(d)
    lines = analyze(snaps)
    (out / "analysis.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("final: sel", sel, "job", h.peekw(0x516C0), "cmd", h.peekw(0x57FD4), "iter", h.iter_count())
    print(passes_table(out / "passes.log", 12))

def key_test(h, keys=("f", "f")):
    """Real keys (xdotool, 150 ms taps) after the map has been up for a while: F = Get Food ($57fd4 = 6; the second F toggles it off again, as clicking
    the icon twice does).  Returns the list of (key, $57fd4 before, after)."""
    res = []
    for k in keys:
        before = h.peekw(0x57FD4)
        h.key(k, hold=0.15)
        time.sleep(2.5)
        res.append((k, before, h.peekw(0x57FD4)))
    print("real keys:", ", ".join(f"{k}: $57fd4 {b} -> {a}" for k, b, a in res))
    return res


def run(h, vhd: bool, name: str, out: Path, secs: float, step: float, skip: str):
    out.mkdir(parents=True, exist_ok=True)
    marks = {}

    def pre_island(h):
        key_latch_dump(h, out)
        arm_all(h, marks)

    boot_user(h, vhd, name, skip, pre_island=pre_island)
    capture(h, out, marks, secs, step)
    if os.environ.get("PMPH_KEYS", "1") == "1":
        key_test(h)


def make_chart_snapshot(h, vhd: bool, snap: Path, skip: str = "space"):
    """Cold boot with an empty name up to the territory chart and save the machine there (no key was typed, so the key latch is clean)."""
    def pre_island(h):
        raise StopIteration

    try:
        boot_user(h, vhd, "", skip, pre_island=pre_island)
    except StopIteration:
        pass
    time.sleep(2.0)
    h.savemem(str(snap))
    print("chart snapshot written:", snap, snap.stat().st_size)


def variant(h, keys: str, out: Path, secs: float, step: float):
    """From a chart snapshot: poke the key latch the way the interrupt hook records `keys` (qol_keys2: PEND[scancode] = 1, ANY = 1),
    then click the island and capture the start of the map."""
    out.mkdir(parents=True, exist_ok=True)
    marks = {}
    for k in keys:
        if k != "-":
            h.debug(f"w ${0xCD4A4 + SC[k.upper()]:x} $01", 0.3)
    if keys.strip("-"):
        h.debug("w $cd4a2 $00 $01", 0.3)
    key_latch_dump(h, out)
    arm_all(h, marks)
    h.goto_st(*pm.ISLAND_XY)
    h.click(hold=0.2)
    t1 = time.time()
    while not h.at("game"):
        if time.time() - t1 > 150:
            raise RuntimeError("3D map view not reached")
        time.sleep(1.0)
    capture(h, out, marks, secs, step)


def passes_table(path: Path, n=12):
    t = path.read_text()
    rows = []

    def val(h, addr):
        m = re.search(r"^%08X: ((?:[0-9a-f]{2} )+)" % addr, h, re.M)
        return "".join(m.group(1).split()) if m else None

    for h in t.split("CPU breakpoint condition(s) matched")[1:n + 1]:
        v = re.search(r"#(\d+) \(dec\)", h)
        if not v or val(h, 0x2DF70) is None:
            continue
        rows.append(f"vbl {v.group(1)} iter {int(val(h, 0x2DF70), 16):3d} stamp {val(h, 0x2DF74)} click {val(h, 0x2DF8E)[:8]} latches {val(h, 0x2DF96)} held {val(h, 0x2DF9E)} "
                    f"cmd {val(h, 0x57FD4)} job {val(h, 0x516C0)} win {val(h, 0x7A36)} ANY {val(h, 0xCD4A2)}")
    return "pass log (first %d):\n" % n + "\n".join(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk")
    ap.add_argument("--vhd")
    ap.add_argument("--name", default="Bench")
    ap.add_argument("--skip", default="space")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--out", required=True)
    ap.add_argument("--secs", type=float, default=30.0, help="seconds of state capture after the map appears")
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--hopts", default="")
    ap.add_argument("--snap-out", help="cold boot with an empty name to the territory chart and write this snapshot, then stop")
    ap.add_argument("--snap", help="restore this chart snapshot instead of booting (floppy only), poke --keys into the key latch, click the island")
    ap.add_argument("--keys", default="", help="letters poked into PEND with --snap ('-' = none)")
    a = ap.parse_args()
    extra = a.hopts.split()
    if a.snap:
        h = PM(snapshot=a.snap, disk=Path(a.disk), machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=extra)
    elif a.vhd:
        h = make_vhd_pm(Path(a.vhd), a.machine, a.tos, a.mem, extra)
    else:
        h = make_floppy_pm(Path(a.disk), a.machine, a.tos, a.mem, extra)
    try:
        if a.snap_out:
            make_chart_snapshot(h, a.vhd is not None, Path(a.snap_out), a.skip)
        elif a.snap:
            variant(h, a.keys, Path(a.out), a.secs, a.step)
        else:
            run(h, a.vhd is not None, a.name, Path(a.out), a.secs, a.step, a.skip)
    finally:
        h.close()


if __name__ == "__main__":
    main()
