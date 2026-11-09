#!/usr/bin/env python3
"""A/B gate for the Powermonger display patches (p4_*): identical picture + exact cycles per rendered pass + fps.

    python3 tools/pmab.py [--only p4_x ...] [--base p4_y ...] [--snapshot map_idle get_men battle_320 | x.sav ...]
                          [--mhz 8 16] [--vbls 700] [--walk] [--st] [--poke ADDR:HEX] [--neg] [--no-fps]

Adapted from games/hunter/tools/huntab.py (see work/notes/p4_raster.md section 1 for the argument).  Hunter's world runs on
the VBL counter; Powermonger's does too once the tick_* patches are in (world = 4.00 ticks/s from $6f304, `timing.md`).  A
patch that makes a frame shorter therefore moves the SAME world state to a different pass, so "frame N after the start" is
not comparable.  This gate removes the problem instead of locking frame lengths:

  * BOTH runs (base and patched) carry the tick_* set (TICK, below), the test_walk* pointer driver (TESTSET) and --base; the
    patched run adds --only.  Everything is applied live (snapshots hold unpatched code) at the first call of the flip
    routine's SECOND instruction ($1880; a patch may sit on $187a) after an absolute VBL: the same instant in both runs.
  * At every flip entry ($187a) a capture writes BOTH screen buffers ($1c700 + $fa00 B = the visible 32000 B of each) into a FIFO
    this process drains (a pipe holds 64000 B; the emulator only stalls if we are behind, nothing is lost), and prints the world
    tick $4bb3e, the pass kind (RON, tick_head data +6), the buffer pointers $2df78/$2df7c and the pointer words $2df92/$2df94.
    There are only THREE persistent breakpoints (S1, CAP, end): Hatari evaluates every condition breakpoint at every instruction,
    a capture breakpoint per flip (hunter's method) made a run 50x slower.
    No input: the picture is a function of (world tick, pass kind R/T): a T pass renders the state after the tick's logic with
    the men/weather of the previous tick (they run after the render), an R pass (render only, no logic) renders the state after
    the whole tick.  Frames are matched by that key, not by flip number, and compared byte for byte:
      - `back`  = the buffer just rendered ($2df7c at flip entry; the pointer is NOT in it);
      - `shown` = the displayed buffer at that moment = the previous frame + the software pointer the VBL handler drew.  It is
        compared when the previous frame's key and the pointer position agree (the buffer address is not part of the key: the
        two runs flip a different number of times).  This is the pointer gate: the pointer is redrawn by the VBL handler in an
        interrupt, so its pixels are a function of the code under test, not of the render.
  * Pointer driver (test_walk, test_walk2, test_walk3; test only).  The game polls the IKBD every VBL (absolute mode, `$0D`) and
    the packet handler copies the reply to the draw words $2df92/$2df94, so a poke of those words is overwritten within a VBL
    and the harness' xdotool warp reaches the game as motion at a wall-clock dependent moment.  The three patches replace the
    two copies by PX/PY and set PX/PY at the world-tick increment of the main loop ($13034, T and S passes only) from a table of
    16 positions (edges, the one-column x > 304 case, the y > 184 clip, corners) indexed by the new tick (--walk) or entry 0
    (default).  The position is a pure function of the tick for every pass of that tick, including the game's own logic and
    UI/hover code, which reads it (a first version that changed the position at flips made the army-icon blits into the
    background picture differ between runs with different S/R pass mixes: section 1 of the notes).
  * Cycles.  S1 = $13096 (after the VBL wait of the pass), S2 = $187a (flip entry): the render stage including the interrupts
    inside it (pointer code of ~12 VBLs, sample IRQ), WITHOUT the idle wait for the next VBL.  `work` = mean S2-S1 over every
    rendered pass of the run; `paired` = the same over the frames whose key is in both runs.  Cycle counts are CPU cycles
    (Hatari's CycleCounter: an instruction costs the same at 8 and 16 MHz, the VBL is 50 Hz).  fps = flips per window of
    --vbls VBLs (VBL-based, host load does not enter).  p4_chase moves the copy in front of S1: compare fps and period for it.
    Self test: no --only = base and patched identical = IDENTICAL with equal cycles (+-0.01 %).  Negative control: --neg.
  * --st: the patched live image carries FLAGS = 6 (no STE DMA/blitter: the plain-ST code path) instead of 3; the machine
    stays an STE (the snapshots are STE ones), so this proves the fallback code, not the hardware (cold boot on `--machine st`).
  * --poke ADDR:HEXBYTES: extra bytes written in the patched run only at the apply flip (p4_spr: `bdc04:b17e0002` = pre-shifted cache).
  * Also printed for the BASE run: how many frames equal the frame two flips earlier (what a static-frame skip could save at most) and
    how many consecutive same-tick render-only frames are identical (item 6).
  * Start state: `--mhz 16` uses Hatari's cpuclock switch, which lands at a wall-clock dependent emulated instant, so the two runs
    can start from slightly different passes at 16 MHz; frames are matched by key, so this only shows as a NOTE on flip 1.

Machine time: Hatari runs fast-forward, breakpoints stay cycle-exact.  Exit status 0 = every hard comparison identical.
Related live tests (not part of this tool): patches/test_blit.s (random differential test of the sprite paths), test_copy.s (copy cost).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import struct
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent / "tools"), str(HERE)]
from pm import PM, SNAP  # noqa: E402

TESTSET = ['test_walk', 'test_walk2', 'test_walk3']
TICK = ["tick_head", "tick_pass", "tick_wx", "tick_men", "tick_click", "tick_click2", "tick_click3"]
FLIP = 0x187A            # flip routine entry (called once per rendered pass)
APPLYPC = 0x1880         # where the live set is applied: 2nd instruction of the flip routine (test_walk patches the first one: never write under the PC)
MODE = 0xCE400           # test_walk data word: != 0 = pointer walks with the world tick
PXADDR = 0xCE402         # test_walk PX/PY words (the pointer position the IKBD packet handler copies)
S1PC = 0x13096           # after `jsr $1870` (VBL wait) of the pass
BUFS = (0x1C700, 0xFA00)  # both screen buffers, contiguous
D = 0xB8A00              # tick_head data block (+6 RON.w)
WORK = Path("/tmp/pmab")
SHORT = {"map_idle": "map_idle", "get_men": "get_men", "battle_320": "battle_320", "battle_260": "battle_260",
         "battle_290": "battle_290", "battle_350": "battle_350", "battle_380": "battle_380", "map_idle_4mb": "map_idle_4mb"}
DEFAULT_SNAPS = ["map_idle", "get_men", "battle_320"]
POINT_STEP = 37
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
_pm_lock = threading.Lock()
TIMEOUT = 300


def snap_path(s: str) -> Path:
    p = Path(s)
    if p.exists():
        return p
    return SNAP / (s if s.endswith(".sav") else s + ".sav")


def memsize_of(sp: Path) -> int:
    return 4096 if "4mb" in sp.name else 1024


def make_pm(**kw) -> PM:
    with _pm_lock:                   # PM() swaps $HOME for Hatari's config: not thread safe
        return PM(**kw)


# ---- live patch sets -----------------------------------------------------------------------------------------------
def tag_for(names: list[str], st: bool) -> str:
    return f"{names[0][:10] if names else 'none'}+{len(names)}-{hashlib.md5(('+'.join(names) + str(st)).encode()).hexdigest()[:6]}"


def make_live(names: list[str], st: bool = False) -> str:
    """pmpatch.py live image of `names`; sites cut into <= 40-byte `w` lines (Hatari truncates debugger lines of ~240 chars)."""
    live = WORK / tag_for(names, st) / "live"
    live.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(HERE / "pmpatch.py"), "live", "--only", *names, "--out", str(live)]
    if st:
        cmd.append("--no-ste")
    subprocess.run(cmd, check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    jp = Path(str(live) + ".json")
    spec = json.loads(jp.read_text())
    sites = []
    for s in spec["sites"]:
        raw = bytes.fromhex(s["new"])
        for o in range(0, len(raw), 40):
            sites.append({**s, "addr": s["addr"] + o, "new": raw[o:o + 40].hex()})
    spec["sites"] = sites
    jp.write_text(json.dumps(spec, indent=1))
    return str(live)


def apply_cmds(live: str) -> list[str]:
    spec = json.loads(Path(live + ".json").read_text())
    c = [f"loadbin {Path(live + '.img')} ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])) for s in spec["sites"]]
    return c


def poke_ptr(x: int, y: int) -> list[str]:
    """pointer position words: the draw variables $2df92/$2df94 and the IKBD shadow $1c492/$1c494"""
    h = lambda v: f"${v >> 8:02x} ${v & 255:02x}"
    return [f"w $2df92 {h(x)} {h(y)}", f"w $1c492 {h(x)} {h(y)}"]


def at_vbl_for(snap: Path) -> int:
    cache = WORK / "at.json"
    d = json.loads(cache.read_text()) if cache.exists() else {}
    k = f"{snap.name}:{snap.stat().st_mtime_ns}"
    if k not in d:
        h = make_pm(snapshot=str(snap), memsize_kb=memsize_of(snap))
        try:
            v = h.vbl()
        finally:
            h.close()
        d[k] = (v // 100 + 6) * 100
        cache.write_text(json.dumps(d))
    return d[k]


# ---- one run -------------------------------------------------------------------------------------------------------
def one(snap: Path, at: int, live: str, out: Path, vbls: int, mhz: int, walk: bool, fps: bool, bg: bool = False, pokes: tuple = ()) -> dict:
    """Restore `snap`, apply the live set at the first flip after VBL `at`, run `vbls` VBLs.  Two persistent breakpoints only
    (Hatari evaluates every condition breakpoint at every instruction: 16 of them made a run 50x slower): S1 after the pass's
    VBL wait, CAP at the flip entry.  CAP's debugger file prints the key values and writes both screen buffers into a FIFO
    that this process drains (a pipe holds 64000 B, so the emulator only ever stalls when we are behind: nothing is lost)."""
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    h = make_pm(snapshot=str(snap), memsize_kb=memsize_of(snap))
    stop = threading.Event()
    frames = bytearray()
    rd = None
    try:
        R = h.R
        fifo = R / "scr.fifo"
        os.mkfifo(fifo)
        fd = os.open(fifo, os.O_RDONLY | os.O_NONBLOCK)

        def drain():
            while not stop.is_set():
                r, _, _ = select.select([fd], [], [], 0.05)
                if r:
                    try:
                        d = os.read(fd, 1 << 20)
                    except BlockingIOError:
                        continue
                    if d:
                        frames.extend(d)
                    else:
                        time.sleep(0.002)          # writer closed: wait for the next one
        rd = threading.Thread(target=drain, daemon=True)
        rd.start()
        time.sleep(1.0)
        if mhz != 8:
            h.set_cpuclock(mhz)
        cmds = apply_cmds(live)
        for pk in pokes:                                          # --poke ADDR:HEXBYTES (patched run only), e.g. bd400:0002 = p4_spr's BLT mode
            ad, hx = pk.split(":")
            cmds.append(f"w ${int(ad, 16):x} " + " ".join(f"${hx[i:i + 2]}" for i in range(0, len(hx), 2)))
        cmds.append(f"w ${PXADDR:x} $00 $e5 $00 $ad")           # PX/PY = the snapshot's pointer (229,173) until the first flip hook
        if walk:
            cmds.append(f"w ${MODE:x} $00 $01")
        (R / "s1.txt").write_text(f"e ${S1PC:x}\ne VBL\ne CycleCounter\n")
        cmds.append(f"b pc = ${S1PC:x} :trace :file {R / 's1.txt'}")
        (R / "cap.txt").write_text("\n".join([f"e ${FLIP:x}", "e VBL", "e CycleCounter", "e ($4bb3e).l", f"e (${D + 6:x}).w",
                                              "e ($2df78).l", "e ($2df7c).l", "e ($2df92).w", "e ($2df94).w",
                                              f"savebin {fifo} ${BUFS[0]:x} ${BUFS[1]:x}"] + ([f"savebin {fifo} $78000 $7d00"] if bg else [])) + "\n")
        cmds.append(f"b pc = ${FLIP:x} :trace :file {R / 'cap.txt'}")
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {out}/end.flag $0 2\ne VBL\n")
        cmds.append(f"b VBL > {at + vbls} :trace :once :file {end}")
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        for c in cmds:
            if len(c) > 235:
                raise ValueError(f"debugger command line too long: {c[:60]}...")
        if h.vbl() >= at:
            raise ValueError(f"at_vbl {at} already passed")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${APPLYPC:x} :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (out / "end.flag").exists():
            if time.time() - t > TIMEOUT:
                raise TimeoutError(f"run did not complete; log tail:\n{h._logtext()[-1500:]}")
            time.sleep(0.3)
        time.sleep(0.8)
        text = h._logtext()[start:]
        (out / "log.txt").write_text(text)
    finally:
        stop.set()
        if rd:
            rd.join()
        h.close()
    ev = []                       # ("s1", vbl, cyc) | ("c", vbl, cyc, ticks, ron, shown, back, x, y)
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in NUM.findall(blk)]
        if len(m) >= 3 and m[0] == S1PC:
            ev.append(("s1", m[1], m[2]))
        elif len(m) >= 9 and m[0] == FLIP:
            ev.append(("c", *m[1:9]))
    work, last_s1, cap_work = [], None, []
    for e in ev:
        if e[0] == "s1":
            last_s1 = e[2]
        else:
            w = ((e[2] - last_s1) & 0xFFFFFFFF) if last_s1 is not None else None
            cap_work.append(w)
            if w is not None:
                work.append(w)
            last_s1 = None
    caps = [e for e in ev if e[0] == "c"]
    FS = BUFS[1] + (32000 if bg else 0)
    nfr = len(frames) // FS
    recs = []
    for n, e in enumerate(caps[:nfr]):
        _, vbl, cyc, ticks, ron, shown, back, x, y = e
        s = bytes(frames[n * FS:n * FS + BUFS[1]])
        bgimg = bytes(frames[n * FS + BUFS[1]:(n + 1) * FS]) if bg else None
        bi = lambda a: a - BUFS[0]
        sb, ss = s[bi(back):bi(back) + 32000], s[bi(shown):bi(shown) + 32000]
        recs.append(dict(n=n + 1, ticks=ticks, ron=ron, shown=shown, back=back, x=x, y=y, vbl=vbl, work=cap_work[n],
                         hb=hashlib.md5(sb).hexdigest(), hs=hashlib.md5(ss).hexdigest(), sb=sb, ss=ss, bg=bgimg))
    return dict(recs=recs, work=work, flips=len(caps), window=(caps[-1][1] - caps[0][1]) if len(caps) > 1 else 0, nsk=len(work))


def keyof(r):
    return (r["ticks"], r["ron"])


def diff_desc(a: bytes, b: bytes) -> str:
    d = [i for i in range(32000) if a[i] != b[i]]
    rows = sorted({i // 160 for i in d})
    cols = sorted({(i % 160) // 8 for i in d})
    return f"{len(d)} B differ, rows {rows[0]}-{rows[-1]}, 16-px columns {cols[0]}-{cols[-1]}"


def compare(B: dict, P: dict, a) -> tuple[bool, list[str], dict]:
    notes, ok = [], True
    bm = {}
    for i, r in enumerate(B["recs"]):
        bm.setdefault(keyof(r), []).append((i, r))
    pm_ = {}
    for i, r in enumerate(P["recs"]):
        pm_.setdefault(keyof(r), []).append((i, r))
    nback = nshown = 0
    paired = []
    for i, r in enumerate(P["recs"]):
        # the j-th frame of a key in the patched run is matched with the j-th of the same key in the base run
        j = [q for q, _ in pm_[keyof(r)]].index(i)
        cand = bm.get(keyof(r), [])
        if j >= len(cand):
            continue
        bi, br = cand[j]
        nback += 1
        if r["hb"] != br["hb"]:
            ok = False
            notes.append(f"  BACK DIFFER key (tick {r['ticks']}, {'R' if r['ron'] else 'T'}) patched flip {r['n']} / base flip {br['n']}: "
                         + diff_desc(br["sb"], r["sb"]))
        # shown buffer: same previous frame, same pointer, same buffer
        pp = P["recs"][i - 1] if i else None
        bp = B["recs"][bi - 1] if bi else None
        if pp and bp and keyof(pp) == keyof(bp) and (a.neg or (r["x"], r["y"]) == (br["x"], br["y"])):
            nshown += 1
            if r["hs"] != br["hs"]:
                ok = False
                notes.append(f"  SHOWN DIFFER (pointer {r['x']},{r['y']}) patched flip {r['n']} / base flip {br['n']}: " + diff_desc(br["ss"], r["ss"]))
        paired.append((br, r))
    # strict flip-1 comparison (same inputs in both runs)
    if B["recs"] and P["recs"]:
        b1, p1 = B["recs"][0], P["recs"][0]
        if keyof(b1) != keyof(p1):
            notes.append(f"  NOTE flip 1 keys differ: base {keyof(b1)} patched {keyof(p1)}: the two runs did not start from the same emulated instant "
                         "(Hatari's cpuclock switch is applied at a wall-clock dependent moment), so the flip-by-number check is skipped; frames are matched by key")
        elif b1["hb"] != p1["hb"]:
            ok = False
            notes.append("  FLIP 1 DIFFERS: " + diff_desc(b1["sb"], p1["sb"]))
    return ok, notes, dict(nback=nback, nshown=nshown, paired=paired)


def dup2(R: dict) -> tuple[int, int]:
    """(frames equal to the frame two flips earlier, frames compared): the double buffer holds the frame of two passes ago, so these are
    the passes a static-frame skip could have saved at most (item 6): the render stage would redraw exactly what is already there."""
    r = R["recs"]
    return sum(1 for i in range(2, len(r)) if r[i]["hb"] == r[i - 2]["hb"]), max(0, len(r) - 2)


def rr_pairs(R: dict) -> tuple[int, int]:
    """(identical, total) over consecutive rendered frames of the SAME world tick and both render-only passes: such a pair has no world
    logic between its renders (tick patches), so it is the case a conservative static skip could use."""
    r = R["recs"]
    pairs = [(a, b) for a, b in zip(r, r[1:]) if a["ron"] and b["ron"] and a["ticks"] == b["ticks"]]
    return sum(1 for a, b in pairs if a["hb"] == b["hb"]), len(pairs)


def mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=[], help="patch set under test (added on top of the tick set and --base)")
    ap.add_argument("--base", nargs="*", default=[], help="patches both runs carry besides the tick set")
    ap.add_argument("--no-tick", action="store_true", help="do not add the tick_* set (the world is then per frame: only flip 1 is comparable)")
    ap.add_argument("--snapshot", nargs="*", default=DEFAULT_SNAPS)
    ap.add_argument("--mhz", nargs="*", type=int, default=[8])
    ap.add_argument("--vbls", type=int, default=700, help="run length in VBLs from the apply flip: every flip in it is captured and compared; also the fps / cycles window")
    ap.add_argument("--points", type=int, default=1, help="start points (absolute VBLs, 37 apart) per snapshot")
    ap.add_argument("--walk", action="store_true", help="poke a different pointer position at every captured flip")
    ap.add_argument("--st", action="store_true", help="patched run with FLAGS=6 (plain-ST code path)")
    ap.add_argument("--poke", action="append", default=[], help="ADDR:HEXBYTES written in the patched run at the apply flip (repeatable), e.g. bd400:0002")
    ap.add_argument("--no-fps", action="store_true")
    ap.add_argument("--neg", action="store_true", help="negative control: the BASE run walks the pointer, the patched run holds it still, and the shown "
                    "buffers are compared regardless of the pointer position: the gate must report DIFFER")
    ap.add_argument("--keep", action="store_true", help="keep the base captures cached between runs (default: recapture)")
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    tick = [] if a.no_tick else TICK
    bnames, pnames = tick + TESTSET + a.base, tick + TESTSET + a.base + a.only
    blive, plive = make_live(bnames), make_live(pnames, a.st)
    ok_all = True
    print(f"base set    : {' '.join(bnames)}\npatched set : {' '.join(pnames)}{'  [FLAGS=6, plain-ST path]' if a.st else ''}")
    for sn in a.snapshot:
        sp = snap_path(sn)
        at0 = at_vbl_for(sp)
        for mhz in a.mhz:
            acc = dict(bw=[], pw=[], bpw=[], ppw=[], bf=0, pf=0, bwin=0, pwin=0, nback=0, nshown=0)
            ok = True
            notes = []
            for pi in range(a.points):
                at = at0 + pi * POINT_STEP
                bd = WORK / f"b_{tag_for(bnames, False)}" / f"{sp.stem}_{mhz}_{at}{'_w' if a.walk else ''}"
                pd = WORK / f"p_{tag_for(pnames, a.st)}" / f"{sp.stem}_{mhz}_{at}{'_w' if a.walk else ''}"
                with ThreadPoolExecutor(2) as ex:
                    fb = ex.submit(one, sp, at, blive, bd, a.vbls, mhz, a.walk or a.neg, not a.no_fps)
                    fp = ex.submit(one, sp, at, plive, pd, a.vbls, mhz, a.walk and not a.neg, not a.no_fps, False, tuple(a.poke))
                    B, P = fb.result(), fp.result()
                cok, cn, st = compare(B, P, a)
                ok &= cok
                notes += [f"p{pi}: {x}" for x in cn]
                acc["bw"] += B["work"]; acc["pw"] += P["work"]
                acc["bf"] += B["flips"]; acc["pf"] += P["flips"]
                acc["bwin"] += B["window"]; acc["pwin"] += P["window"]
                acc["nback"] += st["nback"]; acc["nshown"] += st["nshown"]
                d2 = dup2(B)
                acc["d2"] = acc.get("d2", 0) + d2[0]; acc["d2n"] = acc.get("d2n", 0) + d2[1]
                rr = rr_pairs(B)
                acc["rr"] = acc.get("rr", 0) + rr[0]; acc["rrn"] = acc.get("rrn", 0) + rr[1]
                acc["bpw"] += [br["work"] for br, r in st["paired"] if br["work"] is not None and r["work"] is not None]
                acc["ppw"] += [r["work"] for br, r in st["paired"] if br["work"] is not None and r["work"] is not None]
            ok_all &= ok
            res = "IDENTICAL" if ok else "DIFFER"
            line = f"{sn} @{mhz} MHz: {res} (back frames matched {acc['nback']}, shown+pointer matched {acc['nshown']}, flips captured {len(P['recs'])}/{len(B['recs'])})"
            if not a.no_fps:
                bw, pw = mean(acc["bw"]), mean(acc["pw"])
                bf = 50.0 * acc["bf"] / acc["bwin"] if acc["bwin"] else 0.0
                pf = 50.0 * acc["pf"] / acc["pwin"] if acc["pwin"] else 0.0
                bq, pq = mean(acc["bpw"]), mean(acc["ppw"])
                line += (f" | work/pass {bw:.0f} -> {pw:.0f} ({pw - bw:+.0f}, {100 * (pw - bw) / bw if bw else 0:+.2f} %, n {len(acc['bw'])}/{len(acc['pw'])})"
                         f" | paired {bq:.0f} -> {pq:.0f} ({100 * (pq - bq) / bq if bq else 0:+.2f} %, n {len(acc['bpw'])})"
                         f" | flips {acc['bf']} -> {acc['pf']} fps {bf:.3f} -> {pf:.3f} ({100 * (pf - bf) / bf if bf else 0:+.1f} %)")
            line += f" | base frames == the frame 2 flips earlier: {acc.get('d2', 0)}/{acc.get('d2n', 0)}; consecutive same-tick R frames identical: {acc.get('rr', 0)}/{acc.get('rrn', 0)}"
            print(line, flush=True)
            for x in notes[:12]:
                print("   ", x)
    print("ALL IDENTICAL" if ok_all else "MISMATCH")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
