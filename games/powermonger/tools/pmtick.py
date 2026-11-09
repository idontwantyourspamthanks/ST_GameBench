#!/usr/bin/env python3
"""Timing gates for the Powermonger fixed-tick patches (tick_head tick_pass tick_wx tick_men).
Private live builder (assembles patches/tick_*.s with vasm, writes build/tick/live.{img,json}) until PMLoader's pmpatch.py exists.

    python3 tools/pmtick.py live                       # build the live image
    python3 tools/pmtick.py rate  SNAP MHZ VBLS [--unpatched]   # world tick rate, fps, pass kinds
    python3 tools/pmtick.py ab    SNAP MHZ VBLS        # per-tick state equality vs unpatched (full RAM $0-$60000, masks in MASKS)
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys, tempfile, threading, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent / "tools"), str(HERE)]
from pm import PM, SNAP  # noqa: E402

PATCHDIR = GAME / "patches"
NAMES = ["tick_head", "tick_pass", "tick_wx", "tick_men", "tick_click", "tick_click2", "tick_click3"]
IMG_BASE = 0xB8800
IMG_LEN = 0x400
D = 0xB8A00
FLIP = 0x187A
LOOPTOP = 0x12FD8
VBL = 0x6F304
TICKCNT = 0x4BB3E     # long, +1 per world tick (original: +1 per pass)
ITER = 0x2DF70        # long, +1 per pass (patched: also on render-only passes)


def parse(path: Path):
    hdr, segs, cur, pre = {}, [], None, []
    for line in path.read_text().splitlines():
        m = re.match(r"^;\s*(name|default|site|orig|data|note):\s*(.*)$", line)
        if m and cur is None:
            hdr.setdefault(m.group(1), m.group(2).strip()); continue
        if cur is None and re.match(r"^\s*\w+\s+equ\s+", line):
            pre.append(line); continue
        m = re.match(r"^\s*org\s+\$([0-9a-fA-F]+)\s*$", line)
        if m:
            cur = (int(m.group(1), 16), []); segs.append(cur)
        elif cur is not None:
            cur[1].append(line)
    return hdr, segs, pre


def assemble(org, lines, pre):
    src = "\n".join(pre) + f"\n\torg\t${org:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "s.s"; s.write_text(src); o = Path(td) / "s.bin"
        r = subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(o), str(s)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"vasm failed {src}\n{r.stderr}")
        return o.read_bytes()


def build_live(names=NAMES, out="build/tick/live"):
    img = bytearray(IMG_LEN)
    sites = []
    for n in names:
        hdr, segs, pre = parse(PATCHDIR / f"{n}.s")
        site = int(hdr["site"].lstrip("$"), 16)
        orig = bytes.fromhex(hdr["orig"])
        for org, lines in segs:
            b = assemble(org, lines, pre)
            if org == site:
                assert len(b) <= len(orig), (n, len(b), len(orig))
                new = b + b"\x4e\x71" * ((len(orig) - len(b)) // 2)
                sites.append({"addr": site, "orig": orig.hex(), "new": new.hex(), "name": n})
            else:
                assert IMG_BASE <= org and org + len(b) <= IMG_BASE + IMG_LEN, (n, hex(org))
                img[org - IMG_BASE: org - IMG_BASE + len(b)] = b
    o = GAME / out
    o.parent.mkdir(parents=True, exist_ok=True)
    o.with_suffix(".img").write_bytes(bytes(img))
    o.with_suffix(".json").write_text(json.dumps({"img_base": IMG_BASE, "sites": sites}, indent=1))
    return str(o)


def apply_cmds(live):
    spec = json.loads(Path(live + ".json").read_text())
    c = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])) for s in spec["sites"]]
    return c


def wait_gone(h, start, timeout=900):
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("breakpoint never fired")
        time.sleep(0.3)
    time.sleep(0.4)


def at_flip(h, cmds):
    """Run debugger `cmds` at the next call of the flip routine (code is only patched at a frame boundary)."""
    f = h.R / "atflip.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :once :file {f}")
    wait_gone(h, start, 120)


def rd(h, a, n):
    """bytes at a from the debugger `m` output"""
    out = h.debug(f"m ${a:x} {n}", 0.5)
    bs = bytearray()
    for ln in out.splitlines():
        m = re.match(r"[0-9A-Fa-f]{8}:\s(.*)", ln)
        if m:
            bs += bytes(int(x, 16) for x in m.group(1).split("  ")[0].split())
    return bytes(bs[:n])


def cmd_rate(a):
    live = build_live()
    h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        if not a.unpatched:
            at_flip(h, apply_cmds(live))
        v0 = h.vbl(); t0 = h.peekl(TICKCNT); i0 = h.peekl(ITER)
        d0 = rd(h, D, 24) if not a.unpatched else b""
        f = h.fps(a.vbls)
        v1 = h.vbl(); t1 = h.peekl(TICKCNT); i1 = h.peekl(ITER)
        d1 = rd(h, D, 24) if not a.unpatched else b""
        dv = v1 - v0
        print(f"{a.snap} {a.mhz} MHz {'orig' if a.unpatched else 'patched'}: {dv} VBL, flips {f['flips']} (fps {f['flips']*50/a.vbls:.2f}), "
              f"world ticks {t1-t0} ({(t1-t0)*50/dv:.3f}/s), passes {i1-i0} ({(i1-i0)*50/dv:.3f}/s)")
        if d0:
            L = lambda b, o: int.from_bytes(b[o:o+4], 'big')
            print(f"  tick passes {L(d1,8)-L(d0,8)}, R passes {L(d1,12)-L(d0,12)}, S (skip) passes {L(d1,16)-L(d0,16)}")
    finally:
        h.close()


def watch_hits(h, addr, action, window, width="w"):
    """Arm a change-watch on `addr`, run `action()`, collect hit times (s after the action started) for `window` s."""
    h.debug("b all", 0.3)
    f = h.R / "wh.txt"
    f.write_text("e VBL\n")
    h.cmd(f"hatari-debug b (${addr:x}).{width} ! (${addr:x}).{width} :trace :file {f}")
    time.sleep(0.4)
    s0 = len(h._logtext())
    t0 = time.time()
    seen = []
    th = threading.Thread(target=action, daemon=True); th.start()
    while time.time() - t0 < window:
        n = h._logtext()[s0:].count("Reading debugger commands")
        while len(seen) < n:
            seen.append(time.time() - t0)
        time.sleep(0.01)
    th.join()
    h.debug("b all", 0.3)
    return seen


def cmd_input(a):
    live = build_live()
    h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        if not a.unpatched:
            at_flip(h, apply_cmds(live))
        tag = f"{a.snap} {a.mhz} MHz {'orig' if a.unpatched else 'patched'}"
        # 1. pointer: relative move, first change of the pointer X word
        h.goto_st(60, 100)
        r = watch_hits(h, 0x1C492, lambda: h.rel(30, 0, 3), 1.5)
        print(f"{tag}: pointer X first change after {r[0]*1000:.0f} ms, {len(r)} changes in 1.5 s" if r else f"{tag}: pointer no change")
        # 2. click on the compass arrow: the view rotates in steps of 4 units per pass ($12f56 -> $ff9a)
        h.goto_st(36, 162)
        r = watch_hits(h, 0xFF9A, lambda: h.click(hold=0.3), 3.0)
        if len(r) > 2:
            print(f"{tag}: compass click -> first rotation step after {r[0]*1000:.0f} ms, {len(r)} steps in 3 s ({len(r)/3.0:.1f} steps/s)")
        else:
            print(f"{tag}: compass click no response {r}")
        # 3. held cursor key: one scroll step per pass
        h.goto_st(100, 100)
        def keyhold():
            h._xdo("keydown", "Right"); time.sleep(2.0); h._xdo("keyup", "Right")
        r = watch_hits(h, 0x4BB3A, keyhold, 2.6)
        if len(r) > 2:
            gaps = [y - x for x, y in zip(r, r[1:])]
            print(f"{tag}: Right key held 2 s: {len(r)} scroll steps, first after {r[0]*1000:.0f} ms, mean step {sum(gaps)/len(gaps)*1000:.0f} ms ({len(r)/2.0:.1f} steps/s)")
        else:
            print(f"{tag}: Right key hits {r}")
    finally:
        h.close()


DUMP_LEN = 0x60000
# ranges that legitimately differ between runs (interrupt-driven or scratch): screens + stack scratch, VBL/mouse/pointer/sample IRQ state,
# the sound queue (expiry times from $6f304), the ping-pong of $2df72-$2df8e (click latch, VBL flag, screen pointers)
MASKS = [(0x1C700, 0x2C100, "screens"), (0x2C100, 0x2CC00, "stack"),
         (0x1AF30, 0x1AF40, "sample irq pointer"), (0x1C480, 0x1C4E0, "mouse/pointer"), (0x2DF74, 0x2DF84, "click latch, screen pointers"), (0x2DF88, 0x2DF90, "VBL flag"),
         (0x12952, 0x12CA0, "sound queue"), (0x58050, 0x58070, "sound channels"), (0xE3E2, 0xE3E6, "draw ptr scratch"), (0x12F58, 0x12F5A, "flip flag"),
         (0x8830, 0x8840, "scratch")]


def log_passes(h, live, mhz, vbls, tag, poke=()):
    """Restore state, apply `live` (None = nothing) at a flip, then dump RAM $0-$60000 at every loop top for `vbls` VBL.
    Returns [(iter, tickcnt, bytes)]."""
    if mhz != 8:
        h.set_cpuclock(mhz)
    at_flip(h, list(poke) + (apply_cmds(live) if live else ["e VBL"]))
    cur = h.R / "cur.bin"
    f = h.R / "dumpcmd.txt"
    f.write_text(f"savebin {cur} $0 ${DUMP_LEN:x}\n")
    got, stop = [], threading.Event()

    def poll():
        last = None
        while not stop.is_set():
            try:
                st = cur.stat()
            except FileNotFoundError:
                time.sleep(0.003); continue
            if st.st_size == DUMP_LEN and st.st_mtime_ns != last:
                time.sleep(0.03)
                st2 = cur.stat()
                if st2.st_mtime_ns == st.st_mtime_ns and st2.st_size == DUMP_LEN:
                    b = cur.read_bytes()
                    last = st.st_mtime_ns
                    got.append(b)
            time.sleep(0.004)
    th = threading.Thread(target=poll, daemon=True); th.start()
    h.debug("b all", 0.3)
    s2 = len(h._logtext())
    v0 = h.vbl()
    h.cmd(f"hatari-debug b pc = ${LOOPTOP:x} :trace :file {f}")
    time.sleep(0.2)
    h.cmd(f"hatari-debug b VBL > {v0 + vbls} :trace :once")
    wait_gone(h, s2)
    h.debug("b all", 0.3)
    time.sleep(0.5)
    stop.set(); th.join()
    L = lambda b, o: int.from_bytes(b[o:o + 4], "big")
    return [(L(b, ITER), L(b, TICKCNT), b) for b in got]


SITE_MASKS = [(0x13020, 0x13026), (0x13074, 0x1307C), (0x130B0, 0x130B6), (0x130C2, 0x130C8), (0x12F8, 0x12FC), (0x1354, 0x1358), (0x1373E, 0x13742)]   # the patched sites themselves


def masked(a):
    return any(lo <= a < hi for lo, hi, _ in MASKS) or any(lo <= a < hi for lo, hi in SITE_MASKS)


def diff_words(a, b):
    out = []
    for i in range(0, DUMP_LEN, 2):
        pass
    # fast path: chunked compare
    import numpy as np
    x = np.frombuffer(a, dtype=">u2"); y = np.frombuffer(b, dtype=">u2")
    idx = np.nonzero(x != y)[0] * 2
    return [int(i) for i in idx if not masked(int(i))]


def group(addrs, gap=16):
    out = []
    for a in addrs:
        if out and a - out[-1][1] <= gap:
            out[-1][1] = a + 2
        else:
            out.append([a, a + 2])
    return out


def cmd_ab(a):
    live = build_live()
    res = {}
    def one(name, lv):
        h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
        try:
            time.sleep(1.5)
            mh = a.mhz if name == "P" else (a.vs or a.mhz)
            res[name] = log_passes(h, lv, mh, a.vbls if (lv and not a.vs) else int(a.vbls * 1.6), name, a.poke)
        finally:
            h.close()
    ts = [threading.Thread(target=one, args=("U", live if a.vs else None)), threading.Thread(target=one, args=("P", live))]
    [t.start() for t in ts]; [t.join() for t in ts]
    U, P = res["U"], res["P"]
    ub = {}
    for it, k, b in U:
        ub.setdefault(k, b)
    # continuity of the raw logs
    print(f"{a.snap} {a.mhz} MHz: unpatched {len(U)} passes (ticks {U[0][1]}..{U[-1][1]}), patched {len(P)} loop tops (ticks {P[0][1]}..{P[-1][1]})")
    its = [it for it, _, _ in P]
    print("  patched log gaps (missed loop tops):", sum(max(0, y - x - 1) for x, y in zip(its, its[1:])))
    its = [it for it, _, _ in U]
    print("  unpatched log gaps:", sum(max(0, y - x - 1) for x, y in zip(its, its[1:])))
    bad, n, ticks, vals = {}, 0, set(), {}
    for it, k, b in P:
        u = ub.get(k)
        if u is None:
            continue
        n += 1; ticks.add(k)
        d = diff_words(u, b)
        if d:
            for g in group(d):
                bad.setdefault((g[0], g[1]), []).append(it)
                if len(vals.setdefault((g[0], g[1]), [])) < 40:
                    vals[(g[0], g[1])].append((it, k, u[g[0]:g[1]].hex(), b[g[0]:g[1]].hex()))
    print(f"compared {n} loop tops over {len(ticks)} distinct world ticks")
    neg = sum(1 for it, k, b in P if ub.get(k + 1) is not None and diff_words(ub[k + 1], b))
    nn = sum(1 for it, k, b in P if ub.get(k + 1) is not None)
    print(f"negative control: patched tick k vs unpatched tick k+1 differs in {neg} of {nn} loop tops")
    rng = sum(1 for it, k, b in P if ub.get(k) is not None and ub[k][0x2DF84:0x2DF88] != b[0x2DF84:0x2DF88])
    print(f"RNG $2df84 differs in {rng} loop tops; RNG value changes over the run: {len(set(b[0x2DF84:0x2DF88] for _, _, b in P))} distinct; season counter $57fec {int.from_bytes(P[0][2][0x57FEC:0x57FEE],'big')}..{int.from_bytes(P[-1][2][0x57FEC:0x57FEE],'big')}")
    # pixel check: the displayed buffer ($2df78) at the FIRST loop top of every tick equals the unpatched frame of that tick (a T pass is the original pass)
    seen_k, same, tot, ptr_only = set(), 0, 0, 0
    for it, k, b in P:
        if k in seen_k or ub.get(k) is None:
            continue
        seen_k.add(k)
        sp = int.from_bytes(b[0x2DF78:0x2DF7C], "big"); su = int.from_bytes(ub[k][0x2DF78:0x2DF7C], "big")
        fp, fu = b[sp:sp + 32000], ub[k][su:su + 32000]
        tot += 1
        if fp == fu:
            same += 1
    print(f"displayed frame at the first loop top of each tick: {same} of {tot} byte-identical to the unpatched frame of that tick")
    mv = sum(1 for i in range(512) if P[0][2][0x51B66 + i*50 + 8:0x51B66 + i*50 + 12] != P[-1][2][0x51B66 + i*50 + 8:0x51B66 + i*50 + 12])
    print(f"men records whose x/z changed first->last loop top: {mv}")
    if not bad:
        print("IDENTICAL (everything in $0-$60000 except MASKS)")
    else:
        for (lo, hi), its in sorted(bad.items())[:60]:
            print(f"DIFF ${lo:x}-${hi:x} in {len(its)} loop tops, first iters {its[:4]}")
            for v in vals[(lo, hi)][:12]:
                print("    iter %d tick %d unpatched %s patched %s" % v)
    return 0 if not bad else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("live")
    r = sub.add_parser("rate"); r.add_argument("snap"); r.add_argument("mhz", type=int); r.add_argument("vbls", type=int)
    r.add_argument("--unpatched", action="store_true")
    i = sub.add_parser("input"); i.add_argument("snap"); i.add_argument("mhz", type=int); i.add_argument("--unpatched", action="store_true")
    q = sub.add_parser("ab"); q.add_argument("snap"); q.add_argument("mhz", type=int); q.add_argument("vbls", type=int)
    q.add_argument("--poke", action="append", default=[])
    q.add_argument("--vs", type=int, default=0, help="compare patched at MHZ against PATCHED at this clock (instead of unpatched)")
    a = ap.parse_args()
    if a.cmd == "live":
        print(build_live())
    elif a.cmd == "rate":
        cmd_rate(a)
    elif a.cmd == "input":
        cmd_input(a)
    elif a.cmd == "ab":
        sys.exit(cmd_ab(a))
