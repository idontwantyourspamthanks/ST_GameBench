"""Track editor gate library (tile-grid editor, design section 15): boots the HD build to the track editor and drives it with real key / joystick input.
Raw memory is read with the debugger (savebin).  The variable map VAR is read from the `vName equ N` lines of patches/ovl/msedit.s (key = the name without the `v`, lower case),
and SYM (routine addresses, for breakpoints) from the same source assembled exactly as tools/msrpatch.py does: neither can go stale."""
import sys, time, struct, os, re, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CG_LOGS", str(HERE / "logs8"))
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
import msrtrack as mt
import msrpatch as P

EV = 0x140000
CPS = 0x110000
OVL = P.OVL_SRC.read_text()
VAR = {m.group(1).lower(): int(m.group(2)) for m in re.finditer(r"^v(\w+)\s+equ\s+(\d+)", OVL, re.M)}
ED_TMP = Path(os.environ.get("ED_TMP", "/tmp/msred8")); ED_TMP.mkdir(parents=True, exist_ok=True)

def symbols():
    """{label: address} of the overlay (a vasm listing of the source assembled at EDBASE with the tool's equates)"""
    common = "".join(f"{k}\tequ\t${v:x}\n" for k, v in P.CP_EQUS.items()) + "FLOPPY\tequ\t0\n"
    src = f"IB\tequ\t${P.IB:x}\nTABLE\tequ\t${P.TABLE:x}\n{common}\n\torg\t${P.CP_EQUS['EDBASE']:x}\n" + OVL.replace(P.VERSION_TAG, P.release_version()) + "\n"
    (ED_TMP / "ovl_full.s").write_text(src)
    r = subprocess.run([P.VASM, "-Fbin", "-m68000", "-quiet", "-L", str(ED_TMP / "ovl.lst"), "-o", str(ED_TMP / "ovl.bin"), str(ED_TMP / "ovl_full.s")], capture_output=True, text=True)
    if r.returncode: raise SystemExit(r.stderr)
    return {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^(\w+)\s+A:([0-9A-F]{8})", (ED_TMP / "ovl.lst").read_text(), re.M)}

def fast_mem(r):
    """Run.mem (a debugger `m` dump read back from Hatari's log) re-reads the whole log on every call and polls every 0.1 s: a gate makes thousands of reads and the log grows to megabytes.
    This one reads the log from the offset it had when the command was sent and polls every 20 ms; same parsing."""
    h = r.h
    def mem(addr, n):
        off = h.logpath.stat().st_size
        h.cmd(f"hatari-debug m ${addr:x} {n}")
        last = re.compile(rf"^{addr + ((n - 1) // 16) * 16:08x}:.*\n", re.I | re.M); t = time.time(); out = ""
        while time.time() - t < 8:
            time.sleep(0.02)
            with open(h.logpath, "rb") as f:
                f.seek(off); out = f.read().decode("latin1")
            if last.search(out): break
        b = bytearray()
        for ln in out.splitlines():
            m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})(?:  |$)", ln)
            if m and addr <= int(m.group(1), 16) < addr + n: b += bytes.fromhex(m.group(2).replace(" ", ""))
        return bytes(b[:n])
    r.mem = mem

