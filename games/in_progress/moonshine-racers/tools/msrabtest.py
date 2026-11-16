#!/usr/bin/env python3
"""A/B gate for pixel-identical render patches (precedent: midwinter2 tools/abtest.py), Moonshine Racers.

    python3 tools/msrabtest.py --only mr_edge [more patches] [--snapshots race_grid race_start race_up race_drive]
                               [--flips 10 40] [--state 120] [--rate]

Per snapshot (work/snapshots/ste1m_<name>.sav, stock game, NO mt_* tick patches unless named in --only):
  1. PIXELS: restore the snapshot, at the first flip ($d1ca) after a fixed VBL apply the patch set live (`msrpatch.py live --only ...`: payload image
     loadbin + site bytes), then at the N-th following flip save both screen buffers ($70000 and $78000, the visible 32000 bytes each) and
     compare against the same capture of the unpatched game (cached in work/render/ab/base/).  One Hatari at a time.
  2. STATE (--state N): at every execution of $7b86 (first instruction after the flip: `addq.w #1,$100e`) dump $1000-$13ff, $29c8-$34ff, $4500-$4fff and
     the RNG long $dae6 for N passes (patch applied at the first $7a88), keyed by the pass counter $100e; stock and patched must agree on every
     byte of every common pass (the pacing differs, the per-pass state must not).
  3. --rate: passes per second and VBL per pass of the stock and patched game over 600 VBL (flips counted at $d1ca).
Exit status 0 = everything compared is identical.  A negative control (`--only mr_negctl`) must report DIFFER.
"""
from __future__ import annotations

import argparse
import os
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from msr import Moonshine, GAME  # noqa: E402

SNAPS = GAME / "work" / "snapshots"
AB = GAME / "work" / "render" / "ab"
VISIBLE = 0x7D00
BUFFERS = {"b70000": (0x70000, VISIBLE), "b78000": (0x78000, VISIBLE)}
STATE_RANGES = [(0x1000, 0x400), (0x29C8, 0xB38), (0x4500, 0xB00), (0xDAE6, 4)]
DEFAULT_SNAPS = ["race_grid", "race_start", "race_up", "race_drive"]


def snap_path(name: str) -> str:
    p = Path(name)
    return str(p if p.exists() else SNAPS / f"ste1m_{name}.sav")


def live_build(names: list[str]) -> Path:
    tag = "+".join(n.replace("mr_", "") for n in names)
    if len(tag) > 40:
        tag = hashlib.md5(tag.encode()).hexdigest()[:10]
    out = AB / "live" / (tag + os.environ.get("MSR_LIVETAG", ""))     # MSR_LIVETAG: keeps builds from a scratch MSR_PATCHDIR apart
    out.parent.mkdir(parents=True, exist_ok=True)
    tool = os.environ.get("MSRPATCH_TOOL", str(GAME / "tools/msrpatch.py"))        # MSRPATCH_TOOL: a private copy of the tool (same CLI, `live`)
    r = subprocess.run([sys.executable, tool, "live", "--only", *names, "--out", str(out.relative_to(GAME))],
                       capture_output=True, text=True, cwd=GAME)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)
    return out


def with_pokes(live: Path | None, pokes: list[str], tag: str) -> Path | None:
    """live image + extra memory writes `addr=hexbytes` (e.g. 11c6=01) applied at the same instant, for BOTH the stock and the patched run
    (live None = stock: a 4-byte zero image at $B3FF0 stands in)."""
    if not pokes:
        return live
    out = AB / "live" / f"poke_{tag}"
    if live:
        spec = json.loads(live.with_suffix(".json").read_text())
        out.with_suffix(".img").write_bytes(live.with_suffix(".img").read_bytes())
    else:
        spec = {"img_base": 0xB3FF0, "sites": []}
        out.with_suffix(".img").write_bytes(bytes(4))
    for pk in pokes:
        ad, val = pk.split("=")
        spec["sites"].append({"addr": int(ad, 16), "orig": "", "new": val, "name": "poke"})
    out.with_suffix(".json").write_text(json.dumps(spec))
    return out


