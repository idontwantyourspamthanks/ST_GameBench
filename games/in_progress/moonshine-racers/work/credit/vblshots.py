"""Deterministic screen capture by VBL count (cold boot, no input): at each given VBL the debugger saves $70000-$77FFF and $78000-$7FFFF (both screen
buffers) and the palette/video registers; screens are decoded afterwards.
  python3 vblshots.py hd|fl BUILD OUTDIR MACHINE MEM TOS VBL [VBL ...]      e.g.  hd build/credit_hd out ste 1024 1.62 2500 2520
For --cpu 16 (Mega STE boots at 8 MHz, switched at VBL 200 like tools/play.sh) set env CPU=16."""
import sys, time, os, re
sys.path.insert(0, 'tools')
from pathlib import Path
import msr
from stharness import TOS
kind, build, out, machine, mem, tos = sys.argv[1:7]
vbls = [int(x) for x in sys.argv[7:]]
REL = bool(os.environ.get("REL"))      # REL=1: the numbers are VBLs after the first execution of $78524 (stage 1 has just drawn the title picture)
os.makedirs(out, exist_ok=True)
out = os.path.abspath(out)
if kind == "hd":
    from msr import Moonshine, GAME
    h = Moonshine(machine=machine, memsize_kb=int(mem), game_dir=GAME / build, tos=TOS[tos])
else:
    from msrfloppy import mk
    h = mk(build, machine=machine, mem=int(mem), tos=tos)
try:
    if os.environ.get("CPU"):
        f = h.R / "clk.txt"; f.write_text(f"setopt --cpuclock {os.environ['CPU']}\n")
        h.cmd(f"hatari-debug b VBL > 200 :trace :once :file {f}")
    if REL:
        f0 = h.R / "rel.txt"; f0.write_text("e VBL\n")
        st0 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $78524 :trace :once :file {f0}")
        t = time.time()
        while "#" not in h._logtext()[st0:].split("e VBL")[-1] or "(dec)" not in h._logtext()[st0:]:
            time.sleep(0.5)
            if time.time() - t > 900: raise TimeoutError("$78524 never reached")
        import re as _re
        v0 = int(_re.findall(r"#(\d+) \(dec\)", h._logtext()[st0:])[-1])
        print("stage 1 hook site reached at VBL", v0, flush=True)
        vbls = [v0 + n for n in vbls]
    for n in vbls:
        f = h.R / f"cap_{n}.txt"
        f.write_text(f"m $ff8200 16\nm $ff8240 32\nsavebin {out}/{n}_70000.bin $70000 $8000\nsavebin {out}/{n}_78000.bin $78000 $8000\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {n} :trace :once :file {f}")
        t = time.time()
        while not (os.path.exists(f"{out}/{n}_78000.bin") and "Removed CPU breakpoint" in h._logtext()[start:]):
            time.sleep(0.3)
            if time.time() - t > 200:
                raise TimeoutError(f"VBL {n} never reached")
        time.sleep(0.6)
        Path(f"{out}/{n}.log").write_text(h._logtext()[start:])
        print(n, "ok", flush=True)
finally:
    h.close()
