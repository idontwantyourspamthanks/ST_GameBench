#!/usr/bin/env python3
"""HUD lab for Moonshine Racers (MSRHud): per-pass HUD-call cycles, per-pass state, pixel captures, with live pokes (call skips).

    import sys; sys.path.insert(0, 'work/hud'); from hudlab import *
    r = run('race_start', pokes={}, npass=30)               # stock: stage cycles per pass + state per pass
    r = run('race_start', pokes=skip('f22c'), npass=30)      # the call bsr $f22c at $efbc replaced by nop nop
r = {pass: {'stage': {name: cycles}, 'work': cycles}, ...} plus r.state {pass: {addr: byte}}.
Pokes are applied at the first execution of $7a88 (start of the render part of a pass), by a debugger `w`; nothing else is modified.
One Hatari per call (distinct scratch dir from the harness), closed in `finally`.
"""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from msr import Moonshine  # noqa

CYC = 160256
SNAPS = GAME / "work" / "snapshots"
OUT = HERE

# HUD call sites inside $ef7a: name -> (address of the call insn, length)
CALLS = {
    "de1c": (0xEF7E, 6), "f1c0": (0xEF84, 4), "efc6": (0xEF88, 4), "f214": (0xEF8C, 4), "f3b6": (0xEF94, 4),
    "f430": (0xEF98, 4), "f53c": (0xEF9C, 4), "11ef0": (0xEFA0, 6), "f90c": (0xEFA6, 4), "f620": (0xEFAA, 4),
    "f76a": (0xEFAE, 4), "f7f0": (0xEFB2, 4), "de6c": (0xEFB6, 6), "f22c": (0xEFBC, 4), "f134": (0xEFC0, 4),
}
# stage chain: return addresses (stage k = cycles from the previous point to this return)
STAGES = [("start", 0x796A), ("pre_ef7a", 0x7B4C), ("de1c", 0xEF84), ("f1c0", 0xEF88), ("efc6", 0xEF8C), ("f214", 0xEF90),
          ("f3b6", 0xEF98), ("f430", 0xEF9C), ("f53c", 0xEFA0), ("11ef0", 0xEFA6), ("f90c", 0xEFAA), ("f620", 0xEFAE),
          ("f76a", 0xEFB2), ("f7f0", 0xEFB6), ("de6c", 0xEFBC), ("f22c", 0xEFC0), ("f134", 0xEFC4), ("flip", 0xD1CA)]
HUD_STATE = [(0x1000, 1024)]
GATE_STATE = [(0x1000, 1024), (0x29C8, 2872), (0x4500, 2816), (0xDAE6, 4), (0xDAFC, 8), (0x5FF8, 2)]


def snap_path(name):
    p = Path(name)
    return str(p if p.exists() else SNAPS / f"ste1m_{name}.sav")


def skip(*names):
    """pokes {addr: bytes} replacing the named HUD calls by nops."""
    return {CALLS[n][0]: bytes.fromhex("4e71" * (CALLS[n][1] // 2)) for n in names}


def poke_cmds(pokes):
    cmds = []
    for a, b in pokes.items():
        b = bytes(b)
        for k in range(0, len(b), 8):
            cmds.append(f"w ${a + k:x} " + " ".join(f"${x:02x}" for x in b[k:k + 8]))
    return cmds


def _wait_removed(h, start, pat="Removed CPU breakpoint", timeout=300):
    t = time.time()
    while pat not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("breakpoint never hit")
        time.sleep(0.2)
    time.sleep(0.3)


def apply_pokes(h, pokes, at_pc=0x7A88, extra_cmds=(), at_pass=None):
    cmds = poke_cmds(pokes) + list(extra_cmds)
    if not cmds:
        return
    if len(max(cmds, key=len)) > 240:
        raise ValueError("cmd too long")
    f = h.R / "apply.txt"
    f.write_text("\n".join(cmds) + "\n")
    start = len(h._logtext())
    cond = f" && ($100e).w = ${at_pass:x}" if at_pass is not None else ""
    h.cmd(f"hatari-debug b pc = ${at_pc:x}{cond} :trace :once :file {f}")
    _wait_removed(h, start)


def parse_state(log, key=0x100E):
    res = {}
    for ht in log.split("> e VBL")[1:]:
        mem = {}
        mv = re.search(r"#(\d+) \(dec\)", ht)
        if mv: mem[-1] = int(mv.group(1))
        for ln in ht.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
            if m:
                a = int(m.group(1), 16)
                for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))):
                    mem[a + i] = x
        if key in mem:
            kk = (mem[key] << 8) | mem[key + 1]
            if kk in res and mem.get(-1) is not None:   # pass counter wrapped (race restart): keep both, key + 100000 per wrap
                w = 1
                while kk + 100000 * w in res: w += 1
                kk += 100000 * w
            res[kk] = mem
    return res


