#!/usr/bin/env python3
"""Gates for the predict-ahead men interpolation (p3b_interp + p3b_delta on top of the tick_* set).  Notes: work/notes/interp.md.

    python3 tools/pminterp.py state SNAP MHZ VBLS [--toff] [--selfcmp [--selfip]]
                                                               # (a) RAM $0-$60000 at every loop top, tick set vs tick set + interp (--selfcmp: noise control)
    python3 tools/pminterp.py strip SNAP MHZ VBLS [--tk] [--toff] [--png DIR --crop X0 Y0 X1 Y1 --sheet] [--dump F.json]
                                                               # (c) consecutive frames: screen position (x, y) of every people record the
                                                               #     renderer blits ($11f82), per pass; --png writes the frames, --sheet a contact sheet in work/shots
    python3 tools/pminterp.py cost  SNAP MHZ VBLS              # (d) cycles of the p3b routines (CycleCounter between breakpoints)
    python3 tools/pminterp.py rate  SNAP MHZ VBLS              # (d) fps / ticks / pass mix, tick-only and interp side by side
    python3 tools/pminterp.py edge  SNAP MHZ VBLS KIND [--rec N --at T]   # (e) poke a record at a tick: teleport | free | angel | pause
    python3 tools/pminterp.py ui    SNAP MHZ VBLS [--at X,Y ...]          # (e) open the query window, check the people table is restored
    python3 tools/pminterp.py boot  [--machine ste --tos 1.62 --mem 1024]  # (f) cold boot of build/interp/floppy/powermonger.st at 8 and 16 MHz

Images: `pmpatch.py live` (build/live/tk = tick set, build/live/ip = tick set + p3b_interp + p3b_delta), applied live at the first flip after the restore
(snapshots hold unpatched code).  --toff pokes PD+0 (TOFF) = 1: tick passes are drawn without offset (the frame of the tick-only build).
The floppy for `boot`: pmpatch.py build --floppy --out build/interp --only <default set> p3b_interp p3b_delta
"""
from __future__ import annotations

import argparse
import os
import re
import select
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent / "tools"), str(HERE)]
import pmtick as T  # noqa: E402
from pm import PM, SNAP  # noqa: E402

TICK = ["tick_head", "tick_pass", "tick_wx", "tick_men", "tick_click", "tick_click2", "tick_click3"]
IP = TICK + ["p3b_interp", "p3b_delta"]
PD = 0xB8A80
FLIP = 0x187A
BLIT = 0x11F82
SHOTS = GAME / "work" / "shots"


def live_image(names, tag):
    out = GAME / "build" / "live" / tag
    subprocess.run([sys.executable, str(HERE / "pmpatch.py"), "live", "--only", *names, "--out", str(out)], check=True, cwd=GAME,
                   stdout=subprocess.DEVNULL)
    return str(out)


