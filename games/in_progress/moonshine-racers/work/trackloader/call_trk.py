#!/usr/bin/env python3
"""Debugger-driven call of the scratch HAGA-window file reader (trkread.s) in a restored race snapshot of the patched HD build.
   run via run_hatari_env.sh.   call_trk.py --snap SNAP.sav --machine ste --mem 2048 [--tos 2.06] --path 'A:\\MSTRACKS.TRK' [--floppy disk/campaign.st] [--hdfile]
   What it does: restore the snapshot (the race is running, standing start), optionally copy MSTRACKS.TRK to C:\\FILES and/or insert the floppy image in drive A
   with `hatari-option --disk-a`, then at the next execution of the flip routine $d1ca (a breakpoint with a :file script) load trkread.bin at $100000,
   callstub.bin at $100400 and the parameters at $100500, set PC to the stub; a second breakpoint at the stub's `done` prints the VBL counter.
   Afterwards: results (d0/d1/SR), VBL cost, compare the bytes at the destination with the file, IKBD parser state, race still running ($100e, $5ff8)."""
import argparse, os, re, struct, sys, time, zlib, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
G = HERE.parents[1]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
from stharness import TOS

ap = argparse.ArgumentParser()
ap.add_argument("--snap", required=True); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--tos"); ap.add_argument("--game", default="/tmp/msrl_dist/MOONSHR")
ap.add_argument("--path", default="MSTRACKS.TRK"); ap.add_argument("--floppy"); ap.add_argument("--hdfile", action="store_true")
ap.add_argument("--dest", type=lambda x: int(x, 0), default=0x120000); ap.add_argument("--max", type=lambda x: int(x, 0), default=0x40000)
ap.add_argument("--keep-open", action="store_true"); ap.add_argument("--then", help="extra debugger command run after the call (e.g. 'w $6105 1')")
ap.add_argument("--calls", type=int, default=1, help="repeat the call this many times (each at a fresh flip breakpoint)")
ap.add_argument("--wait-before", type=float, default=3)
ap.add_argument("--drive", action="store_true", help="hold joystick up ($6105=1) so the car is moving during and after the call")
ap.add_argument("--noresult-wait", action="store_true")
ap.add_argument("--ref", help="reference file the read-back must equal (default disk/MSTRACKS.TRK); with --hdfile it is also the file copied to C:\\FILES")
a = ap.parse_args()
TRK = Path(a.ref) if a.ref else HERE / "disk" / "MSTRACKS.TRK"
kw = {"tos": TOS[a.tos]} if a.tos else {}
h = Moonshine(snapshot=a.snap, game_dir=a.game, machine=a.machine, memsize_kb=a.mem, **kw)
log = lambda *x: print(*x, flush=True)
try:
    time.sleep(a.wait_before)
    f0 = h.peekw(0x100E); time.sleep(2); f1 = h.peekw(0x100E)
    log(f"race running before: $100e {f0} -> {f1}  $1021={h.peekb(0x1021)} $102c={h.peekw(0x102c)} $5ff8={h.peekw(0x5ff8)} $130c={h.peekw(0x130c)}")
    if a.hdfile:
        (h.R / "C" / "FILES").mkdir(exist_ok=True); shutil.copy(TRK, h.R / "C" / "FILES" / "MSTRACKS.TRK"); log("copied MSTRACKS.TRK to C:\\FILES")
    if a.floppy:
        h.cmd(f"hatari-option --disk-a {Path(a.floppy).resolve()}"); time.sleep(2); log("inserted floppy", a.floppy)
    log("ikbd before: $6102 $6103 $610e $6105 =", [h.peekb(x) for x in (0x6102, 0x6103, 0x610E, 0x6105)])
    if a.drive:
        h.drive(True); time.sleep(4); log(f"driving: $5ff8={h.peekw(0x5ff8)} $130c={h.peekw(0x130c)} $6105={h.peekb(0x6105)}")
    for call in range(a.calls):
        pb = a.path.encode() + b"\0"
        (HERE / "param.bin").write_bytes(struct.pack(">II", a.dest, a.max) + pb)
        (HERE / "apply.txt").write_text(
            f"loadbin {HERE}/trkread.bin $100000\nloadbin {HERE}/callstub.bin $100400\nloadbin {HERE}/param.bin $100500\ne VBL\nr pc=$100400\n")
        (HERE / "end.txt").write_text("e VBL\n")
        n0 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $100436 :trace :once :file {HERE}/end.txt"); time.sleep(0.3)
        h.cmd(f"hatari-debug b pc = $d1ca :trace :once :file {HERE}/apply.txt")
        t0 = time.time()
        while time.time() - t0 < 120:
            time.sleep(0.5)
            txt = h._logtext()[n0:]
            if txt.count("#") >= 2 and "VBL" in txt and txt.count("(dec)") >= 2: break
        txt = h._logtext()[n0:]
        vbls = [int(x) for x in re.findall(r"#(\d+) \(dec\)", txt)]
        log(f"call {call}: VBL at start/end:", vbls, "=> VBL cost", (vbls[-1] - vbls[0]) if len(vbls) >= 2 else "?", f"(wall {time.time() - t0:.1f} s)")
        time.sleep(1)
        o = h.debug("m $100600 12", 0.8); log(o.strip())
        d0 = h.peekl(0x100600); d1 = h.peekl(0x100604); sr = h.peekw(0x100608); mark = h.peekw(0x10060A)
        log(f"d0={d0:#010x} ({d0 - (1 << 32) if d0 >= 1 << 31 else d0})  bytes={d1}  SR at entry={sr:#06x}  done marker={mark:#06x}")
        if d0 == 0 and d1:
            out = HERE / "snap" / "dest.bin"
            h.debug(f"savebin {out} {a.dest:#x} {d1:#x}", 2.0); time.sleep(1)
            got = out.read_bytes(); want = TRK.read_bytes()
            log("data compare:", len(got), "bytes read; equal to MSTRACKS.TRK:", got == want[:len(got)] and len(got) == len(want), "crc", hex(zlib.crc32(got) & 0xffffffff))
        if a.then: log(h.debug(a.then, 0.8).strip())
    log("ikbd after: $6102 $6103 $610e $6105 =", [h.peekb(x) for x in (0x6102, 0x6103, 0x610E, 0x6105)])
    f0 = h.peekw(0x100E); p0 = h.peekw(0x5FF8); time.sleep(3); f1 = h.peekw(0x100E); p1 = h.peekw(0x5FF8)
    log(f"race running after: $100e {f0} -> {f1}  $1021={h.peekb(0x1021)} $5ff8 {p0} -> {p1} $130c={h.peekw(0x130c)} $6105={h.peekb(0x6105)}  vbl {h.vbl()}")
    h.shot(str(HERE / "snap" / "after_call.png"))
    if a.keep_open: input("press enter")
finally:
    h.close()
