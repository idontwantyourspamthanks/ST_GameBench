"""Cold boot to the race, SPACE into the race loop, hold up for SECS seconds, sample $100e/$5ff8/$130c/$1226 and the patch sites.
python3 cold_tc.py MACHINE MEM TOS GAMEDIR [secs=120] [mhz=0]"""
import sys, time, re
G = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, G + '/tools'); sys.path.insert(0, G + '/work/hud/build')
from msr import Moonshine
from stharness import TOS
machine, mem, tos, game = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
secs = int(sys.argv[5]) if len(sys.argv) > 5 else 120
mhz = int(sys.argv[6]) if len(sys.argv) > 6 else 0
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=G + '/' + game, tos=TOS[tos])
def rd(addr, n):
    out = h.debug(f"m ${addr:x} {n}", 0.7); g = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return bytes(g[addr + i] for i in range(n))
try:
    ok = h.boot_to_race(log=lambda *a: None)
    print(f"{machine} {mem} KB TOS {tos} {game}: boot_to_race {ok} vbl {h.vbl()}", flush=True)
    print("marker $b2700:", rd(0xb2700, 4).hex(), "sites e406:", rd(0xe406, 6).hex(), "e316:", rd(0xe316, 6).hex(), "17c24:", rd(0x17c24, 6).hex(), "e2e8:", rd(0xe2e8, 6).hex(), "18bf4:", rd(0x18bf4, 6).hex(), "18c86:", rd(0x18c86, 6).hex(), flush=True)
    h.keypress(57); time.sleep(8)
    for k in range(6):
        if h.peekb(0x1021) == 2 and h.peekw(0x100e) > 20: break
        h.keypress(57); time.sleep(5)
    if mhz: h.set_cpuclock(mhz)
    print("race loop: $1021", h.peekb(0x1021), "$100e", h.peekw(0x100e), flush=True)
    h.drive(True)
    t0 = time.time(); v0 = h.vbl(); p0 = h.peekw(0x100e)
    while time.time() - t0 < secs:
        time.sleep(10)
        print(f"t={time.time()-t0:5.0f}s vbl={h.vbl()-v0:6d} $100e={h.peekw(0x100e)} $5ff8={h.peekw(0x5ff8)} $130c={h.peekw(0x130c)} $1226={h.peekb(0x1226)} $1021={h.peekb(0x1021)}", flush=True)
    print("RESULT alive; passes", h.peekw(0x100e), "(from", p0, ")")
    h.shot(G + f'/work/tightC/res/cold_{machine}_{mem}.png')
finally:
    h.close()
