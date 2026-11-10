#!/usr/bin/env python3
"""Key-vs-click world-state equality gate for qol_keys (same method as pmtick.py `ab`: whole RAM $0-$60000 at every loop top, compared per world tick).

Run A (clicks):  tick set + pm_tooltip + test_qolclick; at the pass of world tick T the debugger pokes TQ (x, y, button) and test_qolclick latches the
                 click the way the VBL handler does.
Run B (keys):    tick set + pm_tooltip + qol_keys + qol_keys2; at the same pass the debugger pokes PEND[scancode] (1, +2 with Shift) = what qol_keys2's
                 interrupt hook stores for a key press; qol_keys turns it into the click.
Both pokes happen at the `jsr $7202` of $130fc, i.e. right before the click dispatch, so the click is handled in the same pass.  Every event
of the schedule (one per 2 ticks) must leave RAM identical in A and B at every later loop top (masks: pmtick.MASKS + the two hook sites).
Negative control: B at tick k against A at tick k+1.

    python3 tools/pmqol_state.py [SNAP=get_men] [MHZ=8] [VBLS=700] [SET=0|1|2]
"""
from __future__ import annotations

import re
import sys
import threading
import time
from pathlib import Path

import pmab
import pmtick
from pm import PM, SNAP

PAT = Path(__file__).resolve().parent.parent / "patches" / "qol_keys.s"
KT = {}
for m in re.finditer(r"key[ \t]+\$([0-9a-f]+),(\d),(\d+),(\d+)", PAT.read_text()):
    KT[int(m.group(1), 16)] = (int(m.group(2)), int(m.group(3)), int(m.group(4)))

# (label, scancode, shift)
EVENTS = [("1 passive", 0x02, 0), ("H go home", 0x23, 0), ("3 aggressive", 0x04, 0), ("F get food", 0x21, 0), ("D drop food", 0x20, 0),
          ("R derank", 0x13, 0), ("N drop items", 0x31, 0), ("2 neutral", 0x03, 0), ("Q query", 0x10, 0), ("A attack", 0x1E, 0),
          ("I invent", 0x17, 0), ("M get men", 0x32, 0), ("[ rotate left", 0x1A, 0), ("] rotate right", 0x1B, 0), ("= zoom in", 0x0D, 0),
          ("- zoom out", 0x0C, 0), ("Shift+[ fine left", 0x1A, 1), ("Shift+] fine right", 0x1B, 1), ("Shift+= closest", 0x0D, 1),
          ("Shift+- farthest", 0x0C, 1), ("F2 map", 0x3C, 0), ("F1 map", 0x3B, 0), ("X transfer men", 0x2D, 0), ("S supply food", 0x1F, 0)]
SET = int(sys.argv[4]) if len(sys.argv) > 4 else 0           # 0..2: events 8*SET .. 8*SET+7
if SET == 3:       # the 90-degree rotations take 16 passes (up to 17 ticks at 8 MHz) to settle: far apart, so the camera words can be compared settled
    EVENTS = [e for e in EVENTS if e[0] in ("[ rotate left", "] rotate right")]
else:
    EVENTS = EVENTS[8 * SET:8 * SET + 8]
SPACING = 22 if SET == 3 else 5
WATCH = [("cmd", 0x57FD4), ("query", 0x57FEA), ("posture", 0x516FC), ("heading", 0xFF9A), ("zoom", 0x57FFC), ("map", 0x58098), ("cell", 0x5804C)]


def bytes_cmd(addr, bs):
    return f"w ${addr:x} " + " ".join(f"${b:02x}" for b in bs)


def event_cmds(kind, ev):
    label, sc, shift = ev
    flg, x, y = KT[sc]
    right = 1 if (shift and flg & 1) else 0
    if kind == "A":
        return [bytes_cmd(0xCE900, [0, 1, x >> 8, x & 255, y >> 8, y & 255, 0, right])]
    return [bytes_cmd(0xCD4A4 + sc, [3 if shift else 1]), bytes_cmd(0xCD4A2, [0, 1])]    # PEND[sc], then ANY (the order qol_keys2's interrupt hook uses)


