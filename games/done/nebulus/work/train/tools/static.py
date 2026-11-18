import sys, time, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus'); SH = G / 'work/train/shots/gate'
label, game = sys.argv[1], Path(sys.argv[2]).resolve()
h = Nebulus(workdir=f'/tmp/strun-ntg-{label}', game=game)
def grab(addr, n):
    p = f'/tmp/ntg_{label}.bin'; Path(p).unlink(missing_ok=True)
    h.debug(f"savebin {p} ${addr:x} ${n:x}", 0.6)
    for _ in range(30):
        if Path(p).exists() and Path(p).stat().st_size == n: break
        time.sleep(0.2)
    d = Path(p).read_bytes(); Path(p).unlink(); return d
try:
    print(f'[{label}] boot_to_game', h.boot_to_game(timeout=120))
    mk = grab(0xB0020, 6); print(f'[{label}] marker {mk[:4]} count {struct.unpack(">H", mk[4:6])[0]}; $3b0a4 {grab(0x3b0a4,10).hex()}; $3792c {grab(0x3792c,6).hex()}; $76c00 {grab(0x76c00,4).hex()}')
    for i in range(6):
        t = struct.unpack('>3H', grab(0x3ad98, 6)); st = struct.unpack('>4H', grab(0x3398c, 8)); run = struct.unpack('>H', grab(0x33938, 2))[0]; pl = struct.unpack('>H', grab(0x33a20, 2))[0]
        print(f'[{label}] s{i}: timer {t} states {st} run {run} player {pl}', flush=True)
        if i == 2: h.shot(str(SH / f'{label}_s.png'))
        time.sleep(3.0)
finally:
    h.close()
