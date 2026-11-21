"""Campaign release gates (MSRCampaign2): shared helpers for the HD and floppy campaign gate scripts.
Private HOME and the Hatari binary come from env.sh; one Hatari at a time.  Raw lines go to stdout and to <logs>/<tag>.txt.
Hatari runs normal speed for every input sequence (key presses, the shop click) and fast-forward (`--fast-forward true`, ~26x) only while waiting for a
state that persists (boot intro, race to the finish, ending), see `ff()`."""
import os, re, struct, sys, time, shutil, tempfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
G = HERE.parents[1]                                   # games/in_progress/moonshine-racers
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
from stharness import Hatari, TOS
import msrfloppy

LOGDIR = Path(os.environ.get("CG_LOGS", HERE / "logs")); LOGDIR.mkdir(parents=True, exist_ok=True)
CAMP = G / "work" / "camphd" / "camp"                 # test campaigns (work/camphd/mkcamp.py): c3.trk / c3.st = three custom tracks on base levels 0, 3, 5; bad_*.trk; bad_crc.st
V = dict(act=0xb8e00, loaded=0xb8e01, count=0xb8e02, pos=0xb8e04, start=0xb8e06, ptr=0xb8e08)
W = lambda b, o=0: struct.unpack(">H", b[o:o + 2])[0]
L = lambda b, o=0: struct.unpack(">I", b[o:o + 4])[0]
MACH = {"ste": "STE", "megaste": "Mega STE", "st": "ST", "megast": "Mega ST"}
_logf = None

def logopen(tag):
    global _logf
    _logf = open(LOGDIR / f"{tag}.txt", "w")

