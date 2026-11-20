import os, re, struct, sys, time, shutil, tempfile, argparse
os.environ["HOME"] = "/tmp/msr101/home"
os.environ["HATARI"] = "/home/ryan/Code/AtariST/hattari/build/src/hatari"
G = "/home/ryan/Code/AtariST/gamebench"
sys.path.insert(0, G + "/tools"); sys.path.insert(0, G + "/games/in_progress/moonshine-racers/tools")
from msr import Moonshine
from stharness import Hatari, TOS
import msrfloppy
ap = argparse.ArgumentParser()
ap.add_argument("build"); ap.add_argument("root"); ap.add_argument("tag")
ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--tos")
ap.add_argument("--pace-only", action="store_true"); ap.add_argument("--driveb", action="store_true")
ap.add_argument("--play", type=int, default=300)
a = ap.parse_args()
OUT = "/tmp/msr101/out/" + a.tag; os.makedirs(OUT, exist_ok=True)
LOGF = open(OUT + ".log", "w")
def log(*x):
    s = " ".join(str(v) for v in x); print(s, flush=True); LOGF.write(s + "\n"); LOGF.flush()
def mem(h, addr, n):
    n0 = len(h._logtext()); h.cmd(f"hatari-debug m ${addr:x} {n}")
    last = addr + ((n - 1) // 16) * 16; t = time.time(); out = ""
    while time.time() - t < 8:
        time.sleep(0.15); out = h._logtext()[n0:]
        if re.search(rf"^{last:08x}:", out, re.I | re.M):
            time.sleep(0.1); out = h._logtext()[n0:]; break
    b = bytearray()
    for ln in out.splitlines():
        m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})(?:  |$)", ln)
        if m and addr <= int(m.group(1), 16) < addr + n: b += bytes.fromhex(m.group(2).replace(" ", ""))
    return bytes(b[:n])
W = lambda b, o=0: struct.unpack(">H", b[o:o + 2])[0]
L = lambda b, o=0: struct.unpack(">I", b[o:o + 4])[0]
def st(h):
    return dict(v=h.vbl(), f21=mem(h,0x1021,1)[0], f24=mem(h,0x1024,1)[0], f28=mem(h,0x1028,1)[0], p100e=W(mem(h,0x100e,2)),
                ptr=mem(h,0x6100,0x18).hex(), extra=L(mem(h,0xb8f38,4)))
def shot(h, n): return h.shot(f"{OUT}/{n}.png")
def pin(h):
    for _ in range(8): h.cmd("hatari-event mousemove -100 -80"); time.sleep(0.05)
    time.sleep(0.3)
def mv(h, x, y):
    for _ in range(10): h.cmd(f"hatari-event mousemove {x // 10} {y // 10}"); time.sleep(0.05)
    time.sleep(0.3)
def click(h): h.cmd("hatari-event leftdown"); time.sleep(0.3); h.cmd("hatari-event leftup"); time.sleep(0.3)
def race_up(h): return L(mem(h,0x23c0,4)) != 0 and W(mem(h,0x100e,2)) > 30 and mem(h,0x1021,1)[0] == 2 and mem(h,0x1024,1)[0] == 0
tos = TOS[a.tos] if a.tos else None
wd = f"/tmp/msr101/run_{a.tag}"; shutil.rmtree(wd, ignore_errors=True)
if a.build == "hd":
    kw = {"tos": tos} if tos else {}
    h = Moonshine(snapshot=None, game_dir=a.root + "/MOONSHR", machine=a.machine, memsize_kb=a.mem, workdir=wd, extra=["--joy1","keys"], **kw)
else:
    extra = ["--disk-a", a.root + "/MOONSHR_floppy/disk_a.st", "--joy1", "keys"]
    h = Hatari(game_dir=msrfloppy.GAME / "originals" / "floppy", machine=a.machine, memsize_kb=a.mem, tos=tos, autorun=None, files=[], workdir=wd, extra=extra)
bad = lambda: len(re.findall("Bus Error|Address Error", h._logtext()))
TM = []
def boot():
    t0 = time.time(); n = 0; swapped = False
    while time.time() - t0 < 900:
        time.sleep(4); v = h.vbl()
        if a.build == "hd" and v > 1500 and n % 3 == 0: shot(h, f"boot_{v}")
        if a.build == "fl" and v > 500 and n % 3 == 0: shot(h, f"boot_{v}")
        n += 1
        if (a.build == "hd" and v > 5000) or (a.build == "fl" and v > 1500):
            try:
                if race_up(h): return True
            except Exception: pass
            if a.build == "fl" and not swapped and h.screen_matches(msrfloppy.DISK2_REF, msrfloppy.DISK2_BOX):
                d2 = tempfile.mkdtemp(prefix="msr101_d2_") + "/disk2.st"; shutil.copy(a.root + "/MOONSHR_floppy/disk_b.st", d2)
                h.cmd(f"hatari-option --disk-{'b' if a.driveb else 'a'} {d2}"); time.sleep(2); swapped = True; log("disk2 inserted into drive", "B" if a.driveb else "A", "at vbl", v)
            # title / Ike / story screens: does the pointer move?
            try:
                if mem(h,0x1021,1)[0] != 2:
                    p0 = mem(h,0x6106,4); mv(h, 40, 20); p1 = mem(h,0x6106,4)
                    TM.append((v, mem(h,0x1021,1)[0], mem(h,0x1028,1)[0], p0.hex(), p1.hex()))
            except Exception: pass
            h.keypress(57)
    return False
try:
    t0=time.time(); lo,hi=(2300,3400) if a.build=="hd" else (400,1500); n=0
    while time.time()-t0<600:
        v=h.vbl()
        if v>hi: break
        if v>lo: shot(h,f"credit_{v}"); n+=1
        time.sleep(0.8)
    log("credit shots",n,"last vbl",v)
finally:
    h.close()
