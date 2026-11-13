"""Error cells: a save that cannot succeed must give the game's own DISK FILE ERROR box and return to the game.
  --kind full    ACSI + HDDRIVER 4 MB image filled to < 56,690 B free (Fwrite comes back short)
  --kind wprot   Hatari GEMDOS drive C + a write-protected blank 720K in A:, drawer A:\\ (Fcreate / Fwrite fail with EWRPRO through TOS's floppy driver)
  --kind nodisk  the same without a disk in A: (drawer A:\\)
python3 cell_err.py --tag X --kind full|wprot|nodisk [--build DIR]"""
import argparse, shutil, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--kind", required=True)
ap.add_argument("--build", default="build/Pop2Save"); ap.add_argument("--machine", default="ste"); ap.add_argument("--tos", default=None); ap.add_argument("--mem", type=int, default=2048)
a = ap.parse_args()
P = lambda *x: print(*x, flush=True)
td = Path(tempfile.mkdtemp(prefix="p2err-"))
disk_a = None
if a.kind in ("wprot",):
    disk_a = td / "blank.st"
    subprocess.run(["mformat", "-C", "-f", "720", "-i", str(disk_a), "::"], check=True)
if a.kind == "full":
    h, info = make("acsi", a.build, a.machine, a.tos, a.mem, a.tag, size_mb=8, leave=30000)
elif a.kind == "wphd":
    h, info = make("hd", a.build, a.machine, a.tos, a.mem, a.tag, extra=["--protect-hd", "on"])
else:
    h, info = make("hd", a.build, a.machine, a.tos, a.mem, a.tag, disk_a=disk_a, prot=(a.kind == "wprot"))


def mfree(img):
    md = subprocess.run(["mdir", "-i", f"{img}@@1024", "::"], capture_output=True, text=True).stdout
    return int(re.findall(r"([\d ]+) bytes free", md)[-1].replace(" ", ""))


try:
    ok = h.boot_to_game(); P(f"CELL {a.tag}: {info} kind={a.kind} in_play={ok} marker={h.marker()!r} turn={turn(h)}")
    if a.kind == "full":
        P("free bytes on the image before:", mfree(info["img"]))
    time.sleep(5)
    nb = len(logbad(h))
    arm(h, 0x80300, SD / f"out_{a.tag}_pre.bin", "&& d0 = 1", tag="pre")
    arm(h, 0x2cbea, SD / f"out_{a.tag}_ret.bin", tag="ret")
    assert open_req(h); choose(h, "save")
    if a.kind not in ("full", "wphd"):
        drawer(h, "a:\\")
    name(h, "t1"); confirm(h)
    time.sleep(10); shot(h, f"{a.tag}_after10s.png")
    time.sleep(10); p = shot(h, f"{a.tag}_after20s.png")
    P(f"turn now {turn(h)} (the world is stopped while the game's requester / error box is up): frozen={frozen(h)}")
    P(f"write call reached: {(SD/f'out_{a.tag}_pre.bin').exists()}; returned to the game's wrapper ($2cbea): {(SD/f'out_{a.tag}_ret.bin').exists()}; shot {p.name}")
    h._click(416, 184, 3); shot(h, f"{a.tag}_ok.png")
    cancel(h); time.sleep(2); h._click(416, 370, 3)
    r = wait_running(h, 30)
    P(f"after the error box: game running={r} turn={turn(h)} in_play={h.in_play() if r else None}")
    if a.kind == "full":
        time.sleep(15)
        P("free bytes on the image after :", mfree(info["img"]))
        P(subprocess.run(["mdir", "-i", f"{info['img']}@@1024", "::FILES"], capture_output=True, text=True).stdout)
        part = td / "part.img"
        subprocess.run(["dd", f"if={info['img']}", f"of={part}", "bs=512", "skip=2", "status=none"], check=True)
        P("fsck.fat -n:", subprocess.run(["fsck.fat", "-n", str(part)], capture_output=True, text=True).stdout.strip().splitlines()[-1])
    if a.kind in ("wprot", "nodisk", "wphd"):
        P("A: image listing after:", subprocess.run(["mdir", "-i", str(disk_a), "::"], capture_output=True, text=True).stdout[-200:] if disk_a else "(no disk)")
        P("host drive FILES:", sorted(p.name for p in (h.R / "C/FILES").iterdir()))
    bad = logbad(h); P(f"LOG errors beyond the boot probe: {len(bad)-nb} total {len(bad)}"); [P("  ", l) for l in bad[:6]]
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}.log")
    h.close()