def cmd_state(a):
    tk, ip = live_image(TICK, "tk"), live_image(IP, "ip")
    if a.selfcmp:                                   # noise control: tick-only against tick-only (--selfip: interp against interp)
        if a.selfip:
            tk = ip
        else:
            ip = tk
    res = {}

    def one(name, live, pokes):
        h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
        try:
            time.sleep(1.5)
            res[name] = T.log_passes(h, live, a.mhz, a.vbls, name, pokes)
        finally:
            h.close()
    pk = ["w $b8a80 $00 $01"] if a.toff else []
    ts = [threading.Thread(target=one, args=("U", tk, [])), threading.Thread(target=one, args=("P", ip, pk))]
    [t.start() for t in ts]; [t.join() for t in ts]
    U, P = res["U"], res["P"]
    ubl, ub = {}, {}
    for it, k, b in U:
        ubl.setdefault(k, []).append(b)
        ub.setdefault(k, b)
    its = [it for it, _, _ in P]
    print(f"{a.snap} {a.mhz} MHz{' TOFF' if a.toff else ''}: tick-only {len(U)} loop tops (ticks {U[0][1]}..{U[-1][1]}), interp {len(P)} loop tops (ticks {P[0][1]}..{P[-1][1]}), "
          f"missed loop tops {sum(max(0, y - x - 1) for x, y in zip(its, its[1:]))}")
    bad, n, ticks, vals = {}, 0, set(), {}
    seen = {}
    for it, k, b in P:
        j = seen.get(k, 0)
        seen[k] = j + 1
        # the j-th loop top of a world tick against the j-th of the tick-only run (T top first, then the render-only tops): the same phase
        # of the tick (a time-dependent input/pointer latch differs between a T top and a later R top of one tick, in either build)
        u = ubl.get(k, [])[j] if j < len(ubl.get(k, [])) else None
        if u is None:
            continue
        n += 1; ticks.add(k)
        d = T.diff_words(u, b)
        for g in T.group(d):
            bad.setdefault((g[0], g[1]), []).append(it)
            if len(vals.setdefault((g[0], g[1]), [])) < 6:
                vals[(g[0], g[1])].append((it, k, u[g[0]:g[1]].hex(), b[g[0]:g[1]].hex()))
    print(f"compared {n} loop tops over {len(ticks)} distinct world ticks (RAM $0-$60000, masks as pmtick.py MASKS)")
    neg = sum(1 for it, k, b in P if ub.get(k + 1) is not None and T.diff_words(ub[k + 1], b))
    nn = sum(1 for it, k, b in P if ub.get(k + 1) is not None)
    print(f"negative control: interp tick k vs tick-only tick k+1 differs in {neg} of {nn} loop tops")
    mv = sum(1 for i in range(512) if P[0][2][0x51B66 + i * 50 + 8:0x51B66 + i * 50 + 12] != P[-1][2][0x51B66 + i * 50 + 8:0x51B66 + i * 50 + 12])
    print(f"men records whose x/z changed first -> last loop top: {mv}")
    if not bad:
        print("IDENTICAL")
    else:
        for (lo, hi), its in sorted(bad.items())[:40]:
            print(f"DIFF ${lo:x}-${hi:x} in {len(its)} loop tops, first iters {its[:4]}")
            for v in vals[(lo, hi)]:
                print("    iter %d tick %d tick-only %s interp %s" % v)
    return 0 if not bad else 1


# ---- strip: screen positions + frames ------------------------------------------------------------------------------
PEOPLE_LO, PEOPLE_HI = 0x51B66, 0x57F66


