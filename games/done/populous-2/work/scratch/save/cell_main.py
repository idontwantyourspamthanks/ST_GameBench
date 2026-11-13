"""Main round-trip cell: python3 cell_main.py --tag X [--media hd|acsi|floppy] [--machine ste] [--tos 1.62] [--mem 2048] [--build DIR] [--keep OUTDIR]
save T1, T2, overwrite T1, directory lists, load T2 / T1 byte-compared to RAM at the write call, load of a missing name -> the game's error box.
"""
import argparse, hashlib, json, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True); ap.add_argument("--media", default="hd"); ap.add_argument("--machine", default="ste")
ap.add_argument("--tos", default=None); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--build", default="build/Pop2Save")
ap.add_argument("--loop", type=int, default=0, help="N further save/load calls in a row (first 4 saves, then alternating load/save)")
ap.add_argument("--keep", default=None, help="copy the saved files here at the end (persistence cell)")
a = ap.parse_args()
OUT = SD / f"out_{a.tag}"; OUT.mkdir(exist_ok=True)
md5 = lambda b: hashlib.md5(b).hexdigest()
res = {}
h, info = make(a.media, a.build, a.machine, a.tos, a.mem, a.tag)


def P(*x):
    print(*x, flush=True)


def saved_bytes(n, expect=None):
    if a.media == "hd":
        p = hdfile(h, n); return p.read_bytes() if p.exists() else None
    if a.media == "acsi":           # HDDRIVER's write-back cache reaches the image a few seconds after the call
        for _ in range(14):
            b = imgfile(info["img"], n)
            if b is not None and len(b) == SIZE and (expect is None or b == expect):
                return b
            time.sleep(2.5)
        return b
    return None


def do_save(nm, dumpname):
    for attempt in (1, 2):         # a debugger breakpoint is sometimes not hit on the very first call (harness slip): the save is then repeated once
        arm(h, 0x80300, OUT / dumpname, "&& d0 = 1")
        assert open_req(h), "requester did not open"
        choose(h, "save"); name(h, nm); confirm(h)
        ok = waitfile(OUT / dumpname, 40 if attempt == 1 else 60)
        r = wait_running(h)
        if ok:
            break
        P(f"  (dump of {nm} missed on attempt {attempt}; the file is on the disk, repeating the save)")
    d = (OUT / dumpname).read_bytes() if ok else b""
    t = int.from_bytes(d[0x16c:0x16e], "big") if d else None
    return ok, r, d, t


def do_load(nm, dumpname, expect_err=False):
    arm(h, 0x2cc5e, OUT / dumpname)
    assert open_req(h), "requester did not open"
    choose(h, "load"); name(h, nm); confirm(h)
    ok = waitfile(OUT / dumpname, 40)
    time.sleep(3)
    return ok