def at_vbl_for(snap: str) -> int:
    cache = AB / "at_vbl.json"
    d = json.loads(cache.read_text()) if cache.exists() else {}
    key = f"{Path(snap).name}:{Path(snap).stat().st_mtime_ns}"
    if key not in d:
        h = Moonshine(snapshot=snap)
        try:
            time.sleep(2)
            v = h.vbl()
        finally:
            h.close()
        d[key] = (v // 100 + 4) * 100
        AB.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(d))
    return d[key]


def capture(snap: str, at: int, live: Path | None, out: Path, flips: int) -> dict:
    h = Moonshine(snapshot=snap)
    try:
        h.capture_frames(str(out), flip_addr=0xD1CA, at_vbl=at, nth_flip=flips, live=str(live) if live else None, buffers=BUFFERS)
    finally:
        h.close()
    return {n: hashlib.md5((out / f"{n}.bin").read_bytes()[:VISIBLE]).hexdigest() for n in BUFFERS}


def diffbytes(a: Path, b: Path) -> int:
    n = 0
    for f in BUFFERS:
        x, y = (a / f"{f}.bin").read_bytes(), (b / f"{f}.bin").read_bytes()
        n += sum(1 for i in range(min(len(x), len(y), VISIBLE)) if x[i] != y[i])
    return n


def apply_live(h, live: Path, at_pc: int, timeout: float = 120):
    spec = json.loads(live.with_suffix(".json").read_text())
    cmds = [f"loadbin {live.with_suffix('.img').resolve()} ${spec['img_base']:x}"]
    for s in spec["sites"]:
        b = bytes.fromhex(s["new"])
        for k in range(0, len(b), 8):
            cmds.append(f"w ${s['addr'] + k:x} " + " ".join(f"${x:02x}" for x in b[k:k + 8]))
    if len(max(cmds, key=len)) > 240:
        raise ValueError("debugger command line too long")
    f = h.R / "apply.txt"
    f.write_text("\n".join(cmds) + "\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${at_pc:x} :trace :once :file {f}")
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("apply breakpoint never hit")
        time.sleep(0.2)
    time.sleep(0.4)


def state_run(snap: str, live: Path | None, npass: int) -> dict:
    """{pass counter $100e: {addr: byte}} for npass passes."""
    h = Moonshine(snapshot=snap)
    try:
        time.sleep(1.5)
        if live:
            apply_live(h, live, 0x7A88)
        f = h.R / "state.txt"
        f.write_text("e VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in STATE_RANGES))   # Hatari's `m` count is DECIMAL (hex counts were rejected/misread)
        h.debug("b all", 0.3)
        n0 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
        t0 = time.time()
        while h._logtext()[n0:].count("> e VBL") < npass:
            if time.time() - t0 > 1200:
                break
            time.sleep(1)
        h.debug("b all", 0.5)
        log = h._logtext()[n0:]
    finally:
        h.close()
    res = {}
    for ht in log.split("> e VBL")[1:]:
        mem = {}
        for ln in ht.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
            if m:
                a = int(m.group(1), 16)
                for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))):
                    mem[a + i] = x
        if 0x100E in mem:
            res[(mem[0x100E] << 8) | mem[0x100F]] = mem
    return res


def state_compare(a: dict, b: dict) -> tuple[int, int, dict]:
    common = sorted(set(a) & set(b))
    where = {}
    state_compare.compared = 0       # bytes compared (passes x addresses present in both captures)
    for k in common:
        for ad, x in a[k].items():
            if ad in b[k]:
                state_compare.compared += 1
            if ad in b[k] and b[k][ad] != x:
                where.setdefault(ad, []).append((k, x, b[k][ad]))
    return len(common), sum(len(v) for v in where.values()), where