def run(kind, snap, mhz, vbls, names, res):
    h = PM(snapshot=str(SNAP / f"{snap}.sav"))
    try:
        time.sleep(1.5)
        live = pmab.make_live(names)
        if mhz != 8:
            h.set_cpuclock(mhz)
        pmtick.at_flip(h, pmab.apply_cmds(live))
        t0 = h.peekl(pmtick.TICKCNT) + 3
        sched = [(t0 + SPACING * i, ev) for i, ev in enumerate(EVENTS)]
        sched = [(T + 1, ev) for T, ev in sched]
        cur = h.R / "cur.bin"
        f = h.R / "dumpcmd.txt"
        f.write_text(f"savebin {cur} $0 ${pmtick.DUMP_LEN:x}\n")
        got, stop = [], threading.Event()

        def poll():
            last = None
            while not stop.is_set():
                try:
                    st = cur.stat()
                except FileNotFoundError:
                    time.sleep(0.003)
                    continue
                if st.st_size == pmtick.DUMP_LEN and st.st_mtime_ns != last:
                    time.sleep(0.03)
                    st2 = cur.stat()
                    if st2.st_mtime_ns == st.st_mtime_ns and st2.st_size == pmtick.DUMP_LEN:
                        got.append(cur.read_bytes())
                        last = st.st_mtime_ns
                time.sleep(0.004)

        th = threading.Thread(target=poll, daemon=True)
        th.start()
        h.debug("b all", 0.3)
        s2 = len(h._logtext())
        v0 = h.vbl()
        h.cmd(f"hatari-debug b pc = ${pmtick.LOOPTOP:x} :trace :file {f}")
        time.sleep(0.2)
        endf = h.R / "endcmd.txt"
        endf.write_text(f"savebin {h.R / 'end.flag'} $0 2\n")
        h.cmd(f"hatari-debug b VBL > {v0 + vbls} :trace :once :file {endf}")

        def armer():             # ONE conditional breakpoint at a time (every condition is evaluated at every instruction), armed 2 ticks ahead
            for T, ev in sched:
                while not stop.is_set():
                    if got and int.from_bytes(got[-1][pmtick.TICKCNT:pmtick.TICKCNT + 4], "big") >= T - 4:
                        break
                    time.sleep(0.02)
                ef = h.R / f"ev{T}.txt"
                ef.write_text("\n".join(event_cmds(kind, ev)) + "\n")
                h.cmd(f"hatari-debug b pc = $130fc && ($4bb3e).l = {T} :trace :once :file {ef}")
                while not stop.is_set():
                    if got and int.from_bytes(got[-1][pmtick.TICKCNT:pmtick.TICKCNT + 4], "big") > T:
                        break
                    time.sleep(0.02)
        threading.Thread(target=armer, daemon=True).start()
        t = time.time()
        while not (h.R / "end.flag").exists():
            if time.time() - t > 3000:
                raise TimeoutError
            time.sleep(0.3)
        res[kind + "_fired"] = h._logtext()[s2:].count("Removed CPU breakpoint") - 1
        time.sleep(0.5)
        h.debug("b all", 0.3)
        time.sleep(0.5)
        stop.set()
        th.join()
        L = lambda b, o: int.from_bytes(b[o:o + 4], "big")
        res[kind] = ([(L(b, pmtick.ITER), L(b, pmtick.TICKCNT), b) for b in got], sched)
    finally:
        h.close()


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else "get_men"
    mhz = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    vbls = int(sys.argv[3]) if len(sys.argv) > 3 else 700
    pmtick.SITE_MASKS += [(0x130FC, 0x13102), (0x199C, 0x19A2)]
    # the camera animation (heading $ff9a + $12f56 steps of 4 PER PASS) and everything the renderer derives from it (view tables $3f364-$3f600,
    # $f1e0-$f1fc, $f894, $fec4, $ff9a-$ffa6) depend on how many passes a tick got, which differs by a few cycles between the two runs; camera
    # words are compared separately below at a settled tick.  The pointer save area is interrupt state.
    pmtick.SITE_MASKS += [(0xF1E0, 0xF200), (0xF890, 0xF89A), (0xFEC0, 0xFEC8), (0xFF90, 0xFFB0), (0x3F360, 0x3F600), (0x12F56, 0x12F58), (0x1C550, 0x1C5C0)]
    names = {"A": pmab.TICK + ["pm_tooltip", "test_qolclick"], "B": pmab.TICK + ["pm_tooltip", "qol_keys", "qol_keys2"]}
    res = {}
    ts = [threading.Thread(target=run, args=(k, snap, mhz, vbls, names[k], res)) for k in "AB"]
    [t.start() for t in ts]
    [t.join() for t in ts]
    (A, sched), (B, _) = res["A"], res["B"]
    print(f"event breakpoints fired: click run {res['A_fired']} of {len(sched)}, key run {res['B_fired']} of {len(sched)}")
    ab = {}
    for it, k, b in A:
        ab.setdefault(k, b)
    bb = {}
    for it, k, b in B:
        bb.setdefault(k, b)
    print(f"{snap} {mhz} MHz: click run {len(A)} loop tops (ticks {A[0][1]}..{A[-1][1]}), key run {len(B)} (ticks {B[0][1]}..{B[-1][1]}); {len(EVENTS)} events, one per {SPACING} ticks from tick {sched[0][0]}")
    bad, n, ticks = {}, 0, set()
    for it, k, b in B:
        a = ab.get(k)
        if a is None:
            continue
        n += 1
        ticks.add(k)
        for g in pmtick.group(pmtick.diff_words(a, b)):
            bad.setdefault(tuple(g), []).append((it, k))
    print(f"compared {n} loop tops over {len(ticks)} distinct world ticks")
    neg = sum(1 for it, k, b in B if ab.get(k + 1) is not None and pmtick.diff_words(ab[k + 1], b))
    print(f"negative control: key run tick k vs click run tick k+1 differs in {neg} of {sum(1 for it, k, b in B if ab.get(k + 1) is not None)} loop tops")
    # evidence that every event acted: the watched UI / world words just before and 1 tick after the event (key run)
    W = lambda b, a: int.from_bytes(b[a:a + 2], "big")
    print("event                tick  " + "  ".join(f"{n:>7s}" for n, _ in WATCH) + "   (value at the tick of the event -> two ticks later, key run)")
    for T, (label, sc, shift) in sched:
        nxt = lambda k: next((kk for kk in sorted(bb) if kk >= k), None)
        b0, b1 = bb.get(nxt(T)), bb.get(nxt(T + SPACING))
        if b0 is None or b1 is None:
            print(f"{label:20s} {T:5d}  (not logged)")
            continue
        print(f"{label:20s} {T:5d}  " + "  ".join(f"{W(b0, a):3x}>{W(b1, a):<3x}" for _, a in WATCH))
    # camera words at the last logged tick of every event window must be equal (the animation has settled)
    CAM = [("tiltA", 0xFF96), ("tiltB", 0xFF98), ("zoom", 0x57FFC), ("scrollx", 0x4BB3A), ("scrolly", 0x4BB3C), ("map", 0x58098)]
    if SET == 3 or SET == 2:      # the heading animates 4 units PER PASS: only compared where it has settled (set 3: 22 ticks apart; set 2: single 4-unit steps)
        CAM.insert(0, ("heading", 0xFF9A))
    camdiff = 0
    for T, (label, sc, shift) in sched:
        k = max((kk for kk in ab if T <= kk <= T + SPACING - 1 and kk in bb), default=None)
        if k is None:
            continue
        va = [W(ab[k], a) for _, a in CAM]
        vb = [W(bb[k], a) for _, a in CAM]
        if va != vb:
            camdiff += 1
            print(f"CAMERA {label} tick {k}: click run {dict(zip([n for n, _ in CAM], va))} key run {dict(zip([n for n, _ in CAM], vb))}")
    print(f"camera words (heading, tilt, zoom, scroll, map mode) at the end of every event window: {'all equal' if not camdiff else str(camdiff) + ' DIFFER'}")
    bad = {k: v for k, v in bad.items()} if not camdiff else (bad or {(0, 0): [(0, 0)]})
    if not bad:
        print("IDENTICAL (everything in $0-$60000 except the pmtick MASKS and the two hook sites): every command issued by key == the same command issued by click")
        return 0
    for (lo, hi), its in sorted(bad.items())[:40]:
        print(f"DIFF ${lo:x}-${hi:x} in {len(its)} loop tops, first (iter, tick) {its[:4]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