try:
    t0 = time.time(); ok = h.boot_to_game()
    P(f"CELL {a.tag}: {info} boot {time.time()-t0:.0f}s in_play={ok} marker={h.marker()!r} turn={turn(h)} $2cc5a={h.peekl(0x2cc5a):#x} $2cbe6={h.peekl(0x2cbe6):#x} $2cb10={h.peekl(0x2cb10):#x}")
    time.sleep(6)
    ok1, r1, A1, t1 = do_save("t1", "A1.bin")
    P(f"SAVE T1: dump={ok1} back_in_play={r1} turn_in_dump={t1} md5(dump)={md5(A1)}")
    f = saved_bytes("T1.GAM", A1); P(f"  T1.GAM on disk: {len(f) if f else None} B, equals RAM at write: {f == A1}")
    shot(h, f"{a.tag}_after_save1.png")
    time.sleep(8)
    ok2, r2, A2, t2 = do_save("t2", "A2.bin")
    P(f"SAVE T2: dump={ok2} back_in_play={r2} turn_in_dump={t2} md5={md5(A2)}")
    f2 = saved_bytes("T2.GAM", A2); P(f"  T2.GAM on disk: {len(f2) if f2 else None} B, equals RAM at write: {f2 == A2}")
    time.sleep(8)
    ok3, r3, A3, t3 = do_save("t1", "A3.bin")
    P(f"SAVE T1 again (overwrite): dump={ok3} back_in_play={r3} turn_in_dump={t3} md5={md5(A3)}")
    f3 = saved_bytes("T1.GAM", A3); P(f"  T1.GAM on disk: {len(f3) if f3 else None} B, equals the NEW RAM: {f3 == A3}, differs from the first save: {f3 != A1}")
    # directory: the LOAD requester lists both
    time.sleep(3)
    assert open_req(h); choose(h, "load"); time.sleep(8); shot(h, f"{a.tag}_dir.png")
    P(f"DIRECTORY shot {a.tag}_dir.png")
    cancel(h); time.sleep(1); P("  cancel -> running", running(h))
    # load T2 then T1, compared with the save dumps
    okb = do_load("t2", "B2.bin"); B2 = (OUT / "B2.bin").read_bytes() if okb else b""
    P(f"LOAD T2: dump={okb} RAM after read == RAM at T2 save: {B2 == A2}; turn in RAM {int.from_bytes(B2[0x16c:0x16e],'big') if B2 else None}; turn now {turn(h)} running={running(h)}")
    time.sleep(6)
    okb = do_load("t1", "B1.bin"); B1 = (OUT / "B1.bin").read_bytes() if okb else b""
    P(f"LOAD T1: dump={okb} RAM after read == RAM at the 2nd T1 save: {B1 == A3}; turn now {turn(h)} running={running(h)}")
    time.sleep(5)
    # missing file: RAM before the call (bp at the blob entry, d0 = 0) vs after it returned (bp at $2cc5e)
    arm(h, 0x80300, OUT / "BXpre.bin", "&& d0 = 0", tag="BXpre")
    okb = do_load("nope", "BX.bin", True); BX = (OUT / "BX.bin").read_bytes() if okb else b""
    BXp = (OUT / "BXpre.bin").read_bytes() if (OUT / "BXpre.bin").exists() else b""
    p = shot(h, f"{a.tag}_missing.png")
    P(f"LOAD NOPE (missing): bp hit={okb}; RAM after the failed read == RAM before the call: {BX == BXp and len(BX) == SIZE}; shot {p.name} (the game's DISK FILE ERROR box)")
    h._click(416, 184, 2); shot(h, f"{a.tag}_missing2.png")   # OK: the hit row is y=184 (y=177 is the glyph centre and misses)
    cancel(h); time.sleep(2)
    P(f"after missing-file error: game running={running(h)} turn={turn(h)} in_play={h.in_play()}")
    loopfail = None
    if a.loop:
        nb0 = len(logbad(h))
        for i in range(a.loop):
            nm = "l%d" % (i % 4); t1 = time.time()
            try:
                if i >= 4 and i % 2 == 1:
                    arm(h, 0x2cc5e, OUT / f"L{i}.bin", tag=f"L{i}")
                    assert open_req(h); choose(h, "load"); name(h, nm); confirm(h)
                    okf = waitfile(OUT / f"L{i}.bin", 40); r = wait_running(h, 60); what = "load"
                else:
                    assert open_req(h); choose(h, "save"); name(h, nm); confirm(h)
                    r = wait_running(h, 60); okf = True; what = "save"
            except Exception as e:
                r = False; okf = False; what = "EXC " + repr(e)
            bad = logbad(h)
            st = "ok" if (r and okf and len(bad) == nb0) else "FAIL"
            P(f"LOOP {i:2d} {what} {nm} running={r} turn={turn(h) if r else None} t={time.time()-t1:.0f}s new_log_errors={len(bad)-nb0} {st}")
            if st != "ok":
                loopfail = i; break
            time.sleep(1)
        P(f"LOOP {a.loop} calls: " + ("PASS" if loopfail is None else f"FAIL at {loopfail}"))
    if a.keep:
        kd = Path(a.keep); kd.mkdir(parents=True, exist_ok=True)
        for n in ("T1.GAM", "T2.GAM"):
            b = saved_bytes(n)
            if b: (kd / n).write_bytes(b)
        (kd / "A3.bin").write_bytes(A3); (kd / "A2.bin").write_bytes(A2)
        P("kept", sorted(x.name for x in kd.iterdir()))
    bad = logbad(h)
    P(f"LOG bus/address-error/halt lines: {len(bad)}"); [P("  ", l) for l in bad[:8]]
    P(f"RESULT {a.tag}: " + ("PASS" if (ok1 and r1 and f == A1 and f2 == A2 and f3 == A3 and f3 != A1 and B2 == A2 and B1 == A3 and BX == BXp and not bad and loopfail is None) else "CHECK"))
except Exception as e:
    import traceback; traceback.print_exc()
    P("EXCEPTION", repr(e)); P("LOG TAIL:", *h._logtext().splitlines()[-8:], sep="\n")
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}.log")
    h.close()