def rate(snap: str, live: Path | None, vbls: int = 600) -> dict:
    h = Moonshine(snapshot=snap)
    try:
        time.sleep(1.5)
        if live:
            apply_live(h, live, 0x7A88)
        time.sleep(1)
        v0 = h.vbl()
        h.debug("b all", 0.3)
        h.cmd("hatari-debug b pc = $d1ca :trace")
        time.sleep(0.3)
        start = h._arm_vbl(vbls)
        out = h._wait_removed(start)
        h.debug("b all", 0.3)
        n = out.count("pc = $d1ca :trace")
    finally:
        h.close()
    return {"flips": n, "vbls": vbls, "vbl_per_pass": vbls / n if n else None}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="+", required=True)
    ap.add_argument("--snapshots", nargs="*", default=DEFAULT_SNAPS)
    ap.add_argument("--flips", nargs="*", type=int, default=[10, 40])
    ap.add_argument("--state", type=int, default=0, help="per-pass state compare over N passes (0 = skip)")
    ap.add_argument("--rate", action="store_true")
    ap.add_argument("--rebase", action="store_true", help="ignore cached stock captures")
    ap.add_argument("--poke", nargs="*", default=[], help="extra writes addr=hexbytes applied to both runs at the apply instant (e.g. 11c6=01)")
    a = ap.parse_args()
    ptag = hashlib.md5(" ".join(a.poke).encode()).hexdigest()[:6] if a.poke else ""
    live = with_pokes(live_build(a.only), a.poke, "p_" + "+".join(x.replace("mr_", "") for x in a.only)[:30] + ptag)
    stock_live = with_pokes(None, a.poke, "stock" + ptag)
    ok = True
    print(f"patch set: {' '.join(a.only)}{'  pokes ' + ' '.join(a.poke) if a.poke else ''}  (live image {live.with_suffix('.img').name}, {live.with_suffix('.img').stat().st_size} B)")
    for name in a.snapshots:
        snap = snap_path(name)
        at = at_vbl_for(snap)
        for fl in a.flips:
            bd = AB / "base" / f"{name}_{at}_{fl}{ptag}"
            if a.rebase or not (bd / "b78000.bin").exists():
                capture(snap, at, stock_live, bd, fl)
            bm = {n: hashlib.md5((bd / f"{n}.bin").read_bytes()[:VISIBLE]).hexdigest() for n in BUFFERS}
            pd = AB / "patched" / f"{'+'.join(x.replace('mr_', '') for x in a.only)[:40]}" / f"{name}_{at}_{fl}{ptag}"
            pm = capture(snap, at, live, pd, fl)
            same = bm == pm
            ok &= same
            nd = 0 if same else diffbytes(bd, pd)
            print(f"PIXELS {name:11s} at VBL {at} flip {fl:3d}: {'IDENTICAL' if same else f'DIFFER ({nd} bytes of 64000)'}  "
                  f"md5 {pm['b70000'][:8]} {pm['b78000'][:8]} (stock {bm['b70000'][:8]} {bm['b78000'][:8]})", flush=True)
        if a.state:
            sa = state_run(snap, stock_live, a.state)
            sb = state_run(snap, live, a.state)
            n, nd, where = state_compare(sa, sb)
            ok &= (nd == 0 and n > 0)
            print(f"STATE  {name:11s}: stock {len(sa)} passes, patched {len(sb)}, common {n}; {state_compare.compared} bytes compared ({state_compare.compared // max(n, 1)} per pass); differing bytes {nd} at {len(where)} addresses"
                  + (" -> " + ", ".join(f"${x:04x}" for x in sorted(where)[:12]) if where else ""), flush=True)
        if a.rate:
            r0, r1 = rate(snap, stock_live), rate(snap, live)
            print(f"RATE   {name:11s}: stock {r0['flips']} flips/{r0['vbls']} VBL = {r0['vbl_per_pass']:.2f} VBL/pass; "
                  f"patched {r1['flips']} flips = {r1['vbl_per_pass']:.2f} VBL/pass", flush=True)
    print("RESULT:", "ALL IDENTICAL" if ok else "DIFFERENCES FOUND")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
