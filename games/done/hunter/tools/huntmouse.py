#!/usr/bin/env python3
r"""Hunter mouse pointer: per-VBL motion measurement and the gates of patches/ptr_*.s (work/notes/mouse.md).

    python3 tools/huntmouse.py meas VARIANT MACHINE SCEN [--tag T] [--hz 60]   # cold boot to the main menu, drive the host mouse, log, print stats
    python3 tools/huntmouse.py ana TAG [TAG ...]                     # stats of saved logs (/tmp/hunmouse/ev_<tag>.json)
    python3 tools/huntmouse.py cons TAG [TAG ...]                    # conservation gate: final position = start + sum of the raw packets
    python3 tools/huntmouse.py model TAG [TAG ...]                   # every drawn position = the ptr_vbl algorithm in Python fed with the logged packets
    python3 tools/huntmouse.py cold --kind hd --machine st|ste|megaste|tt [--variant after]   # cold boot to the 3D view + in-game pointer checks
    python3 tools/huntmouse.py cold --kind fl --machine ste|falcon|tt [--variant after]    # same, floppy build

VARIANT = orig (no patch but the staging code: PP's pointer code), before (the default set without ptr_*), after (the default set + ptr_*),
broken (after, with the remainder carry removed) and nox (after, X motion never committed): the negative controls of `cons`/`model` and of `cold`.  Every variant also carries the two logger patches
test_mlogd (the position the game draws each VBL) and test_mlogb (every byte the ACIA handler decodes), so the log is the same
whatever pointer code runs.  Log at $B8200 (HD builds only): entries of 8 bytes (word VBL, word type 0 = position / 3 = ACIA byte, word a, word b).
Host mouse: a small XTest injector (C, compiled on first use into /tmp/hunmouse) sends relative events at exact 10 ms spacing; xdotool's own sleeps are too loose.
Hatari delivers host motion in whole events only if they are 3 host px or more per 10 ms (smaller steps were dropped in every run: work/notes/mouse.md).
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import shutil
import statistics as st
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
BENCH = GAME.parent.parent.parent
sys.path[:0] = [str(BENCH / "tools"), str(HERE)]
OUT = Path("/tmp/hunmouse")
LOGBASE, LOGEND = 0xB8200, 0xBFFE0
LOGGERS = ["test_mlogd", "test_mlogb"]
LIM = {"x": 312, "y": 191}                   # the pointer clamp ($e4/$e6 in the menu)

# scenarios: (interval_us, [dx, dy, count, ...]).  3 host px per 10 ms = 150 ST px/s (the Hatari window shows ST px at 2x).
SCEN = {
    "mid":  [(10000, [-3, 0, 90, 3, 0, 90, -3, 0, 90, 3, 0, 90, 0, -3, 60, 0, 3, 60, 0, -3, 60, 0, 3, 60])],
    "fast": [(10000, [-6, 0, 45, 6, 0, 45, -6, 0, 45, 6, 0, 45, 0, -6, 30, 0, 6, 30, 0, -6, 30, 0, 6, 30])],
    # net motion that never reaches the clamp from (0,0): the conservation gate
    "cons": [(10000, [3, 0, 90, -3, 0, 80, 3, 0, 60, -3, 0, 60, 0, 3, 60, 0, -3, 50, 0, 3, 40, 0, -3, 40])],
}

INJECTOR = r"""
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <stdlib.h>
#include <time.h>
int main(int argc, char **argv){            /* mm DISPLAY INTERVAL_US dx dy n [dx dy n ...] */
  Display *d = XOpenDisplay(argv[1]); if(!d) return 1;
  long us = atol(argv[2]); struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
  for(int i=3;i+2<argc;i+=3){ int dx=atoi(argv[i]), dy=atoi(argv[i+1]), n=atoi(argv[i+2]);
    for(int k=0;k<n;k++){ XTestFakeRelativeMotionEvent(d,dx,dy,0); XFlush(d);
      t.tv_nsec += us*1000; while(t.tv_nsec>=1000000000){t.tv_nsec-=1000000000;t.tv_sec++;}
      clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &t, NULL); } }
  XCloseDisplay(d); return 0; }
