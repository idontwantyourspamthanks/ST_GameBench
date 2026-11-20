#!/usr/bin/env python3
"""PSG (YM2149) port-direction and select/write atomicity check on a Hatari trace.  Exit code 1 on violations.

Real hardware rule that stock Hatari (2.6.x) does NOT model: PSG register 7 bit 6 / bit 7 = I/O port A / port B direction (1 = output).
Port A (reg 14) carries the floppy drive-select (bits 1-2) and side (bit 0) lines.  With bit 6 = 0 the chip does not drive them, the
lines float high, NO drive is selected and the floppy is dead (Midwinter 2 v1.5/v1.6 on a real STE: music plays, no disk activity).
Hatari keeps PSGRegisters[14] and selects the drive whatever reg 7 says, so every emulator gate passes.  This replays the trace instead.

    python3 tools/psgcheck.py TRACE|- [--name N] [--game-pcs 27c4e,27c54] [--strict-b] [--near 32] [--max-bad-frames N] [--quiet]
                                      [--keep FILE] [--json FILE]
    from psgcheck import check; res = check("psg.trace")      # res.ok, res.violations, res.warnings, res.summary

Make the trace with `--trace psg_write,fdc --trace-file F` (harness: `Hatari(..., trace_psg=True)`, then `h.psg_check()`; the harness streams the
trace through a FIFO into this script, because a game with a sample player writes the PSG 100 000 times a second: 10 MB/s, GBs per run, and /tmp is RAM).
TRACE may be a file, a FIFO or `-` (stdin).  --keep FILE stores only the lines that matter (reg 7/14/15 writes, FDC commands, resets, one line per frame).
Sound ON is not needed for the trace itself, but run DMA-sound machines with `sound=True` anyway: the game's sound tick only runs its register writes then.

Checks (V = violation, exit 1; W = warning only):
  V  FDC command (`fdc type ... spinup=|settle=|force int 0x`) issued while reg 7 bit 6 = 0   (--game-pcs: count only commands from those pcs)
  V  write to reg 14 while reg 7 bit 6 = 0 (the write has no effect on the pins)
  V  non-atomic select/write: a data write whose register differs from the last select made by the SAME code (pc within --near bytes), with another
     code's select of the data write's register in between = an interrupt-side select landed between a main-code select and its data write, so the
     data went to the wrong register.  `movep` pairs (same pc) and `move.b`/`move.b` pairs not interrupted are fine.
  W  write to reg 15 / FDC command while reg 7 bit 7 = 0 (port B input; harmless for the floppy; V with --strict-b)
  W  frames (video_cyc falls by > 20000 between trace lines) that start with reg 7 bits 6/7 not both set; the longest run is reported
     (legit: boot stub tunes and the window between a sound init and the first tick; V only with --max-bad-frames).
Power-on: Hatari resets the PSG to reg 7 = 0 (`ym reset` line); TOS writes reg 7 early.  Limits: select + READ pairs are not traced (a read-modify-write
interrupted between its read and its write is only caught when the interrupt changes the selected register); a lost update to the SAME register is invisible.
"""
import argparse
import json
import re
import sys
from collections import deque, namedtuple

RE_SEL = re.compile(r"^ym write reg=0x([0-9a-f]+) video_cyc=(\d+).*?pc=([0-9a-f]+)")
RE_DAT = re.compile(r"^ym write data reg=0x([0-9a-f]+) val=0x([0-9a-f]+) video_cyc=(\d+).*?pc=([0-9a-f]+)")
RE_FDC = re.compile(r"^fdc type (?:I|II|III|IV) (?!verify)(?:.*?\b(?:spinup|settle)=|force int 0x)")
RE_PC = re.compile(r"pc=([0-9a-f]+)")
RE_CYC = re.compile(r"video_cyc=(\d+)")
MASK = 0xc0

Result = namedtuple("Result", "ok violations warnings summary")


