# WW1 HD on the Falcon (GEMDOS folder): LOAD click with a swept hold time; after each load: the "left button held" latch $2edbc with the button UP, then one OPTION click.
import sys, time, re, os
from pathlib import Path
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1/tools")
import pmww, wwhd
hd, wd, mach = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
holds = [float(x) for x in sys.argv[4].split(",")]
trace = len(sys.argv) > 5 and sys.argv[5] == "trace"
kw = dict(machine=mach, tos=pmww.TOS["4.04" if mach == "falcon" else "1.62"], memsize_kb=4096 if mach == "falcon" else 1024)
if mach == "falcon": kw["extra"] = ["--borders", "false"]
h = wwhd.PMWHD(hd, workdir=wd, **kw)
HELD, LATCH = 0x2EDBC, 0x2EDB6
def idle(t=60):
    t0 = time.time()
    while time.time() - t0 < t and not (h.peekw(pmww.WINDOW_OPEN) == 0 and h.ticking(1.0)): time.sleep(1)
def close_window():
    for _ in range(3):
        if h.peekw(pmww.WINDOW_OPEN) == 0: return
        h.click_st(200, 60, hold=0.6, wait=2.0)
def arm():
    for k, a, sc in (("d", 0x86e, "e VBL\ne HBL\n"), ("p", 0x75c00, "e VBL\ne HBL\nm $1d2b1 1\n"), ("v", 0x788, "e VBL\ne HBL\nm $1d2af 1\nm $2edbc 2\n"), ("s", 0x7740c, "e VBL\ne HBL\n")) + ((("x", int(os.environ["STUB"], 16), "e VBL\ne HBL\n"),) if os.environ.get("STUB") else ()):
        (h.R / f"t{k}.txt").write_text(sc)
        h.cmd(f"hatari-debug b pc = ${a:x} :trace :file {h.R / f't{k}.txt'}"); time.sleep(0.15)
def timeline(txt):
    ev = []
    for b in txt.split("Reading debugger commands from '")[1:]:
        k = b.split("'", 1)[0].rsplit("/", 1)[-1]
        n = re.findall(r"#(\d+) \(dec\)", b); m = re.findall(r"^[0-9A-F]{8}: ((?:[0-9a-f]{2} ?)+)", b, re.M)
        if len(n) < 2: continue
        ev.append((k[1], int(n[0]), int(n[1]), [x.strip() for x in m]))
    return ev
def show(ev):
    name = {"d": "VBL handler sends $0D", "p": "packet complete, buttons", "v": "VBL handler dispatch $1d2af / held $2edbc", "s": "hd_sector entry", "x": "pending VBL taken by the rte stub of hd_core replay"}
    i0 = next((i for i, e in enumerate(ev) if e[0] == "p" and e[3] and e[3][0] != "00"), 0)
    last = max((i for i, e in enumerate(ev) if e[0] == "s"), default=i0)
    for k, v, hb, m in ev[max(0, i0 - 3):last + 16]:
        print(f"    vbl {v} hbl {hb:3d}  {name[k]} {' / '.join(m)}")
try:
    h.boot_to_options(log=print); time.sleep(2)
    h.options_to_map(noprot=True, swap=False, log=print); time.sleep(2)
    h.click_st(*pmww.OPTION_XY, hold=0.6, wait=2.0); h.click_st(*pmww.FILE_BTN_XY, hold=0.6, wait=2.0); h.click_st(*pmww.SAVE_BTN_XY, hold=0.6, wait=4.0)
    idle(); time.sleep(2)
    print(f"saved (hold 0.6): held={h.peekw(HELD)} window={h.peekw(pmww.WINDOW_OPEN):#x} slot flag on disk={h.host_savedisk()[pmww.SLOT_FLAG_OFF]:#x}", flush=True)
    for hold in holds:
        close_window(); idle()
        h.click_st(*pmww.OPTION_XY, hold=0.6, wait=2.0); w1 = h.peekw(pmww.WINDOW_OPEN)
        h.click_st(*pmww.FILE_BTN_XY, hold=0.6, wait=2.0)
        h.goto_st(*pmww.LOAD_BTN_XY)
        mark = len(h._logtext())
        if trace: arm()
        v0 = h.vbl(); h.click(hold=hold); time.sleep(3.0)
        if trace: h.debug("b all", 0.5)
        idle(); time.sleep(1.0)
        held = h.peekw(HELD)
        txt = h._logtext()[mark:]
        h.click_st(*pmww.OPTION_XY, hold=0.2, wait=2.0)
        op = h.peekw(pmww.WINDOW_OPEN) != 0
        print(f"LOAD hold {hold:.2f} s (option window before: {w1:#x}): button up, held latch $2edbc = {held} -> next OPTION click {'opens the window' if op else 'LOST'}; held after = {h.peekw(HELD)}", flush=True)
        if trace and (held or hold == holds[0]): show(timeline(txt))
finally:
    h.close()
