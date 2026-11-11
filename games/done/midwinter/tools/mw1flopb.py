#!/usr/bin/env python3
"""Drive-B experiments for the Midwinter 1 floppy set (see work/notes/floppy_driveb.md).

    python3 tools/mw1flopb.py NAME MACHINE TOS MEM_KB DISKDIR MODE [--tail S] [--fastfdc] [--wp] [--a MWA] [--b MWB] [--bp PC,PC] [--nob]

MODE (where MWB goes):
  swapA     at the 'Insert graphics disk' prompt, drive A -> MWB          (the documented route)
  insB      at the prompt, MWB is inserted into drive B (A keeps MWA)    (user report)
  startB    MWB is in drive B from power-on (A = MWA)
  swapBoth  at the prompt, MWB into B and MWA removed from A
  none      nothing is changed (A = MWA, B empty)
  lateswapA nothing at the first prompt; at the dark retry prompt drive A -> MWB (one-drive user who pressed a key too early)
Keys: space every 4 s after 20 s (like mw1floppy.py).  Shots every 4 s into /tmp/mw1fb_NAME/.
Exit 0 when the Game Options screen is reached.
"""
import shutil, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mw1harness import MW1, TOS, REF  # noqa: E402

a = sys.argv[1:]
name, machine, tos, mem, diskdir, mode = a[:6]
tail = float(a[a.index("--tail") + 1]) if "--tail" in a else 150
fast = "--fastfdc" in a
wp = "--wp" in a
srcA = a[a.index("--a") + 1] if "--a" in a else "MWA"
srcB = a[a.index("--b") + 1] if "--b" in a else "MWB"
out = Path("/tmp") / f"mw1fb_{name}"
shutil.rmtree(out, ignore_errors=True)
out.mkdir()
log = open(f"/tmp/mw1fb_{name}.log", "w")


def L(*x):
    s = " ".join(str(v) for v in x)
    print(s, flush=True)
    log.write(s + "\n")


def find(d, stem):
    for ext in (".st", ""):
        p = Path(d) / (stem + ext)
        if p.exists():
            return p
    raise SystemExit("no image " + stem)


scratch = Path(tempfile.mkdtemp(prefix="mw1fb-"))
shutil.copy(find(diskdir, srcA), scratch / "mwboot.st")
shutil.copy(find(diskdir, srcB), scratch / "mwgfx.st")
shutil.copy(find(diskdir, "MWC"), scratch / "mwdata.st")
empty = scratch / "empty"
empty.mkdir()
extra = ["--disk-a", str(scratch / "mwboot.st"), "--fastfdc", "yes" if fast else "no"]
if mode == "startB":
    extra += ["--disk-b", str(scratch / "mwgfx.st")]
if "--nob" in a:
    extra += ["--drive-b", "false"]
if wp:
    extra += ["--protect-floppy", "on"]
h = MW1(game_dir=empty, snapshot=None, machine=machine, tos=TOS[tos], memsize_kb=int(mem), autorun="", extra=extra)

bps = [x for x in a[a.index("--bp") + 1].split(",")] if "--bp" in a else []
for i, pc in enumerate(bps):
    cf = scratch / f"bp{i}.txt"
    cf.write_text("r\nm $258a2 4\nm $2c4d2 2\nm $ff8800 4\n")
    h.cmd(f"hatari-debug b pc = ${pc} :trace :file {cf}")
    time.sleep(0.5)

