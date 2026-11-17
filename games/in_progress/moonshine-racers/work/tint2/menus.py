"""Menu / mouse exploration: cold boot a game dir (HD) and walk the screens to the race, sampling the game mode byte $1021, the pass counter $100e and the IKBD mouse
variables $6106-$6117 on every screen; at every screen move the (Xvfb) host mouse and click, then sample again (does the game see the mouse?).
python3 menus.py GAMEDIR TAG [stock]   (GAMEDIR relative to the game root; `stock` = originals/MOONSHR)
Screenshots work/tint2/shots/menu_<TAG>_NN_{a,b}.png (a = before the mouse input, b = after the move + click)."""
import sys, time, re
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build")
from mxlib import *
from msr import Moonshine, GAME
gd, tag = sys.argv[1], sys.argv[2]
h = Moonshine(game_dir=GAME / gd)
OUT = GAME / "work/tint2/shots"; OUT.mkdir(parents=True, exist_ok=True)
def rd(a, n):
    out = h.debug(f"m ${a:x} {n}", 0.7); g = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            x = int(m.group(1), 16)
            for i, b in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[x + i] = b
    return bytes(g[a + i] for i in range(n))
def sample(lbl):
    v = h.vbl(); m = rd(0x6100, 24)
    print(f"{lbl:14s} vbl {v:6d} $1021={h.peekb(0x1021)} $100e={h.peekw(0x100e):5d} joy $6105={m[5]:02x} mouse $6106={m[6:12].hex()} $610c={m[12:15].hex()} $610f-$6117={m[15:24].hex()}", flush=True)
try:
    t0 = time.time(); n = 0; last_mode = None
    while time.time() - t0 < 500:
        time.sleep(4)
        v = h.vbl()
        if v < 5000:
            continue
        mode, p = h.peekb(0x1021), h.peekw(0x100e)
        sample(f"screen {n:02d}")
        h.shot(str(OUT / f"menu_{tag}_{n:02d}_a.png"))
        # host mouse: move + click on this screen, then look at the game's mouse variables
        h.center(); time.sleep(0.5)
        h.rel(60, 40); time.sleep(0.8)
        sample("  after move")
        h.click("1"); time.sleep(1.0)
        sample("  after click")
        h.shot(str(OUT / f"menu_{tag}_{n:02d}_b.png"))
        n += 1
        if mode == 2 and p > 40:
            print("race loop reached", flush=True)
            break
        h.keypress(57)
    print("done", flush=True)
finally:
    h.close()
