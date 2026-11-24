"""Cold boot a build on machine/TOS/RAM/clock; report in_race, marker, exceptions logged.
python3 work/mste/boot.py MACHINE MEM TOS GAMEDIR CLOCK [timeout] [--trace]"""
import sys, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/tools')
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from msr import Moonshine, GAME
from stharness import TOS
machine, mem, tos, game, clock = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
timeout = float(sys.argv[6]) if len(sys.argv) > 6 and not sys.argv[6].startswith('--') else 300
extra = ['--cpuclock', clock]
if '--trace' in sys.argv: extra += ['--trace', 'cpu_exception']
if '++' in sys.argv: extra += sys.argv[sys.argv.index('++') + 1:]
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / game, tos=TOS[tos], extra=extra)
try:
    ok = h.boot_to_race(timeout=timeout, log=lambda *a: None)
    print(f"RESULT {machine} {mem}KB TOS {tos} clk {clock} build {game}: in_race={ok} vbl={h.vbl()}", flush=True)
    print(h.debug("m $b2700 16", 0.8).strip())
    log = h._logtext()
    print("log lines:", len(log.splitlines()))
    for ln in log.splitlines():
        if re.search(r"bus error|address error|exception|WARN|ERROR|halt", ln, re.I): print("LOG", ln)
    if ok:
        h.keypress(57); time.sleep(8)
        for _ in range(6):
            if h.peekb(0x1021) == 2 and h.peekw(0x100e) > 20: break
            h.keypress(57); time.sleep(5)
        h.drive(True); time.sleep(20)
        a = h.debug("m $b8f38 4", 0.8).strip().splitlines()[-1]; v0 = h.vbl(); time.sleep(10)
        b = h.debug("m $b8f38 4", 0.8).strip().splitlines()[-1]; v1 = h.vbl()
        print("RACE $1021", h.peekb(0x1021), "$100e", h.peekw(0x100e), "pos", h.peekw(0x5ff8), "extras counter", a, "->", b, f"over {v1-v0} VBL")
        h.shot(str(h.R / "race.png")); print("SHOT", h.R / "race.png")
    print("SCRATCH", h.R)
finally:
    h.close()
