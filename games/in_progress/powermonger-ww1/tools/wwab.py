#!/usr/bin/env python3
"""Stage 5 A/B gate for the WW1 display patches (p4_*, p6_*, p7_*): identical picture + cycles per rendered pass + fps.

    python3 tools/wwab.py --only p4_ptr_a p4_ptr_b [--base p4_clamp ...] --snapshot /tmp/pmww1s5/snaps/ste_get_men.sav ...
                          [--machine ste|st|megaste] [--mhz 8 16] [--vbls 700] [--walk] [--neg] [--no-frames] [--poke ADDR:HEX]

Port of games/done/powermonger/tools/pmab.py (its docstring has the full argument; work/notes/p4_raster.md section 1) to WW1.
The snapshots hold the committed default set (tick_*, p3b_*, snd_* ... live), so unlike master nothing but the patch under test is applied live:
  * BOTH runs restore the same snapshot, apply `test_walk*` (the pointer driver, tests only) and `--base` live; the patched run additionally applies `--only`.
    Applied at the first call of the flip routine's 2nd instruction ($e14) after an absolute VBL (same emulated instant in both runs).
  * At every flip entry ($e0e) a capture prints the world tick (tick_head's TICKS $72a88), the pass kind (RON $72a86), the buffer pointers [$2ed98] (shown) /
    [$2ed9c] (back = the frame just rendered), the pointer words, VBL and CycleCounter, and writes both screen buffers ($1d500 + $fa00) (and --c3 ADDR, a third
    buffer) into a FIFO this process drains.  Frames are matched by (tick, pass kind), not by flip number: a patch that shortens a pass moves the same world
    state to another pass, the world runs on the VBL counter (tick_head).
  * back = the buffer just rendered (compared byte for byte); shown = the displayed buffer = the previous frame + the software pointer the VBL handler drew
    (compared when the previous frame's key and the pointer position agree): the pointer gate.
  * Cycles: S1 = $13e0a (after the VBL wait of the pass) .. $e0e (flip entry) = the render stage including the interrupts inside it; fps = flips per window of
    --vbls emulated VBLs.  Cycle counts are CPU cycles of the emulated clock (not host time).
  * `p3b_interp` / `tick_rain` make render-only (R) frames depend on the pass phase, which a faster patch moves: the default pokes TOFF=1 (PD+0 $73f80, p3b off) in
    both runs so every frame is a hard comparison; `--tonly` makes R frames informational instead.
  * --neg: negative control (the BASE run walks the pointer, the patched run holds it still, shown buffers compared regardless): must report DIFFER.
Exit status 0 = every hard comparison identical.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwpatch  # noqa: E402

TESTSET = ["test_walk", "test_walk2", "test_walk3"]
FLIP = 0xE0E
APPLYPC = 0xE14             # 2nd instruction of the flip routine (nothing of ours sits under the PC)
S1PC = 0x13E0A              # after `jsr $e04` (VBL wait) of the pass
BUFS = (0x1D500, 0xFA00)    # both screen buffers (A = $1d500, B = $25200), contiguous
D_TICKS, D_RON = 0x72A88, 0x72A86
STATE = (0x44C3E, 0x18C00)  # the game state a save slot holds (the whole world: people, captains, houses, ...)
TOFF = 0x73F80              # p3b_interp PD+0
MODE, PXA = 0x77C00, 0x77C02  # test_walk data
WORK = Path("/tmp/pmww1s5b/ab")
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
MACH = {"ste": ("ste", "1.62", 1024), "st": ("st", "1.04", 1024), "megaste": ("megaste", "2.06", 4096)}
TIMEOUT = 420
_lock = threading.Lock()
TIPMASK = False


def make_pm(**kw):
    with _lock:
        return pmww.PMW(**kw)


# ---- live patch sets --------------------------------------------------------------------------------------------------
def patch_writes(names: list[str]) -> list[tuple[int, bytes]]:
    """(address, bytes) of every site and blob of the named patches (assembled by wwpatch), plus zero spans of their `; data:` areas."""
    allp = {p.name: p for p in wwpatch.load_all()}
    out = []
    for n in names:
        p = allp[n]
        if p.site is not None:
            orig, new = wwpatch.resolve(p)
            out.append((p.site, new))
        for org, lines in p.segments:
            if org == p.site:
                continue
            out.append((org, wwpatch.assemble(org, lines, "\n".join(p.preamble))))
        for a, ln in p.data:
            out.append((a, bytes(ln)))
        if n == "p6_slope":                      # the table its `init` computes at boot: run that init code (unicorn, wwfill_test) and write the result
            import wwfill_test
            out += [w for w in wwfill_test.with_init_data(out, [n]) if w[0] == 0xB8000][-1:]
    return out


def make_live(names: list[str], tag: str, machine: str = "ste") -> list[str]:
    """Debugger commands applying the patches: big spans through loadbin files, sites as `w` lines of <= 40 bytes."""
    d = WORK / "live" / tag
    d.mkdir(parents=True, exist_ok=True)
    cmds = []
    # data zero spans first (they may sit under a blob's range only if overlapping: wwpatch rejects overlaps), then blobs, then sites last
    writes = patch_writes(names)
    allp = {p.name: p for p in wwpatch.load_all()}
    sites = {allp[n].site for n in names if allp[n].site is not None}
    for i, (a, b) in enumerate(writes):
        if a in sites and len(b) <= 40:
            continue
        f = d / f"w{i}_{a:x}.bin"
        f.write_bytes(b)
        cmds.append(f"loadbin {f} ${a:x}")
    for a, b in writes:
        if a in sites and len(b) <= 40:
            cmds.append(f"w ${a:x} " + " ".join(f"${x:02x}" for x in b))
    if "p4_spr" in names:                          # what p4_spr's `init` (boot, supervisor) decides: blitter on the STE family, cache elsewhere
        cmds.append(f"w $df004 $b1 $7e $00 ${1 if machine in ('ste', 'megaste') else 2:02x}")
    return cmds


def hexbytes(pk: str) -> str:
    ad, hx = pk.split(":")
    return f"w ${int(ad, 16):x} " + " ".join(f"${hx[i:i + 2]}" for i in range(0, len(hx), 2))


def snap_info(snap: Path, machine: str) -> dict:
    cache = WORK / "info.json"
    WORK.mkdir(parents=True, exist_ok=True)
    d = json.loads(cache.read_text()) if cache.exists() else {}
    k = f"{snap}:{snap.stat().st_mtime_ns}"
    if k not in d:
        m, tos, mem = MACH[machine]
        h = make_pm(snapshot=str(snap), machine=m, tos=pmww.TOS[tos], memsize_kb=mem, workdir=str(WORK / "info_home"))
        try:
            time.sleep(1.0)
            v = h.vbl()
            d[k] = dict(at=(v // 100 + 6) * 100, x=h.peekw(0x2EDB2), y=h.peekw(0x2EDB4))
        finally:
            h.close()
        cache.write_text(json.dumps(d))
    return d[k]


# ---- one run ----------------------------------------------------------------------------------------------------------
def one(snap: Path, machine: str, at: int, cmds_live: list[str], out: Path, vbls: int, mhz: int, walk: bool, px: tuple, pokes: tuple,
        frames: bool, c3: int | None, tag: str, counts: tuple = (), state: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    import shutil
    for f in out.glob("*"):
        shutil.rmtree(f) if f.is_dir() else f.unlink()
    m, tos, mem = MACH[machine]
    h = make_pm(snapshot=str(snap), machine=m, tos=pmww.TOS[tos], memsize_kb=mem, workdir=str(out / "run"))
    stop = threading.Event()
    buf = bytearray()
    rd = None
    try:
        R = h.R
        fd = None
        if frames:
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
                            buf.extend(d)
                        else:
                            time.sleep(0.002)
            rd = threading.Thread(target=drain, daemon=True)
            rd.start()
        time.sleep(1.0)
        if mhz and mhz != 8:
            h.set_cpuclock(mhz)
        cmds = list(cmds_live) + [hexbytes(p) for p in pokes]
        cmds.append(f"w ${PXA:x} ${px[0] >> 8:02x} ${px[0] & 255:02x} ${px[1] >> 8:02x} ${px[1] & 255:02x}")
        if walk:
            cmds.append(f"w ${MODE:x} $00 $01")
        (R / "s1.txt").write_text(f"e ${S1PC:x}\ne VBL\ne CycleCounter\n")
        cmds.append(f"b pc = ${S1PC:x} :trace :file {R / 's1.txt'}")
        (R / "cnt.txt").write_text("e pc\n")
        for c in counts:
            cmds.append(f"b pc = ${c:x} :trace :file {R / 'cnt.txt'}")
        cap = [f"e ${FLIP:x}", "e VBL", "e CycleCounter", f"e (${D_TICKS:x}).l", f"e (${D_RON:x}).w", "e ($2ed98).l", "e ($2ed9c).l", "e ($2edb2).w", "e ($2edb4).w"]
        if frames:
            cap.append(f"savebin {fifo} ${BUFS[0]:x} ${BUFS[1]:x}")
            if c3:
                cap.append(f"savebin {fifo} ${c3:x} $7d00")
            if state:
                cap.append(f"savebin {fifo} ${STATE[0]:x} ${STATE[1]:x}")
        (R / "cap.txt").write_text("\n".join(cap) + "\n")
        cmds.append(f"b pc = ${FLIP:x} :trace :file {R / 'cap.txt'}")
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {out}/end.flag $0 2\ne VBL\n")
        cmds.append(f"b VBL > {at + vbls} :trace :once :file {end}")
        (R / "apply.txt").write_text("\n".join(cmds) + "\n")
        for c in cmds:
            if len(c) > 235:
                raise ValueError(f"debugger line too long: {c[:60]}...")
        if h.vbl() >= at:
            raise ValueError(f"at_vbl {at} already passed")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${APPLYPC:x} :trace :once :file {R / 'apply.txt'}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (out / "end.flag").exists():
            if time.time() - t > TIMEOUT:
                raise TimeoutError(f"{tag}: run did not complete; log tail:\n{h._logtext()[-1500:]}")
            time.sleep(0.3)
        time.sleep(0.8)
        text = h._logtext()[start:]
        (out / "log.txt").write_text(text)
    finally:
        stop.set()
        if rd:
            rd.join()
        h.close()
    ev = []
    hits = {c: 0 for c in counts}
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        mm = [int(v) for v in NUM.findall(blk)]
        if len(mm) == 1 and mm[0] in hits:
            hits[mm[0]] += 1
            continue
        if len(mm) >= 3 and mm[0] == S1PC:
            ev.append(("s1", mm[1], mm[2]))
        elif len(mm) >= 9 and mm[0] == FLIP:
            ev.append(("c", *mm[1:9]))
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
    FS = BUFS[1] + (32000 if c3 else 0) + (STATE[1] if state else 0)
    nfr = len(buf) // FS if frames else 0
    recs = []
    for n, e in enumerate(caps[:nfr] if frames else caps):
        _, vbl, cyc, ticks, ron, shown, back, x, y = e
        r = dict(n=n + 1, ticks=ticks, ron=ron, shown=shown, back=back, x=x, y=y, vbl=vbl, work=cap_work[n])
        if frames:
            s = bytes(buf[n * FS:n * FS + BUFS[1]])
            c3img = bytes(buf[n * FS + BUFS[1]:n * FS + BUFS[1] + 32000]) if c3 else None

            def grab(a):
                if c3 and a == c3:
                    return c3img
                assert BUFS[0] <= a and a + 32000 <= BUFS[0] + BUFS[1], f"screen buffer ${a:x} outside the captured regions"
                return s[a - BUFS[0]:a - BUFS[0] + 32000]
            sb, ss = grab(back), grab(shown)
            if TIPMASK:
                sb, ss = tipmask(sb), tipmask(ss)
            r.update(hb=hashlib.md5(sb).hexdigest(), hs=hashlib.md5(ss).hexdigest(), sb=sb, ss=ss)
            if state:
                st_ = bytes(buf[(n + 1) * FS - STATE[1]:(n + 1) * FS])
                r["hst"] = hashlib.md5(st_).hexdigest()
                r["st"] = st_
        recs.append(r)
    return dict(recs=recs, work=work, flips=len(caps), window=(caps[-1][1] - caps[0][1]) if len(caps) > 1 else 0, hits=hits, ticks=(caps[-1][3] - caps[0][3]) if len(caps) > 1 else 0)


def tipmask(b: bytes) -> bytes:
    m = bytearray(b)
    for row in range(6):
        m[row * 160 + 56:row * 160 + 160] = bytes(104)
    return bytes(m)


def keyof(r):
    return (r["ticks"], r["ron"])


def diff_desc(a: bytes, b: bytes) -> str:
    d = [i for i in range(32000) if a[i] != b[i]]
    rows = sorted({i // 160 for i in d})
    cols = sorted({(i % 160) // 8 for i in d})
    return f"{len(d)} B differ, rows {rows[0]}-{rows[-1]}, 16-px columns {cols[0]}-{cols[-1]}"


def compare(B, P, a):
    notes, ok = [], True
    bm, pm_ = {}, {}
    for i, r in enumerate(B["recs"]):
        bm.setdefault(keyof(r), []).append((i, r))
    for i, r in enumerate(P["recs"]):
        pm_.setdefault(keyof(r), []).append((i, r))
    nback = nshown = nrdiff = nstate = nstr = 0
    paired = []
    for i, r in enumerate(P["recs"]):
        j = [q for q, _ in pm_[keyof(r)]].index(i)
        cand = bm.get(keyof(r), [])
        if j >= len(cand):
            continue
        bi, br = cand[j]
        if a.tonly and r["ron"]:
            if r["hb"] != br["hb"]:
                nrdiff += 1
            continue
        nback += 1
        if r["hb"] != br["hb"]:
            ok = False
            notes.append(f"  BACK DIFFER key (tick {r['ticks']}, {'R' if r['ron'] else 'T'}) patched flip {r['n']} / base flip {br['n']}: " + diff_desc(br["sb"], r["sb"]))
        if a.state:
            if r["hst"] == br["hst"]:
                nstate += 1
            elif r["ron"]:
                nstr += 1
            else:
                ok = False
                d_ = [k for k in range(STATE[1]) if r["st"][k] != br["st"][k]]
                notes.append(f"  STATE DIFFER key (tick {r['ticks']}, T) patched flip {r['n']} / base flip {br['n']}: {len(d_)} B, first at ${STATE[0] + d_[0]:x}, last ${STATE[0] + d_[-1]:x}")
        pp = P["recs"][i - 1] if i else None
        bp = B["recs"][bi - 1] if bi else None
        if pp and bp and keyof(pp) == keyof(bp) and (a.neg or (r["x"], r["y"]) == (br["x"], br["y"])) and not (a.tonly and pp["ron"]):
            nshown += 1
            if r["hs"] != br["hs"]:
                ok = False
                notes.append(f"  SHOWN DIFFER (pointer {r['x']},{r['y']}) patched flip {r['n']} / base flip {br['n']}: " + diff_desc(br["ss"], r["ss"]))
        paired.append((br, r))
    if B["recs"] and P["recs"]:
        b1, p1 = B["recs"][0], P["recs"][0]
        if keyof(b1) != keyof(p1):
            notes.append(f"  NOTE flip 1 keys differ: base {keyof(b1)} patched {keyof(p1)} (runs started from slightly different instants); frames are matched by key")
        elif b1["hb"] != p1["hb"] and not (a.tonly and b1["ron"]):
            ok = False
            notes.append("  FLIP 1 DIFFERS: " + diff_desc(b1["sb"], p1["sb"]))
    return ok, notes, dict(nback=nback, nshown=nshown, paired=paired, nrdiff=nrdiff, nstate=nstate, nstr=nstr)


def rr_pairs(R):
    """(identical, total) over consecutive rendered frames of the SAME world tick that are both render-only: no world logic between them."""
    r = R["recs"]
    pairs = [(a, b) for a, b in zip(r, r[1:]) if a["ron"] and b["ron"] and a["ticks"] == b["ticks"]]
    return sum(1 for a, b in pairs if a["hb"] == b["hb"]), len(pairs)


def mean(v):
    return sum(v) / len(v) if v else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=[], help="patch set under test (on top of the snapshot's set and --base)")
    ap.add_argument("--base", nargs="*", default=[], help="patches both runs carry live (earlier accepted perf patches)")
    ap.add_argument("--snapshot", nargs="+", required=True)
    ap.add_argument("--machine", default="ste", choices=list(MACH))
    ap.add_argument("--mhz", nargs="*", type=int, default=[8], help="8 = as restored; 16 = hatari-option --cpuclock 16 (master's method); 0 = as restored on a Mega STE")
    ap.add_argument("--vbls", type=int, default=700)
    ap.add_argument("--points", type=int, default=1)
    ap.add_argument("--walk", action="store_true")
    ap.add_argument("--neg", action="store_true")
    ap.add_argument("--tonly", action="store_true")
    ap.add_argument("--state", action="store_true", help="also capture the 101 376 B game state $44c3e (what a save slot holds) at every flip: T frames must be identical, R frames are counted")
    ap.add_argument("--no-frames", action="store_true", help="speed only: no frame capture / comparison")
    ap.add_argument("--no-toff", action="store_true", help="do not poke p3b TOFF=1 (men interpolation stays on)")
    ap.add_argument("--base-poke", action="append", default=[])
    ap.add_argument("--poke", action="append", default=[], help="ADDR:HEXBYTES, patched run only (e.g. p4_spr BLT mode)")
    ap.add_argument("--c3", help="HEXADDR third screen buffer (p7_triple)")
    ap.add_argument("--tipmask", action="store_true")
    ap.add_argument("--base-only", action="store_true", help="run only the base side (speed number of the current set): the patched run is skipped")
    ap.add_argument("--count", nargs="*", default=[], help="HEX code addresses: executions counted in both runs (patched code paths)")
    ap.add_argument("--tag", default="ab")
    a = ap.parse_args()
    global TIPMASK
    TIPMASK = a.tipmask
    c3 = int(a.c3, 16) if a.c3 else None
    WORK.mkdir(parents=True, exist_ok=True)
    bnames, pnames = TESTSET + a.base, TESTSET + a.base + a.only
    blive = make_live(bnames, f"{a.tag}_b", a.machine)
    plive = make_live(pnames, f"{a.tag}_p", a.machine)
    toff = [] if a.no_toff else [f"{TOFF:x}:0001"]
    print(f"machine {a.machine}\nbase set    : snapshot + {' '.join(bnames)}\npatched set : snapshot + {' '.join(pnames)}", flush=True)
    ok_all = True
    frames = not a.no_frames
    for sn in a.snapshot:
        sp = Path(sn)
        info = snap_info(sp, a.machine)
        for mhz in a.mhz:
            acc = dict(bw=[], pw=[], bpw=[], ppw=[], bf=0, pf=0, bwin=0, pwin=0, nback=0, nshown=0, nrdiff=0)
            ok, notes = True, []
            for pi in range(a.points):
                at = info["at"] + pi * 37
                nm = f"{sp.stem}_{mhz}_{at}{'_w' if a.walk else ''}"
                px = (info["x"], info["y"])
                bd, pd = WORK / a.tag / "b" / nm, WORK / a.tag / "p" / nm
                bp = tuple(toff) + tuple(a.base_poke)
                pp = bp + tuple(a.poke)
                runs = [("b", bd, blive, a.walk or a.neg, bp)]
                if not a.base_only:
                    runs.append(("p", pd, plive, a.walk and not a.neg, pp))
                res = [one(sp, a.machine, at, lv, d, a.vbls, mhz, wk, px, pk, frames, c3, t, tuple(int(c, 16) for c in a.count), a.state) for t, d, lv, wk, pk in runs]     # ONE Hatari at a time
                B = res[0]
                acc["bw"] += B["work"]; acc["bf"] += B["flips"]; acc["bwin"] += B["window"]; acc["bt"] = acc.get("bt", 0) + B["ticks"]
                if a.base_only:
                    continue
                P = res[1]
                acc["pw"] += P["work"]; acc["pf"] += P["flips"]; acc["pwin"] += P["window"]; acc["pt"] = acc.get("pt", 0) + P["ticks"]
                if frames and (len(P["recs"]) < 0.5 * len(B["recs"]) or len(B["recs"]) < 5):
                    ok = False
                    notes.append(f"  RUN FAILED: patched run captured {len(P['recs'])} flips against {len(B['recs'])} (a crashed or stalled run is a FAIL)")
                if frames:
                    for k_, R_ in (("b", B), ("p", P)):
                        i_, n_ = rr_pairs(R_)
                        acc["rr" + k_] = acc.get("rr" + k_, (0, 0))[0] + i_, acc.get("rr" + k_, (0, 0))[1] + n_
                    cok, cn, st = compare(B, P, a)
                    ok &= cok
                    notes += [f"p{pi}: {x}" for x in cn]
                    acc["nback"] += st["nback"]; acc["nshown"] += st["nshown"]; acc["nrdiff"] += st["nrdiff"]
                    acc["nstate"] = acc.get("nstate", 0) + st["nstate"]; acc["nstr"] = acc.get("nstr", 0) + st["nstr"]
                    acc["bpw"] += [br["work"] for br, r in st["paired"] if br["work"] is not None and r["work"] is not None]
                    acc["ppw"] += [r["work"] for br, r in st["paired"] if br["work"] is not None and r["work"] is not None]
            ok_all &= ok
            bw, pw = mean(acc["bw"]), mean(acc["pw"])
            bf = 50.0 * acc["bf"] / acc["bwin"] if acc["bwin"] else 0.0
            pf = 50.0 * acc["pf"] / acc["pwin"] if acc["pwin"] else 0.0
            if a.base_only:
                print(f"{sp.stem} {a.machine} @{mhz} MHz BASE: work/pass {bw:.0f} (n {len(acc['bw'])}) flips {acc['bf']} in {acc['bwin']} VBL fps {bf:.3f}", flush=True)
                continue
            if frames and acc["nback"] == 0:
                ok = False
            ok_all &= ok
            res_s = "IDENTICAL" if ok else "DIFFER"
            line = f"{sp.stem} {a.machine} @{mhz} MHz: " + (f"{res_s} (back frames matched {acc['nback']}, shown+pointer matched {acc['nshown']}"
                                                          f"{', R frames differing (allowed) ' + str(acc['nrdiff']) if a.tonly else ''}, flips captured {len(P['recs'])}/{len(B['recs'])})" if frames else "speed only")
            bq, pq = mean(acc["bpw"]), mean(acc["ppw"])
            line += (f" | work/pass {bw:.0f} -> {pw:.0f} ({pw - bw:+.0f}, {100 * (pw - bw) / bw if bw else 0:+.2f} %, n {len(acc['bw'])}/{len(acc['pw'])})"
                     + (f" | paired {bq:.0f} -> {pq:.0f} ({100 * (pq - bq) / bq if bq else 0:+.2f} %, n {len(acc['bpw'])})" if frames else "")
                     + f" | world ticks/s {50.0 * acc.get('bt', 0) / acc['bwin'] if acc['bwin'] else 0:.3f} -> {50.0 * acc.get('pt', 0) / acc['pwin'] if acc['pwin'] else 0:.3f}"
                     + f" | flips {acc['bf']} -> {acc['pf']} fps {bf:.3f} -> {pf:.3f} ({100 * (pf - bf) / bf if bf else 0:+.1f} %)")
            if frames and a.state:
                line += f" | world state ($44c3e..) identical in {acc.get('nstate', 0)} frames, differing only in render-only frames: {acc.get('nstr', 0)}"
            if frames:
                line += f" | same-tick consecutive R frames identical: base {acc['rrb'][0]}/{acc['rrb'][1]}, patched {acc['rrp'][0]}/{acc['rrp'][1]}"
            print(line, flush=True)
            if a.count:
                print("   hits (last point) base " + " ".join(f"${c}:{B['hits'][int(c, 16)]}" for c in a.count) + " | patched " + " ".join(f"${c}:{P['hits'][int(c, 16)]}" for c in a.count))
            for x in notes[:12]:
                print("   ", x)
    if a.base_only:
        sys.exit(0)
    print("ALL IDENTICAL" if ok_all else "MISMATCH")
    sys.exit(0 if ok_all or not frames else 1)


if __name__ == "__main__":
    main()