def run(snap, pokes=None, npass=30, state=None, stages=True, extra_cmds=(), keep=False, tag="h", timeout=1500, at_pass=None, shots_at=(), shotdir=None, live=None, stagelist=None):
    """Restore snap, apply pokes (+ extra debugger cmds) at $7a88, then log `npass` passes of stage cycles and (optional) state ranges."""
    pokes = pokes or {}
    h = Moonshine(snapshot=snap_path(snap))
    res = {}
    stdat = {}
    try:
        time.sleep(1.5)
        if live:
            import msrabtest as ab
            ab.apply_live(h, Path(live), 0x7A88)
            time.sleep(0.4)
        apply_pokes(h, pokes, extra_cmds=extra_cmds, at_pass=at_pass)
        time.sleep(0.4)
        h.debug("b all", 0.3)
        n0 = len(h._logtext())
        for N in shots_at:
            sd = Path(shotdir); sd.mkdir(parents=True, exist_ok=True)
            cf = h.R / f"cap_{N:x}.txt"
            cf.write_text(f"savebin {sd}/s{N:x}_70000.bin $70000 $7d00\nsavebin {sd}/s{N:x}_78000.bin $78000 $7d00\nsavebin {sd}/s{N:x}_1004.bin $1004 4\n")
            h.cmd(f"hatari-debug b pc = $7b86 && ($100e).w = ${N:x} :trace :once :file {cf}")
            time.sleep(0.2)
        if state:
            sf = h.R / "state.txt"
            sf.write_text("e VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in state))
            h.cmd(f"hatari-debug b pc = $7b86 :trace :file {sf}")
            time.sleep(0.3)
        SL = stagelist or STAGES
        if stages:
            pcs = [pc for _, pc in SL]
            for i, pc in enumerate(pcs):
                nxt = pcs[(i + 1) % len(pcs)]
                extra = "m $100e 2\n" if pc == pcs[0] else ""
                (h.R / f"{tag}_{pc:x}.txt").write_text(f"e VBL\ne FrameCycles\n{extra}b pc = ${nxt:x} :trace :once :file {h.R}/{tag}_{nxt:x}.txt\n")
            h.cmd(f"hatari-debug b pc = ${pcs[0]:x} :trace :once :file {h.R}/{tag}_{pcs[0]:x}.txt")
        t0 = time.time()
        while True:
            log = h._logtext()[n0:]
            if stages:
                done = log.count("> e FrameCycles") >= npass * len(SL)
            elif state:
                done = log.count("> e VBL") >= npass
            else:
                done = bool(shots_at) and (Path(shotdir) / f"s{max(shots_at):x}_1004.bin").exists()
            if done or time.time() - t0 > timeout:
                break
            time.sleep(1)
        h.debug("b all", 0.5)
        log = h._logtext()[n0:]
        if state:
            stdat = parse_state(log)
    finally:
        h.close()
    out = _parse_stages(log, SL) if stages else {}
    return Result(out, stdat, log)


class Result(dict):
    def __init__(self, d, state, log):
        super().__init__(d); self.state = state; self.log = log

    def mean(self, key="work", passes=None):
        ks = [k for k in sorted(self) if passes is None or k in passes]
        v = [self[k][key] if key in ("work",) else self[k]["stage"].get(key, 0) for k in ks]
        return sum(v) / max(1, len(v))

    def table(self, skipfirst=0):
        ks = sorted(self)[skipfirst:]
        names = [n for n, _ in STAGES[1:-1]]
        out = {}
        for n in names + ["work"]:
            v = [self[k]["work"] if n == "work" else self[k]["stage"].get(n, 0) for k in ks]
            out[n] = (sum(v) / max(1, len(v)), min(v) if v else 0, max(v) if v else 0)
        return out


def _parse_stages(log, SL=None):
    SL = SL or STAGES
    ev = []
    cur = None; vals = []
    for ln in log.splitlines():
        m = re.match(r"\tpc = \$([0-9a-f]+) :once :trace", ln)
        if m:
            if cur is not None and len(vals) >= 2: ev.append((cur, *vals))
            cur = int(m.group(1), 16); vals = []; continue
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m and cur is not None:
            vals.append(int(m.group(1))); continue
        m = re.match(r"([0-9a-f]{8}):\s+([0-9a-f]{2}) ([0-9a-f]{2})", ln, re.I)
        if m and cur is not None and int(m.group(1), 16) == 0x100E:
            vals.append(int(m.group(2) + m.group(3), 16))
    if cur is not None and len(vals) >= 2: ev.append((cur, *vals))
    raw = [(pc, v[0], v[1], v[2] if len(v) > 2 else None) for pc, *v in ev]
    best = None
    for c0 in sorted({fc for _, _, fc, _ in raw}) + [CYC]:
        t = [(v + (1 if fc < c0 else 0)) * CYC + fc for _, v, fc, _ in raw]
        bad = sum(1 for i in range(1, len(t)) if t[i] < t[i - 1])
        if best is None or bad < best[0]: best = (bad, c0)
    c0 = best[1]
    tt = [(pc, (v + (1 if fc < c0 else 0)) * CYC + fc, p) for pc, v, fc, p in raw]
    pcs = [pc for _, pc in SL]
    names = {pc: n for n, pc in SL}
    res = {}
    i = 0
    while i < len(tt):
        if tt[i][0] == pcs[0] and tt[i][2] is not None:
            k = tt[i][2]
            seq = tt[i:i + len(pcs)]
            if len(seq) == len(pcs) and [s[0] for s in seq] == pcs:
                st = {names[seq[j][0]]: seq[j][1] - seq[j - 1][1] for j in range(1, len(seq))}
                res[k] = {"stage": st, "work": seq[-1][1] - seq[0][1], "violations": best[0]}
                i += len(pcs); continue
        i += 1
    return res


def read_buffers(h_or_none=None):
    pass


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("snap"); ap.add_argument("--skip", nargs="*", default=[]); ap.add_argument("--passes", type=int, default=20)
    ap.add_argument("--state", action="store_true")
    a = ap.parse_args()
    r = run(a.snap, skip(*a.skip), a.passes, state=HUD_STATE if a.state else None)
    print(f"{a.snap} skip={a.skip}: {len(r)} passes")
    for n, (m, lo, hi) in r.table().items():
        print(f"  {n:8s} mean {m:10.0f} min {lo:8d} max {hi:8d}")


# ---------------------------------------------------------------------------------------------------------------- persistence helpers
KEEP = [0x100E, 0x10BA, 0x10C0, 0x10CA, 0x10CE, 0x10D8, 0x11C2, 0x11D9, 0x11DC, 0x10DC, 0x10DE, 0x10E0, 0x10E2, 0x11AB, 0x11AC, 0x11AD, 0x11AE,
        0x11B1, 0x11B2, 0x10F8, 0x10F9, 0x1226, 0x1024, 0x5FF8, 0x130C, 0x11CE, 0x11CF]


def v(m, a, n=2):
    try:
        return int.from_bytes(bytes(m[a + i] for i in range(n)), "big")
    except KeyError:
        return None


def save(r, name):
    d = {str(k): {"stage": x["stage"], "work": x["work"]} for k, x in r.items()}
    st = {}
    for k, m in r.state.items():
        st[str(k)] = {"v": {f"{a:x}": v(m, a, n) for a, n in [(0x10BA, 2), (0x10C0, 2), (0x10CA, 2), (0x10CE, 4), (0x10D8, 4), (0x11C2, 2), (0x11D9, 1), (0x11DC, 1),
                                                               (0x10DC, 2), (0x10DE, 2), (0x10E0, 2), (0x10E2, 2), (0x11AB, 1), (0x11AC, 1), (0x11AD, 1), (0x11AE, 1), (0x11B1, 1),
                                                               (0x11B2, 1), (0x10F8, 1), (0x10F9, 1), (0x1226, 1), (0x1024, 1), (0x5FF8, 2), (0x130C, 2), (0x11CE, 1), (0x11CF, 1)]}}
    (OUT / "res").mkdir(exist_ok=True)
    json.dump({"passes": d, "state": st}, open(OUT / "res" / f"{name}.json", "w"))


def load(name):
    d = json.load(open(OUT / "res" / f"{name}.json"))
    return {int(k): x for k, x in d["passes"].items()}, {int(k): x["v"] for k, x in d["state"].items()}


# ---------------------------------------------------------------------------------------------------------------- poison film (footprints)
FILM_PCS = [0xEF7E, 0xEF84, 0xEF88, 0xEF8C, 0xEF90, 0xEF98, 0xEF9C, 0xEFA0, 0xEFA6, 0xEFAA, 0xEFAE, 0xEFB2, 0xEFB6, 0xEFBC, 0xEFC0, 0xEFC4]
FILM_NAMES = ["de1c", "f1c0", "efc6", "f214", "f3b6", "f430", "f53c", "11ef0", "f90c", "f620", "f76a", "f7f0", "de6c", "f22c", "f134"]  # stage ending at FILM_PCS[1:]


def film(snap, pokes, poison70=0x00, poison78=0xFF, outdir=None, tag="film", plain=False, at_pass=None):
    """One pass: before each HUD call both screen buffers are overwritten with a poison byte ($70000 <- poison70, $78000 <- poison78) and
    after the call both are saved.  A byte of the saved back buffer that differs from the poison was WRITTEN by that call (footprint).
    plain=True: no poison, only the saved buffers after each call (to see the pixel changes)."""
    outdir = Path(outdir or (OUT / "res" / tag)); outdir.mkdir(parents=True, exist_ok=True)
    pf = {}
    for b in (poison70, poison78):
        p = OUT / "res" / f"poison_{b:02x}.bin"
        if not p.exists(): p.write_bytes(bytes([b]) * 32000)
    h = Moonshine(snapshot=snap_path(snap))
    try:
        time.sleep(1.5)
        h.debug("b all", 0.3)
        for i, pc in enumerate(FILM_PCS):
            lines = []
            if i > 0:
                lines += [f"savebin {outdir}/{FILM_NAMES[i - 1]}_70000.bin $70000 $7d00", f"savebin {outdir}/{FILM_NAMES[i - 1]}_78000.bin $78000 $7d00"]
            if i < len(FILM_PCS) - 1:
                if not plain:
                    lines += [f"loadbin {OUT / 'res' / f'poison_{poison70:02x}.bin'} $70000", f"loadbin {OUT / 'res' / f'poison_{poison78:02x}.bin'} $78000"]
                lines += [f"b pc = ${FILM_PCS[i + 1]:x} :trace :once :file {h.R}/{tag}_{FILM_PCS[i + 1]:x}.txt"]
            else:
                lines += ["e VBL"]
            (h.R / f"{tag}_{pc:x}.txt").write_text("\n".join(lines) + "\n")
        # pokes and the arming of the first film stage happen at the same instant (no passes lost in between)
        apply_pokes(h, pokes, at_pass=at_pass, extra_cmds=[f"b pc = ${FILM_PCS[0]:x} :trace :once :file {h.R}/{tag}_{FILM_PCS[0]:x}.txt"])
        t0 = time.time()
        while not (outdir / "f134_78000.bin").exists() and time.time() - t0 < 120:
            time.sleep(0.5)
        time.sleep(1.0)
        h.debug("b all", 0.3)
    finally:
        h.close()
    return outdir


def footprint(outdir, name, poison70=0x00, poison78=0xFF):
    """-> {buffer: (bytes written, bbox (x0,y0,x1,y1) in px (16-px groups), list of rows)} for the stage `name`."""
    res = {}
    for buf, pz in (("70000", poison70), ("78000", poison78)):
        d = (Path(outdir) / f"{name}_{buf}.bin").read_bytes()
        idx = [i for i in range(32000) if d[i] != pz]
        if not idx:
            res[buf] = (0, None); continue
        ys = [i // 160 for i in idx]
        xs = [(i % 160) // 8 * 16 for i in idx]
        res[buf] = (len(idx), (min(xs), min(ys), max(xs) + 15, max(ys)))
    return res


def written(snap, pokes, tag, plain=False, at_pass=None):
    """Footprint of every HUD call in one pass = union of the bytes written, measured with poison 00 and poison ff (both buffers).
    -> {name: {'bytes': n, 'bbox': (x0,y0,x1,y1) px, 'rows': {y: nbytes}}}"""
    sets = {}
    for p in (0x00, 0xFF):
        d = film(snap, pokes, p, p, tag=f"{tag}_{p:02x}", at_pass=at_pass)
        for n in FILM_NAMES:
            w = set()
            for buf in ("70000", "78000"):
                b = (d / f"{n}_{buf}.bin").read_bytes()
                w |= {i for i in range(32000) if b[i] != p} if True else set()
            sets.setdefault(n, []).append(w)
    out = {}
    for n, (w0, wf) in sets.items():
        w = w0 | wf
        if not w:
            out[n] = {"bytes": 0, "bbox": None}; continue
        ys = [i // 160 for i in w]; xs = [(i % 160) // 8 * 16 for i in w]
        out[n] = {"bytes": len(w), "bbox": (min(xs), min(ys), max(xs) + 15, max(ys)), "only00": len(w0), "onlyff": len(wf)}
    return out


SUB = [("start", 0x796A), ("pre_ef7a", 0x7B4C), ("de1c", 0xEF84), ("f1c0", 0xEF88), ("efc6", 0xEF8C), ("f214", 0xEF90), ("f3b6", 0xEF98), ("f430", 0xEF9C),
       ("f53c.sprite", 0xF5BC), ("f53c.mask", 0xF5DE), ("f53c.col", 0xF5E6), ("f53c.hand", 0xF61E), ("f53c", 0xEFA0),
       ("11ef0", 0xEFA6), ("f90c.sprite", 0xF9D6), ("f90c", 0xEFAA), ("f620.tank", 0xF636), ("f620", 0xEFAE), ("f76a", 0xEFB2),
       ("f7f0.sprite", 0xF83E), ("f7f0.col", 0xF848), ("f7f0.needle1", 0xF8C2), ("f7f0.needle2", 0xF8D0), ("f7f0", 0xEFB6), ("de6c", 0xEFBC),
       ("f22c.col", 0xF234), ("f22c.line1", 0xF246), ("f22c.line2", 0xF258), ("f22c.line3", 0xF26A), ("f22c.line4", 0xF278), ("f22c.pre", 0xF350),
       ("f22c.dot1", 0xF376), ("f22c.dot2", 0xF386), ("f22c.dot3", 0xF396), ("f22c.dot4", 0xF3A8), ("f22c.dot5", 0xF3B4), ("f22c", 0xEFC0), ("f134", 0xEFC4), ("flip", 0xD1CA)]


def run_sub(snap, pokes=None, npass=40, stagelist=None, at_pass=None, live=None, timeout=1500):
    """Like run() but every stage pc is a PERSISTENT breakpoint (conditional sub-stages may not hit in a pass without breaking a chain).
    -> {pass: {label: cycles since the previous logged event of the same pass}} (a label that did not fire in a pass is absent)."""
    SL = stagelist or SUB
    h = Moonshine(snapshot=snap_path(snap))
    try:
        time.sleep(1.5)
        if live:
            import msrabtest as ab
            ab.apply_live(h, Path(live), 0x7A88); time.sleep(0.4)
        apply_pokes(h, pokes or {}, at_pass=at_pass)
        time.sleep(0.3)
        h.debug("b all", 0.3)
        n0 = len(h._logtext())
        for name, pc in SL:
            extra = "m $100e 2\n" if pc == SL[0][1] else ""
            (h.R / f"sub_{pc:x}.txt").write_text(f"e VBL\ne FrameCycles\n{extra}")
            h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R}/sub_{pc:x}.txt")
            time.sleep(0.15)
        t0 = time.time()
        while time.time() - t0 < timeout:
            log = h._logtext()[n0:]
            if log.count("> e FrameCycles") >= npass * len(SL) * 0.9 and len(re.findall(r"\$100e", log)) > 0 and log.count("m $100e") > npass:
                break
            time.sleep(1)
        h.debug("b all", 0.5)
        log = h._logtext()[n0:]
    finally:
        h.close()
    ev = []; cur = None; vals = []
    for ln in log.splitlines():
        m = re.match(r"> e VBL", ln)
        m2 = re.match(r"\tpc = \$([0-9a-f]+) :trace :file", ln)
        if m2:
            if cur is not None and len(vals) >= 2: ev.append((cur, *vals))
            cur = int(m2.group(1), 16); vals = []; continue
        mm = re.search(r"#(\d+) \(dec\)", ln)
        if mm and cur is not None: vals.append(int(mm.group(1))); continue
        mm = re.match(r"([0-9a-f]{8}):\s+([0-9a-f]{2}) ([0-9a-f]{2})", ln, re.I)
        if mm and cur is not None and int(mm.group(1), 16) == 0x100E: vals.append(int(mm.group(2) + mm.group(3), 16))
    if cur is not None and len(vals) >= 2: ev.append((cur, *vals))
    best = None
    raw = [(pc, v[0], v[1], v[2] if len(v) > 2 else None) for pc, *v in ev]
    for c0 in sorted({fc for _, _, fc, _ in raw}) + [CYC]:
        t = [(vb + (1 if fc < c0 else 0)) * CYC + fc for _, vb, fc, _ in raw]
        bad = sum(1 for i in range(1, len(t)) if t[i] < t[i - 1])
        if best is None or bad < best[0]: best = (bad, c0)
    c0 = best[1]
    tt = [(pc, (vb + (1 if fc < c0 else 0)) * CYC + fc, p) for pc, vb, fc, p in raw]
    names = {pc: n for n, pc in SL}
    res = {}; cur = None; prev = None
    for pc, t, p in tt:
        if pc == SL[0][1]:
            cur = p; prev = t; res[cur] = {"stage": {}, "start": t}; continue
        if cur is None: continue
        res[cur]["stage"][names[pc]] = t - prev; prev = t
        if pc == SL[-1][1]: res[cur]["work"] = t - res[cur]["start"]
    return {k: v for k, v in res.items() if "work" in v}, best[0]
