#!/usr/bin/env python3
"""A/B gate for Hunter display patches: identical picture + exact cycles per frame + fps.

    python3 games/done/hunter/tools/huntab.py --only p4_x [p4_y ...] [--base p4_z ...] \
        [--snapshot foot_stand foot_walk car_stand car_drive car_turn hills_stand 4mb_foot_stand | path.sav ...] \
        [--points 3 | --views K] [--flips 1 6] [--vbls 600] [--no-fps] [--lock]

Why this is not mw1ab.py (work/notes/p4_raster.md section 1): Hunter's world runs on the VBL counter. The movement and
NPC code multiplies by the number of VBLs the previous frame lasted ($1ac(a5), see frameloop.md/baseline.md), so a patch
that makes one frame cross a VBL boundary changes every later frame's SIMULATION, not only its pixels. "Same picture N flips
later" is therefore only a valid test while both runs keep the same VBL count per frame. The gate is built around that:

  * Per snapshot and per start point (`--points`: absolute VBLs, 37 apart) both runs restore the snapshot and, at the first
    flip ($5fee) after the start VBL, the patched run applies the live patch set (`loadbin` + `w`, both at the flip).
  * flips = 1: the FIRST patched frame. Its inputs (the logic of that frame) ran before any patched code, so both runs draw
    the same frame from the same state. The visible 32000 bytes of BOTH screen buffers ($23000, $2AD00) are saved at the next
    flip and compared. This is the hard gate (any difference = MISMATCH).
  * flips = N > 1: the same, N flips later. The two runs log the VBL of every flip: while their frame durations (in VBLs)
    are equal they must be identical (hard gate); if the VBL count of a frame differs the runs have legitimately diverged
    (state depends on elapsed VBLs) and the row is reported `DIVERGED-TIME` (not a failure, not a pass).
  * Cycles. `work` = cycles from the VBL lock's return ($5fa4) to the next flip entry ($5fd2) = logic + render + the interrupts
    inside it, WITHOUT the idle spin until the next VBL (frames last whole VBLs, so plain flip-to-flip time is quantised and
    hides small gains). work(first) = the first patched frame (same inputs in both runs: the exact saving). `period` = flip
    to flip. After the capture both runs keep running `--vbls` VBLs: flips per window -> fps, mean work, mean period.

  * `--lock`: both runs get `$9ad = $0e` (min frame time 15 VBL) so every frame lasts the same number of VBLs in both runs: every --flips N is then
    a hard comparison. `--views K`: K pseudo-random teleports (player X/Z/heading) instead of the `--points` start VBLs, for many different pictures.
    Per-polygon differential oracle for the polygon patch: tools/polydiff.py (4 MB snapshot).

Machine time = VBL*160256 + FrameCycles (8 MHz PAL, 313 lines x 512). Hatari runs in fast-forward (`--fast-forward on`),
~35x real time; breakpoints stay cycle-exact. Base captures are cached in /tmp/hunab/<base tag>/ (delete after changing a
--base set's code). Live patch sets come from tools/huntpatch.py (`live`, HunterLoader). Exit status 0 = every hard comparison identical.
Only code/data that is resident in the snapshot can be gated this way; boot-time behaviour needs the cold boot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from hunter import Hunter, SNAP  # noqa: E402

FLIP = 0x5FEE                       # move.b d1,$203(a6) in the flip routine $5fd2
LOCK_RET = 0x5FA4                   # after the VBL lock: start of the frame's work
FLIP_ENTRY = 0x5FD2                 # flip routine entry (called once per frame from $5fc2)
VISIBLE = 32000
BUFS = {"b23000": (0x23000, VISIBLE), "b2ad00": (0x2AD00, VISIBLE)}
SHORT = {"foot_stand": "1mb_foot_stand", "foot_walk": "1mb_foot_walk", "car_stand": "1mb_car_stand",
         "car_drive": "1mb_car_drive", "car_turn": "1mb_car_turn", "hills_stand": "1mb_hills_stand",
         "4mb_foot_stand": "4mb_foot_stand"}
DEFAULT_SNAPS = list(SHORT)
WORK = Path("/tmp/hunab")
VBL_CYCLES = 160256
POINT_STEP = 37                     # VBLs between start points (coprime with the 6-11 VBL frame lengths)


def snap_path(s: str) -> Path:
    if s in SHORT:
        return SNAP / f"{SHORT[s]}.sav"
    p = Path(s)
    return p if p.exists() else SNAP / (s if s.endswith(".sav") else s + ".sav")


def memsize_of(sp: Path) -> int:
    return 4096 if sp.name.startswith("4mb") else 1024


# ---- live patch sets ------------------------------------------------------------------------------------------------
def tag_for(names: list[str]) -> str:
    if not names:
        return "base0"
    return f"{names[0][:14]}+{len(names)}-{hashlib.md5('+'.join(sorted(names)).encode()).hexdigest()[:6]}"


def make_live(names: list[str]) -> str | None:
    if not names:
        return None
    live = WORK / tag_for(names) / "live"
    live.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(HERE / "huntpatch.py"), "live", "--only", *names, "--out", str(live)], check=True,
                   cwd=GAME, stdout=subprocess.DEVNULL)
    # one `w` line per <= 40 bytes: Hatari truncates debugger lines of ~240 characters silently
    jp = Path(str(live) + ".json")
    spec = json.loads(jp.read_text())
    sites = []
    for st in spec["sites"]:
        raw = bytes.fromhex(st["new"])
        for o in range(0, len(raw), 40):
            sites.append({**st, "addr": st["addr"] + o, "new": raw[o:o + 40].hex()})
    spec["sites"] = sites
    jp.write_text(json.dumps(spec, indent=1))
    return str(live)


# ---- one run ---------------------------------------------------------------------------------------------------------
def at_vbl_for(snap: Path) -> int:
    cache = WORK / "at.json"
    d = json.loads(cache.read_text()) if cache.exists() else {}
    k = f"{snap.name}:{snap.stat().st_mtime_ns}"
    if k not in d:
        h = Hunter(snapshot=str(snap), memsize_kb=memsize_of(snap))
        try:
            v = h.vbl()
        finally:
            h.close()
        d[k] = (v // 100 + 3) * 100
        cache.write_text(json.dumps(d))
    return d[k]


NUM = re.compile(r"#(\d+) \(dec\)")


def _hits(text: str, tags: dict[int, str]) -> list[tuple[str, int]]:
    """Parse trace blocks printed by the S1/S2/flip log files: each block holds `e <tag>`, `e VBL`, `e FrameCycles`."""
    out = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = NUM.findall(blk)
        if len(m) >= 3 and int(m[0]) in tags:
            out.append((tags[int(m[0])], int(m[1]) * VBL_CYCLES + int(m[2])))
    return out


def pokes_for(view: int | None, lock: bool) -> list[str]:
    """Debugger `w` lines applied at the apply flip in BOTH runs: --lock = minimum frame time 15 VBL ($1a7(a5) = $9ad, so
    every frame lasts the same number of VBLs in both runs and the simulation stays frame-for-frame identical);
    --views = teleport the player ($ab2 X word, $ab6 Z word, $ae6 heading word) to a pseudo-random view."""
    import random
    out = []
    if lock:
        out.append("w $9ad $0e")
    if view is not None:
        r = random.Random(1000 + view)
        x, z, hd = r.randrange(140 << 8, 176 << 8), r.randrange(25 << 8, 60 << 8), r.randrange(0, 65536)
        out.append(f"w $ab2 ${x >> 8:02x} ${x & 255:02x}")
        out.append(f"w $ab6 ${z >> 8:02x} ${z & 255:02x}")
        out.append(f"w $ae6 ${hd >> 8:02x} ${hd & 255:02x}")
    return out


def one(snap: Path, at: int, live: str | None, out: Path, flips: list[int], vbls: int, fps: bool,
        cache: bool = False, pokes: list[str] | None = None) -> dict:
    meta = out / "meta.json"
    if cache and meta.exists() and (out / "done").exists():
        r = json.loads(meta.read_text())
        r["md5"] = {int(k): v for k, v in r["md5"].items()}
        return r
    out.mkdir(parents=True, exist_ok=True)
    h = Hunter(snapshot=str(snap), memsize_kb=memsize_of(snap))
    try:
        R = h.R
        # capture files: one per requested flip count; each saves both buffers and logs the machine time
        caps = []
        for n in flips:
            cf = R / f"c{n}.txt"
            cf.write_text("".join(f"savebin {out}/f{n}_{b}.bin ${a:x} ${ln:x}\n" for b, (a, ln) in BUFS.items())
                          + f"e ${FLIP:x}\ne VBL\ne FrameCycles\n")
            caps.append((n, cf))
        # persistent trace: S1 (frame start, after the VBL lock), S2 (flip entry) with machine time
        tags = {LOCK_RET: "S1", FLIP_ENTRY: "S2", FLIP: "F"}
        for pc in tags:
            (R / f"t{pc:x}.txt").write_text(f"e ${pc:x}\ne VBL\ne FrameCycles\n")
        cmds = [f"e ${FLIP:x}", "e VBL", "e FrameCycles"]      # time stamp of the apply flip (flip k)
        if live:
            spec = json.loads(Path(live + ".json").read_text())
            if len(bytes(Path(live + ".img").read_bytes())):
                cmds.append(f"loadbin {Path(live + '.img')} ${spec['img_base']:x}")
            for s in spec["sites"]:
                cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
        cmds += pokes or []
        for pc in (LOCK_RET, FLIP_ENTRY):
            cmds.append(f"b pc = ${pc:x} :trace :file {R / f't{pc:x}.txt'}")
        for n, cf in caps:
            cnt = f" :{n}" if n > 1 else ""            # Hatari rejects a skip count of 1
            cmds.append(f"b pc = ${FLIP:x}{cnt} :trace :once :file {cf}")
        end = R / "end.txt"
        end.write_text("b all\n")
        cmds.append(f"b VBL > {at + (vbls if fps else 150)} :trace :once :file {end}")
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        if len(max(cmds, key=len)) > 235:
            raise ValueError("debugger command line too long (Hatari truncates silently)")
        if h.vbl() >= at:
            raise ValueError(f"at_vbl {at} already passed")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while h._logtext()[start:].count("Removed CPU breakpoint") < 2 + len(flips):
            if time.time() - t > 300:
                raise TimeoutError(f"run did not complete; log tail:\n{h._logtext()[-1500:]}")
            time.sleep(0.3)
        time.sleep(0.5)
        text = h._logtext()[start:]
    finally:
        h.close()
    ev = _hits(text, {0x5FA4: "S1", 0x5FD2: "S2", 0x5FEE: "F"})
    s1 = [t for k, t in ev if k == "S1"]
    s2 = [t for k, t in ev if k == "S2"]
    fk = [t for k, t in ev if k == "F"]
    # work(first) = first S1 after the apply flip -> next S2 ; stamps per flip for the divergence check
    work = []
    j = 0
    for t1 in s1:
        while j < len(s2) and s2[j] < t1:
            j += 1
        if j < len(s2):
            work.append(s2[j] - t1)
    period = [b - a for a, b in zip(s2, s2[1:])]
    nflip = len(s2)
    span = (s2[-1] - s2[0]) if nflip > 1 else 0
    res = {"md5": {}, "work_first": work[0] if work else 0, "frames": [round((b - a) / VBL_CYCLES) for a, b in zip(fk[:1] + s2, s2)][:max(flips) + 2],
           "flips": nflip, "span_vbl": span / VBL_CYCLES,
           "work_mean": sum(work) / len(work) if work else 0.0, "period_mean": sum(period) / len(period) if period else 0.0}
    for n in flips:
        res["md5"][n] = {b: hashlib.md5((out / f"f{n}_{b}.bin").read_bytes()).hexdigest() for b in BUFS}
    # VBLs from the flip that applied the patch (the capture's pc=$5fee hit) up to flip n: first-frame lengths
    if cache:
        meta.write_text(json.dumps(res))
        (out / "done").write_text("1")
    else:
        meta.write_text(json.dumps(res))
    return res


def diffbytes(a: Path, b: Path, n: int) -> dict:
    r = {}
    for nm in BUFS:
        x, y = (a / f"f{n}_{nm}.bin").read_bytes(), (b / f"f{n}_{nm}.bin").read_bytes()
        r[nm] = sum(1 for i in range(min(len(x), len(y))) if x[i] != y[i])
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=[], help="patch set under test ([] = null patch: a self-test)")
    ap.add_argument("--base", nargs="*", default=[], help="patch set the comparison base uses (default: none)")
    ap.add_argument("--snapshot", nargs="*", default=DEFAULT_SNAPS)
    ap.add_argument("--points", type=int, default=3)
    ap.add_argument("--flips", nargs="*", type=int, default=[1, 6])
    ap.add_argument("--vbls", type=int, default=600, help="measurement window after the capture")
    ap.add_argument("--no-fps", action="store_true")
    ap.add_argument("--lock", action="store_true", help="force 15 VBL frames in both runs: every --flips N is a hard comparison")
    ap.add_argument("--views", type=int, default=0, help="teleport to N pseudo-random views per snapshot (instead of --points)")
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    flips = sorted(set(a.flips) | {1})
    btag, ptag = tag_for(a.base), tag_for(a.only)
    blive, plive = make_live(a.base), make_live(a.only)
    ok = True
    rows = []
    for sn in a.snapshot:
        sp = snap_path(sn)
        at0 = at_vbl_for(sp)
        tot = {"bw": 0.0, "pw": 0.0, "bm": 0.0, "pm": 0.0, "bf": 0, "pf": 0, "bv": 0.0, "pv": 0.0, "bp": 0.0, "pp": 0.0}
        cmp_ok = True
        notes = []
        npts = a.views or a.points
        for pi in range(npts):
            at = at0 + pi * POINT_STEP
            view = pi if a.views else None
            sfx = ("_L" if a.lock else "") + (f"_v{view}" if view is not None else "")
            bd = WORK / btag / f"{sn}_{at}{sfx}"
            pd = WORK / ptag / f"{sn}_{at}{sfx}"
            pk = pokes_for(view, a.lock)
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(one, sp, at, blive, bd, flips, a.vbls, not a.no_fps, True, pk)
                fp = ex.submit(one, sp, at, plive, pd, flips, a.vbls, not a.no_fps, False, pk)
                b, p = fb.result(), fp.result()
            for n in flips:
                same = b["md5"][n] == p["md5"][n]
                if n == 1:
                    kind = "hard"
                else:
                    # flip n is comparable while the first n-1 frame lengths (in VBLs) agree
                    kind = "hard" if (a.lock or b["frames"][:n] == p["frames"][:n]) else "diverged"
                if kind == "hard" and not same:
                    cmp_ok = False
                    notes.append(f"p{pi} flips={n} DIFFER {diffbytes(bd, pd, n)}")
                elif kind == "diverged":
                    notes.append(f"p{pi} flips={n} DIVERGED-TIME frames base={b['frames'][:n]} patched={p['frames'][:n]} "
                                 f"({'same' if same else 'differs'})")
            tot["bw"] += b["work_first"]; tot["pw"] += p["work_first"]
            tot["bm"] += b["work_mean"]; tot["pm"] += p["work_mean"]
            tot["bf"] += b["flips"]; tot["pf"] += p["flips"]
            tot["bv"] += b["span_vbl"]; tot["pv"] += p["span_vbl"]
            tot["bp"] += b["period_mean"]; tot["pp"] += p["period_mean"]
        ok &= cmp_ok
        n = npts
        res = "IDENTICAL" if cmp_ok else "DIFFER"
        line = f"{sn}: {res}"
        if not a.no_fps:
            wf = (tot["pw"] - tot["bw"]) / n
            line += (f" | work(first patched frame) {tot['bw'] / n:.0f} -> {tot['pw'] / n:.0f} ({wf:+.0f}, "
                     f"{100 * wf / (tot['bw'] / n):+.2f} %)"
                     f" | window mean work {tot['bm'] / n:.0f} -> {tot['pm'] / n:.0f}"
                     f" | VBL/frame {tot['bp'] / n / VBL_CYCLES:.2f} -> {tot['pp'] / n / VBL_CYCLES:.2f}"
                     f" | fps {50 * VBL_CYCLES / (tot['bp'] / n):.2f} -> {50 * VBL_CYCLES / (tot['pp'] / n):.2f}")
        print(line, flush=True)
        for x in notes:
            print("   ", x)
    print("ALL IDENTICAL" if ok else "MISMATCH")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
