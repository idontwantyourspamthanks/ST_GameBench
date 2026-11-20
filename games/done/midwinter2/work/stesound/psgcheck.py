#!/usr/bin/env python3
"""Real-hardware rule that Hatari does NOT model: PSG (YM2149) register 7 bits 6+7 = I/O port A / port B direction (1 = output).  With bit 6 = 0 the chip does
not drive port A (reg 14: floppy drive-select bits 1-2, side bit 0), so a write to reg 14 has no effect on the pins and the drive stays deselected (the pins
float high).  Hatari keeps PSGRegisters[14] whatever reg 7 says (src/psg.c), so a failure of this kind (v1.5/v1.6 on an STE / Mega STE: the Amiga sound
replaced the YM tick that rewrote reg 7 every VBL, and the game's sound init `$33870` had zeroed it) is invisible in every Hatari gate.

    python3 psgcheck.py TRACEFILE [NAME]        (trace made with `--trace fdc,psg_write`)

Replays the `ym write data reg=0xN val=0xV` lines in order, keeps the last reg-7 value (power-on: TOS writes $c0), and
  * for every write to reg 14 and every game FDC command (`fdc type ... pc=27c4e|27c54`, the game's `move.w d7,$ff8604`) asserts reg 7 & $c0 == $c0
    (bit 6: port A output = what the drive select needs; bit 7: port B output, as the original YM tick always writes it);
  * samples reg 7 once per video frame (a frame boundary = `video_cyc` falling by > 20000 between consecutive trace lines): FRAMES counts the frames that
    start with reg 7 & $c0 != $c0, and the longest run of such frames (legit: the boot stub's tune / the init -> first music tick window of the ORIGINAL game).
Prints one `PSGCHECK` verdict line: PASS = no reg-14 write and no game FDC command with port A or B an input.
"""
import re, sys

RE_W = re.compile(r"^ym write data reg=0x([0-9a-f]+) val=0x([0-9a-f]+) video_cyc=(\d+) .*?pc=([0-9a-f]+)")
RE_F = re.compile(r"^fdc type ([IV]+)\b.*?video_cyc=(\d+).*?pc=(27c4e|27c54)")
RE_C = re.compile(r"video_cyc=(\d+)")
MASK = 0xc0


def check(path, name="trace"):
    r7 = 0xc0                                   # TOS reset value
    n7 = n14 = nfdc = 0
    bad14 = []; badfdc = []; hist = []
    frames = bad_frames = run = max_run = 0
    prev_cyc = None
    for i, ln in enumerate(open(path, errors="replace")):
        mc = RE_C.search(ln)
        if mc:
            cyc = int(mc.group(1))
            if prev_cyc is not None and prev_cyc - cyc > 20000:        # a new frame
                frames += 1
                if r7 & MASK != MASK:
                    bad_frames += 1; run += 1; max_run = max(max_run, run)
                else:
                    run = 0
            prev_cyc = cyc
        m = RE_W.match(ln)
        if m:
            reg, val, pc = int(m.group(1), 16), int(m.group(2), 16), m.group(4)
            if reg == 7:
                n7 += 1
                if (val & MASK) != (r7 & MASK):
                    hist.append((i + 1, "reg 7 bits 6+7 $%02x -> $%02x (reg 7 := $%02x)" % (r7 & MASK, val & MASK, val), pc))
                r7 = val
            elif reg == 14:
                n14 += 1
                if r7 & MASK != MASK:
                    bad14.append((i + 1, r7, pc, ln.strip()))
            continue
        m = RE_F.match(ln)
        if m:
            nfdc += 1
            if r7 & MASK != MASK:
                badfdc.append((i + 1, r7, "27c4e", ln.strip()[:110]))
    ok = not bad14 and not badfdc
    print(f"reg-7 writes {n7}, reg-14 (port A) writes {n14}, game FDC commands {nfdc}, frames {frames}")
    for h in hist[:12]:
        print("  line %d: %s at pc=%s" % h)
    if len(hist) > 12:
        print(f"  ... {len(hist) - 12} more reg-7 direction-bit changes")
    for tag, lst in (("reg-14 write with port A/B not both output", bad14), ("game FDC command with port A/B not both output", badfdc)):
        if lst:
            print(f"  {len(lst)} x {tag}; first: line {lst[0][0]} r7=${lst[0][1]:02x} {lst[0][3][:90]}; last: line {lst[-1][0]}")
    print(f"  FRAMES with reg 7 bits 6/7 not both set at the frame start: {bad_frames} of {frames} (longest run {max_run})")
    print(f"PSGCHECK {name}: {'PASS' if ok else 'FAIL'} (reg-14 writes with port A/B input: {len(bad14)}, game FDC commands with port A/B input: {len(badfdc)}, bad frames {bad_frames}/{frames}, final reg 7 = ${r7:02x})")
    return ok


if __name__ == "__main__":
    sys.exit(0 if check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else sys.argv[1]) else 1)
