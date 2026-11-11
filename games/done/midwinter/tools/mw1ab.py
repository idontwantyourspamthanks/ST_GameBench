#!/usr/bin/env python3
"""A/B gate for MW1 display patches: pixel identity of all 3 screen buffers + flips per 1000 VBL.

    python3 games/done/midwinter/tools/mw1ab.py --only p4_x [p4_y ...] [--base p4_z ...] \
        [--snapshot stand walk turn busy | path.sav ...] [--flips 8 40] [--no-fps]

For every snapshot and every --flips N it:
  1. restores the snapshot twice (base, patched) and, at the first flip ($bd9a) after a fixed
     ABSOLUTE VBL (snapshot VBL rounded up + 300), optionally applies the patch set live
     (mw1patch.py live), then saves the visible 32000 bytes of the three buffers
     $58000/$68000/$78000 N flips later;
  2. reports IDENTICAL / DIFFER (differing byte count per buffer) and, unless --no-fps,
     right after the capture traces every flip for 1000 VBL: flips per 1000 VBL and exact mean cycles per frame
     (VBL*160256 + FrameCycles between the first and last flip; only for the first N of --flips);
Base = the unpatched game, or the live set given by --base (use it to gate one item against another).
Base captures (incl. their fps) are cached under /tmp/mw1ab/<base tag>/; delete it after changing a --base set's code.

Only patches to resident code / already-loaded data can be gated this way. Exit status 0 = every
comparison identical. Speed is reported, not gated. Short temp paths are deliberate: Hatari truncates
long debugger lines.
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
from mw1 import MW1, SNAP  # noqa: E402

VISIBLE = 32000
FLIP = 0xBD9A
BUFS = {"b58": (0x58000, VISIBLE), "b68": (0x68000, VISIBLE), "b78": (0x78000, VISIBLE)}
SHORT = {"stand": "1mb_ski_stand", "walk": "1mb_ski_walk", "turn": "1mb_ski_turn", "busy": "1mb_ski_busy"}
WORK = Path("/tmp/mw1ab")


def snap_path(s: str) -> Path:
    if s in SHORT:
        return SNAP / f"{SHORT[s]}.sav"
    p = Path(s)
    return p if p.exists() else SNAP / (s if s.endswith(".sav") else s + ".sav")


def tag_for(names: list[str]) -> str:
    if not names:
        return "base0"
    return f"{names[0][:14]}+{len(names)}-{hashlib.md5('+'.join(sorted(names)).encode()).hexdigest()[:6]}"


def make_live(names: list[str]) -> str | None:
    if not names:
        return None
    live = WORK / tag_for(names) / "live"
    live.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(HERE / "mw1patch.py"), "live", "--only", *names, "--out", str(live)],
                   check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    # capture_frames emits one `w $addr <bytes>` debugger line per site and Hatari truncates lines > ~240 chars:
    # split long sites into <= 40-byte chunks (same bytes, same order).
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


def at_vbl_for(snap: Path) -> int:
    cache = WORK / "at.json"
    d = json.loads(cache.read_text()) if cache.exists() else {}
    k = f"{snap.name}:{snap.stat().st_mtime_ns}"
    if k not in d:
        h = MW1(snapshot=str(snap))
        try:
            v = h.vbl()
        finally:
            h.close()
        d[k] = (v // 100 + 4) * 100
        cache.write_text(json.dumps(d))
    return d[k]


VBL_CYCLES = 160256        # 313 lines x 512 cycles (PAL 50 Hz, 8 MHz); FrameCycles is the position inside the VBL


def flip_cycles(h: MW1, vbls: int = 1000) -> dict:
    """Trace every flip in the next `vbls` VBLs with exact machine time (VBL*160256 + FrameCycles).
    flips = hits in the window; cyc = mean cycles per frame between the first and last hit (no edge
    quantisation: both ends are flips)."""
    cf = h.R / "ctrace.txt"
    cf.write_text("e VBL\ne FrameCycles\n")
    h.debug("b all", 0.3)
    v = h.vbl()                 # before the trace breakpoint exists: its `e VBL` output would pollute h.vbl()
    h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :file {cf}")
    time.sleep(0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v + vbls} :trace :once")
    out = h._wait_removed(start)
    h.debug("b all", 0.3)
    ts = []
    for blk in out.split("Reading debugger commands")[1:]:
        m = re.findall(r"#(\d+) \(dec\)", blk)
        if len(m) >= 2:
            ts.append(int(m[0]) * VBL_CYCLES + int(m[1]))
    cyc = (ts[-1] - ts[0]) / (len(ts) - 1) if len(ts) > 1 else 0.0
    return {"flips": len(ts), "cyc": cyc}


def one(snap: Path, at: int, live: str | None, out: Path, flips: int, fps: bool, cache: bool = False) -> dict:
    meta = out / "meta.json"
    if cache and meta.exists() and json.loads(meta.read_text()).get("fps") == fps and (out / "b78.bin").exists():
        return json.loads(meta.read_text())["res"]
    h = MW1(snapshot=str(snap))
    try:
        h.capture_frames(str(out), flip_addr=FLIP, at_vbl=at, nth_flip=flips, live=live, buffers=BUFS)
        f = flip_cycles(h, 1000) if fps else {"cyc": 0.0, "flips": 0}
    finally:
        h.close()
    md = {n: hashlib.md5((out / f"{n}.bin").read_bytes()[:VISIBLE]).hexdigest() for n in BUFS}
    res = {"flips": f["flips"], "cyc": f["cyc"], "md5": md}
    if cache:
        meta.write_text(json.dumps({"fps": fps, "res": res}))
    return res


def diffbytes(a: Path, b: Path) -> dict:
    r = {}
    for n in BUFS:
        x, y = (a / f"{n}.bin").read_bytes()[:VISIBLE], (b / f"{n}.bin").read_bytes()[:VISIBLE]
        r[n] = sum(1 for i in range(VISIBLE) if x[i] != y[i])
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", required=True)
    ap.add_argument("--base", nargs="*", default=[], help="patch set the comparison base uses (default: none)")
    ap.add_argument("--snapshot", nargs="*", default=["stand", "walk", "turn", "busy"])
    ap.add_argument("--flips", nargs="*", type=int, default=[8, 40])
    ap.add_argument("--no-fps", action="store_true")
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    btag, ptag = tag_for(a.base), tag_for(a.only)
    blive, plive = make_live(a.base), make_live(a.only)
    ok = True
    for sn in a.snapshot:
        sp = snap_path(sn)
        at = at_vbl_for(sp)
        for i, n in enumerate(a.flips):
            fps = not a.no_fps and i == 0
            bd = WORK / btag / f"{sn}_{at}_{n}"
            pd = WORK / ptag / f"{sn}_{at}_{n}"
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(one, sp, at, blive, bd, n, fps, True)
                fp = ex.submit(one, sp, at, plive, pd, n, fps)
                b, p = fb.result(), fp.result()
            same = b["md5"] == p["md5"]
            ok &= same
            res = "IDENTICAL" if same else f"DIFFER {diffbytes(bd, pd)}"
            sp_s = (f"; flips/1000VBL {b['flips']} -> {p['flips']}; cycles/frame {b['cyc']:.0f} -> {p['cyc']:.0f} "
                    f"({p['cyc'] - b['cyc']:+.0f}, {100 * (p['cyc'] - b['cyc']) / b['cyc']:+.2f} %)") if fps else ""
            print(f"{sn} --flips {n}: {res}{sp_s}", flush=True)
    print("ALL IDENTICAL" if ok else "MISMATCH")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
