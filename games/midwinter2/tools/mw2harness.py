#!/usr/bin/env python3
"""Headless Hatari harness for Midwinter 2 (HAGA HD version).

Runs Hatari on a private Xvfb display so mouse/keyboard injection (xdotool)
never touches the user's desktop. All state lives in a scratch dir (default
/tmp/mw2run); the game files are copied there so the originals are never
written (the game writes FFD/FFE and savestates).

Library use:
    from mw2harness import Hatari
    h = Hatari(snapshot="work/snapshots/ingame_lobos_foot.sav")
    print(h.fps(250))            # screen flips per 250 VBLs
    rows = h.profile(250)         # [(addr, cycles), ...]
    h.shot("out.png"); h.close()

CLI:
    python3 tools/mw2harness.py fps     --snapshot S [--vbls N]
    python3 tools/mw2harness.py profile --snapshot S [--vbls N] [--top K]
    python3 tools/mw2harness.py shot    --snapshot S --out FILE [--wait SEC]
    python3 tools/mw2harness.py dump    --snapshot S --out FILE

Facts this relies on (observed 2026-11-07, Hatari 2.6.1, STE TOS 1.62, 2 MB):
  * game double-buffers at $60000/$70000 by toggling only $ff8201, so one
    change of ($ff8201).b == one presented frame;
  * debugger commands sent over --cmd-fifo reset the CPU profile buffer, so
    profiling is ended by a self-firing ':trace :once :file' VBL breakpoint;
  * mouse: xdotool relative motion ~1 host px == 1 screenshot px (ST px * 2);
    clicks need mousedown/mouseup with a short hold;
  * map screens select with SPACE while hovering, not a click.
"""
from __future__ import annotations

import argparse
import gzip
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
TOS_DIR = GAME_DIR.parent.parent / "tos"     # gamebench/tos (supply your own images, see tos/README.md)
TOS_STE = TOS_DIR / "TOS_1_62.img"


def retarget_snapshot(src: str | Path, dst: str | Path, new_workdir: str | Path) -> int:
    """Copy the gzip'd Hatari memstate `src` to `dst`, replacing every `/tmp/strun-<id>` (or `/tmp/mw2run-<id>`) scratch path
    inside it by `new_workdir` (the saved configuration holds the emulated hard-disk directory).
    Strings are NUL-terminated fields: the new string is padded in place. Returns the replacement count."""
    raw = gzip.decompress(Path(src).read_bytes())
    new = str(new_workdir).encode()
    olds = set(re.findall(rb"/tmp/(?:strun|mw2run)-[A-Za-z0-9_]+", raw))
    n = 0
    for old in olds:
        if old == new:
            continue
        pos = 0
        while (i := raw.find(old, pos)) >= 0:
            s = raw.rfind(b"\0", 0, i) + 1
            e = raw.find(b"\0", i)
            f = e
            while f < len(raw) and raw[f] == 0:
                f += 1
            field = raw[s:e].replace(old, new)
            if len(field) >= f - s:
                raise ValueError(f"new path longer than the {f - s}-byte field at {s:#x}")
            raw = raw[:s] + field.ljust(f - s, b"\0") + raw[f:]
            pos = s + len(field)
            n += 1
    Path(dst).write_bytes(gzip.compress(raw, 1))
    return n