def log(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    if _logf: _logf.write(s + "\n"); _logf.flush()


class Run:
    """One Hatari: HD build (Moonshine, drive C: = the build folder + overlay) or floppy build (disk_a.st in drive A, no HD)."""
    def __init__(self, kind, machine, mem_kb, tag, build=None, snap=None, camp_hd=None, disk_a=None, disk_b=None, sound=False, psg=False, strict=False, tos=None, d2=None, d2_drive="a", noff=False, extra_args=()):
        self.kind, self.machine, self.mem_kb, self.tag = kind, machine, mem_kb, tag
        self.shotdir = LOGDIR / "shots"; self.shotdir.mkdir(exist_ok=True)
        wd = f"/tmp/msrc3/run_{tag}"; shutil.rmtree(wd, ignore_errors=True)
        self.tmp = Path(tempfile.mkdtemp(prefix=f"cg_{tag}_", dir="/tmp/msrc3"))
        kw = {"tos": TOS[tos]} if tos else {}
        sk = dict(sound=sound, trace_psg=psg, strict=strict)
        extra = (["--joy1", "keys"] if sound else []) + list(extra_args)
        if disk_a: extra += ["--disk-a", str(self._copy(disk_a))]
        if disk_b: extra += ["--disk-b", str(self._copy(disk_b))]
        if kind == "hd":
            ov = None
            if camp_hd:
                ov = self.tmp / "ov"; (ov / "FILES").mkdir(parents=True); shutil.copy(camp_hd, ov / "FILES" / "MSTRACKS.TRK")
            self.h = Moonshine(snapshot=str(snap) if snap else None, game_dir=str(build), machine=machine, memsize_kb=mem_kb, workdir=wd, overlay=ov, extra=extra, **sk, **kw)
        else:
            self.h = Hatari(game_dir=G / "originals" / "floppy", machine=machine, memsize_kb=mem_kb, autorun=None, files=[], workdir=wd, snapshot=str(snap) if snap else None, extra=extra, **sk, **kw)
        self.cur_a = None
        self.ffon = False
        self.noff = noff                                   # never fast-forward (the PSG gate runs in real time)
        self.d2, self.d2_drive, self.d2_done = d2, d2_drive, False   # floppy: disk 2 (copy swapped in at the game's own "Insert Disk 2" prompt)

    def _copy(self, p):
        d = self.tmp / f"{Path(p).stem}_{len(list(self.tmp.iterdir()))}.st"; shutil.copy(p, d); return d

    def close(self):
        try: self.h.close()
        except Exception as e: log("close:", e)

    # ---- plumbing ---------------------------------------------------------------------------------------------------------
    def ff(self, on):
        if on != self.ffon and not (on and self.noff):
            self.h.cmd(f"hatari-option --fast-forward {'true' if on else 'false'}"); self.ffon = on; time.sleep(0.4)

    def mem(self, addr, n):
        h = self.h
        n0 = len(h._logtext()); h.cmd(f"hatari-debug m ${addr:x} {n}")
        last = addr + ((n - 1) // 16) * 16
        t = time.time(); out = ""
        while time.time() - t < 8:
            time.sleep(0.1)
            out = h._logtext()[n0:]
            if re.search(rf"^{last:08x}:", out, re.I | re.M):
                time.sleep(0.05); out = h._logtext()[n0:]; break
        b = bytearray()
        for ln in out.splitlines():
            m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})(?:  |$)", ln)
            if m and addr <= int(m.group(1), 16) < addr + n: b += bytes.fromhex(m.group(2).replace(" ", ""))
        return bytes(b[:n])

    def b(self, a): return self.mem(a, 1)[0]
    def w(self, a): return W(self.mem(a, 2))
    def l(self, a): return L(self.mem(a, 4))
    def poke(self, a, *vals): self.h.debug(f"w ${a:x} " + " ".join(f"${v:02x}" for v in vals), 0.3)
    def vbl(self): return self.h.vbl()
    def shot(self, name): return self.h.shot(str(self.shotdir / f"{self.tag}_{name}.png"))
    def key(self, sc): self.h.keypress(sc)
    def errlines(self): return len(re.findall("Bus Error|Address Error", self.h._logtext()))

    def st(self, label):
        """one raw state line: campaign variables, the race state, the stream pointer and the base level."""
        cv = self.mem(V["act"], 12)
        s = (f"[{label}] vbl={self.vbl()} act={cv[0]:#x} loaded={cv[1]:#x} count={W(cv,2)} pos={W(cv,4)} start={W(cv,6)} ptr={L(cv,8):#x} $102c={self.w(0x102c):#06x} "
             f"len57890={self.w(0x57890)} $23c0={self.l(0x23c0):#x} $1024={self.b(0x1024):#04x} $1027={self.b(0x1027):#04x} $100e={self.w(0x100e)} $5ff8={self.w(0x5ff8)} $1021={self.b(0x1021):#04x}")
        log(s); return s

    # ---- boot -------------------------------------------------------------------------------------------------------------
    def at_prompt(self): return self.kind == "fl" and self.h.screen_matches(msrfloppy.DISK2_REF, msrfloppy.DISK2_BOX)

    def insert(self, drive, path):
        """swap a disk image into drive A/B (a copy: the game never writes the original)"""
        self.h.cmd(f"hatari-option --disk-{drive.lower()} {self._copy(path)}"); time.sleep(3)

    def eject(self, drive):
        self.h.cmd(f"hatari-option --disk-{drive.lower()} none"); time.sleep(3)

    def boot_title(self, tmo=900):
        """Cold boot to the title: fast-forward over the loading (until vbl 4500 HD / 3000 floppy), then normal speed, SPACE every ~4 s until the title is up.
        HD: $1021 == 2, $100e > 40, no race.  Floppy: the title loop $7242 ran (breakpoint hit; the key byte is cleared there).  The floppy build stops on the title, before the 'Insert Disk 2' prompt."""
        h = self.h; t0 = time.time(); lim = 4500 if self.kind == "hd" else 3000
        if self.kind == "fl":
            f = h.R / "clrkey0.txt"; f.write_text("w $60ff $00\n"); h.cmd(f"hatari-debug b pc = $7242 :trace :file {f}"); time.sleep(0.3)
            n0 = len(h._logtext())
        self.ff(True); last = 0
        while time.time() - t0 < tmo:
            time.sleep(0.5)
            v = h.vbl()
            if v < lim: continue
            self.ff(False)
            if self.kind == "fl":
                if "pc = $7242 :trace" in h._logtext()[n0:]:
                    h.debug("b all", 0.3); return True
            else:
                try: ok = self.b(0x1021) == 2 and self.w(0x100e) > 40 and self.l(0x23c0) == 0
                except Exception: ok = False
                if ok: return True
            if time.time() - last > 4: h.keypress(57); last = time.time()
        return False

    # ---- menu / race helpers ----------------------------------------------------------------------------------------------
    def menu_open(self):
        self.key(0x44); time.sleep(3)

    def downs(self, n):
        for _ in range(n): self.key(0x50); time.sleep(0.5)

    def menu_msg(self): return self.l(0x10040a)

    def load_from(self, n_down, wait=60, label="", ffwd=False):
        """In the F10 menu: Down x n_down, Return; waits for V_LOADED or a message (M_MSG != 0).  Returns (loaded, seconds)."""
        self.downs(n_down); self.key(0x1c); t0 = time.time(); time.sleep(2); self.shot(f"{label}loading")
        if ffwd: self.ff(True)
        while time.time() - t0 < wait:
            if self.b(V["loaded"]): break
            if self.menu_msg(): break
            time.sleep(0.5)
        self.ff(False)
        return self.b(V["loaded"]) != 0, time.time() - t0

    def click_exit(self):
        """v1.0.1 shop EXIT, real click: pin the pointer to the top-left, move down (the shop clamps y <= 167 = the EXIT hotspot at x = 0), click."""
        h = self.h
        for _ in range(8): h.cmd("hatari-event mousemove -100 -80"); time.sleep(0.05)
        time.sleep(0.3)
        for _ in range(10): h.cmd("hatari-event mousemove 0 20"); time.sleep(0.05)
        time.sleep(0.3); h.cmd("hatari-event leftdown"); time.sleep(0.3); h.cmd("hatari-event leftup"); time.sleep(0.3)

    def race_up(self):
        return self.l(0x23c0) != 0 and self.w(0x100e) > 30 and self.b(0x1024) == 0

    def exec_hits(self, pcs, clear_key_at=()):
        """arm :trace breakpoints on the given pcs; returns a function counting the hits per pc since.  clear_key_at: pcs whose hit also clears the key byte $60ff (a SPACE sent during the
        ending would otherwise still be in it when the title loop starts and start a new game)."""
        self.h.debug("b all", 0.3)
        f = self.h.R / "clrkey.txt"; f.write_text("w $60ff $00\n")
        for pc in pcs: self.h.cmd(f"hatari-debug b pc = ${pc:x} :trace" + (f" :file {f}" if pc in clear_key_at else "")); time.sleep(0.2)
        n0 = len(self.h._logtext())
        return lambda: {pc: self.h._logtext()[n0:].count(f"pc = ${pc:x} :trace") for pc in pcs}

    def wait_race(self, tmo=240, press=True, shop=True, label=""):
        """SPACE through the screens (and click EXIT in the shop) until a race is running; returns the race-start state tuple (len57890, $102c, $23c0, POS) or None."""
        t0 = time.time(); n = 0
        while time.time() - t0 < tmo:
            time.sleep(1.0)
            try:
                up = self.race_up()
                if up:
                    # sampling discipline: during a REPLAY's setup (time-out: $fda2 stores the block start into $23c0, the ring fill $ff3a then advances it) $100e still holds the previous race's value
                    # (> 30), so race_up() is already true while $23c0 is the block start.  The sample counts only when the stream pointer and the state stayed unchanged for >= 1 s (the car stands).
                    s1 = (self.w(0x57890), self.w(0x102c), self.l(0x23c0), self.w(V["pos"])); time.sleep(1.0)
                    if self.race_up() and s1 == (self.w(0x57890), self.w(0x102c), self.l(0x23c0), self.w(V["pos"])): return s1
                    continue
                if self.d2 and not self.d2_done and self.at_prompt():
                    log(f"[{self.tag}] game's 'Insert Disk 2' prompt at vbl {self.vbl()}: disk 2 into drive {self.d2_drive.upper()}")
                    self.shot("prompt_disk2"); self.insert(self.d2_drive, self.d2); self.key(57); self.d2_done = True; continue
                if press:
                    f24 = self.b(0x1024)
                    if f24 == 0xff and shop:
                        self.ff(False); self.click_exit(); self.key(57); time.sleep(1.5)
                    else:
                        n += 1
                        if n % 3 == 0: self.key(57)
            except Exception as e:
                log("wait_race:", e)
        return None

    def drive_to_finish(self, tmo=240, label="", ffwd=True):
        """joystick up (debugger write of $6105, a deterministic input) until the race is over (`$1024 == $ff`); returns the end state."""
        self.poke(0x6105, 0x01)
        if ffwd: self.ff(True)
        t0 = time.time(); r = False
        while time.time() - t0 < tmo:
            time.sleep(0.4)
            if self.b(0x1024) == 0xff: r = True; break
        self.ff(False); self.poke(0x6105, 0x00)
        return r

    def play_races(self, n, label, tmo=300, ffwd=True):
        """n races of a campaign (the first has been started via the menu): wait, state line at the start, drive to the BAR, state line at the end, cross the shop with a real click."""
        out = []
        for i in range(n):
            r = self.wait_race(tmo=tmo, label=label)
            if r is None: log(f"[{label}] race {i}: no race start within {tmo} s"); self.st(f"{label} race {i} missing"); break
            self.st(f"{label} race {i} start"); self.shot(f"{label}_race{i}")
            out.append(r)
            ok = self.drive_to_finish(tmo=tmo, ffwd=ffwd)
            self.st(f"{label} race {i} over (finished={ok})"); self.shot(f"{label}_over{i}")
            if not ok: break
        return out


