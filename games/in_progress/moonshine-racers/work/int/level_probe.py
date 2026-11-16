"""Other track at the time-out restart: snapshot race_drive, live patch (integrated default set, tick off), poke $102c=LEVEL at the apply instant.
The game's time-out restart ($7306: bit 7 of $102c set -> andi #$f -> replay that level) re-runs the race setup for the poked level: $135a is set from the
colour table list $1362 at $7890, then rd_init runs the generators.  Reports hits of rd_init / gen_static / gen_pt / gen_win / race loop with the VBL,
and after the restart $102c, $135a, WPTR, magic, PM, $1316 (+ a change-watch on $1316 and $135a for the whole run).
python3 level_probe.py LEVEL [SNAP]"""
import sys, time, re, json
sys.path.insert(0, 'tools')
import msrabtest as ab
from msr import Moonshine, GAME
level = int(sys.argv[1]); snap = ab.snap_path(sys.argv[2] if len(sys.argv) > 2 else "race_drive")
names = ["mr_edge", "mr_map", "mr_digit", "rd_geom", "rd_draw", "rd_init"]
live = ab.with_pokes(ab.live_build(names), [f"102c={level:04x}"] if level >= 0 else [], f"lp{level}")
h = Moonshine(snapshot=snap)
try:
    time.sleep(1.5)
    ab.apply_live(h, live, 0x7A88)
    sc = h.R / "vbl.txt"; sc.write_text("e VBL\nm $102c 2\nm $135a 4\nm $1316 2\n")
    h.debug("b all", 0.3)
    for pc in (0xb6000, 0xb43cc, 0xb4424, 0xb567e, 0x78fc):
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {sc}")
    h.cmd(f"hatari-debug b ($1316).w ! ($1316).w :trace :file {sc}")
    h.cmd(f"hatari-debug b ($135a).l ! ($135a).l :trace :file {sc}")
    t0 = time.time()
    while time.time() - t0 < 240:
        time.sleep(5)
        if re.search(r"^pc = \$78fc :trace", h._logtext(), re.M): break
    time.sleep(10)
    log = h._logtext()
    h.debug("b all", 0.5)
    i = log.find("Removed CPU breakpoint")
    for ln in log[i:].splitlines():
        if ln.strip() and not ln.startswith("> b") and "Warning" not in ln and "Changed back" not in ln:
            print(ln.strip()[:150])
    def mm(a, n): return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
    print("AFTER:", mm(0x102c, 2), "|", mm(0x135a, 4), "|", mm(0x1316, 2), "|", mm(0xd0000, 8), "|", mm(0xe7040, 4), "| $100e", mm(0x100e, 2))
finally:
    h.close()