def check(path, name=None, game_pcs=None, strict_b=False, near=32, max_bad_frames=None, quiet=False, out=print, keep=None):
    """Replay `path` (file, FIFO or '-' for stdin); print a report through `out`; return Result(ok, violations, warnings, summary)."""
    name = name or str(path)
    game_pcs = {p.lower() for p in game_pcs} if game_pcs else None
    r7 = 0x00                                   # Hatari PSG reset value; TOS sets it early
    n7 = n14 = n15 = nfdc = nsel = ndat = 0
    viol, warn, hist = [], [], []
    frames = bad_frames = run = max_run = 0
    prev_cyc = None
    ev = deque(maxlen=256)                      # recent ('s'|'d', reg, pc, line)
    src = sys.stdin if path == "-" else open(path, errors="replace")
    kf = open(keep, "w") if keep else None
    for i, ln in enumerate(src, 1):
        if not (ln.startswith("ym ") or ln.startswith("fdc ")):
            continue
        mc = RE_CYC.search(ln)
        if mc:
            cyc = int(mc.group(1))
            if prev_cyc is not None and prev_cyc - cyc > 20000:        # a new frame
                frames += 1
                if r7 & MASK != MASK:
                    bad_frames += 1; run += 1; max_run = max(max_run, run)
                else:
                    run = 0
                if kf:
                    kf.write(ln)
            prev_cyc = cyc
        if ln.startswith("ym write data reg="):
            m = RE_DAT.match(ln)
            if not m:
                continue
            reg, val, pc = int(m.group(1), 16), int(m.group(2), 16), int(m.group(4), 16)
            kind = "d"
        elif ln.startswith("ym write reg="):
            m = RE_SEL.match(ln)
            if not m:
                continue
            reg, pc = int(m.group(1), 16), int(m.group(3), 16)
            kind = "s"
        elif ln.startswith("fdc type "):
            if not RE_FDC.match(ln):
                continue
            kind = "f"
        elif ln.startswith("ym reset"):
            r7 = 0x00; ev.clear()
            if kf:
                kf.write(ln)
            continue
        else:
            continue
        if kind == "s":
            nsel += 1
            ev.append(("s", reg, pc, i))
            if kf and reg in (7, 14, 15):
                kf.write(ln)
        elif kind == "d":
            ndat += 1
            _atomic(ev, reg, pc, i, near, viol)
            ev.append(("d", reg, pc, i))
            if reg == 7:
                n7 += 1
                if (val & MASK) != (r7 & MASK):
                    hist.append((i, "reg 7 bits 6/7 $%02x -> $%02x (reg 7 := $%02x)" % (r7 & MASK, val & MASK, val), "%x" % pc))
                r7 = val
            elif reg == 14:
                n14 += 1
                if not r7 & 0x40:
                    viol.append((i, "reg 14 := $%02x while reg 7 = $%02x (port A input: no effect on the drive-select/side pins) pc=%x" % (val, r7, pc)))
            elif reg == 15:
                n15 += 1
                if not r7 & 0x80:
                    (viol if strict_b else warn).append((i, "reg 15 := $%02x while reg 7 = $%02x (port B input) pc=%x" % (val, r7, pc)))
            if kf and reg in (7, 14, 15):
                kf.write(ln)
        else:
            mp = RE_PC.search(ln)
            pc_s = mp.group(1) if mp else "?"
            if game_pcs is not None and pc_s not in game_pcs:
                continue
            nfdc += 1
            if kf:
                kf.write(ln)
            if not r7 & 0x40:
                viol.append((i, "FDC command with reg 7 = $%02x (port A input: NO drive selected on real hardware): %s" % (r7, ln.strip()[:110])))
            elif not r7 & 0x80:
                (viol if strict_b else warn).append((i, "FDC command with reg 7 = $%02x (port B input): %s" % (r7, ln.strip()[:100])))
    if kf:
        kf.close()
    if path != "-":
        src.close()
    if max_bad_frames is not None and bad_frames > max_bad_frames:
        viol.append((0, "%d frames start with reg 7 bits 6/7 not both set (limit %d, longest run %d)" % (bad_frames, max_bad_frames, max_run)))
    ok = not viol
    summary = ("PSGCHECK %s: %s (violations %d, warnings %d; reg-7 writes %d, reg-14 writes %d, FDC commands %d, selects %d, data writes %d, "
               "frames %d, frames with reg 7 bits 6/7 not both set %d (longest run %d), final reg 7 = $%02x)"
               % (name, "PASS" if ok else "FAIL", len(viol), len(warn), n7, n14, nfdc, nsel, ndat, frames, bad_frames, max_run, r7))
    if not quiet:
        for h in hist[:12]:
            out("  line %d: %s at pc=%s" % h)
        if len(hist) > 12:
            out("  ... %d more reg-7 direction-bit changes" % (len(hist) - 12))
        for tag, lst in (("VIOLATION", viol), ("warning", warn)):
            for ln_no, msg in lst[:8]:
                out("  %s line %d: %s" % (tag, ln_no, msg))
            if len(lst) > 8:
                out("  ... %d more %s lines (last: line %d)" % (len(lst) - 8, tag, lst[-1][0]))
    out(summary)
    return Result(ok, viol, warn, summary)


def _atomic(ev, reg, pc, line, near, viol):
    """Data write `reg` at `pc`: the newest still-pending select made by nearby code (no data write from that code since) must select `reg`."""
    owner = None
    foreign = False
    for kind, r, p, ln in reversed(ev):
        if abs(p - pc) <= near:
            if kind == "d":
                return                          # that code's select was already consumed by a data write
            owner = (r, p, ln)
            break
        if kind == "s" and r == reg:
            foreign = True                      # another code selected `reg` after the owner's select
    if owner and owner[0] != reg and foreign:
        viol.append((line, "NON-ATOMIC select/write: select reg %d at pc=%x (line %d) was overwritten by another code's select of reg %d before the data write at pc=%x: the data went to reg %d"
                     % (owner[0], owner[1], owner[2], reg, pc, reg)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("trace", help="Hatari --trace psg_write,fdc log, a FIFO, or - for stdin")
    ap.add_argument("--name")
    ap.add_argument("--game-pcs", help="comma list of pcs: count only FDC commands issued from these (hex, no 0x)")
    ap.add_argument("--strict-b", action="store_true", help="port B input (reg 7 bit 7 = 0) at reg 15 writes / FDC commands is a violation")
    ap.add_argument("--near", type=int, default=32, help="bytes: two pcs this close are the same code (default 32)")
    ap.add_argument("--max-bad-frames", type=int)
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--keep", help="write the relevant trace lines here (reg 7/14/15, FDC commands, resets, frame starts)")
    ap.add_argument("--json", help="write {ok, summary, violations, warnings} here")
    a = ap.parse_args(argv)
    res = check(a.trace, a.name, a.game_pcs.split(",") if a.game_pcs else None, a.strict_b, a.near, a.max_bad_frames, a.quiet, keep=a.keep)
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"ok": res.ok, "summary": res.summary, "violations": res.violations, "warnings": res.warnings}, f)
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
