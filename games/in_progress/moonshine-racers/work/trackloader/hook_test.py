#!/usr/bin/env python3
"""Live proof of the stage-2 hook design (trkhook.s) in a restored race snapshot of the patched HD build (>= 2 MB machine).
   Campaign entry 0 = base level 3 + the TRACK BLOCK of level 5 (copied from MS2); entry 1 = base 7 with the stock load of base 7's block; entries 2..14 = stock (base = position).
   The hooks are installed through the debugger at the flip routine; the game's own replay path ($102c bit 7, which skips the title and the shop) restarts the race:
   S1  position 1 (set $102c=$0081): hookA must make $102c = 7 during the race and hookB must take the STOCK path ($58c00 = level 7's block);
   S2  position 0 (the position variable is reset by hand, $102c=$0083): $102c = 3, $58c00 = level 5's block (custom), $57890.len = level 3's;
   S3  normal end of the race ($1024=$ff): the restore gives $102c = position 0 | flags, the campaign loop adds 1 -> $102c = 1 (a naive game would read 3+1 = 4).
   A breakpoint at $7306 (before the campaign loop reads $102c) logs $102c and the position variable at every race return."""
import argparse, re, struct, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
G = HERE.parents[1]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools")); sys.path.insert(0, str(G / "work/trackstudy"))
from msr import Moonshine
from stharness import TOS
import msrtrack as M
ap = argparse.ArgumentParser()
ap.add_argument("--snap", required=True); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=4096); ap.add_argument("--tos")
ap.add_argument("--game", default="/tmp/msrl_dist/MOONSHR"); ap.add_argument("--custom", type=int, default=5, help="level whose track block entry 0 gets")
ap.add_argument("--base", type=int, default=3)
ap.add_argument("--count", type=int, help="ptr variant only: campaign length (site D)")
ap.add_argument("--variant", choices=("copy", "ptr"), default="copy", help="copy = trkhook.s (block copied to $58c00); ptr = trkhook2.s (site C: the block is parsed in place in the store)")
a = ap.parse_args()
# ---- store
blk = M.block(a.custom)[2]
store = bytearray(0x1200 + len(blk))
store[0:4] = b"MSTK"; store[4:6] = struct.pack(">H", 15)
for i in range(15):
    store[8 + 8 * i: 16 + 8 * i] = struct.pack(">BBIH", a.base if i == 0 else (7 if i == 1 else i), 1 if i == 0 else 0, 0x1000 if i == 0 else 0, len(blk) if i == 0 else 0)
store[0x1000:0x1000 + len(blk)] = blk
(HERE / "store.bin").write_bytes(store)
kw = {"tos": TOS[a.tos]} if a.tos else {}
h = Moonshine(snapshot=a.snap, game_dir=a.game, machine=a.machine, memsize_kb=a.mem, **kw)
log = lambda *x: print(*x, flush=True)
def mem(addr, n):
    """m dump parsed to bytes; waits until the last line of the dump is in the log (the debugger answers asynchronously)."""
    n0 = len(h._logtext()); h.cmd(f"hatari-debug m ${addr:x} {n}")
    last = addr + ((n - 1) // 16) * 16
    t = time.time(); out = ""
    while time.time() - t < 8:
        time.sleep(0.15)
        out = h._logtext()[n0:]
        if re.search(rf"^{last:08x}:", out, re.I | re.M):
            time.sleep(0.1); out = h._logtext()[n0:]; break
    b = bytearray()
    for ln in out.splitlines():
        m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})(?:  |$)", ln)
        if m and addr <= int(m.group(1), 16) < addr + n: b += bytes.fromhex(m.group(2).replace(" ", ""))
    return bytes(b[:n])
W = lambda b, o=0: struct.unpack(">H", b[o:o + 2])[0]
def state(tag):
    log(f"[{tag}] $102c={W(mem(0x102c, 2)):#06x} $57890.len={W(mem(0x57890, 2))} $58c00={mem(0x58c00, 12).hex()} $23c0={mem(0x23c0, 4).hex()} $1bbc[0..8]={mem(0x1bbc, 8).hex()} "
        f"$5ff8={W(mem(0x5ff8, 2))} $1021={mem(0x1021, 1).hex()} $100e={W(mem(0x100e, 2))}")
def wait_for(cond, secs=90, step=2.5):
    t0 = time.time()
    while time.time() - t0 < secs:
        time.sleep(step)
        if cond(): return True
    return False
