"""Milestone 2 gate library: boots the HD build to the track editor and drives it with real key / joystick input.  Raw memory is read with the debugger (savebin)."""
import sys, time, struct, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CG_LOGS", str(HERE / "logs2"))
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
import msrtrack as mt

EV = 0x140000
CPS = 0x110000
VAR = dict(lbusy=446, nseg=34, nobj=36, total=38, end=42, rl=46, base=48, bart=50, barat=52, ntypes=56, nbar=58, seg=60, pos=62, obj=66, focus=68, zoom=70, redraw=88, state=96, src=98, srcix=100,
           lsel=246, lopen=254, lbad=258, mode=268, mod=200, hcur=202, htop=206, dirty=198, leavew=272, lval=250, vmsg=102, lcnt=226, play=278, chkn=302, chke=304)

class Ed:
    def __init__(self, tag, machine="ste", mem=2048, build="/tmp/msred2/hd", camp=None):
        self.tag = tag; self.build = build
        logopen(tag)
        self.r = Run("hd", machine, mem, tag, build=build, camp_hd=camp, sound=True)
        self.machine, self.mem = machine, mem
        log(f"== {tag}: HD {MACH[machine]} {mem // 1024} MB, build {build}, campaign {camp.name if camp else 'none'}")
    # ---- raw access
    def v(self, name, size=2):
        b = self.r.mem(EV + VAR[name], size)
        return struct.unpack(">h" if size == 2 else ">i", b)[0] if size in (2, 4) else b
    def vu(self, name): return W(self.r.mem(EV + VAR[name], 2))
    def vl(self, name): return L(self.r.mem(EV + VAR[name], 4))
    def grab(self, addr, n, name):
        p = Path("/tmp/msred2") / f"{self.tag[:12]}_{name}.bin"
        if p.exists(): p.unlink()
        self.r.h.debug(f"savebin {p} ${addr:x} {n}", 0.6)
        for _ in range(60):
            if p.exists() and p.stat().st_size == n: break
            time.sleep(0.1)
        return p.read_bytes()
    def segs(self):
        n = self.vu("nseg"); b = self.grab(EV + 0x3000, 12 * n, "seg")
        return [list(struct.unpack(">HHhhBB", b[12 * i:12 * i + 10])) for i in range(n)]
    def objs(self):
        n = self.vu("nobj"); b = self.grab(EV + 0x9000, 8 * n, "obj")
        return [list(struct.unpack(">HHhH", b[8 * i:8 * i + 8])) for i in range(n)]
    def store(self):
        ln = self.r.l(CPS + 8)
        return self.grab(CPS, ln, "store")
    # ---- input
    def send(self, sc): self.r.h.cmd(f"hatari-event keypress 0x{sc:02x}")
    def key(self, sc, n=1, dt=0.16):
        for _ in range(n): self.send(sc); time.sleep(dt)
    def jpoke(self, v): self.r.h.cmd(f"hatari-debug w $6105 ${v:02x}")
    def joy(self, bits, hold=0.12):
        self.jpoke(bits); time.sleep(hold); self.jpoke(0); time.sleep(0.15)
    def fire(self): self.joy(0x80, 0.5)          # a press that also spans a live-preview redraw (about 1 s) of the list loop would be missed by a short pulse
    def wait(self, cond, tmo=30, dt=0.25):
        t0 = time.time()
        while time.time() - t0 < tmo:
            if cond(): return True
            time.sleep(dt)
        return False
    def idle(self, tmo=40):
        """no redraw pending, nothing stale, no list open, for two polls"""
        ok = 0; t0 = time.time()
        while time.time() - t0 < tmo:
            if self.vu("redraw") == 0 and self.vu("dirty") == 0x7fff and self.vu("lopen") == 0 and self.vu("state") == 1: ok += 1
            else: ok = 0
            if ok >= 2: return True
            time.sleep(0.3)
        return False
    def goto_item(self, n):
        for _ in range(12):
            s = self.r.w(0x100406)
            if s == n: return True
            self.send(0x50 if s < n else 0x48); time.sleep(0.6)
        return self.r.w(0x100406) == n
    def settle(self, tmo=60):
        """the list loop is idle: no preview pending or running (two polls in a row)"""
        ok = 0; t0 = time.time()
        while time.time() - t0 < tmo:
            ok = ok + 1 if (self.vu("lpend") == 0 and self.vu("lbusy") == 0) else 0
            if ok >= 2: return True
            time.sleep(0.4)
        return False
    def list_goto(self, idx, tmo=25):
        """move the open list's selection to idx with UP/DOWN keys; every key waits until the selection moved and the live preview it started is finished (keys during a preview redraw are lost)"""
        self.settle()
        for _ in range(60):
            s = self.v("lsel"); cnt = self.vu("lcnt") + 1
            if s == idx: return True
            d = (idx - s) % cnt if s >= 0 else idx + 1
            self.send(0x50 if d <= cnt // 2 else 0x48)
            self.wait(lambda: self.v("lsel") != s, 6, 0.15); time.sleep(0.2); self.settle()
        return self.v("lsel") == idx
    def boot_editor(self, load_camp=True):
        r = self.r
        ok = r.boot_title(); log(f"title reached: {ok}"); check("title reached", ok)
        r.menu_open(); time.sleep(1)
        if load_camp:
            check("LOAD CAMPAIGN FROM HARD DISK item", self.goto_item(1)); self.send(0x1c); t0 = time.time()
            while time.time() - t0 < 60 and not r.b(V["loaded"]): time.sleep(0.5)
            check("campaign loaded", r.b(V["loaded"]) != 0)
            time.sleep(2.5); self.goto_item(3); self.send(0x1c); time.sleep(2.0)   # the play list: < BACK row (3 tracks + back; item 3)
            self.goto_item(4)
        else:
            self.goto_item(3)
        t0 = time.time(); self.send(0x1c)
        while time.time() - t0 < 30 and r.b(0xb8e0c) == 0: time.sleep(0.2)
        time.sleep(1.0)
        check("editor overlay loaded (V_EDOK)", r.b(0xb8e0c) == 0xff)
    def close(self): self.r.close()
