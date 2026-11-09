#!/usr/bin/env python3
"""A/B gate for the Powermonger display patches (p4_*): identical picture + exact cycles per rendered pass + fps.

    python3 tools/pmab.py [--only p4_x ...] [--base p4_y ...] [--snapshot map_idle get_men battle_320 | x.sav ...]
                          [--mhz 8 16] [--flips 24] [--vbls 700] [--walk] [--st] [--no-fps]

Adapted from games/hunter/tools/huntab.py (see work/notes/p4_raster.md section 1 for the argument).  Hunter's world runs on
the VBL counter; Powermonger's does too once the tick_* patches are in (world = 4.00 ticks/s from $6f304, `timing.md`).  A
patch that makes a frame shorter therefore moves the SAME world state to a different pass, so "frame N after the start" is
not comparable.  This gate removes the problem instead of locking frame lengths:

  * BOTH runs (base and patched) carry the tick_* set (TICK, below) plus --base; the patched run adds --only.  The tick set is
    applied live, at the first call of the flip routine ($187a) after an absolute VBL (the same instant in both runs, the same
    restored state), together with the p4_* set; snapshots hold unpatched code.
  * At every flip entry (pc $1880, before the swap) a capture saves BOTH screen buffers ($1c700 + $fa00 B: the visible
    32000 B of each), the screen/pointer words $2df78..$2df97, the world tick counter $4bb3e and the tick data block $b8a00.
    No input: the picture is a function of (world tick $4bb3e, pass kind R/T = D+6): a T pass renders the state after the
    tick's logic with the men/weather of the previous tick (they run after the render), an R pass (render only, no logic)
    renders the state after the whole tick; all R passes of one tick draw the same world.  Frames are matched by that key,
    not by flip number, and compared byte for byte:
      - `back`  = the buffer just rendered ($2df7c at flip entry; the pointer is NOT in it);
      - `shown` = the displayed buffer at that moment = the previous frame + the software pointer the VBL handler drew.  It is
        compared when the previous frame's key, the pointer position and the shown buffer address also agree.  This is the
        pointer gate (the pointer is redrawn by the VBL handler in an interrupt, so its pixels are a function of the code
        under test, not of the render).
    Flip 1 (the first pass that runs patched code, same inputs in both runs) must match by number as well.
  * Pointer pokes: the harness' xdotool warp reaches the game as mouse motion at a wall-clock dependent moment, so both runs
    poke the pointer words ($2df92/$2df94 and the IKBD shadow $1c492/$1c494) at the apply flip; --walk pokes a different
    position at every captured flip (edges, the one-column x > 304 case, the y > 184 clip, corners).
  * Cycles.  S1 = $13096 (after the VBL wait of the pass), S2 = $187a (flip entry): the render stage including the interrupts
    inside it (pointer code of ~12 VBLs, sample IRQ), WITHOUT the idle wait for the next VBL.  `work` = mean S2-S1 over every
    rendered pass of the run; `paired` = the same over the frames whose key is in both runs.  Cycle counts are CPU cycles
    (Hatari's CycleCounter: an instruction costs the same at 8 and 16 MHz, the VBL is 50 Hz).  fps = flips per window of
    --vbls VBLs (VBL-based, host load does not enter).  Self test: no --only = base and patched identical = IDENTICAL with
    equal cycles.
  * --st: the patched live image carries FLAGS = 6 (no STE DMA/blitter: the plain-ST code path) instead of 3; the machine
    stays an STE (the snapshots are STE ones), so this proves the fallback code, not the hardware (cold boot on `--machine st`).

Machine time: Hatari runs fast-forward, breakpoints stay cycle-exact.  Base captures are cached in /tmp/pmab/<tag>/.
Exit status 0 = every hard comparison identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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

TICK = ["tick_head", "tick_pass", "tick_wx", "tick_men", "tick_click", "tick_click2", "tick_click3"]
FLIP = 0x187A            # flip routine entry (called once per rendered pass)
CAPPC = 0x1880           # 2nd instruction of it: before the swap of $2df78/$2df7c
S1PC = 0x13096           # after `jsr $1870` (VBL wait) of the pass
BUFS = (0x1C700, 0xFA00)  # both screen buffers, contiguous
D = 0xB8A00              # tick_head data block (+6 RON.w)
WORK = Path("/tmp/pmab")
SHORT = {"map_idle": "map_idle", "get_men": "get_men", "battle_320": "battle_320", "battle_260": "battle_260",
         "battle_290": "battle_290", "battle_350": "battle_350", "battle_380": "battle_380", "map_idle_4mb": "map_idle_4mb"}
DEFAULT_SNAPS = ["map_idle", "get_men", "battle_320"]
POINT_STEP = 37
# pointer positions poked by --walk (x, y in ST pixels; x > 304 = one-column pointer, y > 184 = clipped rows)
WALK = [(229, 173), (100, 100), (0, 0), (310, 20), (319, 199), (160, 190), (304, 184), (305, 185), (15, 1), (16, 0),
        (250, 60), (303, 100), (64, 120), (200, 183), (8, 197), (311, 150), (123, 45), (90, 177)]
NUM = re.compile(r"#(\d+) \(dec\)")
_pm_lock = threading.Lock()


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
def one(snap: Path, at: int, live: str, out: Path, nflips: int, vbls: int, mhz: int, walk: bool, fps: bool) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    h = make_pm(snapshot=str(snap), memsize_kb=memsize_of(snap))
    try:
        R = h.R
        time.sleep(1.0)
        if mhz != 8:
            h.set_cpuclock(mhz)
        cmds = []
        cmds += apply_cmds(live)
        cmds += poke_ptr(*WALK[0])
        for pc, tag in ((S1PC, "s1"), (FLIP, "s2")):
            (R / f"{tag}.txt").write_text(f"e ${pc:x}\ne VBL\ne CycleCounter\n")
            cmds.append(f"b pc = ${pc:x} :trace :file {R / (tag + '.txt')}")
        for n in range(1, nflips + 1):
            cf = R / f"c{n}.txt"
            body = [f"e ${CAPPC:x}", "e VBL", "e CycleCounter",
                    f"savebin {out}/s{n}.bin ${BUFS[0]:x} ${BUFS[1]:x}", f"savebin {out}/k{n}.bin $2df78 $20",
                    f"savebin {out}/t{n}.bin $4bb3e 4", f"savebin {out}/d{n}.bin ${D:x} $40"]
            if walk:
                body += poke_ptr(*WALK[n % len(WALK)])
            cf.write_text("\n".join(body) + "\n")
            cnt = f" :{n}" if n > 1 else ""
            cmds.append(f"b pc = ${CAPPC:x}{cnt} :trace :once :file {cf}")
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
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (out / "end.flag").exists():
            if time.time() - t > 900:
                raise TimeoutError(f"run did not complete; log tail:\n{h._logtext()[-1500:]}")
            time.sleep(0.3)
        time.sleep(0.5)
        text = h._logtext()[start:]
    finally:
        h.close()
    tags = {S1PC: "s1", FLIP: "s2", CAPPC: "c"}
    ev = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = NUM.findall(blk)
        if len(m) >= 3 and int(m[0]) in tags:
            ev.append((tags[int(m[0])], int(m[1]), int(m[2])))
    s1 = [e for e in ev if e[0] == "s1"]
    s2 = [e for e in ev if e[0] == "s2"]
    # work = S2 - the S1 right before it in the log (a pass that skipped the render has neither); `cap_work[n]` = work of the
    # pass whose flip entry the n-th capture belongs to (the capture file runs right after the S2 file at the same stop)
    work, cap_work, last_s1, last_work, ncap = [], [], None, None, 0
    for tag, v, c in ev:
        if tag == "s1":
            last_s1 = c
        elif tag == "s2":
            last_work = ((c - last_s1) & 0xFFFFFFFF) if last_s1 is not None else None
            if last_work is not None:
                work.append(last_work)
            last_s1 = None
        else:
            cap_work.append(last_work)
    cap = [e for e in ev if e[0] == "c"]
    recs = []
    for n in range(1, nflips + 1):
        try:
            s = (out / f"s{n}.bin").read_bytes()
            k = (out / f"k{n}.bin").read_bytes()
            tk = (out / f"t{n}.bin").read_bytes()
            d = (out / f"d{n}.bin").read_bytes()
        except FileNotFoundError:
            break
        L = lambda b, o: struct.unpack(">I", b[o:o + 4])[0]
        shown, back = L(k, 0), L(k, 4)
        x, y = struct.unpack(">HH", k[0x1A:0x1E])
        ron = struct.unpack(">H", d[6:8])[0]
        bi = lambda a: a - BUFS[0]
        recs.append(dict(n=n, ticks=L(tk, 0), ron=ron, shown=shown, back=back, x=x, y=y,
                         hb=hashlib.md5(s[bi(back):bi(back) + 32000]).hexdigest(),
                         hs=hashlib.md5(s[bi(shown):bi(shown) + 32000]).hexdigest(),
                         sb=s[bi(back):bi(back) + 32000], ss=s[bi(shown):bi(shown) + 32000],
                         vbl=cap[n - 1][1] if n - 1 < len(cap) else None, work=cap_work[n - 1] if n - 1 < len(cap_work) else None))
    return dict(recs=recs, work=work, flips=len(s2), s2=s2, window=(s2[-1][1] - s2[0][1]) if len(s2) > 1 else 0,
                nsk=len(s1), cap_work=cap_work)


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
        if pp and bp and keyof(pp) == keyof(bp) and (r["x"], r["y"]) == (br["x"], br["y"]) and r["shown"] == br["shown"]:
            nshown += 1
            if r["hs"] != br["hs"]:
                ok = False
                notes.append(f"  SHOWN DIFFER (pointer {r['x']},{r['y']}) patched flip {r['n']} / base flip {br['n']}: " + diff_desc(br["ss"], r["ss"]))
        paired.append((br, r))
    # strict flip-1 comparison (same inputs in both runs)
    if B["recs"] and P["recs"]:
        b1, p1 = B["recs"][0], P["recs"][0]
        if keyof(b1) != keyof(p1):
            notes.append(f"  WARNING flip 1 keys differ: base {keyof(b1)} patched {keyof(p1)} (runs diverged before the first patched frame?)")
            ok = False
        elif b1["hb"] != p1["hb"]:
            ok = False
            notes.append("  FLIP 1 DIFFERS: " + diff_desc(b1["sb"], p1["sb"]))
    return ok, notes, dict(nback=nback, nshown=nshown, paired=paired)


def mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=[], help="patch set under test (added on top of the tick set and --base)")
    ap.add_argument("--base", nargs="*", default=[], help="patches both runs carry besides the tick set")
    ap.add_argument("--no-tick", action="store_true", help="do not add the tick_* set (the world is then per frame: only flip 1 is comparable)")
    ap.add_argument("--snapshot", nargs="*", default=DEFAULT_SNAPS)
    ap.add_argument("--mhz", nargs="*", type=int, default=[8])
    ap.add_argument("--flips", type=int, default=24, help="flips captured per run (both buffers, 64000 B each)")
    ap.add_argument("--vbls", type=int, default=700, help="run length in VBLs from the apply flip (fps / cycles window)")
    ap.add_argument("--points", type=int, default=1, help="start points (absolute VBLs, 37 apart) per snapshot")
    ap.add_argument("--walk", action="store_true", help="poke a different pointer position at every captured flip")
    ap.add_argument("--st", action="store_true", help="patched run with FLAGS=6 (plain-ST code path)")
    ap.add_argument("--no-fps", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep the base captures cached between runs (default: recapture)")
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    tick = [] if a.no_tick else TICK
    bnames, pnames = tick + a.base, tick + a.base + a.only
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
                    fb = ex.submit(one, sp, at, blive, bd, a.flips, a.vbls, mhz, a.walk, not a.no_fps)
                    fp = ex.submit(one, sp, at, plive, pd, a.flips, a.vbls, mhz, a.walk, not a.no_fps)
                    B, P = fb.result(), fp.result()
                cok, cn, st = compare(B, P, a)
                ok &= cok
                notes += [f"p{pi}: {x}" for x in cn]
                acc["bw"] += B["work"]; acc["pw"] += P["work"]
                acc["bf"] += B["flips"]; acc["pf"] += P["flips"]
                acc["bwin"] += B["window"]; acc["pwin"] += P["window"]
                acc["nback"] += st["nback"]; acc["nshown"] += st["nshown"]
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
            print(line, flush=True)
            for x in notes[:12]:
                print("   ", x)
    print("ALL IDENTICAL" if ok_all else "MISMATCH")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