class Ed:
    def __init__(self, tag, machine="ste", mem=2048, build=os.environ.get("ED_BUILD", "/tmp/msred8/hd"), camp=None):
        self.tag = tag; self.build = build
        logopen(tag)
        self.r = Run("hd", machine, mem, tag, build=build, camp_hd=camp, sound=True); fast_mem(self.r)
        self.machine, self.mem = machine, mem
        log(f"== {tag}: HD {MACH[machine]} {mem // 1024} MB, build {build}, campaign {camp.name if camp else 'none'}")
    # ---- raw access
    def v(self, name, size=2):
        b = self.r.mem(EV + VAR[name], size)
        return struct.unpack(">h" if size == 2 else ">i", b)[0] if size in (2, 4) else b
    def vu(self, name): return W(self.r.mem(EV + VAR[name], 2))
    def vl(self, name): return L(self.r.mem(EV + VAR[name], 4))
    def grab(self, addr, n, name):
        if n == 0: return b""
        p = ED_TMP / f"{self.tag[:12]}_{name}.bin"
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
    def tiles(self):
        n = self.vu("nseg"); b = self.grab(EV + 0x10000, 2 * n, "tile")
        return list(struct.unpack(f">{n}H", b))
    def shown(self):
        """the 128 grid slots as the editor believes they are on the screen (tile word + frame bits)"""
        return list(struct.unpack(">128H", self.grab(EV + 0x11000, 256, "shw")))
    def screen(self):
        return self.grab(EV + 0x30000, 32000, "scr")
    def store(self):
        ln = self.r.l(CPS + 8)
        return self.grab(CPS, ln, "store")
    def msgtext(self):
        p = self.vl("lmsg")
        if not 0x130000 <= p < 0x140000: return ""
        return self.r.mem(p, 48).split(b"\0")[0].decode("latin1")
    # ---- input
    def send(self, sc): self.r.h.cmd(f"hatari-event keypress 0x{sc:02x}")
    def key(self, sc, n=1, dt=0.16):
        for _ in range(n): self.send(sc); time.sleep(dt)
    def jpoke(self, v): self.r.h.cmd(f"hatari-debug w $6105 ${v:02x}")
    def joy(self, bits, hold=0.12):
        self.jpoke(bits); time.sleep(hold); self.jpoke(0); time.sleep(0.15)
    def fire(self): self.joy(0x80, 0.5)
    def wait(self, cond, tmo=30, dt=0.25):
        t0 = time.time()
        while time.time() - t0 < tmo:
            if cond(): return True
            time.sleep(dt)
        return False
    def quiet(self):
        """one sample: the view loop has nothing to do (no key waiting, tile words current, nothing to draw, no list, no preview running)"""
        names = ("redraw", "tok", "lopen", "state", "lbusy"); lo = min(VAR[n] for n in names); hi = max(VAR[n] for n in names) + 2
        b = self.r.mem(EV + lo, hi - lo); q = self.r.mem(EV + VAR["kqh"], 4)          # (two short dumps: every dump is read back from Hatari's log)
        w = lambda n: W(b, VAR[n] - lo)
        return q[:2] == q[2:] and w("redraw") == 0 and w("tok") == 1 and w("lopen") == 0 and w("state") == 1 and w("lbusy") == 0
    def idle(self, tmo=40):
        """quiet for two polls in a row"""
        ok = 0; t0 = time.time()
        while time.time() - t0 < tmo:
            ok = ok + 1 if self.quiet() else 0
            if ok >= 2: return True
            time.sleep(0.2)
        return False
    def goto_item(self, n):
        for _ in range(12):
            s = self.r.w(0x100406)
            if s == n: return True
            self.send(0x50 if s < n else 0x48); time.sleep(0.6)
        return self.r.w(0x100406) == n
    def settle(self, tmo=60):
        """the list loop is idle: no key waiting, no preview pending or running (two polls in a row)"""
        ok = 0; t0 = time.time()
        while time.time() - t0 < tmo:
            ok = ok + 1 if (self.vu("lpend") == 0 and self.vu("lbusy") == 0 and self.vu("lrd") == 0 and self.vu("kqh") == self.vu("kqt")) else 0
            if ok >= 2: return True
            time.sleep(0.2)
        return False
    def list_goto(self, idx, tmo=25):
        """move the open list's selection to idx with UP/DOWN keys (the key queue takes them back to back; the preview runs once they are all in)"""
        self.settle()
        for _ in range(8):
            s = self.v("lsel"); cnt = self.vu("lcnt") + 1
            if s == idx: return True
            d = (idx - s) % cnt if s >= 0 else idx + 1
            if d <= cnt // 2: self.key(0x50, d, 0.08)
            else: self.key(0x48, cnt - d, 0.08)
            self.wait(lambda: self.v("lsel") == idx, 6, 0.15); self.settle()
        return self.v("lsel") == idx
    def seg_goto(self, k):
        """the grid cursor to segment k: UP / DOWN = 16 segments, LEFT / RIGHT = one (typed back to back: the key queue keeps them)"""
        for _ in range(6):
            s = self.vu("seg")
            if self.vu("focus"):                             # the object list has the cursor (UP / DOWN would walk its objects): Tab = back to the grid
                self.send(0x0f); self.wait(lambda: self.vu("focus") == 0, 5, 0.1)
            if s == k: return self.vu("focus") == 0
            d = k - s
            rows, cols = divmod(abs(d), 16)
            self.key(0x50 if d > 0 else 0x48, rows, 0.05); self.key(0x4d if d > 0 else 0x4b, cols, 0.05)
            self.wait(lambda: self.vu("kqh") == self.vu("kqt"), 20, 0.1); self.idle()
        return self.vu("seg") == k and self.vu("focus") == 0
    def boot_editor(self, load_camp=True, ntr=3):
        r = self.r
        ok = r.boot_title(); log(f"title reached: {ok}"); check("title reached", ok)
        r.menu_open(); time.sleep(1)
        if load_camp:
            check("LOAD CAMPAIGN FROM HARD DISK item", self.goto_item(1)); self.send(0x1c); t0 = time.time()
            while time.time() - t0 < 60 and not r.b(V["loaded"]): time.sleep(0.5)
            check("campaign loaded", r.b(V["loaded"]) != 0)
            time.sleep(2.5); self.goto_item(ntr); self.send(0x1c); time.sleep(2.0)   # the play list: < BACK row (ntr tracks + back; item ntr)
            self.goto_item(4)
        else:
            self.goto_item(3)
        t0 = time.time(); self.send(0x1c)
        while time.time() - t0 < 30 and r.b(0xb8e0c) == 0: time.sleep(0.2)
        time.sleep(1.0)
        check("editor overlay loaded (V_EDOK)", r.b(0xb8e0c) == 0xff)
    def open_track(self, kind, level=3, ntr=3):
        """from the editor's track list: 'stock' = COPY OF AN ORIGINAL TRACK > level, 'straight' = PLAIN STRAIGHT ROAD > scenery level, 'camp' = campaign track `level` > EDIT THIS TRACK.
        ntr = the campaign tracks in the list (0 without a campaign)."""
        if kind == "camp":
            self.key(0x50, level, 0.4); self.send(0x1c); time.sleep(1.2); self.send(0x1c)
        else:
            self.key(0x50, ntr + (0 if kind == "stock" else 1), 0.5); self.send(0x1c); time.sleep(1.0); self.key(0x50, level, 0.35); self.send(0x1c)
        ok = self.wait(lambda: self.vu("state") == 1, 60); time.sleep(0.8)
        return ok and self.idle()
    def close(self): self.r.close()