class Hatari:
    def __init__(self, snapshot: str | None = None, workdir: str | None = None,
                 machine: str = "ste", tos: Path = TOS_STE, memsize_kb: int = 2048,
                 game_dir: Path = GAME_DIR, extra: list[str] | None = None):
        # Every instance gets its own scratch dir and Xvfb display, so several
        # harnesses (e.g. parallel subagents) never share a window, fifo or disk.
        self.machine = machine
        self.R = Path(workdir or tempfile.mkdtemp(prefix="mw2run-"))
        self.R.mkdir(parents=True, exist_ok=True)
        (self.R / "shots").mkdir(exist_ok=True)
        drive = self.R / "C"
        if not drive.exists():
            # Copy only what the game needs: game_dir may be the project root, whose
            # build/, dist/ and tos/ would make every scratch dir ~70 MB.
            drive.mkdir()
            for name in ("RUNME.TOS", "HAGA", "FF240R.BMP", "FFF273.HST", "LFF273.HST", "FILES"):
                src = Path(game_dir) / name
                if src.is_dir():
                    shutil.copytree(src, drive / name)
                elif src.exists():
                    shutil.copy(src, drive / name)
            # Snapshots were taken with a created campaign disk; the shipped FFD is blank.
            overlay = game_dir / "work" / "disk_overlay"
            if overlay.exists():
                shutil.copytree(overlay, drive, dirs_exist_ok=True)
        self.fifo = self.R / "fifo"
        if self.fifo.exists():
            self.fifo.unlink()
        self.logpath = self.R / "log.txt"
        display = self._reserve_display()
        self.env = dict(os.environ, DISPLAY=f":{display}", SDL_VIDEODRIVER="x11")
        # Never play emulated sound on the host speakers (WAV recording still works); HATARI_AUDIBLE=1 to hear it.
        if os.environ.get("HATARI_AUDIBLE") != "1":
            self.env["SDL_AUDIODRIVER"] = "dummy"
        self.env.pop("WAYLAND_DISPLAY", None)
        self.xvfb = subprocess.Popen(["Xvfb", f":{display}", "-screen", "0", "1024x768x24"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if Path(f"/tmp/.X11-unix/X{display}").exists():
                break
            time.sleep(0.1)
        args = ["hatari", "--confirm-quit", "no", "--machine", machine, "--tos", str(tos),
                "--memsize", str(memsize_kb), "--monitor", "rgb", "--harddrive", str(drive),
                "--fast-boot", "yes", "--sound", "off", "--grab",
                "--cmd-fifo", str(self.fifo), "--screenshot-dir", str(self.R / "shots"),
                "--screenshot-format", "png"]
        # Hatari saves back to the --memstate path (default /tmp/hatari.sav) and
        # blocks on an "overwrite?" dialog if it exists, so always use a scratch copy.
        if snapshot:
            self.state = self.R / "state.sav"
            # The memstate embeds the scratch path of drive C from when it was saved;
            # point it at this run's dir, or the game's later file loads fail.
            retarget_snapshot(snapshot, self.state, self.R)
            args += ["--memstate", str(self.state)]
        else:
            # --memstate rejects a missing file; Hatari's default target is used instead.
            self.state = Path("/tmp/hatari.sav")
            args += ["--auto", "C:\\RUNME.TOS"]
        args += extra or []
        self.log = open(self.logpath, "w")
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=self.env)
        self.win = None
        for _ in range(100):
            if self.fifo.exists():
                ids = self._xdo("search", "--name", "Hatari").stdout.split()
                if ids:
                    self.win = ids[0]
                    break
            if self.proc.poll() is not None:
                break
            time.sleep(0.1)
        if self.win is None:
            self.close()
            raise RuntimeError(f"Hatari did not start; see {self.logpath}:\n{self._logtext()[-2000:]}")
        time.sleep(1.5)
        # Mouse motion is ignored until the window has focus and the pointer is inside it.
        self._xdo("windowfocus", self.win)
        self._xdo("mousemove", "--window", self.win, "416", "294")
        time.sleep(0.5)

    # ---- plumbing -------------------------------------------------------
    def _xdo(self, *a):
        return subprocess.run(["xdotool", *a], env=self.env, capture_output=True, text=True)

    def _logtext(self) -> str:
        return self.logpath.read_text(errors="replace")

    def cmd(self, s: str):
        fd = os.open(self.fifo, os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (s + "\n").encode())
        os.close(fd)

    def debug(self, s: str, wait: float = 0.8) -> str:
        n = len(self._logtext())
        self.cmd(f"hatari-debug {s}")
        time.sleep(wait)
        return self._logtext()[n:]

    def vbl(self) -> int:
        return int(re.findall(r"#(\d+) \(dec\)", self.debug("e VBL"))[-1])

    def _arm_vbl(self, n: int, opts: str = "") -> int:
        """Arm a self-firing VBL breakpoint `n` frames ahead; return log offset."""
        v = self.vbl()
        start = len(self._logtext())
        self.cmd(f"hatari-debug b VBL > {v + n} :trace :once{opts}")
        return start

    def _wait_removed(self, start: int, timeout: float = 300) -> str:
        """Block until the :once VBL breakpoint fires; return log text since `start`."""
        t = time.time()
        while "Removed CPU breakpoint" not in self._logtext()[start:]:
            if time.time() - t > timeout:
                raise TimeoutError("VBL breakpoint never fired")
            time.sleep(0.5)
        time.sleep(0.5)
        return self._logtext()[start:]

    # ---- measurements ---------------------------------------------------
    def set_cpuclock(self, mhz: int):
        self.cmd(f"hatari-option --cpuclock {mhz}")
        time.sleep(1.0)

    def peekw(self, addr: int) -> int:
        """Read a big-endian word from emulated RAM."""
        out = self.debug(f"m ${addr:x} 2", 0.6)
        hi, lo = re.findall(rf"{addr:08x}:\s+([0-9a-f]{{2}}) ([0-9a-f]{{2}})", out, re.I)[-1]
        return int(hi + lo, 16)

    def world_rate(self, addr: int = 0x6888, vbls: int = 250) -> dict:
        """Change per emulated second of a world-state word, alongside fps.

        Default $6888 = HUD distance-to-objective (found by RAM diff against the
        HUD readout). Walking straight it falls at a constant rate per *frame*,
        so this exposes frame-rate-linked game speed.
        """
        v0, d0 = self.vbl(), self.peekw(addr)
        f = self.fps(vbls)
        v1, d1 = self.vbl(), self.peekw(addr)
        f["units_per_sec"] = (d0 - d1) * 50.0 / (v1 - v0)
        return f

    def fps(self, vbls: int = 250) -> dict:
        """Count presented frames ($ff8201 toggles) over `vbls` VBLs (50 Hz)."""
        self.debug("b all", 0.3)
        self.cmd("hatari-debug b ($ff8201).b ! ($ff8201).b :trace")
        time.sleep(0.3)
        start = self._arm_vbl(vbls)
        out = self._wait_removed(start)
        self.debug("b all", 0.3)
        flips = len(re.findall(r"\$ff8201 = ", out))
        return {"vbls": vbls, "flips": flips, "fps": flips * 50.0 / vbls,
                "vbls_per_frame": vbls / flips if flips else None}

    def profile(self, vbls: int = 250, top: int = 20000) -> list[tuple[int, int]]:
        """CPU cycles per instruction address over roughly `vbls` VBLs.

        Any fifo debug command resets the profile buffer, so the end breakpoint
        is armed first and `profile on` is the last command sent.
        """
        end = self.R / "prof_end.txt"
        end.write_text(f"profile cycles {top}\n")
        start = self._arm_vbl(vbls + 25, f" :file {end}")
        time.sleep(0.3)
        self.cmd("hatari-debug profile on")
        out = self._wait_removed(start)
        return [(int(a, 16), int(c)) for a, c in
                re.findall(r"^0x([0-9a-f]+)\s+[\d.]+%\s+(\d+)", out, re.M)]

    def dump(self, out: str, start: int = 0, length: int = 0x200000):
        self.debug(f"savebin {Path(out).resolve()} {start} ${length:x}", 2.0)

    FLIP = 0x26E98      # game's screen-flip routine (work/notes/frameloop.md)

    def capture_frames(self, out_dir: str, live: str | None = None,
                       at_vbl: int = 0, nth_flip: int = 20, timeout: float = 300) -> dict:
        """Deterministic A/B capture for a snapshot run.

        At the first flip after absolute VBL `at_vbl` (pick a fixed value a few
        hundred VBLs past the snapshot's VBL so every run uses the same frame), optionally apply a
        live patch set (`live` = prefix written by `mw2patch.py live`, i.e.
        <live>.img/.json). Then, `nth_flip` flips later, save both screen
        buffers ($60000/$70000) and the draw/display pointers to `out_dir`.
        Must be called right after restoring a snapshot. With no input and a
        per-frame simulation, the same snapshot + same flip index gives the
        same game state, so unpatched and patched captures are directly
        comparable regardless of how fast each build renders.
        Returns {'buf60000','buf70000','ptrs'} paths."""
        import json
        od = Path(out_dir).resolve()
        od.mkdir(parents=True, exist_ok=True)
        cap = self.R / "cap.txt"
        cap.write_text(f"savebin {od}/buf60000.bin $60000 $8000\n"
                       f"savebin {od}/buf70000.bin $70000 $8000\n"
                       f"savebin {od}/ptrs.bin $67a6 8\n")
        cmds = []
        if live:
            spec = json.loads(Path(live + ".json").read_text())
            cmds.append(f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}")
            for s in spec["sites"]:
                new = bytes.fromhex(s["new"])
                cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in new))
        cnt = f" :{nth_flip}" if nth_flip > 1 else ""   # Hatari rejects a skip count of 1
        cmds.append(f"b pc = ${self.FLIP:x}{cnt} :trace :once :file {cap}")
        app = self.R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        if self.vbl() >= at_vbl:
            raise ValueError(f"at_vbl {at_vbl} already passed")
        start = len(self._logtext())
        self.cmd(f"hatari-debug b VBL > {at_vbl} && pc = ${self.FLIP:x} :trace :once :file {app}")
        t = time.time()
        while not (od / "ptrs.bin").exists() or len(self._logtext()[start:].split("Removed CPU breakpoint")) < 3:
            if time.time() - t > timeout:
                raise TimeoutError(f"capture did not complete; log tail:\n{self._logtext()[-1500:]}")
            time.sleep(0.5)
        time.sleep(0.5)
        return {"log": self._logtext()[start:], "dir": str(od)}

    def shot(self, out: str | None = None) -> Path:
        before = set((self.R / "shots").iterdir())
        self.cmd("hatari-shortcut screenshot")
        for _ in range(30):
            new = set((self.R / "shots").iterdir()) - before
            if new:
                break
            time.sleep(0.1)
        p = sorted(new)[0]
        if out:
            shutil.copy(p, out)
            return Path(out)
        return p

    def savemem(self, out: str):
        """Write a snapshot to `out` via the scratch memstate path."""
        tmp = self.state
        if tmp.exists():
            tmp.unlink()
        self.cmd("hatari-shortcut savemem")
        for _ in range(50):
            if tmp.exists() and tmp.stat().st_size > 0:
                break
            time.sleep(0.1)
        time.sleep(1.0)
        shutil.copy(tmp, out)

    # ---- input ----------------------------------------------------------
    def rel(self, dx: int, dy: int, steps: int = 10):
        """Relative mouse motion. The host pointer is NOT grabbed: once it reaches
        the Hatari window edge (about ±400 px x and ±290 px y from the centre),
        further motion in that direction is lost. Call center() between large moves."""
        for _ in range(steps):
            self._xdo("mousemove_relative", "--", str(dx // steps), str(dy // steps))
            time.sleep(0.04)

    def center(self):
        """Warp the host pointer to the window centre. The game DOES see this warp
        as a motion delta, so only use it in menus, or when the game is paused."""
        self._xdo("mousemove", "--window", self.win, "416", "294")
        time.sleep(0.2)

    def home(self):
        """Clamp pointer to the top-left of the game's pointer range."""
        self.rel(-800, -600, 20)
        time.sleep(0.3)

    def click(self, button: str = "1", hold: float = 0.25):
        self._xdo("mousedown", button)
        time.sleep(hold)
        self._xdo("mouseup", button)

    def key(self, keysym: str, hold: float = 0.15):
        self._xdo("keydown", "--window", self.win, keysym)
        time.sleep(hold)
        self._xdo("keyup", "--window", self.win, keysym)

    def screen_matches(self, ref: Path, box: tuple[int, int, int, int], tol: float = 8.0) -> bool:
        """True if the screenshot region `box` matches reference image `ref`
        (mean absolute RGB difference below `tol`). Boxes are in ST-screenshot
        coordinates (832x588, picture at (96,58)); TT/Falcon screenshots have no
        border (640 wide), so the box is shifted for them."""
        from PIL import Image, ImageChops, ImageStat
        img = Image.open(self.shot()).convert("RGB")
        if img.width == 640:
            box = (box[0] - 96, box[1] - 58, box[2] - 96, box[3] - 58)
        cur = img.crop(box)
        diff = ImageChops.difference(cur, Image.open(ref).convert("RGB"))
        return sum(ImageStat.Stat(diff).mean) / 3 < tol

    def goto(self, x: int, y: int):
        """Move the game pointer to screenshot pixel (x, y): home first, then move
        relative to it. Home ≈ screenshot (114, 75), TT (107, 67)."""
        self.home()
        hx, hy = (107, 67) if self.machine == 'tt' else (114, 75)    # TT: the picture has no border (measured in work/notes/tt.md)
        self.rel(x - hx, y - hy)
        time.sleep(0.4)

    def boot_to_game(self, mode: str = "M") -> Path:
        """From a cold boot (snapshot=None), reach the Lobos mission start in the 3D view.

        mode: 'M' mouse, 'J' joystick, 'K' keyboard (the M/J/K start screen).
        Needs the created campaign disk (work/disk_overlay). Takes about 4-5 min
        of wall time. Returns a screenshot of the final state.
        """
        time.sleep(25)
        ref = GAME_DIR / "work" / "ref" / "mode_select.png"
        for _ in range(40):                       # intro pictures, credits, 3D attract demo
            self.cmd("hatari-event keypress 57")
            time.sleep(5)
            if self.screen_matches(ref, (280, 350, 560, 420)):
                break
        else:
            raise RuntimeError("never reached the M/J/K screen")
        for _ in range(5):                        # the key is ignored while the screen fades in
            time.sleep(3)
            self.cmd(f"hatari-event keypress {dict(M=50, J=36, K=37)[mode]}")
            time.sleep(5)
            if not self.screen_matches(ref, (280, 350, 560, 420)):
                break
        else:
            raise RuntimeError("M/J/K key not accepted")
        time.sleep(4)
        self.goto(554, 105); self.click(); time.sleep(15)   # PERSONNEL door
        self.goto(389, 140); self.click(); time.sleep(12)   # USE THIS AGENT
        self.goto(414, 185); self.click(); time.sleep(25)   # CONTROL door -> map
        self.goto(150, 280); self.key("space"); time.sleep(18)  # hover LOBOS + space
        self.goto(230, 410); self.click(); time.sleep(15)   # book icon (objectives)
        boss = GAME_DIR / "work" / "ref" / "boss_thumbs.png"
        for _ in range(6):                        # '?' -> boss screen; clicks are lost while
            self.goto(140, 415); self.click()     # the objectives slideshow loads a page
            time.sleep(8)
            if self.screen_matches(boss, (590, 60, 740, 125)):
                break
        else:
            raise RuntimeError("boot_to_game: never reached the boss (thumbs up) screen")
        self.goto(625, 92); self.click(); time.sleep(40)    # thumbs up -> 3D view
        # In the 3D view: $6220 == $d and $700a == 2 (observed by the PatchAccept runs).
        for _ in range(12):
            if self.peekw(0x6220) == 0xD and self.peekw(0x700A) == 2:
                break
            time.sleep(5)
        else:
            raise RuntimeError("boot_to_game: did not reach the 3D view "
                               f"($6220={self.peekw(0x6220):#x}, $700a={self.peekw(0x700A):#x})")
        self.center()
        return self.shot()

    @staticmethod
    def _reserve_display() -> int:
        """Atomically claim a free X display number. Concurrent harnesses
        (threads or processes) used to race onto the same Xvfb and kill each
        other's X server on close."""
        for n in range(100, 400):
            lock = Path(f"/tmp/.X{n}-lock")
            if lock.exists():
                try:
                    os.kill(int(lock.read_text().strip()), 0)
                    continue               # a live X server owns it
                except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
                    lock.unlink(missing_ok=True)      # stale lock from a killed Xvfb
                    Path(f"/tmp/.X11-unix/X{n}").unlink(missing_ok=True)
            if Path(f"/tmp/.X11-unix/X{n}").exists():
                continue
            claim = f"/tmp/.mw2harness-display-{n}"
            try:
                fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:                       # stale claim from a crashed harness?
                    pid = int(Path(claim).read_text() or 0)
                    os.kill(pid, 0)
                    continue               # owner alive
                except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
                    Path(claim).unlink(missing_ok=True)
                    continue               # retry this number on the next call
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return n
        raise RuntimeError("no free X display")

    def close(self):
        self.proc.kill()
        self.proc.wait()
        if self.xvfb:
            self.xvfb.terminate()      # SIGTERM lets Xvfb remove its /tmp/.X<n>-lock
            try:
                self.xvfb.wait(5)
            except subprocess.TimeoutExpired:
                self.xvfb.kill()
                self.xvfb.wait()
        claim = Path(f"/tmp/.mw2harness-display-{self.env['DISPLAY'][1:]}")
        if claim.exists():
            claim.unlink()
        # The game copy (~3.7 MB) is the bulk of the scratch dir; logs and shots stay.
        shutil.rmtree(self.R / "C", ignore_errors=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["fps", "profile", "shot", "dump", "rate"])
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--vbls", type=int, default=250)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--out")
    ap.add_argument("--wait", type=float, default=3.0, help="seconds to run before acting")
    ap.add_argument("--workdir", default=tempfile.mkdtemp(prefix="mw2run-"))
    ap.add_argument("--cpuclock", type=int, choices=[8, 16, 32], default=8)
    a = ap.parse_args(argv)
    h = Hatari(snapshot=a.snapshot, workdir=a.workdir)
    try:
        time.sleep(a.wait)
        if a.cpuclock != 8:
            h.set_cpuclock(a.cpuclock)
        if a.action == "fps":
            print(h.fps(a.vbls))
        elif a.action == "profile":
            rows = h.profile(a.vbls)
            tot = sum(c for _, c in rows) or 1
            print(f"total_cycles={tot} addresses={len(rows)}")
            for addr, c in sorted(rows, key=lambda r: -r[1])[:a.top or None]:
                print(f"{addr:06x} {100 * c / tot:6.2f}% {c}")
        elif a.action == "shot":
            print(h.shot(a.out))
        elif a.action == "dump":
            h.dump(a.out)
            print(a.out)
        elif a.action == "rate":
            print(h.world_rate(vbls=a.vbls))
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
