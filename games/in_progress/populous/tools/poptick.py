#!/usr/bin/env python3
"""Gates for the Populous fixed-rate world tick (patches pop_tick*, work/notes/timing.md).  Modelled on populous-2/tools/p2tick.py.

    python3 tools/poptick.py ab    SNAP MHZ TURNS [--hz 50|60] [--spin N] [--still] [--cmdturn K] [--neg ...]   (a) world state by TURN, patched vs unpatched
    python3 tools/poptick.py rate  SNAP MHZ VBLS  [--hz 50|60] [--unpatched] [--spin N] [--defaults]       (b) turns per emulated second from a snapshot
    python3 tools/poptick.py cold  --machine M --tos T --mem KB [--hz 50|60 ...] [--build DIR]              (b) the same from a cold boot (HD or floppy build)
    python3 tools/poptick.py input SNAP MHZ [--unpatched]                                                   (c) pointer / scroll responsiveness
    python3 tools/poptick.py clicks SNAP MHZ                                                               a fresh click latch survives render-only passes and is taken by the next turn pass

SNAP is busy_castles, busy_quake_volcano or genesis_start (1 MB STE snapshots in work/snapshots).  --hz 60 pokes the shifter sync register ($ff820a) at the apply
point in BOTH runs (Hatari then runs 60 VBL/s; the cycles per VBL printed with every rate are the proof).  Emulated seconds = VBL / hz.
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
from populous import Populous  # noqa: E402
from stharness import TOS  # noqa: E402

TICKSET = ["pop_tick", "pop_tick_render", "pop_tick_logic", "pop_tick_flip", "pop_tick_cmd", "pop_tick_dot"]
DEFAULTS = ["pop_noprot", "pop_credit", "pop_land_mul", "pop_land_score", "pop_ptr", "pop_bgcopy", "pop_fal_ym", "pop_fal_ym_demo"]
RELEASE = DEFAULTS + ["pop_ptrfix", "pop_keys", "pop_keys2", "pop_keys3", "pop_keys4", "pop_tooltip"]    # the release set minus the tick (PopRelease)
WALK = ["test_pwalk"]
D = 0xC6000
oACC, oSKIP, oRON, oREC, oFLAGS, oTICKS, oRPASS, oSPASS, oPPASS, oTPASS = 12, 14, 16, 18, 20, 28, 32, 36, 40, 44
MODE, BX, BY, SPINN = 0xC6F40, 0xC6F42, 0xC6F44, 0xC6F46
TURN = 0x3C506
TOP = 0xB632          # the pass top: before the tick's look
KIND = 0xB6F4         # after the look, T / S / P / R all pass here
APPLYPC = 0xB806      # `jsr $db8a`: not a site, not about to execute a patched instruction
FLIP = 0x16F16
AFTERFLIP = 0xB946
RENDERED = 0xB800     # the render stage is done, the world block is next
WORLD = (0x21100, 0x1C700)           # $21100-$3d7ff, as popabtest
BUFS = (0x4F500, 64000)
MINIMAP = (0, 0, 144, 72)
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
HEX = re.compile(r"\$([0-9a-fA-F]+) \(hex\)")
WORKD = Path("/tmp/poptick")
SNAP = GAME / "work" / "snapshots"
_lock = threading.Lock()
SNAPS = ["busy_castles", "busy_quake_volcano", "genesis_start"]


def snap_path(s):
    p = Path(s)
    return p if p.exists() else SNAP / (s if s.endswith(".sav") else s + ".sav")


# ---------------------------------------------------------------------------------------------------------------------------------
# live images
# ---------------------------------------------------------------------------------------------------------------------------------
def make_live(names):
    tag = hashlib.md5(("+".join(names) + str(max((p.stat().st_mtime_ns for p in (GAME / "patches").glob("*.s")), default=0))).encode()).hexdigest()[:8]
    live = WORKD / f"live_{tag}"
    live.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, str(HERE / "poppatch.py"), "live", "--only", *names, "--out", str(live)], check=True, cwd=GAME, stdout=subprocess.DEVNULL)
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


def apply_cmds(live):
    spec = json.loads(Path(live + ".json").read_text())
    c = [f"loadbin {Path(live + '.img')} ${spec['img_base']:x}"]
    c += [f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])) for s in spec["sites"]]
    return c


def poke_cmd(spec):
    ad, hx = spec.split(":")
    return f"w ${int(ad, 16):x} " + " ".join(f"${hx[i:i + 2]}" for i in range(0, len(hx), 2))


def start_turn_for(snap: Path) -> int:
    cache = WORKD / "at.json"
    d = json.loads(cache.read_text()) if cache.exists() else {}
    k = f"{snap.name}:{snap.stat().st_mtime_ns}"
    if k not in d:
        with _lock:
            h = Populous(snapshot=snap)
        try:
            time.sleep(1.0)
            d[k] = h.peekw(TURN) + 100
        finally:
            h.close()
        WORKD.mkdir(exist_ok=True)
        cache.write_text(json.dumps(d))
    return d[k]


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
    f = h.R / f"smp{target}.txt"
    f.write_text("".join(f"e {e}\n" for e in exprs))
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {target} :trace :once :file {f}")
    wait_gone(h, start, timeout)
    out = {}
    for m in re.finditer(r"> e (.+)\n(?:  .*\n)*= (.*)", h._logtext()[start:]):
        out[m.group(1)] = int(HEX.search(m.group(2)).group(1), 16)
    return out


def at_pc(h, cmds, pc, cond=""):
    f = h.R / "atpc.txt"
    f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${pc:x}{cond} :trace :once :file {f}")
    wait_gone(h, start, 300)


def sync_hz(sync):
    return 50 if sync & 2 else 60


# ---------------------------------------------------------------------------------------------------------------------------------
# (b) rate
# ---------------------------------------------------------------------------------------------------------------------------------
def counters(patched):
    ex = ["VBL", "CycleCounter", f"(${TURN:x}).w"]
    if patched:
        ex += [f"(${D + o:x}).l" for o in (oTICKS, oTPASS, oRPASS, oSPASS, oPPASS)]
    return ex


def report(tag, s0, s1, ex, hz, patched, extra="", cpu_mhz=None):
    dv = s1["VBL"] - s0["VBL"]
    secs = dv / hz
    cyc = ((s1["CycleCounter"] - s0["CycleCounter"]) & 0xFFFFFFFF) / dv
    if cpu_mhz:
        seen = cpu_mhz * 1e6 / cyc
        extra += f" | refresh seen {seen:.2f} Hz" + ("" if abs(seen - hz) < 0.03 * hz else f"  *** NOT {hz} Hz: the VBL rate did not change ***")
    turns = (s1[ex[2]] - s0[ex[2]]) & 0xFFFF
    line = f"RESULT {tag}: {dv} VBL = {secs:.2f} s, {cyc:.0f} cycles/VBL, world turns {turns} = {turns / secs:.3f}/s"
    if patched:
        k = [s1[e] - s0[e] for e in ex[3:]]
        line += f" | ticks(D) {k[0]} = {k[0] / secs:.3f}/s; passes T {k[1]} R {k[2]} S {k[3]} P {k[4]}"
    print(line + extra, flush=True)
    return turns / secs


def cmd_rate(a):
    names = ([] if a.unpatched else TICKSET) + (RELEASE if a.release else DEFAULTS if a.defaults else []) + (["test_pwalk"] if a.spin else [])
    live = make_live(names) if names else None
    h = Populous(snapshot=snap_path(a.snap))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        cmds = (apply_cmds(live) if live else ["e VBL"]) + (["w $ff820a $00"] if a.hz == 60 else []) + ([poke_cmd(f"{SPINN:x}:{a.spin:04x}")] if a.spin else [])
        at_pc(h, cmds, APPLYPC)
        h.cmd("hatari-option --fast-forward on")
        time.sleep(1.0)
        sync = rdb(h, 0xFF820A)[0]
        ex = counters(not a.unpatched)
        s0 = sample_at(h, h.vbl() + 60, ex)
        s1 = sample_at(h, s0["VBL"] + a.vbls, ex)
        report(f"{a.snap} {a.mhz} MHz {a.hz} Hz sync ${sync:02x} {'orig' if a.unpatched else 'patched'}{' +defaults' if a.defaults else ''}{f' +spin {a.spin}' if a.spin else ''}", s0, s1, ex, a.hz, not a.unpatched)
    finally:
        h.close()


# ---------------------------------------------------------------------------------------------------------------------------------
# (b) rate from a cold boot
# ---------------------------------------------------------------------------------------------------------------------------------
def cold_to_play(h, machine, wait_menu=16):
    """The boot sequence of tools/pop_boot_test.py (HD or floppy build)."""
    from populous import HOME, CONQUEST_XY, START_XY
    time.sleep(wait_menu)
    h.key("space", 0.5)
    time.sleep(30)
    h.goto(*CONQUEST_XY, home_xy=HOME)
    h.click(hold=0.4)
    time.sleep(9)
    h.goto(*START_XY, home_xy=HOME)
    h.click(hold=0.4)
    time.sleep(10)
    return h.in_play()


def cmd_cold(a):
    tos = TOS[a.tos]
    extra = (["--mmu", "true"] if a.machine == "tt" else []) + a.extra.split()
    kw = dict(game_dir=GAME / a.build, machine=a.machine, tos=tos, memsize_kb=a.mem, extra=extra)
    h = Populous(**kw)
    try:
        t0 = time.time()
        if a.cpuboot:
            time.sleep(a.cpuboot)
            h.set_cpuclock(a.cpuboot_mhz)
            ok = cold_to_play(h, a.machine, wait_menu=0)
        else:
            ok = cold_to_play(h, a.machine)
        sync = rdb(h, 0xFF820A)[0]
        mark = rdb(h, 0xB3004, 4)
        pc = rdb(h, TOP, 6).hex()
        print(f"boot {time.time() - t0:.0f} s in_play={ok} marker {mark!r} ${TOP:x} {pc} sync $ff820a = ${sync:02x} -> booted at {sync_hz(sync)} Hz", flush=True)
        h.shot(str(GAME / "work" / "shots" / f"tick_{a.tag}.png"))
        patched = pc.startswith("4ef9")
        ex = counters(patched)
        for hz in (a.hz or [sync_hz(sync)]):
            cur = sync_hz(rdb(h, 0xFF820A)[0])
            if hz == 60 and cur != 60:
                h.debug("w $ff820a $00", 0.5)
                time.sleep(1.0)
            elif hz == 50 and cur != 50:
                h.debug("w $ff820a $02", 0.5)
                time.sleep(1.0)
            for mhz in a.clocks:
                if mhz:
                    h.set_cpuclock(mhz)
                time.sleep(1.0)
                h.cmd("hatari-option --fast-forward on")
                s0 = sample_at(h, h.vbl() + 60, ex)
                s1 = sample_at(h, s0["VBL"] + a.vbls * hz // 50, ex)
                h.cmd("hatari-option --fast-forward off")
                cpu = mhz or {"st": 8, "ste": 8, "megaste": 8, "tt": 32, "falcon": 16}[a.machine]
                report(f"cold {a.machine} TOS {a.tos} {a.mem} KB {mhz or 'default'} MHz {hz} Hz ({a.build})", s0, s1, ex, hz, patched, cpu_mhz=cpu)
        h.shot(str(GAME / "work" / "shots" / f"tick_{a.tag}_end.png"))
    finally:
        h.close()


# ---------------------------------------------------------------------------------------------------------------------------------
# (a) world state by turn
# ---------------------------------------------------------------------------------------------------------------------------------
def one(snap, t0, live, out: Path, turns, mhz, hz, walk, pokes=(), cmdpoke=None, patched=False, still=False, render_cap=False, endturn=None, cmdin="R"):
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("*"):
        f.unlink()
    with _lock:
        h = Populous(snapshot=snap)
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
        cmds = apply_cmds(live) + [poke_cmd(p) for p in pokes]
        cmds.append("w $2003e " + " ".join(["$4e $71"] * 15))             # the IKBD packet handler no longer writes the pointer words
        if hz == 60:
            cmds.append("w $ff820a $00")
        mode = (1 | (0 if still else 2)) if walk else 0
        cmds.append(f"w ${MODE:x} $00 ${mode:02x}")
        vx, vy = (max(0, min(40, v - 8)) for v in (h.peekw(Populous.VIEW_X), h.peekw(Populous.VIEW_Y)))
        cmds.append(f"w ${BX:x} $00 ${vx:02x} $00 ${vy:02x}")
        (R / "top.txt").write_text("\n".join([f"e ${TOP:x}", "e VBL", f"e (${TURN:x}).w", f"savebin {fifo} ${WORLD[0]:x} ${WORLD[1]:x}"]) + "\n")
        cmds.append(f"b pc = ${TOP:x} :trace :file {R / 'top.txt'}")
        (R / "kind.txt").write_text("\n".join([f"e ${KIND:x}", "e VBL", f"e (${TURN:x}).w", f"e (${D + oSKIP:x}).w", f"e (${D + oRON:x}).w", "e CycleCounter"]) + "\n")
        cmds.append(f"b pc = ${KIND:x} :trace :file {R / 'kind.txt'}")
        (R / "cap.txt").write_text("\n".join([f"e ${FLIP:x}", "e VBL", f"e (${TURN:x}).w", f"e (${D + oRON:x}).w", "e ($3c510).l",
                                              f"savebin {fifo} ${BUFS[0]:x} ${BUFS[1]:x}"]) + "\n")
        cmds.append(f"b pc = ${FLIP:x} :trace :file {R / 'cap.txt'}")
        (R / "ev.txt").write_text(f"e $b932\ne (${TURN:x}).w\n")
        cmds.append(f"b pc = $b932 :trace :file {R / 'ev.txt'}")       # `jsr $133b0`: the event of turn $1000
        (R / "cell.txt").write_text(f"e $c330\ne (${TURN:x}).w\n")
        cmds.append(f"b pc = $c330 :trace :file {R / 'cell.txt'}")       # a minimap cell of the CLEAN background is redrawn by the world ($c2b8)
        (R / "stale.txt").write_text("w $16f12 $00 $00 $00 $00\n")      # no stale pointer restore into the new back buffer (popabtest: display.md section 3)
        cmds.append(f"b pc = ${AFTERFLIP:x} :trace :file {R / 'stale.txt'}")
        if render_cap:       # the render stage only (no minimap dots, no UI): the frame as the render stage leaves it
            (R / "rnd.txt").write_text("\n".join([f"e ${RENDERED:x}", "e VBL", f"e (${TURN:x}).w", f"e (${D + oRON:x}).w", "e ($3c510).l",
                                                  f"savebin {fifo} ${BUFS[0]:x} ${BUFS[1]:x}"]) + "\n")
            cmds.append(f"b pc = ${RENDERED:x} :trace :file {R / 'rnd.txt'}")
        if cmdpoke:
            k, bts = cmdpoke
            (R / "cmd.txt").write_text(f"w $21e4a {' '.join(f'${b:02x}' for b in bts)}\n")
            if patched:
                cond = f"(${D + oRON:x}).w = 1" if cmdin == "R" else f"(${D + oRON:x}).w = 0"
                cmds.append(f"b pc = ${KIND:x} && (${TURN:x}).w = {k} && {cond} :trace :file {R / 'cmd.txt'}")
            else:
                cmds.append(f"b pc = ${KIND:x} && (${TURN:x}).w = {k} :trace :once :file {R / 'cmd.txt'}")
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {out}/end.flag $0 2\ne VBL\n")
        cmds.append(f"b pc = ${TOP:x} && (${TURN:x}).w = {endturn if endturn is not None else t0 + turns} :trace :once :file {end}")
        app = R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        for c in cmds:
            if len(c) > 235:
                raise ValueError(f"debugger command line too long: {c[:80]}...")
        if h.peekw(TURN) >= t0:
            raise ValueError(f"turn {t0} already passed")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${APPLYPC:x} && (${TURN:x}).w = {t0} :trace :once :file {app}")
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
    kinds, order, cells, events = [], [], set(), []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in NUM.findall(blk)]
        if not m:
            continue
        if m[0] == KIND and len(m) >= 6:
            kinds.append(m[1:6])
        elif m[0] == TOP and len(m) >= 3:
            order.append(("top", m[1], m[2]))
        elif m[0] == FLIP and len(m) >= 5:
            order.append(("flip", *m[1:5]))
        elif m[0] == 0xB932 and len(m) >= 2:
            events.append(m[1])
        elif m[0] == 0xC330 and len(m) >= 2:
            cells.add(m[1])
        elif m[0] == RENDERED and len(m) >= 5:
            order.append(("rnd", *m[1:5]))
    pos = 0
    recs = dict(tops=[], flips=[], rnds=[], kinds=kinds, cells=cells, events=events)
    for o in order:
        need = WORLD[1] if o[0] == "top" else BUFS[1]
        if pos + need > len(buf):
            break
        s = bytes(buf[pos:pos + need])
        pos += need
        if o[0] == "top":
            tw = int.from_bytes(s[TURN - WORLD[0]:TURN - WORLD[0] + 2], "big")
            if tw != o[2]:
                raise RuntimeError(f"capture stream out of step: top record says turn {o[2]}, the dump has turn {tw} (record {len(recs['tops'])}, buffer {len(buf)} bytes, pos {pos})")
            recs["tops"].append(dict(vbl=o[1], turn=o[2], world=s))
        else:
            _, vbl, turn, ron, back = o
            assert back in (0x4F500, 0x57200), hex(back)
            sb = s[back - BUFS[0]:back - BUFS[0] + 32000]
            (recs["flips"] if o[0] == "flip" else recs["rnds"]).append(dict(vbl=vbl, turn=turn, ron=ron, sb=sb, hb=hashlib.md5(sb).hexdigest()))
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


def diff_desc(a: bytes, b: bytes):
    rs = diff_ranges(a, b, 0, gap=160)
    n = sum(e - s for s, e in rs)
    rows = sorted({s // 160 for s, e in rs} | {(e - 1) // 160 for s, e in rs})
    return f"{n} bytes in {len(rs)} spans, rows {rows[:1]}..{rows[-1:]}" if rs else "identical"


# UI / render-derived scratch that is not world state: it follows the passes that ran the render and the UI (a catch-up pass runs neither),
# or is consumed by an interrupt between flips.  Each entry was found from the first runs and is explained in work/notes/timing.md section 4.
MASKS = [(0x2478C, 0x2488C),       # the pointer's saved background (16 rows x 16 bytes): drawn and restored by the VBL routine, which buffer it was in is timing
         (0x24990, 0x249A4),       # the sample player's state (timer A advances it in real time)
         (0x36EB0, 0x36EB8),       # the map cell under the pointer: computed by the UI ($11c18, $11c30), which a catch-up pass (S) does not run
         (0x37EF0, 0x37EF2),       # the number of sprites the render stage listed
         (0x37EB6, 0x37EB7),       # render flags ($14682 bset 7, $146d6 bset 3, cleared at $b706): read by the world only for the sound trigger ($df30-$df88: $36d40, cooldown $36eae);
                                   # a catch-up pass (S) has no render of its own and sees the flags of the last frame drawn
         (0x3B04A, 0x3B24A),       # the sprite list the render stage builds ($14920-$149ce)
         (0x3C50C, 0x3C514),       # the two screen buffer pointers: swapped by every flip, and a render-only pass flips too
         (0x3D58C, 0x3D58E),       # cursor-over-icon flags OR-ed by the render ($14610)
         ]


NOMASK = False


def mask_world(w: bytes, extra=()) -> bytes:
    b = bytearray(w)
    for s, e in ([] if NOMASK else list(MASKS)) + list(extra):
        b[s - WORLD[0]:e - WORLD[0]] = bytes(e - s)
    return bytes(b)


def crop_minimap(fr):
    """The minimap rectangle: x 0..135, y 0..67 ($166f0 plots at x = $40 + cx - cy (1..127), y = (cx + cy) / 2 (0..63)).  Beyond x = 136 or y = 68 the terrain window
    starts, whose tiles change with the world between a T frame (rendered before the world) and an R frame (after it)."""
    out = bytearray()
    for y in range(68):
        row = bytearray(fr[y * 160: y * 160 + 72])
        for pl in range(4):                                  # group 8 (x 128..143): keep x 128..135, the top byte of each plane word
            row[64 + pl * 2] &= 0xFF
            row[64 + pl * 2 + 1] = 0
        out += row
    return bytes(out)


def mask_minimap(fr):
    b = bytearray(fr)
    x0, y0, x1, y1 = MINIMAP
    for y in range(y0, y1):
        b[y * 160 + (x0 // 16) * 8: y * 160 + ((x1 + 15) // 16) * 8] = bytes(((x1 + 15) // 16 - x0 // 16) * 8)
    return bytes(b)


def cmd_ab(a):
    global NOMASK
    NOMASK = a.nomask
    WORKD.mkdir(exist_ok=True)
    base = WALK + (RELEASE if a.release else DEFAULTS if a.defaults else [])
    bl = make_live(base)
    pl = make_live(base + TICKSET + (["test_rtog_a", "test_rtog_b"] if a.render and not a.no_rtog else []))
    sp = snap_path(a.snap)
    t0 = start_turn_for(sp)
    pokes = list(a.both_poke)
    endturn = None
    if a.turnjump:
        pokes.append(f"{TURN:x}:{a.turnjump:04x}")
        endturn = a.turnjump + a.turns
    if a.spin:
        pokes.append(f"{SPINN:x}:{a.spin:04x}")
    cmdp = None
    if a.cmdturn:
        cmdp = (t0 + a.cmdturn, [1, 32, 32])            # command 1 = raise land at vertex (32,32), executed at the end of the pass of that turn
    print(f"base {' '.join(base)}\npatched +{' '.join(TICKSET)}\nsnapshot {a.snap} turn {t0}, {a.turns} turns, {a.mhz} MHz, {a.hz} Hz{', view still' if a.still else ''}{f', command at turn {cmdp[0]}' if cmdp else ''}", flush=True)
    with ThreadPoolExecutor(1) as ex:
        fb = ex.submit(one, sp, t0, bl, WORKD / f"b_{sp.stem}_{a.mhz}", a.turns, a.mhz, a.hz, True, tuple(pokes), cmdp, False, a.still, a.render, endturn, a.cmdin)
        fp = ex.submit(one, sp, t0, pl, WORKD / f"p_{sp.stem}_{a.mhz}", a.turns, a.mhz, a.hz, not a.neg, tuple(pokes) + tuple(a.poke), cmdp, True, a.still, a.render, endturn, a.cmdin)
        B, P = fb.result(), fp.result()
    bw = {}
    for r in B["tops"]:
        bw.setdefault(r["turn"], r)
    notes, ok = [], True
    ncmp = nmis = 0
    first = P["tops"][0]["turn"] if P["tops"] else 0
    per_turn = {}
    extra = ((0x21E4A, 0x21E52),) if cmdp else ()       # the command bytes of player 0 wait in their slot for the turn pass: pending at the pass tops of the poke turn
    for r in P["tops"]:
        per_turn[r["turn"]] = per_turn.get(r["turn"], 0) + 1
        if r["turn"] <= first + 1 or r["turn"] not in bw:
            continue
        ncmp += 1
        if mask_world(r["world"], extra) != mask_world(bw[r["turn"]]["world"], extra):
            nmis += 1
            ok = False
            if nmis <= 3:
                rg = diff_ranges(mask_world(bw[r["turn"]]["world"], extra), mask_world(r["world"], extra), WORLD[0])
                vals = [(hex(s_), bw[r['turn']]['world'][s_ - WORLD[0]:e_ - WORLD[0]][:8].hex(), r['world'][s_ - WORLD[0]:e_ - WORLD[0]][:8].hex()) for s_, e_ in rg[:6]]
                notes.append(f"  WORLD DIFFER at pass top, turn {r['turn']} (VBL {r['vbl']}): {len(rg)} ranges, first (addr, unpatched, patched) {vals}")
    if a.nomask:
        agg = {}
        for r in P["tops"]:
            if r["turn"] <= first + 1 or r["turn"] not in bw:
                continue
            wb, wp = bw[r["turn"]]["world"], r["world"]
            for i in range(len(wb)):
                if wb[i] != wp[i]:
                    agg[WORLD[0] + i] = agg.get(WORLD[0] + i, 0) + 1
        spans, cur = [], None
        for ad in sorted(agg):
            if cur and ad - cur[1] <= 2:
                cur[1] = ad + 1
                cur[2] = max(cur[2], agg[ad])
            else:
                if cur:
                    spans.append(tuple(cur))
                cur = [ad, ad + 1, agg[ad]]
        if cur:
            spans.append(tuple(cur))
        print("  differing byte spans (first-last, max tops a byte differs in), merged within 2 bytes:", ", ".join(f"${s_:x}-${e_ - 1:x}:{n}" for s_, e_, n in spans))
    bf = {}
    for r in B["flips"]:
        bf.setdefault(r["turn"], r)
    nf = nfm = 0
    tf, rf = {}, {}
    for r in P["flips"]:
        (rf if r["ron"] else tf).setdefault(r["turn"], []).append(r)
    kk = P["kinds"]
    after_s = set()
    for i in range(1, len(kk)):
        if kk[i - 1][2] and not kk[i][2] and not kk[i][3]:
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
                notes.append(f"  T-FRAME DIFFER turn {k}: " + diff_desc(bf[k]["sb"], lst[0]["sb"]))
    nrs = nrsm = nmm = nmmm = nexcl = 0
    for k, lst in sorted(rf.items()):
        if k <= first + 1:
            continue
        for x, y in zip(lst, lst[1:]):
            nrs += 1
            if x["hb"] != y["hb"]:
                nrsm += 1
                ok = False
                if nrsm <= 3:
                    notes.append(f"  R-FRAME UNSTABLE turn {k}: " + diff_desc(x["sb"], y["sb"]))
        if k in tf and (k in P["cells"] or k - 1 in P["cells"]):
            nexcl += 1
            continue                        # the world redrew a minimap cell of the clean background: R frames legitimately show it, the T frame of that turn (rendered before) not
        if k in tf:
            for x in lst:
                nmm += 1
                if crop_minimap(x["sb"]) != crop_minimap(tf[k][0]["sb"]):
                    nmmm += 1
                    ok = False
                    if nmmm <= 3:
                        cx, cy = crop_minimap(x["sb"]), crop_minimap(tf[k][0]["sb"])
                        bad = [i for i in range(len(cx)) if cx[i] != cy[i]]
                        rows = sorted({i // 72 for i in bad})
                        if a.dump:
                            Path(a.dump).mkdir(parents=True, exist_ok=True)
                            (Path(a.dump) / f"t{k}_T.bin").write_bytes(tf[k][0]["sb"])
                            (Path(a.dump) / f"t{k}_R{lst.index(x)}.bin").write_bytes(x["sb"])
                        notes.append(f"  R MINIMAP != T MINIMAP turn {k}: {len(bad)} bytes, minimap rows {rows[:1]}..{rows[-1:]}, world cell redrawn in turn {k - 2}..{k + 1}: {sorted(c for c in P['cells'] if k - 3 <= c <= k + 1)}")
    # render-only frames: an R pass of label k renders the world the original renders at the top of its next pass (label k + 1 is the post-logic label; the
    # original's render-stage frame of the pass with top turn k is `rnds` with turn = k at $b800).  Water phase differs by design (one toggle per turn): see notes.
    nrr = nrrm = 0
    if a.render:
        brn = {}
        for r in B["rnds"]:
            brn.setdefault(r["turn"], r)
        for r in P["rnds"]:
            if r["ron"] and r["turn"] in brn and r["turn"] > first + 1:
                nrr += 1
                # the original renders pass top = turn k at label k; the patched R pass of label k renders the same world state
                if r["hb"] != brn[r["turn"]]["hb"]:
                    nrrm += 1
                    ok = False
                    if nrrm <= 3:
                        notes.append(f"  R RENDER != original render, label {r['turn']}: " + diff_desc(brn[r['turn']]["sb"], r["sb"]))
    kc = {"T": 0, "S": 0, "R": 0, "P": 0}
    for _, _, sk, ro, _ in P["kinds"]:
        kc["S" if sk else "R" if ro else "T"] += 1
    emul = (P["tops"][-1]["vbl"] - P["tops"][0]["vbl"]) / a.hz if len(P["tops"]) > 1 else 0
    tr = (P["tops"][-1]["turn"] - P["tops"][0]["turn"]) / emul if emul else 0
    ber = (B["tops"][-1]["turn"] - B["tops"][0]["turn"]) / ((B["tops"][-1]["vbl"] - B["tops"][0]["vbl"]) / a.hz) if len(B["tops"]) > 1 else 0
    print(f"{a.snap} @{a.mhz} MHz {a.hz} Hz: {'IDENTICAL' if ok else 'DIFFER'} | world at pass tops: {ncmp} compared ({nmis} differ) over {len({r['turn'] for r in P['tops']})} turns, "
          f"max {max(per_turn.values()) if per_turn else 0} tops/turn | T frames {nf} compared ({nfm} differ; {nfs} excluded) | R frames: {sum(len(v) for v in rf.values())} "
          f"({nrs} stability pairs, {nrsm} unstable; {nmm} minimap compares, {nmmm} differ, {nexcl} turns excluded (minimap cell redrawn by the world)"
          + (f"; {nrr} render-only compares vs the original render, {nrrm} differ" if a.render else "") + f") | pass kinds T {kc['T']} R {kc['R']} S {kc['S']} | turns/s base {ber:.3f} patched {tr:.3f}", flush=True)
    if a.turnjump:
        print(f"  event of turn $1000 (`jsr $133b0` at $b932): unpatched {len(B['events'])} time(s) {B['events']}, patched {len(P['events'])} time(s) {P['events']}")
        if len(B["events"]) != len(P["events"]) or not B["events"]:
            ok = False
    for n in notes[:10]:
        print(n)
    if ncmp < 10 or nf < 3:
        ok = False
        print("  TOO FEW TURNS COMPARED")
    sys.exit(0 if ok else 1)


# ---------------------------------------------------------------------------------------------------------------------------------
# click latch lifetime
# ---------------------------------------------------------------------------------------------------------------------------------
def cmd_clicks(a):
    """A fresh left click (latch $3d566 = 0, what the VBL routine does for a press) is poked at the top of a pass of turn t1; per pass: kind, the latch as the
    UI sees it (at $bb7c) and after the pass ($bc02).  Patched: R passes hide it (UI sees 1) and give it back, the next T pass takes it (the original takes it in
    the very next pass)."""
    names = [] if a.unpatched else TICKSET
    live = make_live(names) if names else None
    h = Populous(snapshot=snap_path(a.snap))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        t0 = h.peekw(TURN) + 20
        R = h.R
        cmds = apply_cmds(live) if live else ["e VBL"]
        t1 = t0 + 4
        (R / "poke.txt").write_text("w $3d566 $00 $00\n")
        (R / "obs.txt").write_text("\n".join(["e $bb7c", "e VBL", f"e (${TURN:x}).w", f"e (${D + oRON:x}).w", "e ($3d566).w"]) + "\n")
        (R / "obs2.txt").write_text("\n".join(["e $bc02", "e VBL", f"e (${TURN:x}).w", f"e (${D + oRON:x}).w", "e ($3d566).w"]) + "\n")
        cmds.append(f"b pc = $bb7c :trace :file {R / 'obs.txt'}")
        cmds.append(f"b pc = $bc02 :trace :file {R / 'obs2.txt'}")
        cmds.append(f"b pc = ${KIND:x} && (${TURN:x}).w = {t1} :trace :once :file {R / 'poke.txt'}")
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {R}/end.flag $0 2\n")
        cmds.append(f"b pc = ${TOP:x} && (${TURN:x}).w = {t1 + 3} :trace :once :file {end}")
        (R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${APPLYPC:x} && (${TURN:x}).w = {t0} :trace :once :file {R / 'apply.txt'}")
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
    print(f"{'orig' if a.unpatched else 'patched'} {a.snap} {a.mhz} MHz: latch poked to 0 at the look of the pass of turn {t1}; per pass: pc VBL turn RON latch")
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(v) for v in NUM.findall(blk)]
        if len(m) >= 5 and m[0] in (0xBB7C, 0xBC02) and t1 - 1 <= m[2] <= t1 + 3:
            print(f"   {'UI sees ' if m[0] == 0xBB7C else 'pass end '} VBL {m[1]} turn {m[2]} {'R' if m[3] else 'T'} latch {m[4]}")


# ---------------------------------------------------------------------------------------------------------------------------------
# (c) responsiveness
# ---------------------------------------------------------------------------------------------------------------------------------
def watch_hits(h, addr, action, window, exprs=("VBL",), width="w"):
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
    names = ([] if a.unpatched else TICKSET) + (DEFAULTS if a.defaults else [])
    live = make_live(names) if names else None
    h = Populous(snapshot=snap_path(a.snap))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        if live:
            at_pc(h, apply_cmds(live), APPLYPC)
        time.sleep(1.5)
        ex = ["VBL", f"(${TURN:x}).w"] + ([] if a.unpatched else [f"(${D + oRON:x}).w"])
        seen, vals = watch_hits(h, 0x24786, lambda: h.rel(30, 0), 1.5, ex)
        print(f"{'orig' if a.unpatched else 'patched'}{' +defaults' if a.defaults else ''} {a.snap} {a.mhz} MHz: pointer: first $24786 change {seen[0] * 1000:.0f} ms after the move ({len(seen)} change(s))" if seen else "pointer: no change")
        seen, vals = watch_hits(h, Populous.VIEW_X, lambda: h.key("KP_6", 2.0), 2.6, ex)
        if seen:
            vb = [v[0] for v in vals]
            tn = [v[1] for v in vals]
            span = (vb[-1] - vb[0]) / 50.0 if len(vb) > 1 else 0
            ron = sum(1 for v in vals if len(v) > 2 and v[2]) if not a.unpatched else 0
            print(f"   scroll KP_6 held 2 s: {len(seen)} view steps, first after {seen[0] * 1000:.0f} ms, {(len(vb) - 1) / span if span else 0:.1f} steps/s (emulated); world turns during the steps "
                  f"{(tn[-1] - tn[0]) & 0xFFFF} = {((tn[-1] - tn[0]) & 0xFFFF) / span if span else 0:.2f}/s" + ("" if a.unpatched else f"; steps made in render-only passes (turn waiting): {ron}"))
        else:
            print("   scroll: no step")
    finally:
        h.close()


def cmd_pause(a):
    """Pause ($3b2b2 = 1, what command 14/6 does): the world stops (kind P passes = the original pass), and when the pause ends the clock resumes without a burst.
    Every pass is logged at $b6f4 (VBL, turn, SKIP, RON, pause flag); the pause is set and cleared by VBL breakpoints (no emulated time passes while the debugger pokes)."""
    live = make_live(TICKSET)
    h = Populous(snapshot=snap_path(a.snap))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        R = h.R
        v0 = h.vbl() + 400
        v1, v2, v3 = v0 + 300, v0 + 700, v0 + 1000
        (R / "kind.txt").write_text("\n".join([f"e ${KIND:x}", "e VBL", f"e (${TURN:x}).w", f"e (${D + oSKIP:x}).w", f"e (${D + oRON:x}).w", "e ($3b2b2).w"]) + "\n")
        (R / "p1.txt").write_text("w $3b2b2 $00 $01\n")
        (R / "p0.txt").write_text("w $3b2b2 $00 $00\n")
        (R / "end.txt").write_text(f"b all\nsavebin {R}/end.flag $0 2\n")
        cmds = apply_cmds(live) + [f"b pc = ${KIND:x} :trace :file {R / 'kind.txt'}",
                                   f"b VBL > {v1} :trace :once :file {R / 'p1.txt'}", f"b VBL > {v2} :trace :once :file {R / 'p0.txt'}",
                                   f"b VBL > {v3} :trace :once :file {R / 'end.txt'}"]
        (R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${APPLYPC:x} :trace :once :file {R / 'apply.txt'}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (R / "end.flag").exists():
            if time.time() - t > 600:
                raise TimeoutError
            time.sleep(0.3)
        time.sleep(1.0)
        text = h._logtext()[start:]
    finally:
        h.close()
    rows = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        m = [int(x) for x in NUM.findall(blk)]
        if len(m) >= 6 and m[0] == KIND:
            rows.append(m[1:6])
    def win(lo, hi):
        return [r for r in rows if lo <= r[0] < hi]
    def stat(rs):
        k = {"T": 0, "S": 0, "R": 0, "P": 0}
        for vbl, turn, sk, ro, pz in rs:
            k["P" if pz else "S" if sk else "R" if ro else "T"] += 1
        return k
    pre, pau, post = win(v0, v1 + 5), win(v1 + 10, v2), win(v2 + 5, v3)
    print(f"{a.snap} {a.mhz} MHz 50 Hz: running  (VBL {v0}-{v1}): turns {pre[-1][1] - pre[0][1]} in {(pre[-1][0] - pre[0][0]) / 50:.1f} s, passes {stat(pre)}")
    print(f"   paused   (VBL {v1}-{v2}): turns {pau[-1][1] - pau[0][1]} (turn word {pau[0][1]} .. {pau[-1][1]}), passes {stat(pau)} (the original pass: one per VBL at most)")
    first_t = next(r for r in post if not r[4])
    tv = [r[0] for r in post if not r[2] and not r[3] and not r[4]]
    gaps = [y - x for x, y in zip(tv, tv[1:])]
    print(f"   unpaused (VBL {v2}-{v3}): first pass with the pause off at VBL {first_t[0]}; turn passes at VBL {tv[:6]}...; gaps between turn passes (VBL) min {min(gaps)} max {max(gaps)}; "
          f"turns {post[-1][1] - post[0][1]} in {(post[-1][0] - post[0][0]) / 50:.1f} s = {(post[-1][1] - post[0][1]) / ((post[-1][0] - post[0][0]) / 50):.2f}/s")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("ab")
    q.add_argument("snap"); q.add_argument("mhz", type=int); q.add_argument("turns", type=int)
    q.add_argument("--hz", type=int, choices=[50, 60], default=50)
    q.add_argument("--spin", type=int, default=0, help="both runs burn N dbra iterations (10 cycles each) per turn: slow world logic, so S passes happen")
    q.add_argument("--still", action="store_true", help="pointer walk only, the view stays")
    q.add_argument("--defaults", action="store_true", help="both runs carry the default patch set")
    q.add_argument("--release", action="store_true", help="both runs carry the release set without the tick (defaults + pop_ptrfix + pop_keys* + pop_tooltip)")
    q.add_argument("--render", action="store_true", help="also capture the render stage at $b800 and compare R passes with the original render")
    q.add_argument("--dump", help="directory for the frames of failing minimap compares")
    q.add_argument("--nomask", action="store_true", help="no masks: list every differing address range (shows what the masks hide)")
    q.add_argument("--no-rtog", action="store_true", help="negative control of --render: without the water-phase toggle patches the compare must differ")
    q.add_argument("--turnjump", type=lambda v: int(v, 0), default=0, help="both runs poke the turn word to this value at the apply point (4090 = just before the event of turn $1000)")
    q.add_argument("--cmdin", choices=["R", "T"], default="R", help="with --cmdturn: poke the command bytes in a render-only pass (R, default) or in the turn / catch-up pass itself (T: for machines without render-only passes)")
    q.add_argument("--neg", action="store_true"); q.add_argument("--cmdturn", type=int, default=0, help="a raise-land command bytes poked K turns after the start")
    q.add_argument("--poke", action="append", default=[], help="ADDR:HEXBYTES in the patched run only (negative controls)")
    q.add_argument("--both-poke", action="append", default=[])
    r = sub.add_parser("rate")
    r.add_argument("snap"); r.add_argument("mhz", type=int); r.add_argument("vbls", type=int)
    r.add_argument("--hz", type=int, choices=[50, 60], default=50)
    r.add_argument("--unpatched", action="store_true"); r.add_argument("--spin", type=int, default=0)
    r.add_argument("--defaults", action="store_true"); r.add_argument("--release", action="store_true")
    c = sub.add_parser("cold")
    c.add_argument("--machine", default="ste"); c.add_argument("--tos", default="1.62"); c.add_argument("--mem", type=int, default=1024)
    c.add_argument("--hz", type=int, nargs="*", choices=[50, 60], default=None); c.add_argument("--build", default="build/PopTiming/hd")
    c.add_argument("--vbls", type=int, default=2000); c.add_argument("--tag", default="cold")
    c.add_argument("--clocks", nargs="*", type=int, default=[8, 16])
    c.add_argument("--extra", default="")
    c.add_argument("--cpuboot", type=int, default=0); c.add_argument("--cpuboot-mhz", type=int, default=16)
    k = sub.add_parser("clicks")
    k.add_argument("snap"); k.add_argument("mhz", type=int); k.add_argument("--unpatched", action="store_true")
    pz = sub.add_parser("pause")
    pz.add_argument("snap"); pz.add_argument("mhz", type=int)
    i = sub.add_parser("input")
    i.add_argument("snap"); i.add_argument("mhz", type=int); i.add_argument("--unpatched", action="store_true"); i.add_argument("--defaults", action="store_true")
    a = ap.parse_args()
    {"ab": cmd_ab, "rate": cmd_rate, "cold": cmd_cold, "clicks": cmd_clicks, "input": cmd_input, "pause": cmd_pause}[a.cmd](a)


if __name__ == "__main__":
    main()