def trace_run(snap, mhz, live, vbls, toff, want_frames=True, poke=None, reads=()):
    """Restore, apply `live` at the first flip, then log for `vbls` VBLs: every blit ($11f82) with a3 inside the people table (a3, d0 = x,
    d1 = y on the screen, d2 = sprite) and at every flip (VBL, world tick $4bb3e, RON, ACC, the buffer just rendered $2df7c) + the 64000 B
    of both screen buffers into a FIFO.  Returns (text, frames bytes, palette text)."""
    h = PM(snapshot=str(SNAP / f"{snap}.sav"))
    R = h.R
    stop = threading.Event()
    frames = bytearray()
    extra = []
    try:
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
        th = threading.Thread(target=drain, daemon=True); th.start()
        time.sleep(1.5)
        if mhz != 8:
            h.set_cpuclock(mhz)
        cmds = T.apply_cmds(live) if live else ["e VBL"]
        if toff:
            cmds.append(f"w ${PD:x} $00 $01")
        T.at_flip(h, cmds)
        pal = h.debug("m $ff8240 32", 0.5)
        (R / "men.txt").write_text("e a3\ne d0\ne d1\ne d2\n")
        (R / "cap.txt").write_text("\n".join(["e VBL", "e ($4bb3e).l", "e ($b8a06).w", "e ($b8a02).w", "e ($2df7c).l", "e ($4bb3a).w", "e ($4bb3c).w", "e ($ff9a).w"]
                                             + ([f"savebin {fifo} $1c700 $fa00"] if want_frames else [])) + "\n")
        end = R / "end.txt"
        end.write_text(f"b all\nsavebin {R}/end.flag $0 2\n")
        h.debug("b all", 0.3)
        s0 = len(h._logtext())
        v0 = h.vbl()
        if poke:                                   # (ticks from now, [debugger lines]): applied when the world tick counter reaches the value
            (R / "poke.txt").write_text("\n".join(poke[1]) + "\n")
            h.cmd(f"hatari-debug b ($4bb3e).l = ${h.peekl(0x4BB3E) + poke[0]:x} :trace :once :file {R / 'poke.txt'}")
            time.sleep(0.2)
        h.cmd(f"hatari-debug b pc = ${BLIT:x} && a3 > ${PEOPLE_LO - 1:x} && a3 < ${PEOPLE_HI:x} :trace :file {R / 'men.txt'}")
        time.sleep(0.2)
        h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :file {R / 'cap.txt'}")
        time.sleep(0.2)
        h.cmd(f"hatari-debug b VBL > {v0 + vbls} :trace :once :file {end}")
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (R / "end.flag").exists():
            if time.time() - t > 900:
                raise TimeoutError(h._logtext()[-1500:])
            time.sleep(0.3)
        time.sleep(1.0)
        text = h._logtext()[s0:]
        extra = [h.ram(r[0], r[1]) if isinstance(r, tuple) else h.debug(r, 0.5) for r in reads]
    finally:
        stop.set()
        h.close()
    trace_run.extra = extra
    return text, bytes(frames), pal


