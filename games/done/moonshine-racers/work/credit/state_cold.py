"""Cold boot BUILD (HD) / floppy to the race, then per-pass state capture: at every $7b86 (first instruction after the flip, `addq.w #1,$100e`) dump
$1000-$13ff, $29c8-$34ff, $4500-$4fff and $dae6 (the msrabtest STATE ranges, 6,716 B), N passes, keyed by the frame counter $100e.
   python3 state_cold.py hd BUILD OUT.json N [machine mem tos]        |   python3 state_cold.py fl DISK_A OUT.json N [machine mem tos] (disk-2 swap not handled: HD only)"""
import sys, json, re, time
sys.path.insert(0, 'tools')
import msr
from msr import Moonshine, GAME
from stharness import TOS
kind, build, out, npass = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
machine, mem, tos = (sys.argv[5], int(sys.argv[6]), sys.argv[7]) if len(sys.argv) > 7 else ("ste", 1024, "1.62")
RANGES = [(0x1000, 1024), (0x29c8, 2872), (0x4500, 2816), (0xdae6, 4)]
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / build, tos=TOS[tos])
try:
    ok = h.boot_to_race(log=lambda *a: None)
    print("boot_to_race", ok, "vbl", h.vbl(), flush=True)
    h.keypress(57)                       # the race starts with one more SPACE after the position table (tools/play.sh, work/int/cold_int.py)
    t0 = time.time(); fc = []
    while time.time() - t0 < 120:
        time.sleep(3)
        fc.append(h.peekw(0x100e))
        if len(fc) > 3 and fc[-1] > 40: break
    print("race counter samples", fc[-4:], "vbl", h.vbl(), flush=True)
    f = h.R / "state.txt"
    f.write_text("e VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in RANGES))
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
    t0 = time.time()
    while h._logtext()[n0:].count("> e VBL") < npass:
        if time.time() - t0 > 600: break
        time.sleep(1)
    h.debug("b all", 0.5)
    log = h._logtext()[n0:]
finally:
    h.close()
open(out + ".raw", "w").write(log)
res = []
for ht in log.split("> e VBL")[1:]:
    mem_ = {}
    for ln in ht.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): mem_[a + i] = x
    res.append(mem_)
json.dump([{hex(k): x for k, x in mm.items()} for mm in res], open(out, "w"))
print("hits", len(res), "bytes/hit", len(res[0]) if res else 0)
