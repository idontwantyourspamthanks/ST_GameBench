"""STE 2 MB HD play test (~3 min wall): commands by mouse/keys incl. two in a row, tooltips, HAGA statesave."""
import re, shutil, sys, time
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2")
sys.path[:0] = [str(G / "tools"), "/home/ryan/Code/AtariST/gamebench/tools"]
from populous2 import Populous2, HOME
import p2tick as TK
BAD = re.compile(r"bus error|address error|exception [23] |halt|double|illegal", re.I)
S = G / "work/shots"
h = Populous2(game_dir=G / "build/Pop2Release")
def pt(x, y):  # ST coords -> screenshot px
    return HOME[0] + 2 * x, HOME[1] + 2 * y
def q(): return [h.peekl(TK.D + o) for o in (0x48, 0x4C, 0x50)]
try:
    ok = h.boot_to_game(); print("in_play", ok, "marker", h.marker(), "turn", h.peekw(h.TURN), flush=True)
    t_start = time.time()
    q0 = q(); print("queue QPUSH/QPOP/QDROP before", [hex(v) for v in q0])
    # executor dispatch log: every command the executor runs (d0 = command)
    f = h.R / "disp.txt"; f.write_text("e d0\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = $292f8 :trace :file {f}"); time.sleep(0.5)
    mark = len(h._logtext())
    def clickat(x, y, hold=0.25):
        h.goto(*pt(x, y), HOME); h.click(hold=hold)
    # 1) F-keys (category selects)
    for i, k in enumerate(["F1", "F2", "F3", "F4", "F5", "F6"]):
        h.key(k, 0.4); time.sleep(0.8)
    h.shot(str(S / "rel_play_fkeys.png"))
    # 2) effects by mouse: earth category icon, effect slot, then click on the map
    for (cx, cy) in [(59 + 16 * 2, 145 + 8 * 2)]:
        clickat(cx, cy); time.sleep(1.0)
    clickat(42 + 16 * 1, 159 + 8 * 1); time.sleep(1.0)       # an effect slot
    h.shot(str(S / "rel_play_effect_sel.png"))
    clickat(190, 110); time.sleep(2.0)                         # on the map
    clickat(150, 120); time.sleep(2.0)
    # 3) behaviours: strip icons (317-16k, 148+8k), each alone, with a tooltip shot
    for k in (2, 3, 4, 5, 6):
        h.goto(*pt(317 - 16 * k, 148 + 8 * k), HOME); time.sleep(1.5)
        h.shot(str(S / f"rel_play_tooltip_strip{k}.png"))
        h.click(hold=0.25); time.sleep(1.5)
        print(f"strip {k}: turn {h.peekw(h.TURN)} mode {h.peekw(h.MODE):#x}", flush=True)
    # 4) two commands quickly in a row: click strip 3, nudge one icon over, click strip 4 within ~0.3 s wall
    h.goto(*pt(317 - 16 * 3, 148 + 8 * 3), HOME); time.sleep(0.8)
    for rep in range(4):
        h._xdo("mousedown", "1"); time.sleep(0.08); h._xdo("mouseup", "1")
        h._xdo("mousemove_relative", "--", "-32", "16"); time.sleep(0.05)   # next icon (-16 x, +8 y in ST px)
        h._xdo("mousedown", "1"); time.sleep(0.08); h._xdo("mouseup", "1")
        time.sleep(1.2)
        h._xdo("mousemove_relative", "--", "32", "-16"); time.sleep(0.6)
    # keyboard + mouse in the same instant: F-key then click effect/ map
    for rep in range(3):
        h.key("F3", 0.12); h._xdo("mousedown", "1"); time.sleep(0.08); h._xdo("mouseup", "1"); time.sleep(1.5)
    # keypad commands (fight / magnet keys)
    for k in ("KP_Divide",):
        pass
    # 5) tooltips on each category and effect
    for name, (x, y) in [("cat0", (59, 145)), ("cat1", (75, 153)), ("cat5", (139, 185)), ("eff2", (74, 175))]:
        h.goto(*pt(x, y), HOME); time.sleep(2.0); h.shot(str(S / f"rel_play_tt_{name}.png"))
    h.goto(*pt(160, 100), HOME)
    print("turn before idle", h.peekw(h.TURN), "mode", hex(h.peekw(h.MODE)))
    # let it play until ~170 s
    while time.time() - t_start < 170: time.sleep(5)
    log = h._logtext()[mark:]
    disp = re.findall(r"> e d0\n(?:  .*\n)*= (\S+) \(bin\), #(\d+)", log)
    print("executor dispatches:", len(disp), [int(d[1]) for d in disp])
    print("breakpoint hits line:", re.findall(r"matched (\d+) times", log)[-1:] )
    q1 = q(); print("queue after", [hex(v) for v in q1], "delta push/pop/drop", [b - a for a, b in zip(q0, q1)])
    print("turn", h.peekw(h.TURN), "in_play", h.in_play(), "marker", h.marker())
    h.shot(str(S / "rel_play_end.png"))
    # HAGA statesave
    turn_save = h.peekw(h.TURN)
    h.key("KP_Divide", 0.6)
    gs = h.R / "C" / "GS00.TOS"
    for _ in range(60):
        time.sleep(2)
        if gs.exists():
            s1 = gs.stat().st_size; time.sleep(3)
            if gs.stat().st_size == s1 and s1 > 1_000_000: break
    print("statesave: GS00.TOS", gs.stat().st_size if gs.exists() else "NONE", "turn at save", turn_save, "in_play after", h.in_play(), "turn", h.peekw(h.TURN))
    if gs.exists(): shutil.copy(gs, "/tmp/GS00.TOS")
    allb = [l for l in h._logtext().splitlines() if BAD.search(l)]
    print("bus/address errors in log:", len(allb)); print("\n".join(allb[:6]))
finally:
    shutil.copy(h.logpath, G / "work/gates/rel_play.log")
    h.close()
