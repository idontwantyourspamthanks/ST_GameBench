"""Cold boot of build/int_rd (default HD set + rd_geom rd_draw rd_init): when do the road generators run relative to the race loop?
Breakpoints (trace + `e VBL` script): rd_init entry $B6000, its return $78fc, gen_static, gen_pt, gen_win (rd_geom/rd_draw generators), race loop first instruction $7a88.
Usage: init_probe.py BUILD [machine mem]"""
import sys, time, re
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
build = sys.argv[1]; machine = sys.argv[2] if len(sys.argv) > 2 else "ste"; mem = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / build)
try:
    sc = h.R / "vbl.txt"; sc.write_text("e VBL\n")
    for name, pc in (("rd_init", 0xb6000), ("after_init", 0x78fc), ("gen_static", int(sys.argv[4], 16) if len(sys.argv) > 4 else 0xb43cc), ("gen_pt", 0xb4424), ("gen_win", 0xb567e), ("loop7a88", 0x7a88)):
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {sc}")
    print("in_race", h.boot_to_race(log=lambda *a: None), "vbl", h.vbl())
    h.keypress(57); time.sleep(8)
    print("after SPACE vbl", h.vbl(), "$100e", h.peekw(0x100e))
    log = h._logtext()
    keep = [l for l in log.splitlines() if "pc = $" in l or "#" in l and "(dec)" in l]
    # compress: print trace line + following VBL
    out = []
    for l in keep:
        out.append(l.strip())
    seen = {}
    print("\n".join(out[:80]))
    print("magic $d0000:", h.debug("m $d0000 4", 0.6).strip().splitlines()[-1], "| WPTR $e7040:", h.debug("m $e7040 4", 0.6).strip().splitlines()[-1], "| PM $d0004:", h.debug("m $d0004 4", 0.6).strip().splitlines()[-1], "| marker:", h.debug("m $b2700 4", 0.6).strip().splitlines()[-1])
finally:
    h.close()
