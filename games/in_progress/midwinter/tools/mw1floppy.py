#!/usr/bin/env python3
"""Floppy-boot test cell for Midwinter 1 (cold boot from MWA, MWB in the second drive).

    python3 tools/mw1floppy.py NAME MACHINE TOS MEM_KB DISKDIR [--live PREFIX] [--team] [--shots]

DISKDIR holds MWA.st MWB.st (MWC.st optional).  Drive A boots MWA and is swapped to MWB when the game
shows "Insert graphics disk" (work/ref/insert_graphics.png) -- see work/notes/floppy.md.
Prints the marker ($B2FF8) and, with --live, compares the payload and site bytes as mw1cell.py does.
"""
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mw1harness import MW1, TOS, REF  # noqa: E402

a = sys.argv[1:]
name, machine, tos, mem, diskdir = a[:5]
live = a[a.index("--live") + 1] if "--live" in a else None
team = "--team" in a
shots = "--shots" in a
out = Path("/tmp") / f"mw1fl_{name}"
shutil.rmtree(out, ignore_errors=True)
out.mkdir()
log = open(f"/tmp/mw1fl_{name}.log", "w")


def L(*x):
    s = " ".join(str(v) for v in x)
    print(s, flush=True)
    log.write(s + "\n")


scratch = Path(tempfile.mkdtemp(prefix="mw1fl-"))
# NOT A.st/B.st: Hatari's bAutoInsertDiskB would put B.st into drive B when A.st is in drive A
for src, dst in (("MWA.st", "mwboot.st"), ("MWB.st", "mwgfx.st")):
    shutil.copy(Path(diskdir) / src, scratch / dst)
empty = scratch / "empty"
empty.mkdir()
img = spec = None
if live:
    img = Path(live + ".img").read_bytes()
    spec = json.loads(Path(live + ".json").read_text())
h = MW1(game_dir=empty, snapshot=None, machine=machine, tos=TOS[tos], memsize_kb=int(mem), autorun="",
        extra=["--disk-a", str(scratch / "mwboot.st")])


def checks(stage):
    L(f"[{stage}] marker:", h.debug("m $b2ff8 4").strip().splitlines()[-1])
    if img is None:
        return
    p = out / f"{stage}_payload.bin"
    h.debug(f"savebin {p} $b3000 {len(img)}", wait=2)
    ram = p.read_bytes()
    L(f"[{stage}] payload $B3000..+${len(img):x} vs built image: {sum(1 for i in range(len(img)) if ram[i] != img[i])} bytes differ")
    for s in spec["sites"]:
        ln = len(s["new"]) // 2
        q = out / f"{stage}_site.bin"
        h.debug(f"savebin {q} ${s['addr']:x} {ln}", wait=1)
        b = q.read_bytes()
        L(f"[{stage}] site ${s['addr']:06x} [{s['name']}] RAM {b.hex()} new {s['new']} orig {s['orig']} ->",
          "PATCHED" if b.hex() == s["new"] else ("ORIGINAL" if b.hex() == s["orig"] else "OTHER"))


try:
    L("cell", name, machine, "TOS", tos, mem, "KB floppy", diskdir)
    t0 = time.time()
    ok = False
    n = 0
    swapped = False
    while time.time() - t0 < 300:
        time.sleep(4)
        n += 1
        if shots:
            try:
                h.shot(str(out / f"s{n:03d}.png"))
            except RuntimeError as e:
                L("shot failed:", e, "| hatari log tail:", h._logtext()[-600:].replace("\n", " / "))
        if h.at_options():
            ok = True
            break
        if not swapped and h.matches(REF / "insert_graphics.png", (320, 255, 510, 285)):
            L("'Insert graphics disk' prompt after %.0f s: drive A -> MWB.st" % (time.time() - t0))
            h.cmd(f"hatari-option --disk-a {scratch / 'mwgfx.st'}")
            time.sleep(2)
            swapped = True
        if time.time() - t0 > 20:
            h.keypress(57)
    L("Game Options screen reached:", ok, "after %.0f s" % (time.time() - t0))
    if not ok:
        h.shot(str(out / "fail.png"))
        sys.exit(1)
    h.shot(str(out / "options.png"))
    checks("options")
    if team:
        h.goto(415, 385)
        h.click()
        okt = False
        t = time.time()
        while time.time() - t < 90:
            if h.matches(REF / "team_title.png", (320, 50, 510, 90)):
                okt = True
                break
            time.sleep(2)
        L("THE TEAM screen reached:", okt)
        h.shot(str(out / "team.png"))
        checks("team")
finally:
    h.close()