try:
    L("cell", name, machine, tos, mem, "KB", mode, "fastfdc" if fast else "realfdc")
    t0 = time.time()
    n = 0
    ok = False
    stage = 0            # 0 wait bright prompt, 1 key pressed (wait for Options / dark retry prompt), 2 swapped late
    t_key = None
    dark_at = None
    while time.time() - t0 < 300 and not ok:
        time.sleep(2)
        n += 1
        try:
            h.shot(str(out / f"s{n:03d}.png"))
        except RuntimeError as e:
            L("shot failed", e)
        if h.at_options():
            ok = True
            break
        if stage == 0 and h.matches(REF / "insert_graphics_bright.png", (320, 255, 510, 285)):
            L("bright prompt at %.0f s (shot s%03d)" % (time.time() - t0, n))
            if mode == "swapA":
                h.cmd(f"hatari-option --disk-a {scratch / 'mwgfx.st'}")
            elif mode == "insB":
                h.cmd(f"hatari-option --disk-b {scratch / 'mwgfx.st'}")
            elif mode == "swapBoth":
                h.cmd(f"hatari-option --disk-b {scratch / 'mwgfx.st'}")
                time.sleep(1)
                h.cmd("hatari-option --disk-a none")
            time.sleep(2)
            h.keypress(57)
            t_key = time.time()
            stage = 1
        elif stage == 1 and h.matches(REF / "insert_graphics.png", (320, 255, 510, 285)):
            if dark_at is None:
                dark_at = time.time() - t_key
                L("dark retry prompt %.0f s after the key (shot s%03d)" % (dark_at, n))
            if mode == "lateswapA":
                L("drive A -> MWB, key")
                h.cmd(f"hatari-option --disk-a {scratch / 'mwgfx.st'}")
                time.sleep(2)
                h.keypress(57)
                stage = 2
            elif mode in ("none", "noneKeep"):
                time.sleep(tail)
                break
        if stage == 2 and n % 3 == 0:
            h.keypress(57)
        if t_key and time.time() - t_key > tail + 150:
            break
    L("options reached:", ok, "t=%.0f s" % (time.time() - t0), "key->options %.0f s" % (time.time() - t_key) if t_key else "")
    menu = a[a.index("--menu") + 1] if "--menu" in a else None
    if ok and menu:
        # jump into the game's save ($FAE0) / load ($FC18) menu from the Options screen, swap drive A to MWC at the prompt
        entry = {"load": 0xfc18, "save": 0xfae0}[menu]
        h.debug(f"r pc=${entry:x}", wait=1.5)
        time.sleep(6)
        h.shot(str(out / "menu1_prompt.png"))
        h.cmd(f"hatari-option --disk-a {scratch / 'mwdata.st'}")
        time.sleep(2)
        h.keypress(57)
        time.sleep(15)
        h.shot(str(out / "menu2_list.png"))
        if "--slot" in a:                  # click the first game slot (save: writes drive A = the MWC copy)
            h.goto(224, 160)
            h.click()
            time.sleep(25)
            h.shot(str(out / "menu_slot.png"))
            h.cmd("hatari-option --disk-a none")
            time.sleep(3)
            ref = Path(find(diskdir, "MWC")).read_bytes()
            now = (scratch / "mwdata.st").read_bytes()
            L("MWC copy after slot click: %d bytes differ from the original image" % sum(1 for x, y in zip(ref, now) if x != y))
        if "--back" in a:                  # leave the menu with the bottom-left icon, then 'Insert graphics disk'
            h.goto(128, 424)
            h.click()
            time.sleep(8)
            h.shot(str(out / "menu3_back_prompt.png"))
            if "--backswap" in a:
                h.cmd(f"hatari-option --disk-a {scratch / 'mwgfx.st'}")
                time.sleep(2)
            h.keypress(57)
            time.sleep(30)
            h.shot(str(out / "menu4_after.png"))
            L("after back: marker/cursor regs:", h.debug("r", wait=1.5).replace("\n", " | ")[-260:])
        else:
            h.keypress(57)
            time.sleep(8)
            h.shot(str(out / "menu3.png"))
        L("menu shots written; regs:", h.debug("r", wait=1.5).replace("\n", " | ")[-300:])
    h.shot(str(out / "final.png"))
    try:                                   # floppy_driveb state: cur, pref, tried, known[2], pos[2] (words) right before `tried`+2
        blob = (Path(diskdir) / "MWA.st").read_bytes()[0x58200 + 0x6400: 0x58200 + 0x6406]
        if blob[:2] == bytes.fromhex("4279"):
            tried = int.from_bytes(blob[2:6], "big")
            L("driveb vars cur/pref/tried/known/pos:", h.debug(f"m ${tried - 4:x} 16", wait=1.5).strip().splitlines()[-1])
    except Exception as e:
        L("no driveb vars:", e)
    L("final regs:", h.debug("r", wait=1.5).replace("\n", " | ")[-700:])
    if bps:
        Path(f"/tmp/mw1fb_{name}.dbg").write_text(h._logtext())
finally:
    h.close()
sys.exit(0 if ok else 1)
