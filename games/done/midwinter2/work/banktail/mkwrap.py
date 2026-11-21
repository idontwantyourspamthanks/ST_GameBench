#!/usr/bin/env python3
"""Stand-in for a resident driver / accessories on a machine whose TPA starts higher: a tiny TOS program RUNME.TOS that Mshrink()s itself to KEEP bytes (basepage included)
and Pexec()s the real RUNME (renamed FILES\\RUNME2.TOS); the real RUNME's basepage and text then sit KEEP bytes higher, exactly as behind a resident program of that size.
(An AUTO-folder TSR does not work in Hatari's GEMDOS-drive boot: the AUTO folder of the host dir is never run - first attempt, work/banktail/out/ste_tsr.txt: A4 = $fb1e, no shift.)
   usage: mkwrap.py OUT.PRG KEEP_HEX"""
import subprocess, sys, tempfile
from pathlib import Path
out, keep = sys.argv[1], int(sys.argv[2], 16)
src = f"""        section text
start:  movea.l 4(sp),a5
        lea     stk_end(pc),sp
        move.l  #{keep},-(sp)
        move.l  a5,-(sp)
        clr.w   -(sp)
        move.w  #$4a,-(sp)
        trap    #1
        lea     12(sp),sp
        clr.l   -(sp)
        pea     tail(pc)
        pea     name(pc)
        clr.w   -(sp)
        move.w  #$4b,-(sp)
        trap    #1
        lea     16(sp),sp
        clr.w   -(sp)
        trap    #1
tail:   dc.b    0,0
name:   dc.b    "FILES\\RUNME2.TOS",0
        even
stk:    dcb.b   256,0
stk_end:
"""
with tempfile.TemporaryDirectory() as d:
    s = Path(d) / "w.s"; s.write_text(src)
    subprocess.run(["vasmm68k_mot", "-Ftos", "-nosym", "-m68000", "-quiet", "-o", out, str(s)], check=True)
print(out, Path(out).stat().st_size, "B, keeps", hex(keep))