"""


def injector() -> Path:
    OUT.mkdir(exist_ok=True)
    exe = OUT / "mm"
    if not exe.exists():
        src = OUT / "mm.c"
        src.write_text(INJECTOR)
        subprocess.run(["gcc", "-O2", "-o", str(exe), str(src), "-lX11", "-lXtst"], check=True)
    return exe


def run_py(*args: str, env=None):
    return subprocess.run([sys.executable, str(HERE / "huntpatch.py"), *args], check=True, capture_output=True, text=True, cwd=GAME, env=env)


def default_names() -> list[str]:
    out = run_py("list").stdout
    return [ln.split()[0] for ln in out.splitlines() if len(ln.split()) > 2 and ln.split()[1] == "yes"]


def build_variant(variant: str, floppy: bool = False) -> Path:
    """Build the variant (HD or floppy) into /tmp/hunmouse/<variant>[_fl] and return the folder / disk image."""
    names = default_names()
    base = [n for n in names if not n.startswith("ptr_")]
    ptr = ["ptr_vbl", "ptr_x", "ptr_y"]
    sel = {"orig": [], "before": base, "after": base + ptr, "broken": base + ptr, "nox": base + ptr, "default": names}[variant]
    if floppy:
        sel = [n for n in sel if n not in ("sav_hook", "sav_open", "sav_sync")]
    out = OUT / (variant + ("_fl" if floppy else ""))
    env = None
    if variant in ("broken", "nox"):             # negative controls: a scratch patch tree with one deliberate fault
        import os
        tree = OUT / f"patches_{variant}"
        shutil.rmtree(tree, ignore_errors=True)
        shutil.copytree(GAME / "patches", tree)
        f, old, new = (("ptr_vbl.s", "        move.w  d1,6(a0)\n", "        clr.w   6(a0)\n") if variant == "broken" else          # the division remainder is dropped
                       ("ptr_y.s", "        add.w   d0,PTR.l                ; PX\n", "        nop\n"))                                            # X motion is never committed
        s = (tree / f).read_text()
        assert old in s
        (tree / f).write_text(s.replace(old, new))
        env = dict(os.environ, HUNT_PATCHDIR=str(tree))
    snd = GAME / "build" / "hunter_snd.bin"
    args = ["build", "--only", *sel, *([] if floppy else LOGGERS), "--out", str(out)]
    if snd.exists():
        args += ["--samples", str(snd)]
    if floppy:
        args += ["--floppy"]
    run_py(*args, env=env)
    return out / "HUNTER_disk1.st" if floppy else out


# ---- boot to the main menu ---------------------------------------------------------------------------------------------
def boot_menu(game: Path, machine: str):
    import hunter
    from hunter import Hunter, TOS
    import test_hd_image as thi
    cfg = {"ste": ("1.62", [], 1024), "megaste": ("2.06", ["--cpuclock", "16", "--monitor", "rgb"], 4096),
           "tt": ("3.06", ["--cpuclock", "32", "--monitor", "vga", "--mmu", "true"], 4096), "st": ("1.04", [], 1024)}[machine]
    orig = hunter.build_hd
    hunter.build_hd = lambda img, **k: orig(img, game=game, **k)
    try:
        h = Hunter(machine=machine, tos=TOS[cfg[0]], memsize_kb=cfg[2], extra=cfg[1])
    finally:
        hunter.build_hd = orig
    try:
        t = 400
        if machine == "tt":
            thi.wait_drive_c(h)
            time.sleep(3)
            h.keypress(57)
            time.sleep(3)
        else:
            if machine == "megaste":
                thi.wait_drive_c(h)
            h._stage("hw", False, 12, t)
            h.keypress(57)
            h._stage("title1", False, 6, t)
            h.keypress(57)
        h._stage("title2", False, 22, t)
        time.sleep(1.5)
        h.key("space", 0.3)
        h._stage("main", False, 3, t)
        time.sleep(1.5)
        return h
    except Exception:
        h.close()
        raise


def mouse(h, interval_us: int, segs: list[int]) -> subprocess.Popen:
    return subprocess.Popen([str(injector()), h.env["DISPLAY"], str(interval_us), *map(str, segs)], env=h.env)


def read_log(h, path: Path):
    h.debug(f"savebin {path} ${LOGBASE:x} $7e00", 2.5)
    d = path.read_bytes()
    ptr = struct.unpack(">I", d[:4])[0]
    n = (ptr - LOGBASE - 16) // 8
    return [struct.unpack(">HHHH", d[16 + 8 * i:24 + 8 * i]) for i in range(n)]


def measure(variant: str, machine: str, scen: str, tag: str, hz: int = 50) -> Path:
    OUT.mkdir(exist_ok=True)
    h = boot_menu(build_variant(variant), machine)
    try:
        g = h._xdo("getwindowgeometry", "--shell", h.win).stdout
        W, H = (int(re.search(rf"{k}=(\d+)", g).group(1)) for k in ("WIDTH", "HEIGHT"))
        h._xdo("mousemove", "--window", h.win, str(W // 2), str(H // 2))
        time.sleep(0.8)
        if hz == 60:
            h.debug("w $ff820a $00", 0.5)                            # the shifter's 60 Hz sync mode (as tools/hunthz.py forces it)
        h.debug("w $b8200 " + " ".join(["$00"] * 16), 0.5)          # start the log
        for iv, segs in SCEN[scen]:
            mouse(h, iv, segs).wait()
            time.sleep(0.4)
        time.sleep(0.5)
        ev = read_log(h, OUT / f"log_{tag}.bin")
    finally:
        h.close()
    p = OUT / f"ev_{tag}.json"
    p.write_text(json.dumps(ev))
    return p


# ---- analysis ----------------------------------------------------------------------------------------------------------
def s8(x: int) -> int:
    x &= 0xFF
    return x - 256 if x >= 128 else x


def load(tag: str):
    ev = json.loads((OUT / f"ev_{tag}.json").read_text())
    pos = [(v, a, b) for v, t, a, b in ev if t == 0]
    # ACIA bytes -> mouse packets (header $f8..$fb + dx + dy); joystick packets ($fd + 2) are skipped by the same state machine
    cnt = {0xF6: 7, 0xF7: 5, 0xF8: 2, 0xF9: 2, 0xFA: 2, 0xFB: 2, 0xFC: 6, 0xFD: 2, 0xFE: 1, 0xFF: 1}
    pk, i, by = [], 0, [(v, a & 0xFF) for v, t, a, b in ev if t == 3]
    while i < len(by):
        v, b = by[i]
        if b in cnt:
            n = cnt[b]
            if 0xF8 <= b <= 0xFB and i + 2 < len(by):
                pk.append((by[i + 2][0], s8(by[i + 1][1]), s8(by[i + 2][1])))    # stamped with the dy byte (the packet's end)
            i += n + 1
        else:
            i += 1
    return pos, pk


def axis_series(pos, ax):
    i = 1 if ax == "x" else 2
    return [(p1[0], p1[i] - p0[i], min(p0[i], p1[i]) > 0 and max(p0[i], p1[i]) < LIM[ax]) for p0, p1 in zip(pos, pos[1:])]


def runs_of(series):
    """Runs of same-sign motion; a stalled VBL is bridged when the next moving one has the same sign (so a stall counts as a stall)."""
    runs, cur, sign = [], [], 0
    for i, (v, d, ok) in enumerate(series):
        if not ok:
            if cur:
                runs.append(cur)
            cur, sign = [], 0
            continue
        if d == 0:
            nxt = next((s for s in series[i + 1:i + 5] if s[2] and s[1] != 0), None)
            if sign and nxt and (nxt[1] > 0) == (sign > 0):
                cur.append((v, d))
                continue
            if cur:
                runs.append(cur)
            cur, sign = [], 0
            continue
        s = 1 if d > 0 else -1
        if sign and s != sign:
            runs.append(cur)
            cur = []
        sign = s
        cur.append((v, d))
    if cur:
        runs.append(cur)
    return runs


def stats(tag: str, quiet: bool = False) -> dict:
    pos, pk = load(tag)
    res: dict[str, list] = {}
    for ax in "xy":
        for r in runs_of(axis_series(pos, ax)):
            if len(r) < 20:
                continue
            vals = [abs(d) for v, d in r][3:-3]
            if len(vals) < 12:
                continue
            med = st.median(vals)
            key = ax + ("+" if sum(d for v, d in r) > 0 else "-")
            res.setdefault(key, []).append(dict(n=len(vals), mean=round(st.mean(vals), 2), sd=round(st.pstdev(vals), 2), zero=sum(v == 0 for v in vals),
                                                spike=sum(1 for v in vals if v >= 1.5 * med and v > 0), min=min(vals), max=max(vals),
                                                hist=dict(sorted(collections.Counter(vals).items()))))
    if not quiet:
        print(f"== {tag}: {len(pos)} VBL entries, {len(pk)} mouse packets")
        for k, l in sorted(res.items()):
            for s in l:
                print(f"  {k}  VBLs {s['n']:3d}  mean {s['mean']:5.2f} px/VBL  sd {s['sd']:4.2f}  min {s['min']} max {s['max']}  zero-VBLs {s['zero']}  "
                      f"spikes {s['spike']}  {s['hist']}")
    return res


def pooled(tags: list[str]) -> dict:
    """Pooled per direction over several logs: n, mean, sd, zero-VBL and spike counts."""
    acc: dict[str, list] = collections.defaultdict(list)
    for t in tags:
        pos, _ = load(t)
        for ax in "xy":
            for r in runs_of(axis_series(pos, ax)):
                if len(r) >= 20:
                    vals = [abs(d) for v, d in r][3:-3]
                    if len(vals) >= 12:
                        med = st.median(vals)
                        acc[ax + ("+" if sum(d for v, d in r) > 0 else "-")].append((vals, med))
    out = {}
    for k, l in sorted(acc.items()):
        vals = [v for vs, m in l for v in vs]
        out[k] = dict(n=len(vals), mean=round(st.mean(vals), 2), sd=round(st.pstdev(vals), 2), zero=sum(v == 0 for v in vals),
                      spike=sum(1 for vs, m in l for v in vs if v >= 1.5 * m and v > 0))
    return out


def cons(tag: str) -> bool:
    """Final pointer position == first position + sum of the raw packets, EXACTLY (three zero VBLs after the last packet flush the box filter and its remainder: sum of the outputs = sum of the inputs); the path never touched the clamp."""
    pos, pk = load(tag)
    if not pos or not pk:
        print(f"CONS {tag}: no data")
        return False
    p0, p1 = pos[0], pos[-1]
    sx, sy = sum(p[1] for p in pk), sum(p[2] for p in pk)
    edge = False
    for i, ax in ((1, "x"), (2, "y")):          # per axis, from its first move on (the pointer starts at 0,0)
        fi = next((k for k, p in enumerate(pos) if p[i] != p0[i]), len(pos))
        edge |= any(p[i] <= 0 or p[i] >= LIM[ax] for p in pos[fi:])
    dx, dy = p1[1] - p0[1], p1[2] - p0[2]
    # packets are not halved in the fixed game; in the original the negative ones were, so only `after` can pass
    ok = dx == sx and dy == sy and not edge
    print(f"CONS {tag}: pointer moved ({dx},{dy}); raw packets sum ({sx},{sy}); clamp touched {edge}  -> {'OK' if ok else 'FAIL'}")
    return ok


def trunc_div(a: int, b: int) -> tuple[int, int]:
    q = abs(a) // b * (1 if a >= 0 else -1)
    return q, a - q * b


def model(tag: str) -> bool:
    """The ptr_vbl algorithm in Python (3-VBL box mean of the collected packets, remainder carried, clamped), fed with the logged packets:
    every drawn position of the log must equal the model's (the code does what the spec says)."""
    pos, pk = load(tag)
    u = collections.defaultdict(lambda: [0, 0])
    for v, dx, dy in pk:
        u[v][0] += dx
        u[v][1] += dy
    state = [[0, 0, 0], [0, 0, 0]]            # per axis: h1, h2, remainder
    cur = [pos[0][1], pos[0][2]]
    bad, n = 0, 0
    for (v0, x0, y0), (v, x, y) in zip(pos, pos[1:]):
        pend = u.get(v0, [0, 0])             # packets handled after draw v0 and before draw v (v = v0 + 1): the hook before draw v takes them
        for ax in (0, 1):
            h1, h2, f = state[ax]
            q, f = trunc_div(pend[ax] + h1 + h2 + f, 3)
            state[ax] = [pend[ax], h1, f]
            if q:
                cur[ax] = min(max(cur[ax] + q, 0), LIM["xy"[ax]])
        n += 1
        if (x, y) != tuple(cur):
            bad += 1
            cur = [x, y]                      # resynchronise so one slip is counted once
    print(f"MODEL {tag}: {n} VBLs, {bad} differ from the algorithm -> {'OK' if bad == 0 else 'FAIL'}")
    return bad == 0


