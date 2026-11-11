#!/usr/bin/env python3
"""Pixel-equality gate for the Populous 2 display patches (pop2_spr, pop2_ptr, pop2_clamp): patched vs unpatched, same input, N turns.

    python3 tools/p2abtest.py --only pop2_spr [--base X ..] [--snapshot busy1 game_start] [--turns 130] [--mhz 8 16]
                              [--poke ADDR:HEX ..] [--base-poke ADDR:HEX ..] [--bmhz 8] [--neg] [--coverage] [--no-walk]

Exit status 0 = every hard comparison identical.  Nothing here is Populous-2-specific except the addresses below
(work/notes/display.md has the evidence for each of them).

What is compared.  The game is frame-coupled and VBL-independent in play: one world turn ($3979a, +1 at $22fa2 in the pass top) per
rendered pass, one flip ($1bfe) per pass.  Both runs restore the same snapshot, apply a live patch set at the flip of the same TURN (snapshot turn + 100; snapshots hold
unpatched code), and then run for --turns flips (one flip = one turn).  Patched code only
changes how fast a pass is, so frames are matched by TURN, not by flip number (a faster pass moves nothing in the world).
At EVERY flip entry ($1bfe, i.e. the end of the pass of turn T) the debugger writes into a FIFO this process drains:
  * both screen buffers ($2300 and $a000, 32000 B each), classified as `back` (= $392e0, the frame just rendered; the pointer
    is NOT in it) and `shown` (= $392dc, the previous frame plus the software pointer the VBL handler drew);
  * the world RAM $39600-$473ff (map $3979e, people/effect/third lists, players, view, click state: 56,832 B), hashed per turn;
  * the turn, the pointer words $393fa/$393fc, the VBL count and the CPU cycle counter.
and, at $1254e (after the pass's VBL wait), the cycle counter again: work/pass = cycles from there to the flip entry.
Each turn must match in back (byte for byte), shown (byte for byte, pointer included) and world (md5).  Only THREE persistent
breakpoints exist (S1, CAP, end; Hatari evaluates every condition at every instruction).

Input is a pure function of the turn (patches/test_walk, test_walk2, test_walk3, carried by BOTH runs): the pointer visits 16
positions (map, panel, all four edges, corners, x > 304, y > 184) two turns each, and one cursor key is held for 16 turns at a
time (+x, +y, -x, -y), so the view scrolls over the map and sprites cross every screen edge.  --no-walk holds the input still.
--coverage prints, for the BASE run, how often each sprite-routine entry point ran (so the gate's claim to have exercised a
clip variant is a number, not a hope).
--neg is the negative control: the patched run does not walk (the shown buffers and the world must DIFFER).  A deliberately
broken patch is the stronger control: --poke ADDR:HEX writes bytes into the patched run only at the apply instant.
Self-test: no --only = both runs identical; --bmhz 8 --mhz 16 = same code at two CPU speeds (proves the capture does not
depend on pass timing).
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
GAME = HERE.parent
sys.path[:0] = [str(HERE), str(GAME.parent.parent.parent / "tools")]
from populous2 import Populous2  # noqa: E402

FLIP = 0x1BFE            # flip routine entry: called once per rendered pass
APPLYPC = 0x1C04         # live set applied at the 2nd instruction of the flip (never write under the PC)
S1PC = 0x1254E           # after `jsr $1bf4` (the VBL wait) at the top of a pass
TURN = 0x3979A           # long
BUFS = (0x2300, 0xFA00)  # both screen buffers, contiguous ($2300 and $a000)
WORLD = (0x39600, 0xDE00)  # $39600-$473ff
WALKSET = ["test_walk", "test_walk2", "test_walk3"]
PX, MODE, BX = 0x86F00, 0x86F04, 0x86F06     # test_walk data (patches/test_walk.s): PX.w PY.w MODE.w BX.w BY.w
SPRITE_ENTRIES = {0x2122E: "front end", 0x211BE: "16px front end", 0x212B4: "16px 2-col", 0x21322: "neg-x shift",
                  0x21368: "1-col", 0x213B0: "3-col (main)", 0x2147E: "neg-x 3-col", 0x21530: "2-col right edge"}
WORK = Path("/tmp/p2ab")
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
TIMEOUT = 600
_lock = threading.Lock()


def snap_path(s: str) -> Path:
    p = Path(s)
    return p if p.exists() else Populous2.SNAP / (s if s.endswith(".sav") else s + ".sav")


def make_live(names: list[str]) -> str:
    """pop2patch.py live image of `names`; sites cut into <= 40-byte `w` lines (Hatari truncates debugger lines of ~240 chars)."""
    tag = hashlib.md5("+".join(names).encode()).hexdigest()[:8]
    live = WORK / f"live_{tag}"
    live.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(HERE / "pop2patch.py"), "live", "--only", *names, "--out", str(live)],
                   check=True, cwd=GAME, stdout=subprocess.DEVNULL)
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


def poke_cmd(spec: str) -> str:
    ad, hx = spec.split(":")
    return f"w ${int(ad, 16):x} " + " ".join(f"${hx[i:i + 2]}" for i in range(0, len(hx), 2))


def start_turn_for(snap: Path) -> int:
    """The turn at which both runs apply their live set: the snapshot's turn + 20 (a few seconds of play), cached.  Applying by TURN (not by
    VBL) makes the start identical at any CPU clock: the walk input is a function of the turn."""
    cache = WORK / "at.json"
    d = json.loads(cache.read_text()) if cache.exists() else {}
    k = f"{snap.name}:{snap.stat().st_mtime_ns}"
    if k not in d:
        with _lock:
            h = Populous2(snapshot=snap)
        try:
            time.sleep(1.0)
            d[k] = h.peekl(TURN) + 100
        finally:
            h.close()
        cache.write_text(json.dumps(d))
    return d[k]


def one(snap: Path, t0: int, live: str, out: Path, turns: int, mhz: int, walk: bool, pokes: tuple,
        coverage: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    with _lock:
        h = Populous2(snapshot=snap)
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
                        time.sleep(0.002)
        rd = threading.Thread(target=drain, daemon=True)
        rd.start()
        time.sleep(1.0)
        if mhz != 8:
            h.set_cpuclock(mhz)
        cmds = apply_cmds(live) + [poke_cmd(p) for p in pokes]
        cmds.append(f"w ${PX:x} $00 $a0 $00 $64")                    # PX/PY: the pointer stays at (160,100) until the first walk step
        cmds.append(f"w ${MODE:x} $00 ${3 if walk else 0:02x}")
        vx, vy = (max(0, min(40, v - 8)) for v in (h.peekw(Populous2.VIEW_X), h.peekw(Populous2.VIEW_Y)))      # the square surrounds the snapshot's view
        cmds.append(f"w ${BX:x} $00 ${vx:02x} $00 ${vy:02x}")
        (R / "s1.txt").write_text("\n".join([f"e ${S1PC:x}", "e VBL", "e CycleCounter", f"e (${TURN:x}).l", "e ($392dc).l", "e ($393fa).w", "e ($393fc).w",
                                              "e ($11d50).w", f"savebin {fifo} ${BUFS[0]:x} ${BUFS[1]:x}"]) + "\n")
        cmds.append(f"b pc = ${S1PC:x} :trace :file {R / 's1.txt'}")
        (R / "cap.txt").write_text("\n".join([
            f"e ${FLIP:x}", "e VBL", "e CycleCounter", f"e (${TURN:x}).l", "e ($392e0).l", "e ($392dc).l", "e ($393fa).w", "e ($393fc).w", "e ($11d50).w", "e ($202e).l", "e ($2246).w",
            f"savebin {fifo} ${BUFS[0]:x} ${BUFS[1]:x}", f"savebin {fifo} ${WORLD[0]:x} ${WORLD[1]:x}"]) + "\n")
        cmds.append(f"b pc = ${FLIP:x} :trace :file {R / 'cap.txt'}")
        if True:
            for a in SPRITE_ENTRIES:
                cmds.append(f"b pc = ${a:x} :trace")
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {out}/end.flag $0 2\ne VBL\n")
        cmds.append(f"b pc = ${FLIP:x} :{turns} :trace :once :file {end}")     # the turns-th flip after the apply flip
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        for c in cmds:
            if len(c) > 235:
                raise ValueError(f"debugger command line too long: {c[:60]}...")
        if h.peekl(TURN) >= t0:
            raise ValueError(f"turn {t0} already passed")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${APPLYPC:x} && (${TURN:x}).l = {t0} :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (out / "end.flag").exists():
            if time.time() - t > TIMEOUT:
                raise TimeoutError(f"run did not complete; log tail:\n{h._logtext()[-1500:]}")
            time.sleep(0.3)
        time.sleep(1.5)
        text = h._logtext()[start:]
        (out / "log.txt").write_text(text)
    finally:
        stop.set()
        if rd:
            rd.join()
        h.close()
    ev = []
    cov = {a: 0 for a in SPRITE_ENTRIES}
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in NUM.findall(blk)]
        pcm = re.search(r"pc = \$([0-9a-f]+)", blk)
        if pcm and int(pcm.group(1), 16) in cov:
            cov[int(pcm.group(1), 16)] += 1
        if len(m) >= 8 and m[0] == S1PC:
            ev.append(("s1", *m[1:8]))
        elif len(m) >= 11 and m[0] == FLIP:
            ev.append(("c", *m[1:11]))
    FSS, FSC = BUFS[1], BUFS[1] + WORLD[1]
    recs, s1s, work, last_s1, pos = [], {}, [], None, 0
    for e in ev:
        need = FSS if e[0] == "s1" else FSC
        if pos + need > len(frames):
            break
        s = bytes(frames[pos:pos + need])
        pos += need
        if e[0] == "s1":
            _, vbl, cyc, turn, shown, x, y, shp = e
            assert shown in (0x2300, 0xA000), hex(shown)
            ss = s[shown - BUFS[0]:shown - BUFS[0] + 32000]
            s1s[turn] = dict(turn=turn, vbl=vbl, x=x, y=y, shp=shp, ss=ss, hs=hashlib.md5(ss).hexdigest())
            last_s1 = cyc
            continue
        _, vbl, cyc, turn, back, shown, x, y, shp, a4, hid = e
        assert back in (0x2300, 0xA000) and shown in (0x2300, 0xA000) and back != shown, (hex(back), hex(shown))
        sb = s[back - BUFS[0]:back - BUFS[0] + 32000]
        ss = s[shown - BUFS[0]:shown - BUFS[0] + 32000]
        w = ((cyc - last_s1) & 0xFFFFFFFF) if last_s1 is not None else None
        last_s1 = None
        recs.append(dict(n=len(recs) + 1, turn=turn, vbl=vbl, x=x, y=y, shp=shp, a4=a4, hid=hid, work=w, sb=sb, ss=ss, world=s[BUFS[1]:],
                         hb=hashlib.md5(sb).hexdigest(), hs=hashlib.md5(ss).hexdigest(), hw=hashlib.md5(s[BUFS[1]:]).hexdigest()))
    return dict(recs=recs, s1=s1s, cov=cov, flips=len(recs))


def diff_desc(a: bytes, b: bytes, stride: int = 160) -> str:
    d = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    if not d:
        return "no byte differs"
    rows = sorted({i // stride for i in d})
    return f"{len(d)} B differ, first at offset {d[0]} (row {d[0] // stride}), rows {rows[0]}-{rows[-1]}"


def dump_pair(a, tag: str, turn: int, br: bytes, pr: bytes):
    if getattr(a, "dump", None):
        d = Path(a.dump)
        d.mkdir(parents=True, exist_ok=True)
        (d / f"t{turn}_{tag}_base.bin").write_bytes(br)
        (d / f"t{turn}_{tag}_patched.bin").write_bytes(pr)


def compare(B: dict, P: dict, a) -> tuple[bool, list[str], dict]:
    """Per turn T (present in both runs): back (the rendered frame, flip entry), world (md5), shown at S1 (the frame just flipped plus the pointer the
    first VBL after the flip drew: always comparable) and shown at the flip entry (the frame plus the pointer after the pass's last VBL: compared
    only when the pointer shape word $11d50 was the same at this flip, the previous flip and in both runs; a hover that changes the shape mid-pass
    changes which VBL redraws it, so the ORIGINAL game shows the old or the new pointer at the flip depending on pass length: base @8 vs base @16 MHz
    differ there, work/notes/display.md)."""
    notes, ok = [], True
    bm = {r["turn"]: r for r in B["recs"]}
    nb = ns = nw = n1 = nshape = 0
    skipped = 0
    first = P["recs"][0]["turn"] if P["recs"] else 0
    for r in P["recs"]:
        br = bm.get(r["turn"])
        if br is None:
            skipped += 1
            continue
        if r["turn"] <= first + 1 and not a.no_skip_first:
            skipped += 1          # the apply instant: the very first pass mixes unpatched and patched code
            continue
        nb += 1
        if r["hb"] != br["hb"]:
            ok = False
            dump_pair(a, "back", r["turn"], br["sb"], r["sb"])
            notes.append(f"  BACK DIFFER turn {r['turn']}: " + diff_desc(br["sb"], r["sb"]))
        nw += 1
        if r["hw"] != br["hw"]:
            ok = False
            notes.append(f"  WORLD DIFFER turn {r['turn']}: " + diff_desc(br["world"], r["world"], 4))
        b1, p1 = B["s1"].get(r["turn"]), P["s1"].get(r["turn"])
        if b1 and p1:
            n1 += 1
            if b1["hs"] != p1["hs"]:
                ok = False
                dump_pair(a, "s1shown", r["turn"], b1["ss"], p1["ss"])
                notes.append(f"  SHOWN@S1 DIFFER turn {r['turn']} (pointer {b1['x']},{b1['y']} / {p1['x']},{p1['y']}, shape {b1['shp']:#x}/{p1['shp']:#x}): " + diff_desc(b1["ss"], p1["ss"]))
        bprev, pprev = bm.get(r["turn"] - 1), next((q for q in P["recs"] if q["turn"] == r["turn"] - 1), None)
        stable = bprev and pprev and br["shp"] == bprev["shp"] == r["shp"] == pprev["shp"]
        if (r["x"], r["y"]) == (br["x"], br["y"]) and (stable or a.neg):
            ns += 1
            if r["hs"] != br["hs"]:
                ok = False
                dump_pair(a, "shown", r["turn"], br["ss"], r["ss"])
                notes.append(f"  SHOWN DIFFER turn {r['turn']} (pointer {r['x']},{r['y']}; shape {br['shp']:#x}/{r['shp']:#x}, [$202e] {br['a4']:#x}/{r['a4']:#x}): " + diff_desc(br["ss"], r["ss"]))
        else:
            nshape += 1
    return ok, notes, dict(nb=nb, ns=ns, nw=nw, n1=n1, nshape=nshape, skipped=skipped)


def mean(v):
    v = [x for x in v if x is not None]
    return sum(v) / len(v) if v else 0.0


def rate(R: dict) -> tuple[float, float]:
    """(flips per emulated second, turns per emulated second) over the captured window."""
    r = R["recs"]
    if len(r) < 2:
        return 0.0, 0.0
    sec = (r[-1]["vbl"] - r[0]["vbl"]) / 50.0
    return (len(r) - 1) / sec, (r[-1]["turn"] - r[0]["turn"]) / sec


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=[], help="patch set under test (added on top of the walk driver and --base)")
    ap.add_argument("--base", nargs="*", default=[], help="patches both runs carry")
    ap.add_argument("--snapshot", nargs="*", default=["busy1", "game_start"])
    ap.add_argument("--turns", type=int, default=130, help="turns captured after the apply flip (the walk repeats every 64)")
    ap.add_argument("--mhz", nargs="*", type=int, default=[8], help="CPU clock of the PATCHED run")
    ap.add_argument("--bmhz", type=int, default=None, help="CPU clock of the base run (default: the patched run's)")
    ap.add_argument("--poke", action="append", default=[], help="ADDR:HEXBYTES in the patched run only, at the apply flip")
    ap.add_argument("--base-poke", action="append", default=[], help="ADDR:HEXBYTES in both runs")
    ap.add_argument("--no-walk", action="store_true")
    ap.add_argument("--neg", action="store_true", help="negative control: the patched run does not walk")
    ap.add_argument("--coverage", action="store_true", help="count the sprite-routine entry points in the base run")
    ap.add_argument("--no-skip-first", action="store_true", help="also compare the first captured turn (the apply flip)")
    ap.add_argument("--dump", help="directory: write the base/patched shown+back buffers of every turn whose SHOWN differs")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    bnames = WALKSET + a.base
    pnames = WALKSET + a.base + a.only
    blive, plive = make_live(bnames), make_live(pnames)
    ok_all = True
    print(f"base set    : {' '.join(bnames)}\npatched set : {' '.join(pnames)}")
    for sn in a.snapshot:
        sp = snap_path(sn)
        t0 = start_turn_for(sp)
        for mhz in a.mhz:
            bm = a.bmhz or mhz
            walk = not a.no_walk
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(one, sp, t0, blive, WORK / f"b_{sp.stem}_{bm}", a.turns, bm, walk, tuple(a.base_poke), a.coverage)
                fp = ex.submit(one, sp, t0, plive, WORK / f"p_{sp.stem}_{mhz}", a.turns, mhz, walk and not a.neg,
                               tuple(a.base_poke) + tuple(a.poke))
                B, P = fb.result(), fp.result()
            ok, notes, st = compare(B, P, a)
            if st['nb'] < 10 or st['ns'] < 5 or st['n1'] < 10:
                ok = False
                notes.append(f"  TOO FEW TURNS COMPARED (back {st['nb']}, shown {st['ns']}): not a pass")
            ok_all &= ok
            bw, pw = mean([r["work"] for r in B["recs"]]), mean([r["work"] for r in P["recs"]])
            bf, bt = rate(B)
            pf, pt = rate(P)
            passv = [q["vbl"] - p["vbl"] for p, q in zip(P["recs"], P["recs"][1:])]
            print(f"{sn} @{mhz} MHz (base @{bm}): {'IDENTICAL' if ok else 'DIFFER'} | turns compared: back {st['nb']}, "
                  f"world {st['nw']}, shown@S1+pointer {st['n1']}, shown@flip+pointer {st['ns']} (shape-change passes not compared: {st['nshape']}) (skipped {st['skipped']}); flips captured {len(P['recs'])}/{len(B['recs'])}; patched min VBL/pass {min(passv) if passv else '-'}"
                  f" | work/pass {bw:.0f} -> {pw:.0f} ({100 * (pw - bw) / bw if bw else 0:+.2f} %)"
                  f" | fps {bf:.3f} -> {pf:.3f} ({100 * (pf - bf) / bf if bf else 0:+.1f} %), turns/s {bt:.3f} -> {pt:.3f}", flush=True)
            if True:
                print("   sprite entry coverage (base run): " + ", ".join(f"{SPRITE_ENTRIES[k]} ${k:x}: {v}" for k, v in B["cov"].items()))
            for x in notes[:12]:
                print("   ", x)
    print("ALL IDENTICAL" if ok_all else "MISMATCH")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