def parse_events(text):
    """-> passes [dict(vbl, tick, ron, acc, back, men={rec: [(x, y, sprite)]})]; the men blits logged before a flip belong to that pass."""
    passes, men = [], {}
    sg = lambda v: v - 65536 if v & 0x8000 else v
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        vals = [int(x, 16) for x in re.findall(r"^= .*\$([0-9a-fA-F]+) \(hex\)", blk, re.M)]
        if "pc = $11f82" in blk:
            if len(vals) >= 4:
                a3, d0, d1, d2 = vals[:4]
                men.setdefault((a3 - PEOPLE_LO) // 50, []).append((sg(d0 & 0xFFFF), sg(d1 & 0xFFFF), d2 & 0xFFFF))
        elif "pc = $187a" in blk and len(vals) >= 8:
            passes.append(dict(vbl=vals[0], tick=vals[1], ron=vals[2], acc=vals[3], back=vals[4], cam=tuple(vals[5:8]), men=men))
            men = {}
    return passes


def planar_png(buf, pal_text, path, crop=None, scale=2):
    from PIL import Image
    import numpy as np
    words = []
    for ln in pal_text.splitlines():
        m = re.match(r"[0-9A-Fa-f]{8}:\s(.*)", ln)
        if m:
            words += [int(x, 16) for x in m.group(1).split("  ")[0].split()]
    pal = []
    for i in range(16):
        w = (words[2 * i] << 8 | words[2 * i + 1]) if 2 * i + 1 < len(words) else 0
        pal.append(tuple(17 * ((w >> sh) & 15) for sh in (8, 4, 0)))
    a = np.frombuffer(buf, dtype=">u2").reshape(200, 20, 4)
    img = np.zeros((200, 320), dtype=np.uint8)
    for px in range(16):
        bit = (a >> (15 - px)) & 1
        idx = bit[:, :, 0] | (bit[:, :, 1] << 1) | (bit[:, :, 2] << 2) | (bit[:, :, 3] << 3)
        img[:, px::16] = idx
    rgb = np.array(pal, dtype=np.uint8)[img]
    im = Image.fromarray(rgb)
    if crop:
        im = im.crop(crop)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
    im.save(path)


def cmd_strip(a):
    live = live_image(TICK, "tk") if a.tk else live_image(IP, "ip")
    text, frames, pal = trace_run(a.snap, a.mhz, live, a.vbls, a.toff)
    passes = parse_events(text)
    FS = 0xFA00
    print(f"{a.snap} {a.mhz} MHz {'tick-only' if a.tk else 'interp' + (' TOFF' if a.toff else '')}: {len(passes)} flips, {len(frames) // FS} frames captured")
    (Path(a.out) if a.out else Path("/tmp/pmi")).mkdir(parents=True, exist_ok=True)
    # per record: positions per pass
    recs = sorted({r for p in passes for r in p["men"]})
    print("pass: vbl tick kind acc(half-VBL)   = frame order; positions are the blit coordinates (x, y) of the record")
    mov = []
    for r in recs:
        xs = [p["men"].get(r, [None])[0] for p in passes]
        pts = [(x[0], x[1]) for x in xs if x]
        if len(set(pts)) > 1:
            mov.append(r)
    print(f"records blitted in the window: {len(recs)}; whose screen position changes: {len(mov)}")
    for r in mov[:a.nrec]:
        row = []
        for p in passes:
            v = p["men"].get(r)
            row.append(f"{v[0][0]:4d},{v[0][1]:4d}" if v else "   -    ")
        print(f"rec {r:3d}: " + " | ".join(row))
    back = flat = tot = 0
    steps = []
    for r in mov:
        pts = [(p["men"][r][0][0], p["men"][r][0][1]) for p in passes if r in p["men"]]
        if len(pts) < 4:
            continue
        ex, ey = pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]
        if ex == 0 and ey == 0:
            continue
        prog = [(x - pts[0][0]) * ex + (y - pts[0][1]) * ey for x, y in pts]
        for u, v in zip(prog, prog[1:]):
            tot += 1
            back += v < u
            flat += v == u
        steps += [abs(x1 - x0) + abs(y1 - y0) for (x0, y0), (x1, y1) in zip(pts, pts[1:])]
    print(f"progress along each mover's net displacement, {tot} consecutive-frame pairs: backwards {back}, unchanged {flat}, forwards {tot - back - flat}"
          f"; mean |step| per frame {sum(steps) / max(1, len(steps)):.2f} px")
    print("pass  :", " | ".join(f"{'R' if p['ron'] else 'T'}{p['tick'] & 0xFFF:3d}   " for p in passes))
    print("vbl   :", " | ".join(f"{p['vbl'] % 10000:5d}   " for p in passes))
    print("acc   :", " | ".join(f"{p['acc']:4d}    " for p in passes))
    print("camera ($4bb3a, $4bb3c, $ff9a) distinct over the window:", sorted({p["cam"] for p in passes}))
    if a.png and frames:
        out = Path(a.png); out.mkdir(parents=True, exist_ok=True)
        nfr = len(frames) // FS
        for i in range(min(nfr, len(passes))):
            both = frames[i * FS:(i + 1) * FS]
            back = passes[i]["back"]
            b = both[back - 0x1C700: back - 0x1C700 + 32000]
            tag = f"{a.snap}_{a.mhz}_{'tk' if a.tk else 'ip'}{'_toff' if a.toff else ''}"
            planar_png(b, pal, out / f"{tag}_{i:02d}_{'R' if passes[i]['ron'] else 'T'}{passes[i]['tick']}.png", crop=tuple(a.crop) if a.crop else None)
        print(f"frames in {out}")
        if a.sheet:
            from PIL import Image, ImageDraw
            tag = f"{a.snap}_{a.mhz}_{'tk' if a.tk else 'ip'}{'_toff' if a.toff else ''}"
            fs = sorted(out.glob(f"{tag}_*.png"))[:a.sheet_n]
            ims = [Image.open(f) for f in fs]
            if ims:
                w, h = ims[0].size
                cols = 4
                rows = (len(ims) + cols - 1) // cols
                sh = Image.new("RGB", (cols * w, rows * (h + 14)), (30, 30, 30))
                dr = ImageDraw.Draw(sh)
                for i, (im, f) in enumerate(zip(ims, fs)):
                    x, y = (i % cols) * w, (i // cols) * (h + 14)
                    sh.paste(im, (x, y + 14))
                    pi = passes[i]
                    dr.text((x + 3, y + 1), f"{'R' if pi['ron'] else 'T'} tick {pi['tick']} vbl {pi['vbl']} acc {pi['acc']}", fill=(255, 255, 0))
                SHOTS.mkdir(parents=True, exist_ok=True)
                dst = SHOTS / f"interp_strip_{tag}.png"
                sh.save(dst)
                print(f"sheet {dst}")
    if a.dump:
        import json
        Path(a.dump).write_text(json.dumps([dict(vbl=p["vbl"], tick=p["tick"], ron=p["ron"], acc=p["acc"], men={str(k): v for k, v in p["men"].items()}) for p in passes]))
    return 0


def cmd_rate(a):
    """fps (flips per VBL window), world ticks/s, pass mix for the tick-only and the interp image, run side by side."""
    imgs = {"tick-only": live_image(TICK, "tk"), "interp": live_image(IP, "ip")}
    out = {}

    def one(name, live):
        h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
        try:
            time.sleep(1.5)
            if a.mhz != 8:
                h.set_cpuclock(a.mhz)
            T.at_flip(h, T.apply_cmds(live))
            v0 = h.vbl(); t0 = h.peekl(T.TICKCNT)
            d0 = T.rd(h, T.D, 24)
            f = h.fps(a.vbls)
            v1 = h.vbl(); t1 = h.peekl(T.TICKCNT)
            d1 = T.rd(h, T.D, 24)
            L = lambda b, o: int.from_bytes(b[o:o + 4], "big")
            out[name] = (f["flips"], a.vbls, t1 - t0, v1 - v0, L(d1, 8) - L(d0, 8), L(d1, 12) - L(d0, 12), L(d1, 16) - L(d0, 16))
        finally:
            h.close()
    ts = [threading.Thread(target=one, args=(n, l)) for n, l in imgs.items()]
    [t.start() for t in ts]; [t.join() for t in ts]
    for n, (fl, vb, tk, dv, T_, R_, S_) in out.items():
        print(f"{a.snap} {a.mhz} MHz {n}: flips {fl} in {vb} VBL (fps {fl * 50 / vb:.3f}), world ticks {tk} in {dv} VBL ({tk * 50 / dv:.3f}/s), tick passes {T_} R {R_} S {S_}")
    return 0


def cmd_edge(a):
    """(e) edge cases: poke a walking record (default get_men record 9) when the world tick counter reaches tick+AT, then show its blit
    position per pass, the mover count / list after the run and the record itself.  kinds: teleport (x high byte := $3f: a jump of cells,
    |delta| > STEP), free (+5 := 0: the man entered a building / left the table), angel (+5 $fe, +6 $0c, +7 4, +18 $7e: death)."""
    live = live_image(IP, "ip")
    base = PEOPLE_LO + a.rec * 50
    cmds = {"teleport": [f"w ${base + 8:x} $3f"], "free": [f"w ${base + 5:x} $00"],
            "angel": [f"w ${base + 5:x} $fe $0c $04", f"w ${base + 18:x} $00 $7e"], "pause": ["w $57ff2 $00 $01"]}[a.kind]
    text, _frames, _pal = trace_run(a.snap, a.mhz, live, a.vbls, False, want_frames=False, poke=(a.at, cmds),
                                    reads=[(PD, 32), (0xB9500, 5120), (base, 50)])
    passes = parse_events(text)
    print(f"{a.snap} {a.mhz} MHz edge '{a.kind}' record {a.rec} (${base:x}), poke when the tick reaches +{a.at}: {len(passes)} flips")
    print(" ".join(f"{'R' if p['ron'] else 'T'}{p['tick'] % 1000}:" + (f"{p['men'][a.rec][0][0]},{p['men'][a.rec][0][1]}" if a.rec in p["men"] else "-") for p in passes))
    print(f"records blitted per pass: first {len(passes[0]['men'])}, last {len(passes[-1]['men'])}; distinct screen positions of record {a.rec} over the run: "
          f"{sorted({tuple(q[:2]) for p in passes for q in p['men'].get(a.rec, [])})[:12]}")
    pd, lst, rec = trace_run.extra
    nmov = int.from_bytes(pd[2:4], "big")
    ents = {int.from_bytes(lst[10 * i:10 * i + 2], "big"): (int.from_bytes(lst[10 * i + 2:10 * i + 4], "big", signed=True), int.from_bytes(lst[10 * i + 4:10 * i + 6], "big", signed=True)) for i in range(nmov)}
    print(f"after the run: NMOV {nmov}; record {a.rec} (offset ${a.rec * 50:x}) in the mover list: {ents.get(a.rec * 50, 'NO')}; record bytes +5/+6/+7 {rec[5]:02x} {rec[6]:02x} {rec[7]:02x}, x ${rec[8]:02x}{rec[9]:02x} z ${rec[10]:02x}{rec[11]:02x}")
    return 0


def cyc_per_vbl(h, span=50):
    """CPU cycles per VBL (Hatari CycleCounter over `span` VBLs): ~160 k at 8 MHz, ~320 k at 16 MHz."""
    f = h.R / "cv.txt"
    f.write_text("e VBL\ne CycleCounter\n")
    h.debug("b all", 0.3)
    s0 = len(h._logtext()); v = h.vbl()
    h.cmd(f"hatari-debug b VBL > {v + 3} :trace :once :file {f}")
    time.sleep(0.3)
    h.cmd(f"hatari-debug b VBL > {v + 3 + span} :trace :once :file {f}")
    t = time.time()
    while h._logtext()[s0:].count(f"Reading debugger commands from '{f}'") < 2 and time.time() - t < 90:
        time.sleep(0.3)
    time.sleep(0.4)
    pr = [(int(a, 16), int(b, 16)) for a, b in re.findall(r"> e VBL\n= .*\$([0-9a-fA-F]+) \(hex\)\n> e CycleCounter\n= .*\$([0-9a-fA-F]+) \(hex\)", h._logtext()[s0:])]
    if len(pr) >= 2:
        return ((pr[1][1] - pr[0][1]) & 0xFFFFFFFF) / max(1, pr[1][0] - pr[0][0])
    return 0.0


def cmd_boot(a):
    """(f) cold boot of build/interp/floppy/powermonger.st (default set + p3b_interp + p3b_delta): marker, sites, then 8 and 16 MHz windows."""
    import pmpatch
    disk = GAME / "build" / "interp" / "floppy" / "powermonger.st"
    sys.path.insert(0, str(HERE))
    import pm
    h = pmpatch.make_pm(disk, None, machine=a.machine, tos=pm.TOS[a.tos], memsize_kb=a.mem)
    try:
        t0 = time.time()
        h.boot_to_game()
        mk = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
        print(f"{a.machine} TOS {a.tos} {a.mem}K: in game after {time.time() - t0:.0f} s, MARKER {mk!r}, FLAGS {h.peekl(pmpatch.FLAGS):#x}")
        print(f"  sites: $130aa {h.ram(0x130AA, 6).hex()} $130c8 {h.ram(0x130C8, 6).hex()} (expect 4eb9000b8aa0 / 4eb9000b8bc0)")
        for mhz in a.clocks:
            h.set_cpuclock(mhz)
            time.sleep(3)
            cv = cyc_per_vbl(h)
            v0 = h.vbl(); t0_ = h.peekl(T.TICKCNT)
            d0 = T.rd(h, T.D, 24); p0 = T.rd(h, PD, 24)
            f = h.fps(a.vbls)
            v1 = h.vbl(); t1 = h.peekl(T.TICKCNT)
            d1 = T.rd(h, T.D, 24); p1 = T.rd(h, PD, 24)
            L = lambda b, o: int.from_bytes(b[o:o + 4], "big")
            W = lambda b, o: int.from_bytes(b[o:o + 2], "big")
            print(f"  {mhz} MHz set: {cv:.0f} cycles/VBL; {v1 - v0} VBL, fps {f['flips'] * 50 / a.vbls:.2f}, ticks {t1 - t0_} ({(t1 - t0_) * 50 / (v1 - v0):.3f}/s), "
                  f"T {L(d1, 8) - L(d0, 8)} R {L(d1, 12) - L(d0, 12)} S {L(d1, 16) - L(d0, 16)}; interp: NMOV {W(p1, 2)}, render passes with offsets {L(p1, 8) - L(p0, 8)}, scans {L(p1, 20) - L(p0, 20)}")
        if a.shot:
            Path(a.shot).parent.mkdir(parents=True, exist_ok=True)
            h.shot(a.shot)
    finally:
        h.close()
    return 0


def cmd_ui(a):
    """(e) query window open: apply the interp image live at 16 MHz, click the Query icon ((76,191), icon 22) and a man, screenshot the window, then log
    every loop top for VBLS: all loop tops of one world tick must have an identical people table (the offsets are restored after every render),
    and the number of render passes that drew offsets must keep growing."""
    live = live_image(IP, "ip")
    h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
    try:
        time.sleep(1.5)
        h.set_cpuclock(a.mhz)
        T.at_flip(h, T.apply_cmds(live))
        time.sleep(3)
        h.click_st(76, 191, wait=1.5)
        SHOTS.mkdir(parents=True, exist_ok=True)
        for i, (x, y) in enumerate(a.at):
            h.click_st(x, y, wait=0.2)
        p0 = T.rd(h, PD, 24)

        def shots():                                  # screenshots while the loop-top log runs: the window must be up in the first ones
            for i, d in enumerate((1.0, 2.0, 2.0)):
                time.sleep(d)
                try:
                    h.shot(str(SHOTS / f"interp_query_{i}.png"))
                except Exception:                     # noqa: BLE001
                    pass
        threading.Thread(target=shots, daemon=True).start()
        res = T.log_passes(h, None, 8, a.vbls, "ui")
        p1 = T.rd(h, PD, 24)
        L = lambda b, o: int.from_bytes(b[o:o + 4], "big")
        print(f"{a.snap} {a.mhz} MHz query window: {len(res)} loop tops, render passes with offsets {L(p1, 8) - L(p0, 8)}, scans {L(p1, 20) - L(p0, 20)}, NMOV {int.from_bytes(p1[2:4], 'big')}")
        groups = {}
        for it, k, b in res:
            groups.setdefault(k, []).append(b[0x51B66:0x57F66])
        bad = sum(1 for k, v in groups.items() if any(x != v[0] for x in v))
        multi = sum(1 for v in groups.values() if len(v) > 1)
        print(f"  world ticks with >1 loop top: {multi}; of those with a people table that differs between the tops: {bad}")
        h.shot(str(SHOTS / "interp_query_end.png"))
    finally:
        h.close()
    return 0


AP_IN, AP_CALL, AP_RET, AP_RTS, DL_IN, DL_OUT = 0xB8AA0, 0xB8B72, 0xB8B78, 0xB8BBC, 0xB8BC0, 0xB8C2E


def cmd_cost(a):
    """Cycles (CycleCounter) of the p3b wrappers: ap = apply (AP_IN -> AP_CALL) + restore (AP_RET -> AP_RTS); dl = AP delta list (DL_IN -> DL_OUT).
    Pairs split by a VBL interrupt (the VBL value differs between the two stops) are dropped."""
    live = live_image(IP, "ip")
    h = PM(snapshot=str(SNAP / f"{a.snap}.sav"))
    try:
        time.sleep(1.5)
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        T.at_flip(h, T.apply_cmds(live))
        R = h.R
        (R / "c.txt").write_text("e pc\ne CycleCounter\ne VBL\ne ($b8a06).w\ne ($b8a02).w\ne ($b8a82).w\n")
        h.debug("b all", 0.3)
        s0 = len(h._logtext()); v0 = h.vbl()
        for pc in (AP_IN, AP_CALL, AP_RET, AP_RTS, DL_IN, DL_OUT):
            h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {R / 'c.txt'}")
            time.sleep(0.15)
        h.cmd(f"hatari-debug b VBL > {v0 + a.vbls} :trace :once")
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while "Removed CPU breakpoint" not in h._logtext()[s0:]:
            time.sleep(0.5)
            if time.time() - t > 900:
                break
        time.sleep(0.5)
        text = h._logtext()[s0:]
        h.debug("b all", 0.3)
    finally:
        h.close()
    ev = []
    for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
        vals = [int(x, 16) for x in re.findall(r"^= .*\$([0-9a-fA-F]+) \(hex\)", blk, re.M)]
        if len(vals) >= 6:
            ev.append(vals[:6])
    def pairs(x, y):
        out, last = [], None
        for pc, cyc, vbl, ron, acc, nm in ev:
            if pc == x:
                last = (cyc, vbl, ron, nm)
            elif pc == y and last and last[1] == vbl:
                out.append(((cyc - last[0]) & 0xFFFFFFFF, last[2], last[3]))
                last = None
            elif pc == y:
                last = None
        return out
    pre, post, dl = pairs(AP_IN, AP_CALL), pairs(AP_RET, AP_RTS), pairs(DL_IN, DL_OUT)
    mean = lambda v: sum(v) / len(v) if v else 0
    for name, d in (("ap apply (entry -> jsr $f898)", pre), ("ap restore (after jsr -> rts)", post), ("dl delta list (entry -> jmp $6a3a, tick passes)", dl)):
        for ron in (1, 0):
            v = [c for c, r, n in d if r == ron and c < 400000]
            nm = sorted({n for c, r, n in d if r == ron})
            if v:
                print(f"{a.snap} {a.mhz} MHz {name}: {'R' if ron else 'T'} passes n={len(v)} mean {mean(v):.0f} min {min(v)} max {max(v)} cycles (NMOV {nm[:6]})")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    bq = sub.add_parser("boot"); bq.add_argument("--machine", default="ste"); bq.add_argument("--tos", default="1.62"); bq.add_argument("--mem", type=int, default=1024)
    bq.add_argument("--clocks", type=int, nargs="+", default=[8, 16]); bq.add_argument("--vbls", type=int, default=700); bq.add_argument("--shot")
    for n in ("state", "strip", "cost", "rate", "edge", "ui"):
        q = sub.add_parser(n); q.add_argument("snap"); q.add_argument("mhz", type=int); q.add_argument("vbls", type=int)
        q.add_argument("--toff", action="store_true")
        if n == "ui":
            q.add_argument("--at", type=lambda v: tuple(int(x) for x in v.split(",")), nargs="+", default=[(180, 105)])
        if n == "edge":
            q.add_argument("kind", choices=["teleport", "free", "angel", "pause"]); q.add_argument("--rec", type=int, default=9); q.add_argument("--at", type=int, default=4)
        if n == "state":
            q.add_argument("--selfcmp", action="store_true"); q.add_argument("--selfip", action="store_true")
        if n == "strip":
            q.add_argument("--tk", action="store_true"); q.add_argument("--png"); q.add_argument("--out"); q.add_argument("--dump")
            q.add_argument("--crop", type=int, nargs=4); q.add_argument("--nrec", type=int, default=14)
            q.add_argument("--sheet", action="store_true"); q.add_argument("--sheet-n", dest="sheet_n", type=int, default=12)
    a = ap.parse_args()
    if a.cmd == "boot":
        sys.exit(cmd_boot(a))
    sys.exit({"state": cmd_state, "strip": cmd_strip, "cost": cmd_cost, "rate": cmd_rate, "edge": cmd_edge, "ui": cmd_ui}[a.cmd](a))
