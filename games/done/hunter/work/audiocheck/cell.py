#!/usr/bin/env python3
"""One audio-check cell: cold boot of a SHIPPED zip, bank/payload integrity at checkpoints, optional play / save+load / effect capture.

    python3 work/audiocheck/cell.py NAME --kind hd|fl|fl2|hd12|fl12 --machine ste1|ste4|ms1|ms4|st1|tt4|fal4 [--clk 8|16] [--play SECS]
                                    [--saveload] [--fx] [--ring SECS] [--keep]

NAME = label (workdir /tmp/huntbank/NAME).  Output: /tmp/huntbank/out/NAME.txt (raw lines) and work/audiocheck/out/NAME.txt.
Checkpoints: hw (START running, low RAM kept for the TOS-copy search), load (marker HNPO seen = the payload and bank were just loaded), title,
3d (full RAM dump), play (bank re-checked every 30 s), saveload, final (full RAM dump).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ac  # noqa: E402
from ac import T, IMG_BASE, MARKER, FLAGS, SV, MACH, ZIP, REL  # noqa: E402

OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
(T / "out").mkdir(parents=True, exist_ok=True)


class Log:
    def __init__(self, name):
        self.p = T / "out" / f"{name}.txt"
        self.p.write_text("")

    def __call__(self, *a):
        s = " ".join(str(x) for x in a)
        print(s, flush=True)
        with open(self.p, "a") as f:
            f.write(s + "\n")


def make_rig(a, wd: Path, L):
    from stharness import TOS
    mach, tos, mem, extra = MACH[a.machine]
    kw = dict(sound=True, workdir=str(wd))
    if a.kind in ("hd", "hd12", "orig"):
        import huntsave
        g = (ac.GAME if a.kind == "orig" else REL / ZIP[a.kind] / "HUNTER")
        h = huntsave.Rig(game=str(g), machine=mach, tos=TOS[tos], memsize_kb=mem, extra=list(extra), **kw)
    else:
        import huntsave
        d = REL / ZIP[a.kind]
        d2 = d / "HUNTER_disk2_sound.st" if a.kind == "fl2" else None
        h = huntsave.FloppyRig(d / "HUNTER_disk1.st", disk2=d2, drives=1, machine=mach, tos=TOS[tos], memsize_kb=mem, extra=list(extra),
                               fastfdc="yes", **kw)
    return h, mach, mem


class Cell:
    def __init__(self, a, L):
        self.a, self.L = a, L
        self.wd = T / a.name
        shutil.rmtree(self.wd, ignore_errors=True)
        self.wd.mkdir(parents=True)
        self.cap = self.wd / "cap.wav"
        ac.setup_home(self.cap)
        self.h, self.mach, self.mem = make_rig(a, self.wd / "run", L)
        self.ram_kb = self.mem
        self.low_hw = None
        self.t0 = time.time()
        self.res = {"cell": a.name, "kind": a.kind, "machine": a.machine, "cp": {}}

    # ---- checkpoints ------------------------------------------------------------------------------------------------------------
    def cp(self, tag, full=False):
        h, L = self.h, self.L
        if self.a.kind == "orig":
            return None
        try:
            n = 0x23600
            if full:
                ram = ac.savebin(h, self.wd / f"ram_{tag}.bin", 0, self.ram_kb * 1024, tmo=240)
                low = ram
                c = ac.compare_payload(ram[IMG_BASE:IMG_BASE + n], tag)
            else:
                b = ac.savebin(h, self.wd / "bk.bin", IMG_BASE, n)
                c = ac.compare_payload(b, tag)
                low = None
            L(f"t+{time.time() - self.t0:5.0f}s", ac.fmt(c))
            self.res["cp"][tag] = {k: c[k] for k in ("bank", "tail", "code")}
            mk = ac.pk(h, MARKER, 4)
            fl = ac.pk(h, FLAGS, 4)
            sv = ac.pk(h, SV, 8)
            L(f"             MARKER={mk!r} FLAGS={fl.hex()} SV mode/in3d/dma/silent={sv[:4].hex()} $ff8901={ac.pk(h, 0xFF8901, 1).hex()} $ff8921={ac.pk(h, 0xFF8921, 1).hex()}")
            if full:
                for ln in ac.gamex_state(low):
                    L("             " + ln)
                self.scan(low, tag)
            return c
        except Exception as e:  # noqa: BLE001
            L(f"[{tag}] checkpoint FAILED: {e!r}")
            return None

    def cp_hw(self):
        try:
            self.low_hw = ac.savebin(self.h, self.wd / "low_hw.bin", 0, 0x50000)
            self.L(f"t+{time.time() - self.t0:5.0f}s [hw] low RAM $0..$4ffff kept (TOS state before the game)")
        except Exception as e:  # noqa: BLE001
            self.L(f"[hw] dump failed {e!r}")

    def scan(self, ram: bytes, tag):
        """Where do copies of the TOS low-memory image (taken at the HW screen) live now?  Probes of 48 bytes from $400..start of START."""
        L = self.L
        if self.low_hw is None:
            return
        hw = self.low_hw
        found = {}
        for off in range(0x400, 0x14000, 0x180):
            pr = hw[off:off + 48]
            if len(set(pr)) < 12:
                continue
            pos, hits = 0, []
            while True:
                i = ram.find(pr, pos)
                if i < 0 or len(hits) > 8:
                    break
                if not (0x400 <= i < 0x14000 and i == off):
                    hits.append(i)
                pos = i + 1
            if hits:
                found[off] = hits
        if not found:
            L("             TOS-image probes: none found outside $400..$14000 (state changed since the HW screen, or no copy)")
            return
        bases = {}
        for off, hits in found.items():
            for a in hits:
                bases.setdefault(a - off, []).append(off)
        for base, offs in sorted(bases.items(), key=lambda kv: -len(kv[1]))[:6]:
            L(f"             TOS-image copy candidate: base ${base:x} (RAM $0 = ${base:x}) matched by {len(offs)} probes at offsets ${min(offs):x}..${max(offs):x}")

    def bank_watch(self):
        return self.cp("bank", full=False)

    # ---- boot ---------------------------------------------------------------------------------------------------------------------
    def hook(self):
        h, L = self.h, self.L
        import huntvis_cold as vc
        vc.harden(h)
        stage = h._stage
        seen = {"hw": False, "load": False}
        big = self.mem >= 2048

        def st(name, record, wait, timeout=120):
            if name == "title2" and not seen["load"] and self.a.kind != "orig":
                t = time.time()
                while time.time() - t < 400:
                    try:
                        if h.peek(MARKER, 4) in (b"HNPO", b"HNPF"):
                            break
                    except Exception:  # noqa: BLE001
                        pass
                    time.sleep(1.5)
                seen["load"] = True
                self.cp("load")
            if name == "game" and big:
                t = time.time()
                while time.time() - t < 400:
                    if h.in_game():
                        break
                    time.sleep(2)
                else:
                    raise RuntimeError("3D loop not reached")
            else:
                stage(name, record, wait, timeout)
            if name == "hw" and not seen["hw"]:
                seen["hw"] = True
                self.cp_hw()
            if name == "title2":
                self.cp("title")
        h._stage = st

    def boot(self):
        a, h, L = self.a, self.h, self.L
        self.hook()
        mach = self.mach
        if a.kind in ("hd", "hd12", "orig"):
            if mach in ("ste",):
                h.boot_to_game()
            elif mach in ("st",):
                import huntpatch
                time.sleep(10)
                self.cp_hw()
                huntpatch.blind_boot(h)
            elif mach == "tt":
                time.sleep(10)
                self.cp_hw()
                self.boot_tt()
            else:                                       # megaste: slow TOS 2.06 boot
                import test_hd_image as thi
                thi.wait_drive_c(h)
                h._stage("hw", False, 12, 400)
                h.keypress(57)
                h._stage("title1", False, 6, 400)
                h.keypress(57)
                h._stage("title2", False, 22, 400)
                time.sleep(1.5)
                h.key("space", 0.3)
                h._stage("main", False, 3, 400)
                h.goto(*h.START_XY, home_xy=h.HOME_XY)
                h.click()
                h._stage("games", False, 3, 400)
                h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
                h.click()
                h._stage("name", False, 3, 400)
                for c in "bench":
                    h.key(c, 0.15)
                    time.sleep(0.3)
                h.click()
                h._stage("mission", False, 4, 400)
                h.click()
                h._stage("game", False, 9, 400)
                time.sleep(1.0)
        else:
            blind = mach in ("st", "tt", "falcon")
            pb = {"ste": 12, "st": 12, "tt": 35, "falcon": 35}.get(mach, 0)
            if mach == "megaste":
                pb = 0
            path = "swap" if a.kind == "fl2" and mach != "st" else "none"
            h.boot_floppy(path, blind=blind, pb_key_at=pb, log=lambda *x: L("   boot:", *x))
        ok = h.in_game()
        L(f"t+{time.time() - self.t0:5.0f}s BOOT in_game={ok} MARKER={h.peek(MARKER, 4)!r} FLAGS={h.peek(FLAGS, 4).hex()}")
        return ok

    def boot_tt(self):
        h = self.h
        if not h.wait_stage("title2", 300, 2):
            raise RuntimeError("TT: the animated title was not reached")
        time.sleep(1.5)
        h.key("space", 0.3)
        for stage, t in (("main", 40), ("games", 30), ("name", 30), ("mission", 40), ("game", 60)):
            if stage == "games":
                h.goto(*h.START_XY, home_xy=h.HOME_XY)
                h.click()
            elif stage == "name":
                h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
                h.click()
            elif stage == "mission":
                for c in "bench":
                    h.key(c, 0.15)
                    time.sleep(0.3)
                h.click()
            elif stage == "game":
                h.click()
            if not h.wait_stage(stage, t, 2):
                raise RuntimeError(f"TT: screen '{stage}' not reached")
        time.sleep(1.0)

    # ---- phases -----------------------------------------------------------------------------------------------------------------
    def play(self, secs):
        h, L = self.h, self.L
        t = time.time()
        k = 0
        while time.time() - t < secs:
            keys = [("Up",), ("Up", "Left"), ("Up", "Right"), ("Up",)][k % 4]
            h.hold(*keys)
            time.sleep(min(30, secs - (time.time() - t)))
            h.release(*keys)
            k += 1
            self.cp("bank", full=False)
            try:
                if self.a.kind != "orig" and h.peek(MARKER, 4) != b"HNPO":
                    L(f"RESET/CRASH DETECTED after {time.time() - t:.0f} s of play (marker {h.peek(MARKER, 4)!r}), VBL {h.vbl()}")
                    h.shot(str(T / "out" / f"{self.a.name}_reset.png"))
                    break
            except Exception as e:  # noqa: BLE001
                L(f"marker check failed {e!r}")
        L(f"t+{time.time() - self.t0:5.0f}s played {secs} s, in_game={h.in_game()}")
        lt = h._logtext()
        if "pc = $10f74" in lt:
            i = lt.index("pc = $10f74")
            L("TRAP FIRED:\n" + lt[i - 200:i + 2500])

    def saveload(self):
        h, L = self.h, self.L
        try:
            h.walk(2, "Up")
            L("saving")
            h.save(2, "ac")
            L("saved")
            self.cp("saved")
            h.walk(2, "Up", "Left")
            try:
                h.load(2)
            except RuntimeError:
                h.click()
                h.wait_game(40)
            L(f"SAVE+LOAD done, in_game={h.in_game()}")
            self.cp("saveload")
        except Exception as e:  # noqa: BLE001
            L(f"SAVE/LOAD FAILED: {e!r}")
            traceback.print_exc()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--kind", required=True, choices=["hd", "fl", "fl2", "hd12", "fl12", "orig"])
    ap.add_argument("--machine", required=True, choices=list(MACH))
    ap.add_argument("--clk", type=int, default=0)
    ap.add_argument("--play", type=int, default=60)
    ap.add_argument("--saveload", action="store_true")
    ap.add_argument("--fx", action="store_true")
    ap.add_argument("--ring", type=int, default=0)
    ap.add_argument("--voices", action="store_true")
    ap.add_argument("--no-trap", dest="trap", action="store_false", help="do not arm the breakpoint on the exception tail $10f74 (default: armed before play)")
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    L = Log(a.name)
    L(f"CELL {a.name}: kind={a.kind} ({ZIP.get(a.kind, a.kind)}) machine={a.machine} {MACH[a.machine][:3]} clk={a.clk or 'default'}")
    c = None
    try:
        c = Cell(a, L)
        if a.clk:
            c.h.set_cpuclock(a.clk)
        ok = c.boot()
        if ok:
            c.cp("3d", full=True)
            try:
                f = c.h.fps(150)
                L(f"3D view standing: fps {f['fps']:.2f} over 150 VBL; $ff8e21 (Mega STE speed/cache) = {ac.pk(c.h, 0xFF8E21, 1).hex()}; $ff8e01 = {ac.pk(c.h, 0xFF8E01, 1).hex()}")
            except Exception as e:  # noqa: BLE001
                L(f"fps failed {e!r}")
            if a.fx or a.ring or a.voices:
                import fx
                fx.run(c, a)
            if a.trap:
                tf = c.wd / "trap.txt"
                tf.write_text("r\ne VBL\nm $7e700 256\nm $806 64\n")
                c.h.debug("b all", 0.3)
                c.h.cmd(f"hatari-debug b pc = $10f74 :trace :file {tf}")
                time.sleep(0.3)
                L("trap armed at $10f74")
            if a.play:
                c.play(a.play)
            if a.saveload:
                c.saveload()
            c.cp("final", full=True)
    except Exception as e:  # noqa: BLE001
        L(f"CELL FAILED: {e!r}")
        traceback.print_exc()
        try:
            c.h.shot(str(T / "out" / f"{a.name}_fail.png"))
        except Exception:  # noqa: BLE001
            pass
    finally:
        if c:
            h = c.h
            if hasattr(h, "d1"):
                scratch, h.d1 = h.d1.parent, Path("/nonexistent/hd1.st")
            h.close()
            if hasattr(h, "d1") and not a.keep:
                shutil.rmtree(scratch / "run" / "shots", ignore_errors=True)
            if not a.keep:
                for f in c.wd.glob("ram_*.bin"):
                    f.unlink()
            json.dump(c.res, open(T / "out" / f"{a.name}.json", "w"))
    shutil.copy(T / "out" / f"{a.name}.txt", OUT / f"{a.name}.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