# ---- cold boot to the 3D view + in-game pointer ------------------------------------------------------------------------
def cold(kind: str, machine: str, variant: str) -> bool:
    import ttbench as TB
    from hunkeys import T
    if kind == "hd" and machine == "st":          # a plain ST (TOS 1.04, 1 MB): boot_menu, then the menu clicks of Hunter.boot_to_game
        h = boot_menu(build_variant(variant), "st")
        h.goto(*h.START_XY, home_xy=h.HOME_XY)
        h.click()
        h._stage("games", False, 3, 400)
        h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
        h.click()
        h._stage("name", False, 3, 400)
        for c in "bench":
            h.key(c, 0.15)
            time.sleep(0.3)
        h.click()
        h._stage("mission", False, 4, 400)
        h.click()
        h._stage("game", False, 9, 400)
        time.sleep(1.0)
    elif kind == "hd":
        game = build_variant(variant)
        h = TB.boot_hd(game, [], False, machine)
    else:
        disk = build_variant(variant, floppy=True)
        h = TB.boot_floppy(disk, [], False, machine)
    ok = True
    try:
        mk, fl = h.peek(TB.MARKER, 4), h.peek(TB.FLAGS, 4)
        sites = {a: h.peek(a, n).hex() for a, n in ((0xC69A, 8), (0xB30E, 6), (0xB32C, 6))}
        print(f"COLD {kind} {machine} {variant}: in_game={h.in_game()} MARKER={mk!r} FLAGS={fl.hex()} sites {sites}", flush=True)
        ok &= h.in_game() and mk == b"HNPO"
        t = T(h=h)
        g = h._xdo("getwindowgeometry", "--shell", h.win).stdout
        W, H = (int(re.search(rf"{k}=(\d+)", g).group(1)) for k in ("WIDTH", "HEIGHT"))
        h._xdo("mousemove", "--window", h.win, str(W // 2), str(H // 2))
        time.sleep(0.6)
        # in-game pointer: item-table hover hit test (the key_item gate's route): open the table, hover cells, `$252` must equal the cell index
        t.open_table()
        mode = t.mode()
        hits = []
        for item in (0, 5, 14, 19):
            x, y = t.gmove((item % 10) * 32 + 16, (item // 10) * 16 + 8)
            time.sleep(0.5)
            got = int.from_bytes(h.peek(0x806 + 0x252, 2), "big")
            hits.append((item, got, (x, y)))
        print(f"  item table: mode ${mode:02x} (bit 7 clear = open); hover cell -> $252: {hits}", flush=True)
        ok &= not (mode & 0x80) and all(i == g_ for i, g_, _ in hits)
        # a click on a cell does what the cell does: weapon 4 becomes the current weapon ($212)
        t.setstate(cur=0)
        x, y = t.gmove(4 * 32 + 16, 8)
        time.sleep(0.4)
        h.click()
        time.sleep(1.0)
        cur = int.from_bytes(h.peek(0x806 + 0x212, 2), "big")
        print(f"  click on cell 4 at ({x},{y}): current weapon $212 = {cur} (want 4)", flush=True)
        ok &= cur == 4
        t.close_table()
        print(f"  table closed: mode ${t.mode():02x}", flush=True)
        ok &= bool(t.mode() & 0x80)
    finally:
        h.close()
    print(f"COLD {kind} {machine} {variant}: {'OK' if ok else 'FAIL'}", flush=True)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    m = sp.add_parser("meas")
    m.add_argument("variant", choices=["orig", "before", "after", "broken", "nox", "default"])
    m.add_argument("machine", choices=["st", "ste", "megaste", "tt"])
    m.add_argument("scen", choices=list(SCEN))
    m.add_argument("--tag", default=None)
    m.add_argument("--hz", type=int, default=50, choices=[50, 60], help="force the 60 Hz sync mode ($ff820a = 0) before the log starts")
    a_ = sp.add_parser("ana")
    a_.add_argument("tags", nargs="+")
    c_ = sp.add_parser("cons")
    c_.add_argument("tags", nargs="+")
    d_ = sp.add_parser("model")
    d_.add_argument("tags", nargs="+")
    k = sp.add_parser("cold")
    k.add_argument("--kind", choices=["hd", "fl"], default="hd")
    k.add_argument("--machine", default="ste", choices=["st", "ste", "megaste", "tt", "falcon"])
    k.add_argument("--variant", default="after", choices=["orig", "before", "after", "default", "nox"])
    a = ap.parse_args()
    if a.cmd == "meas":
        tag = a.tag or f"{a.variant}_{a.machine}_{a.scen}"
        measure(a.variant, a.machine, a.scen, tag, a.hz)
        stats(tag)
        return 0
    if a.cmd == "ana":
        for t in a.tags:
            stats(t)
        return 0
    if a.cmd == "model":
        return 0 if all([model(t) for t in a.tags]) else 1
    if a.cmd == "cons":
        return 0 if all([cons(t) for t in a.tags]) else 1
    return 0 if cold(a.kind, a.machine, a.variant) else 1


if __name__ == "__main__":
    sys.exit(main())