# ---- checks and text trace -----------------------------------------------------------------------------------------------
FAILS = []
def check(name, cond, detail=""):
    log(f"CHECK {name}: {'PASS' if cond else 'FAIL'} {detail}")
    if not cond: FAILS.append(name)
    return cond

def texts_start(r):
    """trace every text the campaign menu draws: breakpoint on the game's text routine $12268 dumping M_LINE (x, y, text) at each call"""
    f = r.h.R / "txt.txt"; f.write_text("m $100470 48\n")
    r.h.debug("b all", 0.3); r.h.cmd(f"hatari-debug b pc = $12268 :trace :file {f}"); time.sleep(0.3)
    r._tn0 = len(r.h._logtext())

def texts_peek(r):
    """-> [(x, y, text)] drawn since texts_start (the breakpoint stays armed)"""
    lines = r.h._logtext()[r._tn0:].splitlines(); out = []
    for i, ln in enumerate(lines):
        m = re.match(r"\s*00100470:\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})", ln)
        if m and i + 2 < len(lines):
            bb = bytearray()
            for k in range(3):
                mm = re.match(r"\s*[0-9a-fA-F]{8}:\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})", lines[i + k])
                if mm: bb += bytes.fromhex(mm.group(1).replace(" ", ""))
            if len(bb) >= 3:
                out.append((bb[0], bb[1], bytes(bb[2:]).split(b"\0")[0].decode("latin1")))
    return out

def texts_stop(r):
    """-> the list of drawn strings (x, y, text) since texts_start; removes the breakpoint"""
    time.sleep(0.5); r.h.debug("b all", 0.5)
    return texts_peek(r)

def probe_boot(r):
    """what the gate saw at boot: machine-type byte (HD: HAGA+$83 as the trampoline sampled it), $2dc/$42e, marker, IB+4, every campaign site"""
    SITES = ((0x72c4,6),(0x77da,12),(0xfda2,6),(0x731e,6),(0x7252,6),(0x74fe,6),(0x8418,6))
    mk = r.mem(0xb2700, 8)
    if r.kind == "hd":
        base = r.l(0x2dc)
        log(f"BOOT {r.tag}: $2dc={base:#x} $42e={r.l(0x42e):#x} HAGA+$83={r.b(base + 0x83):#04x} marker={mk[:4].decode('latin1')} IB+4={mk[4]:#04x}")
    else:
        log(f"BOOT {r.tag}: marker={mk[:4].decode('latin1')} IB+4={mk[4]:#04x}")
    log("BOOT sites", {hex(a): r.mem(a, n).hex() for a, n in SITES})
    return mk
