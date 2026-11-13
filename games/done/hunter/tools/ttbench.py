#!/usr/bin/env python3
r"""Hunter on a TT with EXACTLY dist/run_tt.sh's machine flags: 3D-view frame rate and cache state (HunterTT, work/notes/tt_v12.md).

    python3 tools/ttbench.py CELL --kind hd|fl --game DIR | --disk FILE [--poke-mch] [--poke-fdc] [--machine tt] [--secs 20]
                             [--hatari-opt "..."] [--vbls 500]

Flags (the run_tt.sh line; the harness' own `--monitor rgb` is overridden by the later --monitor vga):
    --machine tt --tos TOS_3_06_uk.img --memsize 4096 --cpuclock 32 --monitor vga --mmu true  (+ --acsi image | --disk-a floppy)
Metric: a breakpoint on the game's frame-loop top `$253e` (bset #7,$93(a5), once per frame, never patched by any of our sites) counted
over N emulated VBLs (Hatari's `e VBL`), standing at the HQ and walking (Up held).  fps = hits * 50 / VBLs.  Also prints the host
seconds the run took (emulation speed) and CACR read from the debugger.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
sys.path.insert(0, str(HERE))
import hunter  # noqa: E402
from hunter import Hunter, TOS  # noqa: E402
from huntfloppy import HunterFloppy  # noqa: E402
import test_hd_image as thi  # noqa: E402

LOOP_TOP = 0x253E
TT_OPTS = ["--cpuclock", "32", "--monitor", "vga", "--mmu", "true"]      # + --machine tt --tos 3.06 --memsize 4096 from the constructor
MARKER, FLAGS = 0x8BFF8, 0x8BFF0
START_SIG = bytes.fromhex("4e907e1c3f3c00254e4e548f51cffff6")
START_SIG_OFF = 0x590
JAR_MCH_VALUE = 0xD0EE8


class _Gate:
    def at(self, stage: str) -> bool:
        if stage == "game":      # the HUD crop is the ST panel; v1.2 on 2 MB+ 68000 machines has the Amiga dashboard: gate on the loop flag instead
            return bool(self.peek(self.MODE, 1)[0] & 0x80)
        return super().at(stage)


class HDTT(_Gate, Hunter):
    pass


def cacr(h) -> str:
    """CACR from the debugger register dump (Hatari prints it for 68020+)."""
    out = h.debug("r", 0.8)
    m = re.search(r"CACR[: =]+([0-9a-fA-F]+)", out)
    return m.group(1) if m else "?: " + out[-300:].replace("\n", " | ")


def measure(h, vbls: int = 500, tag: str = "", log=print) -> dict:
    """Frames per emulated second over `vbls` VBLs (loop-top breakpoint), plus host seconds and the VBL rate."""
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${LOOP_TOP:x} :trace")
    time.sleep(0.3)
    v0, x0, z0 = h.vbl(), h.peekw(0xAB2), h.peekw(0xAB6)
    t0 = time.time()
    start = h._arm_vbl(vbls)
    out = h._wait_removed(start, timeout=1800)
    dt = time.time() - t0
    h.debug("b all", 0.3)
    v1, x1, z1 = h.vbl(), h.peekw(0xAB2), h.peekw(0xAB6)
    dx, dz = (x1 - x0 + 0x8000) % 0x10000 - 0x8000, (z1 - z0 + 0x8000) % 0x10000 - 0x8000
    wr = ((dx * dx + dz * dz) ** 0.5) * 50.0 / (v1 - v0)
    hits = out.count("CPU breakpoint condition(s) matched")
    # `b VBL > N` removal ends the window; the number of hits above includes only the loop-top breakpoint
    r = {"vbls": vbls, "frames": hits, "fps": hits * 50.0 / vbls, "vbl_per_frame": vbls / hits if hits else None, "host_s": dt,
         "emu_x": vbls / 50.0 / dt, "world_u_s": wr}
    log(f"  MEASURE {tag}: {hits} frames / {vbls} VBL -> {r['fps']:.2f} fps ({r['vbl_per_frame'] and round(r['vbl_per_frame'], 2)} VBL/frame); "
        f"host {dt:.1f} s = {r['emu_x']:.2f}x real time; world {wr:.1f} u/s")
    return r


BUCKETS = [("idle_spin", 0xAAA2, 0xAABE), ("tb", 0x8C1B2, 0x8C400), ("pal", 0x8C014, 0x8C066), ("sky", 0x8F100, 0x8F800),
           ("sky2_pnl", 0x8ED80, 0x8EEA0), ("snd", 0x8E000, 0x8EA00), ("hz", 0x8DA00, 0x8DC00), ("payload_all", 0x8BB00, 0x90000)]


def prof(h, vbls: int, tag: str, log=print) -> dict:
    """Hatari CPU profile over `vbls` VBLs: cycles per VBL by region (idle spin of the frame wait, each patch's payload window)."""
    p = h.profile(vbls, top=40000)
    tot = sum(c for _, c in p)
    out = {"total_per_vbl": tot / vbls}
    for name, lo, hi in BUCKETS:
        out[name] = sum(c for a, c in p if lo <= a < hi) / vbls
    log(f"  PROFILE {tag}: {tot / vbls:,.0f} cycles/VBL total; " + ", ".join(f"{k} {v:,.0f}" for k, v in out.items() if k != "total_per_vbl"))
    return out


def cpu_s(pid: int) -> float:
    f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
    return (int(f[11]) + int(f[12])) / 100.0


def speed(h, vbls: int, tag: str, log=print) -> dict:
    """Host cost of the emulation: Hatari fast-forward (no real-time pacing) over `vbls` emulated VBLs; host wall and process CPU seconds.
    Emulated VBLs per host second = the maximum speed this build can run at on this host."""
    h.cmd("hatari-option --fast-forward true")
    time.sleep(1.0)
    c0, t0 = cpu_s(h.proc.pid), time.time()
    start = h._arm_vbl(vbls)
    h._wait_removed(start, timeout=1800)
    dt, dc = time.time() - t0, cpu_s(h.proc.pid) - c0
    h.cmd("hatari-option --fast-forward false")
    time.sleep(1.0)
    r = {"vbls": vbls, "host_s": dt, "cpu_s": dc, "max_x": vbls / 50.0 / dt}
    log(f"  SPEED {tag}: {vbls} VBL in {dt:.1f} s host ({dc:.1f} s process CPU) = {r['max_x']:.2f}x real time at fast-forward")
    return r


def _safe(fn, *a):
    try:
        return fn(*a)
    except Exception as e:  # noqa: BLE001
        a[-1](f"  {fn.__name__} FAILED: {e!r}")
        return {}


def run_cell(h, name: str, secs: float, vbls: int, log=print, do_prof: bool = True) -> dict:
    res = {}
    mk, fl = h.peek(MARKER, 4), h.peek(FLAGS, 4)
    if getattr(h, "machine_name", "tt") == "megaste":
        extra = f" $ff8e21={h.peek(0xFF8E21, 1).hex()}"
    else:
        extra = f" CACR={cacr(h)}"
    log(f"CELL {name}: in_game={h.in_game()} MARKER={mk!r} FLAGS={fl.hex()}{extra}")
    res["stand"] = measure(h, vbls, f"{name} stand", log)
    if do_prof:
        res["prof_stand"] = prof(h, 100, f"{name} stand", log)
    res["speed_stand"] = _safe(speed, h, 500, f"{name} stand", log)
    h.hold("Up")
    time.sleep(secs)
    res["walk"] = measure(h, vbls, f"{name} walk", log)
    if do_prof:
        res["prof_walk"] = prof(h, 100, f"{name} walk", log)
    res["speed_walk"] = _safe(speed, h, 500, f"{name} walk", log)
    if getattr(h, "machine_name", "tt") == "megaste":
        log(f"  $ff8e21 walking: {h.peek(0xFF8E21, 1).hex()}")
    else:
        log(f"  CACR walking: {cacr(h)}")
    h.release("Up")
    return res


def arm_mch_poke(h, mch: int) -> None:
    p = h.R / "ramscan.bin"
    h.dump(str(p), 0, 0x100000)
    time.sleep(0.5)
    i = p.read_bytes().find(START_SIG)
    if i < 0:
        raise RuntimeError("START signature not found")
    base = i - START_SIG_OFF
    cf = h.R / "mch.txt"
    cf.write_text(f"w ${JAR_MCH_VALUE:x} " + " ".join(f"${(mch >> s) & 255:02x}" for s in (24, 16, 8, 0)) + "\n")
    h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b pc = ${base + START_SIG_OFF:x} :trace :once :file {cf}")
    time.sleep(0.4)


MACHINES = {
    "tt": dict(tos="3.06", opts=TT_OPTS),                                        # dist/run_tt.sh
    "megaste": dict(tos="2.06", opts=["--cpuclock", "16", "--monitor", "rgb"]),  # dist/run_megaste.sh
    "ste": dict(tos="1.62", opts=[], mem=1024),                                  # the harness' STE cell (8 MHz, 1 MB)
    "falcon": dict(tos="4.04", opts=["--mmu", "true"]),                          # Falcon floppy cell (ttfalcon.md section 7)
}


def boot_hd(game: Path | None, extra: list[str], poke_mch: bool, machine: str = "tt", image: Path | None = None):
    """game: a folder with START.TOS (own ACSI image built from it); image: the all-games .vhd/.img (scratch copy + autorun line,
    the test_hd_image.py route; the shipped image is never touched)."""
    cfg = MACHINES[machine]
    orig = hunter.build_hd
    src = None
    if image is not None:
        src = thi.test_image(image, Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", "hunter")
        hunter.build_hd = lambda img, **k: shutil.copy(src, img)
    else:
        hunter.build_hd = lambda img, **k: orig(img, game=game, **k)
    try:
        h = HDTT(machine=machine, tos=TOS[cfg["tos"]], memsize_kb=4096, extra=cfg["opts"] + extra)
    finally:
        hunter.build_hd = orig
    h.machine_name = machine
    h._srcdir = src.parent if src else None
    try:
        stage = h._stage
        h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
        if machine == "megaste":
            thi.wait_drive_c(h)
            h.boot_to_game()
            return h
        thi.wait_drive_c(h)
        time.sleep(3)
        if poke_mch:
            arm_mch_poke(h, 0x20000)
        h.keypress(57)
        time.sleep(3)
        for stg, wait, key in (("title2", 150, None), ("main", 40, "space"), ("games", 30, "start"), ("name", 30, "action"),
                               ("mission", 30, "type"), ("game", 60, "click")):
            if key == "space":
                time.sleep(1.5)
                h.key("space", 0.3)
            elif key == "start":
                h.goto(*h.START_XY, home_xy=h.HOME_XY)
                h.click()
            elif key == "action":
                h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
                h.click()
            elif key == "type":
                for c in "bench":
                    h.key(c, 0.15)
                    time.sleep(0.3)
                h.click()
            elif key == "click":
                h.click()
            if not h.wait_stage(stg, wait, 2):
                raise RuntimeError(f"screen {stg} not reached")
        time.sleep(1.0)
        return h
    except Exception:
        h.close()
        raise


class FL(_Gate, HunterFloppy):
    poke_fdc = False

    def leave_title(self, blind: bool = False, timeout: float = 240) -> None:
        if self.poke_fdc:     # ttfalcon.md section 4: the stock loader's FDC time-out constant at $d51e (`243c 0007 0000`) is too short on a 030
            self.debug("w $d51e $01 $00 $00 $00", 0.3)
        super().leave_title(blind, timeout)


def boot_floppy(disk: Path, extra: list[str], poke_fdc: bool, machine: str = "tt", hook_hits: bool = False):
    cfg = MACHINES[machine]
    h = FL(disk, None, drives=1, machine=machine, tos=TOS[cfg["tos"]], memsize_kb=cfg.get("mem", 4096), extra=cfg["opts"] + extra, fastfdc="no")
    h.machine_name = machine
    h.poke_fdc = poke_fdc
    try:
        if hook_hits:
            h.at_start("b pc = $8d360 :trace\n")
        blind = bool(os.environ.get("TTBLIND"))   # default: stage crops (the HD route proves they match on TT and Falcon); fixed waits led into another (heavy, moving) scene
        ok = h.boot_floppy("none", blind=blind, pb_key_at={"tt": 35, "falcon": 35, "megaste": 120, "ste": 12}[machine])
        if not ok:
            raise RuntimeError("floppy boot did not reach the 3D view")
        if hook_hits:
            n = h._logtext().count("CPU breakpoint condition(s) matched")
            print(f"  HOOK fdc_dma ($8d360) breakpoint hits since the game start: {n}", flush=True)
            h.debug("b all", 0.5)
        return h
    except Exception:
        try:
            q = h.shot()
            shutil.copy(q, f"/tmp/ttv/logs/fail_{machine}_{disk.parent.parent.name}.png")
            print(f"  failure screenshot saved; MARKER={h.peek(MARKER, 4)!r} FLAGS={h.peek(FLAGS, 4).hex()} CACR={cacr(h)[:80]}", flush=True)
        except Exception as e2:  # noqa: BLE001
            print(f"  (no failure screenshot: {e2!r})", flush=True)
        h.close()
        raise


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--kind", choices=["hd", "fl"], default="hd")
    ap.add_argument("--game", default=None, help="HD build dir (the folder with START.TOS)")
    ap.add_argument("--disk", default=None, help="floppy image")
    ap.add_argument("--machine", default="tt", choices=list(MACHINES))
    ap.add_argument("--image", default=None, help="all-games hard-disk image (hunter autorun scratch copy)")
    ap.add_argument("--hook-hits", action="store_true", help="floppy: profile from the game start and report how often fdc_dma ($8d360) ran")
    ap.add_argument("--dump", default=None, help="save RAM $0..$fffff right after the boot")
    ap.add_argument("--poke-fdc", action="store_true", help="stock floppy on a TT: raise the loader's FDC time-out constant")
    ap.add_argument("--poke-mch", action="store_true", help="stock PP HD build: _MCH poke (ttfalcon.md section 2)")
    ap.add_argument("--hatari-opt", default="")
    ap.add_argument("--secs", type=float, default=15)
    ap.add_argument("--vbls", type=int, default=500)
    a = ap.parse_args()
    ex = a.hatari_opt.replace(",", " ").split()
    h = None
    try:
        if a.kind == "hd":
            h = boot_hd(Path(a.game).resolve() if a.game else None, ex, a.poke_mch, a.machine, Path(a.image).resolve() if a.image else None)
        else:
            h = boot_floppy(Path(a.disk).resolve(), ex, a.poke_fdc, a.machine, a.hook_hits)
        if a.dump:
            h.dump(a.dump, 0, 0x100000)
        run_cell(h, a.name, a.secs, a.vbls)
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"CELL {a.name} FAILED: {e!r}")
        return 1
    finally:
        if h is not None:
            h.close()
            if getattr(h, "_srcdir", None):
                shutil.rmtree(h._srcdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
