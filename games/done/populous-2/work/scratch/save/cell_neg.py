"""Negative control: the same blob with the HAGA swap disabled (raw `trap #1` from game context, build/Pop2SaveRaw)."""
import sys, time, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *
tag = "neg_raw"
h, info = make("hd", "build/Pop2SaveRaw", "ste", None, 2048, tag)
P = lambda *x: print(*x, flush=True)
try:
    ok = h.boot_to_game(); P("boot", ok, h.marker(), turn(h))
    time.sleep(5)
    (SD / "NA.bin").unlink(missing_ok=True)
    arm(h, 0x80300, SD / "NA.bin", "&& d0 = 1")
    P("requester", open_req(h)); choose(h, "save"); name(h, "t1"); confirm(h)
    t0 = time.time()
    while time.time() - t0 < 40:
        time.sleep(4)
        try:
            P("t+%2d turn=%s $70=%#x" % (time.time() - t0, turn(h), h.peekl(0x70)))
        except Exception as e:
            P("debugger not answering:", repr(e)); break
    P("T1.GAM on the host drive:", [(p.name, p.stat().st_size) for p in (h.R / "C/FILES").iterdir() if p.suffix == ".GAM"])
    P("NA.bin written (the call was reached):", (SD / "NA.bin").exists())
    try:
        shot(h, tag + ".png"); P("shot ok")
    except Exception as e:
        P("no screenshot", repr(e))
    bad = logbad(h); P("LOG bad lines:", len(bad)); [P("  ", l) for l in bad[:10]]
    P("LOG tail:", *h._logtext().splitlines()[-6:], sep="\n  ")
finally:
    shutil.copy(h.logpath, SD / f"{tag}.log")
    h.close()
