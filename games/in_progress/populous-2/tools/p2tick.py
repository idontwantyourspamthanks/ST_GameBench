#!/usr/bin/env python3
"""Gates for the Populous 2 fixed-rate world tick (patches pop2_tick*, work/notes/timing.md).

    python3 tools/p2tick.py ab   SNAP MHZ TURNS [--hz 50|60] [--spin N]   (a) world state by TURN, patched vs unpatched
    python3 tools/p2tick.py rate SNAP MHZ VBLS  [--hz 50|60] [--unpatched] [--spin N]   (b) turns per emulated second from a snapshot
    python3 tools/p2tick.py cold --machine M --tos T --mem KB [--hz 50|60] [--build DIR] [--vbls N]   (b) the same from a cold boot (HD build)
    python3 tools/p2tick.py input SNAP MHZ [--unpatched]                       (c) pointer / scroll / click responsiveness
    python3 tools/p2tick.py clicks SNAP MHZ [--unpatched]                      the click-latch lifetime in passes
    python3 tools/p2tick.py pointer60                                          the 60 Hz pointer trap ($1a6e) with and without pop2_ntsc2
    python3 tools/p2tick.py hz SNAP MHZ TURNS                                  the picture at 60 Hz == the picture at 50 Hz (unpatched + the 60 Hz fix)
    python3 tools/p2tick.py hold SNAP MHZ                                      the pointer-at-(0,0) hold in real time
    python3 tools/p2tick.py snd                                                sound sequencer steps per second at 50 / 60 Hz

SNAP is busy1 or game_start (2 MB STE snapshots in work/snapshots).  --hz 60 pokes the shifter sync register ($ff820a) at the apply flip
in BOTH runs (Hatari then runs 60 VBL/s; the cycles per VBL printed with every rate are the proof).  Emulated seconds = VBL / hz.
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
import p2abtest as AB  # noqa: E402
from stharness import TOS  # noqa: E402

TICKSET = ["pop2_tick", "pop2_tick_render", "pop2_tick_logic", "pop2_tick_flip", "pop2_tick_dot_a", "pop2_tick_dot_b", "pop2_tick_snd", "pop2_tick_anim"]
NTSCSET = ["pop2_ntsc", "pop2_ntsc2"]
WALK = ["test_walk", "test_walk2", "test_walk3"]
D = 0x82800
oACC, oSKIP, oRON, oTICKS, oRPASS, oSPASS, oPPASS, oTPASS = 12, 14, 16, 28, 32, 36, 40, 44
TURN = 0x3979A
TOP = 0x1254E        # `jsr $22f14`: the pass top, before the tick look
AFTER = 0x12554      # first instruction after the look
FLIP = 0x1BFE
APPLYPC = 0x1C04
WORLD = (0x39600, 0xDE00)
BUFS = (0x2300, 0xFA00)
MINIMAP = (0, 0, 144, 72)            # x0, y0, x1, y1: the minimap dots land in x 5..131, y 4..67 ($126e0: x - y + 68, (x + y) / 2 + 4)
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
HEX = re.compile(r"\$([0-9a-fA-F]+) \(hex\)")
_lock = threading.Lock()
WORK = Path("/tmp/p2tick")


def snap_path(s):
    return AB.snap_path(s)


def wait_gone(h, start, timeout=900):
    t = time.time()
    while "Removed CPU breakpoint" not in h._logtext()[start:]:
        if time.time() - t > timeout:
            raise TimeoutError("breakpoint never fired")
        time.sleep(0.3)
    time.sleep(0.4)


def rdb(h, a, n=1):
    out = h.debug(f"m ${a:x} {n}", 0.5)
    bs = bytearray()
    for ln in out.splitlines():
        m = re.match(r"[0-9A-Fa-f]{8}:\s(.*)", ln)
        if m:
            bs += bytes(int(x, 16) for x in m.group(1).split("  ")[0].split())
    return bytes(bs[:n])


def sample_at(h, target, exprs, timeout=900):
    """Debugger `e` values at ONE stop (the first VBL > target): {expr: int}."""
    f = h.R / f"smp{target}.txt"
    f.write_text("".join(f"e {e}\n" for e in exprs))
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {target} :trace :once :file {f}")
    wait_gone(h, start, timeout)
    out = {}
    for m in re.finditer(r"> e (.+)\n(?:  .*\n)*= (.*)", h._logtext()[start:]):
        out[m.group(1)] = int(HEX.search(m.group(2)).group(1), 16)     # CycleCounter prints negative in dec
    return out


def at_flip(h, cmds, pc=APPLYPC, cond=""):
    f = h.R / "atflip.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${pc:x}{cond} :trace :once :file {f}")
    wait_gone(h, start, 300)


def sync_hz(sync: int) -> int:
    return 50 if sync & 2 else 60


# ---------------------------------------------------------------------------------------------------------------------------------
# (b) rate: turns per emulated second
# ---------------------------------------------------------------------------------------------------------------------------------
def counters(patched: bool):
    ex = ["VBL", "CycleCounter", f"(${TURN:x}).l"]
    if patched:
        ex += [f"(${D + o:x}).l" for o in (oTICKS, oTPASS, oRPASS, oSPASS, oPPASS)]
    return ex


def report(tag, s0, s1, ex, hz, patched, extra="", cpu_mhz=None):
    dv = s1["VBL"] - s0["VBL"]
    secs = dv / hz
    cyc = ((s1["CycleCounter"] - s0["CycleCounter"]) & 0xFFFFFFFF) / dv
    if cpu_mhz:
        seen = cpu_mhz * 1e6 / cyc
        extra += f" | refresh seen {seen:.2f} Hz" + ("" if abs(seen - hz) < 0.03 * hz else f"  *** NOT {hz} Hz: the VBL rate did not change, the turns/s above are computed with the wrong clock ***")
    turns = s1[ex[2]] - s0[ex[2]]
    line = f"RESULT {tag}: {dv} VBL = {secs:.2f} s, {cyc:.0f} cycles/VBL, world turns {turns} = {turns / secs:.3f}/s"
    if patched:
        k = [s1[e] - s0[e] for e in ex[3:]]
        line += f" | ticks(D) {k[0]} = {k[0] / secs:.3f}/s; passes T {k[1]} R {k[2]} S {k[3]} P {k[4]}"
    print(line + extra, flush=True)
    return turns / secs


def cmd_rate(a):
    names = ([] if a.unpatched else TICKSET) + (NTSCSET if (a.ntsc and not a.unpatched) else []) + (["test_tickspin"] if a.spin else [])
    live = AB.make_live(names) if names else None
    h = Populous2(snapshot=snap_path(a.snap))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        cmds = (AB.apply_cmds(live) if live else ["e VBL"]) + (["w $ff820a $00"] if a.hz == 60 else []) + ([AB.poke_cmd(f"82700:{a.spin:04x}")] if a.spin else [])
        at_flip(h, cmds)
        h.cmd("hatari-option --fast-forward on")
        time.sleep(1.0)
        sync = rdb(h, 0xFF820A)[0]
        ex = counters(not a.unpatched)
        s0 = sample_at(h, h.vbl() + 60, ex)
        s1 = sample_at(h, s0["VBL"] + a.vbls, ex)
        report(f"{a.snap} {a.mhz} MHz {a.hz} Hz sync ${sync:02x} {'orig' if a.unpatched else 'patched'}{f' +spin {a.spin}' if a.spin else ''}", s0, s1, ex, a.hz, not a.unpatched)
    finally:
        h.close()


# ---------------------------------------------------------------------------------------------------------------------------------
# (b) rate from a cold boot of an HD build
# ---------------------------------------------------------------------------------------------------------------------------------
def cmd_cold(a):
    tos = TOS[a.tos]
    extra = (["--mmu", "true"] if a.machine == "tt" else []) + a.extra.split()
    kw = dict(game_dir=GAME / a.build, machine=a.machine, tos=tos, memsize_kb=a.mem, extra=extra)
    h = Populous2(**kw)
    try:
        t0 = time.time()
        ok = h.boot_to_game()
        sync = rdb(h, 0xFF820A)[0]
        marker = h.marker()
        pc = rdb(h, 0x22F14, 6).hex()
        print(f"boot {time.time() - t0:.0f} s in_play={ok} marker {marker!r} $22f14 {pc} sync $ff820a = ${sync:02x} -> booted at {sync_hz(sync)} Hz", flush=True)
        h.shot(str(GAME / "work" / "shots" / f"tick_{a.tag}.png"))
        patched = pc.startswith("4ef9")
        ex = counters(patched)
        for hz in (a.hz or [sync_hz(sync)]):
            cur = sync_hz(rdb(h, 0xFF820A)[0])
            if hz == 60 and cur != 60:
                h.debug("w $ff820a $00", 0.5)        # the shifter sync register: bit 1 set = 50 Hz, clear = 60 Hz
                time.sleep(1.0)
            elif hz == 50 and cur != 50:
                h.debug("w $ff820a $02", 0.5)
                time.sleep(1.0)
            if hz != sync_hz(sync):
                h.shot(str(GAME / "work" / "shots" / f"tick_{a.tag}_{hz}hz.png"))
            for mhz in a.clocks:
                if mhz:
                    h.set_cpuclock(mhz)
                time.sleep(1.0)
                h.cmd("hatari-option --fast-forward on")
                s0 = sample_at(h, h.vbl() + 60, ex)
                s1 = sample_at(h, s0["VBL"] + a.vbls * hz // 50, ex)
                h.cmd("hatari-option --fast-forward off")
                cpu = mhz or {"st": 8, "ste": 8, "megaste": 8, "tt": 32, "falcon": 16}[a.machine]
                report(f"cold {a.machine} TOS {a.tos} {a.mem} KB {mhz or 'default'} MHz {hz} Hz", s0, s1, ex, hz, patched, cpu_mhz=cpu)
        h.shot(str(GAME / "work" / "shots" / f"tick_{a.tag}_end.png"))
    finally:
        h.close()


# ---------------------------------------------------------------------------------------------------------------------------------
# (a) world state by turn
# ---------------------------------------------------------------------------------------------------------------------------------
def one(snap, t0, live, out: Path, turns, mhz, hz, walk, patched, pokes=()):
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    with _lock:
        h = Populous2(snapshot=snap)
    stop = threading.Event()
    buf = bytearray()
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
                        buf.extend(d)
                    else:
                        time.sleep(0.002)
        rd = threading.Thread(target=drain, daemon=True)
        rd.start()
        time.sleep(1.0)
        if mhz != 8:
            h.set_cpuclock(mhz)
        cmds = AB.apply_cmds(live) + [AB.poke_cmd(p) for p in pokes]
        if hz == 60:
            cmds.append("w $ff820a $00")
        cmds.append(f"w ${AB.PX:x} $00 $a0 $00 $64")
        cmds.append(f"w ${AB.MODE:x} $00 ${3 if walk else 0:02x}")
        vx, vy = (max(0, min(40, v - 8)) for v in (h.peekw(Populous2.VIEW_X), h.peekw(Populous2.VIEW_Y)))
        cmds.append(f"w ${AB.BX:x} $00 ${vx:02x} $00 ${vy:02x}")
        # every pass top: the world
        (R / "top.txt").write_text("\n".join([f"e ${TOP:x}", "e VBL", f"e (${TURN:x}).l", f"savebin {fifo} ${WORLD[0]:x} ${WORLD[1]:x}"]) + "\n")
        cmds.append(f"b pc = ${TOP:x} :trace :file {R / 'top.txt'}")
        # after the look: the kind of the pass
        (R / "aft.txt").write_text("\n".join([f"e ${AFTER:x}", "e VBL", f"e (${TURN:x}).l", f"e (${D + oSKIP:x}).w", f"e (${D + oRON:x}).w", "e CycleCounter"]) + "\n")
        cmds.append(f"b pc = ${AFTER:x} :trace :file {R / 'aft.txt'}")
        # every flip: the frame
        (R / "cap.txt").write_text("\n".join([f"e ${FLIP:x}", "e VBL", f"e (${TURN:x}).l", f"e (${D + oRON:x}).w", "e ($392e0).l", "e ($393fa).w", "e ($393fc).w",
                                              f"savebin {fifo} ${BUFS[0]:x} ${BUFS[1]:x}"]) + "\n")
        cmds.append(f"b pc = ${FLIP:x} :trace :file {R / 'cap.txt'}")
        (R / "cell.txt").write_text(f"e $1f74c\ne (${TURN:x}).l\n")
        cmds.append(f"b pc = $1f74c :trace :file {R / 'cell.txt'}")      # the logic redraws a minimap cell of the clean background ($1f6e0)
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {out}/end.flag $0 2\ne VBL\n")
        cmds.append(f"b pc = ${TOP:x} && (${TURN:x}).l = {t0 + turns} :trace :once :file {end}")
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        for c in cmds:
            if len(c) > 235:
                raise ValueError(f"debugger command line too long: {c[:80]}...")
        if h.peekl(TURN) >= t0:
            raise ValueError(f"turn {t0} already passed")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${APPLYPC:x} && (${TURN:x}).l = {t0} :trace :once :file {app}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (out / "end.flag").exists():
            if time.time() - t > 1500:
                raise TimeoutError(f"run did not complete; log tail:\n{h._logtext()[-1500:]}")
            time.sleep(0.5)
        time.sleep(1.5)
        text = h._logtext()[start:]
        (out / "log.txt").write_text(text)
    finally:
        stop.set()
        if rd:
            rd.join()
        h.close()
    tops, kinds, flips, cells = [], [], [], set()
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in NUM.findall(blk)]
        if not m:
            continue
        if m[0] == TOP and len(m) >= 3:
            tops.append(m[1:3])
        elif m[0] == AFTER and len(m) >= 6:
            kinds.append(m[1:6])
        elif m[0] == FLIP and len(m) >= 7:
            flips.append(m[1:7])
        elif m[0] == 0x1F74C and len(m) >= 2:
            cells.add(m[1])
    pos = 0
    TW, TF = WORLD[1], BUFS[1]
    # the stream order is the order of the hits that carry a savebin: tops and flips interleaved as they happened -> rebuild it from the log order
    order = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in NUM.findall(blk)]
        if m and m[0] == TOP and len(m) >= 3:
            order.append(("top", m[1], m[2]))
        elif m and m[0] == FLIP and len(m) >= 7:
            order.append(("flip", *m[1:7]))
    recs = dict(tops=[], flips=[], kinds=kinds, cells=cells)
    for o in order:
        need = TW if o[0] == "top" else TF
        if pos + need > len(buf):
            break
        s = bytes(buf[pos:pos + need])
        pos += need
        if o[0] == "top":
            recs["tops"].append(dict(vbl=o[1], turn=o[2], world=s, hw=hashlib.md5(s).hexdigest()))
        else:
            _, vbl, turn, ron, back, x, y = o
            assert back in (0x2300, 0xA000), hex(back)
            sb = s[back - BUFS[0]:back - BUFS[0] + 32000]
            recs["flips"].append(dict(vbl=vbl, turn=turn, ron=ron, x=x, y=y, sb=sb, hb=hashlib.md5(sb).hexdigest()))
    return recs


def diff_ranges(a: bytes, b: bytes, base: int, gap=8):
    out, cur = [], None
    for i in range(min(len(a), len(b))):
        if a[i] != b[i]:
            if cur and i - cur[1] <= gap:
                cur[1] = i + 1
            else:
                if cur:
                    out.append(tuple(cur))
                cur = [i, i + 1]
    if cur:
        out.append(tuple(cur))
    return [(base + s, base + e) for s, e in out]


# UI / render-derived scratch, not world state: it follows the passes that ran the render and the UI (a catch-up pass runs neither):
MASKS = [(0x3962E, 0x39630),       # hover flag the render stage copies from $3e7a4 ($125aa)
         (0x3E7A2, 0x3E7AA),       # hover cell computed by the UI stage ($12fca-$1306c), cleared at its end ($12f6e)
         (0x47149, 0x4714A),       # $4b(player): "this player's unit was drawn" bits, bset by the sprite code ($2081a $20914 $20aa0), read by the UI only
         (0x47283, 0x47284)]


def mask_world(w: bytes) -> bytes:
    b = bytearray(w)
    for s, e in MASKS:
        b[s - WORLD[0]:e - WORLD[0]] = bytes(e - s)
    return bytes(b)


def mask_minimap(fr: bytes) -> bytes:
    """Screen buffer with the minimap rectangle zeroed (16-px groups, 4 planes: 8 bytes per 16 px)."""
    b = bytearray(fr)
    x0, y0, x1, y1 = MINIMAP
    for y in range(y0, y1):
        b[y * 160 + (x0 // 16) * 8: y * 160 + ((x1 + 15) // 16) * 8] = bytes(((x1 + 15) // 16 - x0 // 16) * 8)
    return bytes(b)


def cmd_ab(a):
    WORK.mkdir(exist_ok=True)
    base = WALK + (["test_tickspin"] if a.spin else []) + (NTSCSET if a.hz == 60 else [])      # at 60 Hz both runs carry the 60 Hz fix (the walk drives the pointer below y = 184)
    bl = AB.make_live(base)
    pl = AB.make_live(base + TICKSET)
    sp = snap_path(a.snap)
    t0 = AB.start_turn_for(sp)
    if a.spin:
        a.both_poke = list(a.both_poke) + [f"82700:{a.spin:04x}"]      # SPINN: N dbra iterations (10 cycles each) at the top of every pass in BOTH runs
    print(f"base {' '.join(base)}\npatched +{' '.join(TICKSET)}\nsnapshot {a.snap} turn {t0}, {a.turns} turns, {a.mhz} MHz, {a.hz} Hz", flush=True)
    with ThreadPoolExecutor(2) as ex:
        fb = ex.submit(one, sp, t0, bl, WORK / f"b_{sp.stem}_{a.mhz}", a.turns, a.mhz, a.hz, not a.no_walk, False, pokes=tuple(a.both_poke))
        fp = ex.submit(one, sp, t0, pl, WORK / f"p_{sp.stem}_{a.mhz}", a.turns, a.mhz, a.hz, not a.no_walk and not a.neg, True, pokes=tuple(a.both_poke) + tuple(a.poke))
        B, P = fb.result(), fp.result()
    if a.watch:
        for nm, R_ in (("base", B), ("patched", P)):
            print(f"  {nm} bytes at ${a.watch:x}:")
            for r in R_["tops"][:24]:
                print(f"    turn {r['turn']} VBL {r['vbl']}: {r['world'][a.watch - WORLD[0]:a.watch - WORLD[0] + 16].hex()}")
    bw = {}
    for r in B["tops"]:
        bw.setdefault(r["turn"], r)
    notes, ok = [], True
    ncmp = nmis = 0
    first = P["tops"][0]["turn"] if P["tops"] else 0
    per_turn = {}
    for r in P["tops"]:
        per_turn[r["turn"]] = per_turn.get(r["turn"], 0) + 1
        if r["turn"] <= first + 1 or r["turn"] not in bw:
            continue
        ncmp += 1
        if mask_world(r["world"]) != mask_world(bw[r["turn"]]["world"]):
            nmis += 1
            ok = False
            if nmis <= 3:
                rg = diff_ranges(mask_world(bw[r["turn"]]["world"]), mask_world(r["world"]), WORLD[0])
                vals = [(hex(s_), bw[r['turn']]['world'][s_ - WORLD[0]:e_ - WORLD[0]][:8].hex(), r['world'][s_ - WORLD[0]:e_ - WORLD[0]][:8].hex()) for s_, e_ in rg[:6]]
                notes.append(f"  WORLD DIFFER at pass top, turn {r['turn']} (VBL {r['vbl']}): {len(rg)} ranges, first (addr, unpatched, patched) {vals}")
    bf = {}
    for r in B["flips"]:
        bf.setdefault(r["turn"], r)
    nf = nfm = nr = nrm = 0
    tf, rf = {}, {}
    for r in P["flips"]:
        (rf if r["ron"] else tf).setdefault(r["turn"], []).append(r)
    # the hover highlight in a frame comes from the UI stage of the PREVIOUS pass; a turn pass that follows catch-up passes sees a stale one
    after_s = set()
    kk = P["kinds"]
    for i in range(1, len(kk)):
        if kk[i - 1][2] and not kk[i][2] and not kk[i][3]:        # S, then a T pass
            after_s.add(kk[i][1])
    nfs = 0
    for k, lst in sorted(tf.items()):
        if k <= first + 1 or k not in bf:
            continue
        if k in after_s:
            nfs += 1
            continue
        nf += 1
        if lst[0]["hb"] != bf[k]["hb"]:
            nfm += 1
            ok = False
            if nfm <= 3:
                notes.append(f"  T-FRAME DIFFER turn {k}: " + AB.diff_desc(bf[k]["sb"], lst[0]["sb"]))
    # R frames: stable (two R frames of one turn equal), and the minimap of an R frame == the minimap of the T frame of its turn
    nrs = nrsm = nmm = nmmm = ncell = 0
    for k, lst in sorted(rf.items()):
        if k <= first + 1:
            continue
        for x, y in zip(lst, lst[1:]):
            nrs += 1
            if x["hb"] != y["hb"]:
                nrsm += 1
                ok = False
                if nrsm <= 3:
                    notes.append(f"  R-FRAME UNSTABLE turn {k}: " + AB.diff_desc(x["sb"], y["sb"]))
        if k in tf and k in P["cells"]:
            ncell += 1                         # the logic of this turn redrew a minimap cell of the clean background: the R frame legitimately differs
        elif k in tf:
            def crop(fr):
                x0, y0, x1, y1 = MINIMAP
                return b"".join(fr[y * 160 + (x0 // 16) * 8: y * 160 + ((x1 + 15) // 16) * 8] for y in range(y0, y1))
            for x in lst:
                nmm += 1
                if crop(x["sb"]) != crop(tf[k][0]["sb"]):
                    nmmm += 1
                    ok = False
                    if nmmm <= 3:
                        notes.append(f"  R MINIMAP != T MINIMAP turn {k}")
                        if a.dump:
                            Path(a.dump).mkdir(parents=True, exist_ok=True)
                            (Path(a.dump) / f"t{k}_T.bin").write_bytes(tf[k][0]["sb"])
                            (Path(a.dump) / f"t{k}_R{lst.index(x)}.bin").write_bytes(x["sb"])
    kinds = P["kinds"]
    kc = {"T": 0, "S": 0, "R": 0, "P": 0}
    for _, _, sk, ro, _ in kinds:
        kc["S" if sk else "R" if ro else "T"] += 1
    emul = (P["tops"][-1]["vbl"] - P["tops"][0]["vbl"]) / a.hz if len(P["tops"]) > 1 else 0
    tr = (P["tops"][-1]["turn"] - P["tops"][0]["turn"]) / emul if emul else 0
    ber = (B["tops"][-1]["turn"] - B["tops"][0]["turn"]) / ((B["tops"][-1]["vbl"] - B["tops"][0]["vbl"]) / a.hz) if len(B["tops"]) > 1 else 0
    print(f"{a.snap} @{a.mhz} MHz {a.hz} Hz: {'IDENTICAL' if ok else 'DIFFER'} | world at pass tops: {ncmp} compared ({nmis} differ) over {len({r['turn'] for r in P['tops']})} turns, "
          f"max {max(per_turn.values()) if per_turn else 0} tops/turn | T frames {nf} compared ({nfm} differ; {nfs} excluded: hover highlight stale after catch-up passes) | R frames: {sum(len(v) for v in rf.values())} "
          f"({nrs} stability pairs, {nrsm} unstable; {nmm} minimap compares, {nmmm} differ; {ncell} turns excluded: minimap cell redrawn by the logic) | pass kinds T {kc['T']} R {kc['R']} S {kc['S']} | "
          f"turns/s base {ber:.3f} patched {tr:.3f}", flush=True)
    for n in notes[:10]:
        print(n)
    if ncmp < 10 or nf < 5:
        ok = False
        print("  TOO FEW TURNS COMPARED")
    sys.exit(0 if ok else 1)


def cmd_hz(a):
    """The picture at 60 Hz is the picture at 50 Hz: the UNPATCHED game (plus the 60 Hz fix pop2_ntsc2 and the walk driver) run at 50 and at 60 Hz from the
    same snapshot; the rendered frame (back buffer at the flip) and the world are compared turn by turn."""
    WORK.mkdir(exist_ok=True)
    base = WALK + NTSCSET
    live = AB.make_live(base)
    sp = snap_path(a.snap)
    t0 = AB.start_turn_for(sp)
    with ThreadPoolExecutor(2) as ex:
        f50 = ex.submit(one, sp, t0, live, WORK / f"h50_{sp.stem}", a.turns, a.mhz, 50, True, False)
        f60 = ex.submit(one, sp, t0, live, WORK / f"h60_{sp.stem}", a.turns, a.mhz, 60, True, False)
        A, B = f50.result(), f60.result()
    aw = {}
    for r in A["tops"]:
        aw.setdefault(r["turn"], r)
    af = {}
    for r in A["flips"]:
        af.setdefault(r["turn"], r)
    nw = nwm = nf = nfm = 0
    notes = []
    seen = set()
    for r in B["tops"]:
        if r["turn"] in seen or r["turn"] <= t0 + 1 or r["turn"] not in aw:
            continue
        seen.add(r["turn"])
        nw += 1
        if mask_world(r["world"]) != mask_world(aw[r["turn"]]["world"]):
            nwm += 1
            if nwm <= 3:
                rg = diff_ranges(mask_world(aw[r["turn"]]["world"]), mask_world(r["world"]), WORLD[0])
                notes.append(f"  WORLD DIFFER turn {r['turn']}: {[(hex(x), hex(y)) for x, y in rg[:6]]}")
    seen = set()
    for r in B["flips"]:
        if r["turn"] in seen or r["turn"] <= t0 + 1 or r["turn"] not in af:
            continue
        seen.add(r["turn"])
        nf += 1
        if r["hb"] != af[r["turn"]]["hb"]:
            nfm += 1
            if nfm <= 3:
                notes.append(f"  FRAME DIFFER turn {r['turn']}: " + AB.diff_desc(af[r["turn"]]["sb"], r["sb"]))
    ok = nw >= 20 and nf >= 20 and not nwm and not nfm
    v50 = (A["tops"][-1]["vbl"] - A["tops"][0]["vbl"]) if len(A["tops"]) > 1 else 0
    v60 = (B["tops"][-1]["vbl"] - B["tops"][0]["vbl"]) if len(B["tops"]) > 1 else 0
    print(f"{a.snap} @{a.mhz} MHz unpatched, 50 Hz vs 60 Hz: {'IDENTICAL' if ok else 'DIFFER'} | world per turn {nw} compared ({nwm} differ) | rendered frame per turn {nf} compared ({nfm} differ) | "
          f"window {v50} VBL at 50 Hz = {v50 / 50:.2f} s, {v60} VBL at 60 Hz = {v60 / 60:.2f} s")
    for n in notes:
        print(n)
    sys.exit(0 if ok else 1)


def cmd_pointer60(a):
    """The 60 Hz trap: busy1 with the sync register poked to 60 Hz and the host pointer moved to the bottom edge (ST y 199).  orig60 = the untouched game
    (the VBL handler jumps to the RAM zero-fill at $201c), fix60 = pop2_ntsc + pop2_ntsc2 applied live, orig50 = the untouched game at 50 Hz."""
    for variant in ("orig60", "fix60", "orig50"):
        h = Populous2(snapshot=snap_path("busy1"))
        try:
            time.sleep(1)
            if variant != "orig50":
                h.debug("w $ff820a $00")
                time.sleep(0.5)
            if variant == "fix60":
                live = AB.make_live(NTSCSET)
                for c in AB.apply_cmds(live):
                    h.debug(c, 0.5)
            print(f"== {variant}: sync ${h.peekw(0xFF820A) >> 8:02x}")
            h.rel(0, 260)
            time.sleep(1.5)
            t1 = h.peekw(h.TURN)
            print(f"   pointer x,y = {h.peekw(0x393FA)},{h.peekw(0x393FC)}, turn {t1}")
            time.sleep(2)
            print(f"   2 s later: turn {h.peekw(h.TURN)}, vector $70 = ${h.peekl(0x70):x} (the game's VBL handler is $18fa), $1a6e = ${h.peekw(0x1A6E):04x}")
            print(f"   screenshot {h.shot(str(GAME / 'work' / 'shots' / f'ptr60_{variant}.png'))}")
            print("   log: " + str([ln for ln in h._logtext().splitlines() if "Bus" in ln or "halt" in ln.lower()][:3]))
        finally:
            h.close()


def cmd_snd(a):
    """Sound sequencer steps ($2b29a, called once per VBL by the handler while $2cade is set) per VBL: the original runs it every VBL, so 20 % fast at 60 Hz;
    pop2_tick_snd steps it in 1/300 s units (every VBL at 50 Hz, five of six at 60 Hz)."""
    for hz in (50, 60):
        for patched in (False, True):
            names = (["pop2_tick_snd"] if patched else []) + NTSCSET
            live = AB.make_live(names)
            h = Populous2(snapshot=snap_path("busy1"))
            try:
                time.sleep(1.5)
                at_flip(h, AB.apply_cmds(live) + (["w $ff820a $00"] if hz == 60 else []))
                time.sleep(1.0)
                f = h.R / "snd.txt"
                f.write_text("e VBL\n")
                h.debug("b all", 0.3)
                start = len(h._logtext())
                h.cmd(f"hatari-debug b pc = $2b29a :trace :file {f}")
                time.sleep(0.4)
                h.cmd("hatari-option --fast-forward on")
                time.sleep(6)
                h.cmd("hatari-option --fast-forward off")
                h.debug("b all", 0.5)
                vb = []
                for blk in h._logtext()[start:].split("CPU breakpoint condition(s) matched")[1:]:
                    m = [int(v) for v in NUM.findall(blk)]
                    if m:
                        vb.append(m[-1] if len(m) == 1 else m[1])
                span = vb[-1] - vb[0]
                print(f"{hz} Hz {'patched' if patched else 'orig   '}: {len(vb) - 1} sequencer steps in {span} VBL = {(len(vb) - 1) / span:.4f} per VBL = {(len(vb) - 1) / span * hz:.2f} steps per second")
            finally:
                h.close()


def cmd_hold(a):
    """The pointer-at-(0,0) hold ($22f14 `cmpi.l #8,$392d4`: no pass shorter than 9 VBL while the pointer sits in the top-left corner): the host pointer is homed
    (game pointer (0,0)), then passes and turns are counted over a window.  Original: one turn per pass, passes >= 9 VBL apart (5.5 turns/s at 50 Hz).
    Tick: the hold is 54 units (9 VBL at 50 Hz, 11 at 60 Hz) between UI passes, catch-up passes still bring the world to 6.25 turns/s."""
    for hz in (50, 60):
        for patched in (False, True):
            names = (TICKSET if patched else []) + NTSCSET
            live = AB.make_live(names)
            h = Populous2(snapshot=snap_path(a.snap))
            try:
                time.sleep(1.5)
                if a.mhz != 8:
                    h.set_cpuclock(a.mhz)
                at_flip(h, AB.apply_cmds(live) + (["w $ff820a $00"] if hz == 60 else []))
                h.home()
                time.sleep(1.0)
                x, y = h.peekw(0x393FA), h.peekw(0x393FC)
                h.cmd("hatari-option --fast-forward on")
                ex = counters(patched)
                s0 = sample_at(h, h.vbl() + 60, ex)
                s1 = sample_at(h, s0["VBL"] + 3000, ex)
                h.cmd("hatari-option --fast-forward off")
                dv = s1["VBL"] - s0["VBL"]
                secs = dv / hz
                turns = s1[ex[2]] - s0[ex[2]]
                line = f"{hz} Hz {'patched' if patched else 'orig   '} {a.snap} {a.mhz} MHz, pointer at ({x},{y}): {dv} VBL = {secs:.1f} s, world turns {turns} = {turns / secs:.3f}/s"
                if patched:
                    k = [s1[e] - s0[e] for e in ex[3:]]
                    line += f"; UI passes (T+R) {k[1] + k[2]} = one per {dv / (k[1] + k[2]):.2f} VBL; catch-up passes S {k[3]}"
                print(line, flush=True)
            finally:
                h.close()


# ---------------------------------------------------------------------------------------------------------------------------------
# the click-latch lifetime in passes
# ---------------------------------------------------------------------------------------------------------------------------------
def cmd_clicks(a):
    """At the pass top of turn t1 poke both click latches ($39402/$39404 = 1) and the stamp $3940a = t1 (what the VBL handler does for a click
    made just before this pass), then list, for the following passes, the latch values after the pass-top look ($12554) and the pass kind.
    The original clears them at the top of the second pass after the click ($22f84); with --force-s the tick is made to run catch-up passes."""
    names = [] if a.unpatched else TICKSET
    live = AB.make_live(names) if names else None
    h = Populous2(snapshot=snap_path(a.snap))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        t0 = h.peekl(TURN) + 20
        R = h.R
        cmds = AB.apply_cmds(live) if live else ["e VBL"]
        t1 = t0 + 4
        poke = [f"w $39402 $00 $01", f"w $39404 $00 $01", "w $3940a $00 $00 ${:02x} ${:02x}".format((t1 >> 8) & 255, t1 & 255)]
        if a.force_s and not a.unpatched:
            poke.append(f"w ${D + oACC:x} $00 $8c")
        (R / "poke.txt").write_text("\n".join(poke) + "\n")
        (R / "obs.txt").write_text("\n".join(["e $12554", "e VBL", f"e (${TURN:x}).l", f"e (${D + oSKIP:x}).w", f"e (${D + oRON:x}).w", "e ($39402).w", "e ($39404).w"]) + "\n")
        cmds.append(f"b pc = $12554 :trace :file {R / 'obs.txt'}")
        cmds.append(f"b pc = ${TOP:x} && (${TURN:x}).l = {t1} :trace :once :file {R / 'poke.txt'}")
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {R}/end.flag $0 2\n")
        cmds.append(f"b pc = ${TOP:x} && (${TURN:x}).l = {t1 + 7} :trace :once :file {end}")
        (R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${APPLYPC:x} && (${TURN:x}).l = {t0} :trace :once :file {R / 'apply.txt'}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (R / "end.flag").exists():
            if time.time() - t > 300:
                raise TimeoutError
            time.sleep(0.3)
        time.sleep(1.0)
        text = h._logtext()[start:]
    finally:
        h.close()
    rows = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in NUM.findall(blk)]
        if len(m) >= 7 and m[0] == AFTER:
            rows.append(m[1:7])
    print(f"{'orig' if a.unpatched else 'patched'}{' (forced catch-up)' if a.force_s else ''} {a.snap} {a.mhz} MHz: poke at the top of the pass that starts turn {t1 + 1} (stamp = {t1}); per pass after its look: VBL turn kind latch402 latch404")
    on = False
    for vbl, turn, sk, ro, l2, l4 in rows:
        if turn >= t1:
            on = True
        if on and turn <= t1 + 7:
            print(f"   VBL {vbl} turn {turn} kind {'S' if sk else 'R' if ro else 'T'} latch {l2} {l4}")


# ---------------------------------------------------------------------------------------------------------------------------------
# (c) responsiveness
# ---------------------------------------------------------------------------------------------------------------------------------
def watch_hits(h, addr, action, window, exprs=("VBL",), width="w"):
    """Change-watch on `addr`; run `action()` in a thread; hit times (s after the action started) and the values of `exprs` at each hit."""
    h.debug("b all", 0.3)
    f = h.R / "wh.txt"
    f.write_text("".join(f"e {e}\n" for e in exprs))
    h.cmd(f"hatari-debug b (${addr:x}).{width} ! (${addr:x}).{width} :trace :file {f}")
    time.sleep(0.4)
    s0 = len(h._logtext())
    t0 = time.time()
    seen = []
    th = threading.Thread(target=action, daemon=True)
    th.start()
    while time.time() - t0 < window:
        n = h._logtext()[s0:].count("Reading debugger commands")
        while len(seen) < n:
            seen.append(time.time() - t0)
        time.sleep(0.01)
    th.join()
    h.debug("b all", 0.3)
    text = h._logtext()[s0:]
    vals = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        vals.append([int(HEX.search(x).group(1), 16) for x in re.findall(r"= .*\(hex\)", blk)][:len(exprs)])
    return seen, vals


def cmd_input(a):
    names = [] if a.unpatched else TICKSET
    live = AB.make_live(names) if names else None
    h = Populous2(snapshot=snap_path(a.snap))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        if live:
            at_flip(h, AB.apply_cmds(live))
        time.sleep(1.5)
        ex = ["VBL", f"(${TURN:x}).l"] + ([] if a.unpatched else [f"(${D + oRON:x}).w"])
        # pointer: 30 host px to the right
        seen, vals = watch_hits(h, 0x393FA, lambda: h.rel(30, 0), 1.5, ex)
        print(f"{'orig' if a.unpatched else 'patched'} {a.snap} {a.mhz} MHz: pointer: first $393fa change {seen[0] * 1000:.0f} ms after the move ({len(seen)} change(s))" if seen else "pointer: no change")
        # scroll: Right held 2 s
        seen, vals = watch_hits(h, Populous2.VIEW_X, lambda: h.key("Right", 2.0), 2.6, ex)
        if seen:
            vb = [v[0] for v in vals]
            tn = [v[1] for v in vals]
            span = (vb[-1] - vb[0]) / 50.0 if len(vb) > 1 else 0
            ron = sum(1 for v in vals if len(v) > 2 and v[2]) if not a.unpatched else 0
            print(f"   scroll Right held 2 s: {len(seen)} view steps, first after {seen[0] * 1000:.0f} ms, {(len(vb) - 1) / span if span else 0:.1f} steps/s (emulated); world turns during the steps {tn[-1] - tn[0]} "
                  f"= {(tn[-1] - tn[0]) / span if span else 0:.2f}/s" + ("" if a.unpatched else f"; steps made in render-only passes (turn waiting): {ron}"))
        else:
            print("   scroll: no step")
    finally:
        h.close()

# ---------------------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("ab")
    q.add_argument("snap"); q.add_argument("mhz", type=int); q.add_argument("turns", type=int)
    q.add_argument("--hz", type=int, choices=[50, 60], default=50)
    q.add_argument("--spin", type=int, default=0, help="both runs carry test_tickspin with this many dbra iterations (10 cycles each) burnt at the top of every pass: slow passes, so S passes happen (12800 = 0.8 VBL at 8 MHz)")
    q.add_argument("--no-walk", action="store_true"); q.add_argument("--neg", action="store_true")
    q.add_argument("--watch", type=lambda v: int(v, 16), help="print the 16 bytes at this address (hex) at every pass top of both runs, per turn")
    q.add_argument("--dump", help="directory for the frames of failing minimap compares")
    q.add_argument("--poke", action="append", default=[], help="ADDR:HEXBYTES in the patched run only, at the apply flip (negative controls)")
    q.add_argument("--both-poke", action="append", default=[], help="ADDR:HEXBYTES in BOTH runs, at the apply flip (400ee:0a turns a building into an object of kind $0a)")
    r = sub.add_parser("rate")
    r.add_argument("snap"); r.add_argument("mhz", type=int); r.add_argument("vbls", type=int)
    r.add_argument("--hz", type=int, choices=[50, 60], default=50)
    r.add_argument("--unpatched", action="store_true"); r.add_argument("--spin", type=int, default=0)
    r.add_argument("--ntsc", action="store_true", help="add pop2_ntsc/pop2_ntsc2 to the patched set (at 60 Hz they are what keeps the pointer alive)")
    c = sub.add_parser("cold")
    c.add_argument("--machine", default="ste"); c.add_argument("--tos", default="1.62"); c.add_argument("--mem", type=int, default=2048)
    c.add_argument("--hz", type=int, nargs="*", choices=[50, 60], default=None, help="refresh rates to measure at (the others are forced by poking $ff820a)"); c.add_argument("--build", default="build/tick_hd")
    c.add_argument("--vbls", type=int, default=2000); c.add_argument("--tag", default="cold")
    c.add_argument("--clocks", nargs="*", type=int, default=[8, 16], help="CPU clocks to measure at (0 = the machine's default)")
    c.add_argument("--extra", default="", help="extra Hatari options as one string, e.g. \"--language us\"")
    sub.add_parser("pointer60")
    hp = sub.add_parser("hold")
    hp.add_argument("snap"); hp.add_argument("mhz", type=int)
    sub.add_parser("snd")
    z = sub.add_parser("hz")
    z.add_argument("snap"); z.add_argument("mhz", type=int); z.add_argument("turns", type=int)
    k = sub.add_parser("clicks")
    k.add_argument("snap"); k.add_argument("mhz", type=int); k.add_argument("--unpatched", action="store_true"); k.add_argument("--force-s", action="store_true")
    i = sub.add_parser("input")
    i.add_argument("snap"); i.add_argument("mhz", type=int); i.add_argument("--unpatched", action="store_true")
    a = ap.parse_args()
    {"ab": cmd_ab, "rate": cmd_rate, "cold": cmd_cold, "clicks": cmd_clicks, "input": cmd_input, "hz": cmd_hz, "pointer60": cmd_pointer60, "snd": cmd_snd, "hold": cmd_hold}[a.cmd](a)


if __name__ == "__main__":
    main()