try:
    time.sleep(3)
    state("before")
    stock7 = M.block(7)[2][:12]
    log("custom block (level", a.custom, ") head", blk[:12].hex(), "| level 0 stock head 0190000000960002008cfffe | level 7 stock head", stock7.hex())
    ap_ = HERE / "apply_hook.txt"
    # S1: force the game's own replay path ($102c bit 7) of POSITION 1 (campaign entry 1 = base 7, no custom block -> stock load of level 7's block)
    ap_.write_text(f"""loadbin {HERE}/{"trkhook2.bin" if a.variant == "ptr" else "trkhook.bin"} $100000
loadbin {HERE}/store.bin $110000
w $72c6 $00 $10 $00 $00
w $77da $4e $f9 $00 $10 $01 $00 $4e $71 $4e $71 $4e $71
{"w $fda2 $20 $79 $00 $10 $0f $10" if a.variant == "ptr" else ""}
{f"w $731e $4e $f9 $00 $10 $02 $00{chr(10)}w $100f12 $00 ${a.count:02x}" if a.count else ""}
w $102c $00 $81
w $1024 $ff
e VBL
""")
    (HERE / "at7306.txt").write_text("m $102c 2\nm $100f02 2\ne VBL\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $d1ca :trace :once :file {ap_}"); time.sleep(2)
    h.cmd(f"hatari-debug b pc = $7306 :trace :file {HERE}/at7306.txt")      # every return of the race (before the campaign loop reads $102c)
    ok = wait_for(lambda: W(mem(0x102c, 2)) == 7 and W(mem(0x100e, 2)) > 30 and mem(0x58c00, 12) == stock7)
    state("S1 position 1 (entry 1: base 7, stock block load)"); log("S1 ok (hooks active, $102c = base 7, $58c00 = level 7's stock block):", ok)
    h.shot(str(HERE / "snap" / "hook_S1_pos1_base7_stock.png"))
    # S2: end it with the replay flag after resetting the POSITION variable to 0 -> position 0 = base 3 + level 5's custom block
    h.debug("w $100f02 $00 $00", 0.5); h.debug("w $102c $00 $83", 0.5); h.debug("w $1024 $ff", 0.5)
    ok = wait_for(lambda: W(mem(0x102c, 2)) == a.base and W(mem(0x100e, 2)) > 30 and mem(0x58c00, 4) == blk[:4])
    state("S2 position 0 (entry 0: base 3 + level 5's block)"); log("S2 ok:", ok)
    log("stream pointers $1bb0 $1bb4 $27da $133a $1342:", [mem(x, 4).hex() for x in (0x1bb0, 0x1bb4, 0x27da, 0x133a, 0x1342)])
    # the game's own setup ($ff3a) filled the curve ring $1bbc from the block it parsed: compare with the decoder's expansion of level 5's curve stream
    t5, _b = M.parse(a.custom); exp = [int(v) & 0xffff for v in M.curve_arrays(t5)[:1024]]
    ring = mem(0x1bbc, 2048); got = [W(ring, 2 * i) for i in range(len(ring) // 2)]
    log(f"curve ring $1bbc: {len(got)} words read, first 8 {[hex(x) for x in got[:8]]}; equal to the decoded curve of level {a.custom} (first {len(got)}): {got == exp[:len(got)]}  (the decoded curve of level {a.base} would be {[hex(int(v) & 0xffff) for v in M.curve_arrays(M.parse(a.base)[0])[:4]]}...)")
    h.shot(str(HERE / "snap" / f"hook_S2_{a.variant}_pos0_base3_block5.png"))
    # S3: end the race normally: the restore must give position 0, the campaign loop adds 1 -> $102c = 1 (the shop screen follows); without the restore it would be 4
    h.debug("w $1024 $ff", 0.5)
    ok = wait_for(lambda: W(mem(0x102c, 2)) == 1)
    state("S3 race ended normally"); log("S3 ok ($102c = 1 = position 0 restored + 1; naive would be 4):", ok)
    h.shot(str(HERE / "snap" / "hook_S3_after_race.png"))
    lines = h._logtext()[n0:].splitlines(); pairs = []
    for i, l in enumerate(lines):
        if re.match(r"00100F02:", l, re.I) and i > 1 and re.match(r"0000102C:", lines[i - 2], re.I) and lines[i - 1].startswith("> m $100f02"): pairs.append((lines[i - 2][10:16].replace(" ", ""), l[10:16].replace(" ", "")))
    log("every return of the race ($7306 breakpoint: $102c as the campaign loop will read it, position variable):", pairs)
finally:
    h.close()
