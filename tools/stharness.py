#!/usr/bin/env python3
"""Headless Hatari harness for Atari ST game work (generic; born on Midwinter 2).

Runs Hatari on a private Xvfb display, so mouse and keyboard injection (xdotool)
never touch the user's desktop. Every instance gets its own scratch dir
(/tmp/strun-*) and its own display, so several can run in parallel. The game's
files are copied into the scratch dir, so the originals are never written.

Library use (game-specific navigation lives in games/<game>/tools/, which
subclasses Hatari):
    import sys; sys.path.insert(0, "<gamebench>/tools")
    from stharness import Hatari, TOS
    h = Hatari(game_dir="games/midwinter", snapshot="games/midwinter/work/snapshots/x.sav")
    h = Hatari(game_dir="games/midwinter", snapshot=None, memsize_kb=1024,
               machine="megaste", tos=TOS["2.06"])          # cold boot, autoruns RUNME.TOS
    print(h.fps(250)); rows = h.profile(250); h.shot("out.png"); h.close()

CLI:
    python3 tools/stharness.py fps|profile|shot|dump --game DIR --snapshot S [--vbls N]

Facts and gotchas (Hatari 2.6.1); the skill `st-hatari-harness` explains them:
  * Every debugger breakpoint needs `:trace`, or the run blocks forever on stdin.
  * Clear breakpoints with `b all`; `bc all` is not a command.
  * Any fifo debug command resets the CPU profiler, so profile() arms its
    end breakpoint first.
  * Long debugger command lines are truncated silently; keep paths short.
  * Mouse: xdotool relative motion is about 1 host px per screenshot px (ST px x2).
    Clicks need a hold. The host pointer is not grabbed (the window edge clamps it).
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent
TOS_DIR = BENCH / "tos"
TOS = {
    "1.02": TOS_DIR / "TOS_1_02.img", "1.04": TOS_DIR / "TOS_1_04.img",
    "1.06": TOS_DIR / "TOS_1_06.img", "1.62": TOS_DIR / "TOS_1_62.img",
    "2.06": TOS_DIR / "TOS_2_06.img", "emutos": TOS_DIR / "EmuTOS_1024k.img",
}
# Directory names that are project scaffolding, never game files.
NOT_GAME = {"work", "tools", "build", "dist", "patches", ".omp", "tos", "__pycache__"}


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
    def __init__(self, game_dir: str | Path, snapshot: str | None = None,
                 workdir: str | None = None, machine: str = "ste", tos: Path = TOS["1.62"],
                 memsize_kb: int = 1024, files: list[str] | None = None,
                 overlay: Path | None = None, autorun: str = "C:\\RUNME.TOS",
                 flip_reg: str = "($ff8201).b", extra: list[str] | None = None):
        """game_dir: the game folder (copied to scratch as drive C:).
        files: names inside game_dir to copy (default: everything that isn't scaffolding,
        *.md or *.zip). overlay: a dir copied over the drive afterwards (default
        game_dir/work/disk_overlay if it exists; e.g. a created campaign disk).
        flip_reg: the shifter register expression whose change marks a presented frame."""
        self.game_dir = Path(game_dir).resolve()
        self.flip_reg = flip_reg
        self.R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
        self.R.mkdir(parents=True, exist_ok=True)
        (self.R / "shots").mkdir(exist_ok=True)
        drive = self.R / "C"
        if not drive.exists():
            drive.mkdir()
            names = files or [p.name for p in self.game_dir.iterdir()
                              if p.name not in NOT_GAME and p.suffix.lower() not in (".md", ".zip")]
            for name in names:
                src = self.game_dir / name
                if src.is_dir():
                    shutil.copytree(src, drive / name)
                elif src.exists():
                    shutil.copy(src, drive / name)
            ov = overlay if overlay is not None else self.game_dir / "work" / "disk_overlay"
            if ov and Path(ov).exists():
                shutil.copytree(ov, drive, dirs_exist_ok=True)
        self.fifo = self.R / "fifo"
        if self.fifo.exists():
            self.fifo.unlink()
        self.logpath = self.R / "log.txt"
        display = self._reserve_display()
        self.env = dict(os.environ, DISPLAY=f":{display}", SDL_VIDEODRIVER="x11")
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
        # Hatari saves back to the --memstate path and blocks on an "overwrite?" dialog
        # if it exists, so always restore from a scratch copy.
        if snapshot:
            self.state = self.R / "state.sav"
            # The memstate embeds the scratch path of drive C from when it was saved;
            # point it at this run's dir, or the game's later file loads fail.
            retarget_snapshot(snapshot, self.state, self.R)
            args += ["--memstate", str(self.state)]
        else:
            self.state = Path("/tmp/hatari.sav")      # --memstate rejects a missing file
            if autorun:
                args += ["--auto", autorun]
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
        """Send a remote-control command (hatari-debug / hatari-shortcut / hatari-event / hatari-option)."""
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
        out = self.debug(f"m ${addr:x} 2", 0.6)
        hi, lo = re.findall(rf"{addr:08x}:\s+([0-9a-f]{{2}}) ([0-9a-f]{{2}})", out, re.I)[-1]
        return int(hi + lo, 16)

    def peekl(self, addr: int) -> int:
        return (self.peekw(addr) << 16) | self.peekw(addr + 2)

    def fps(self, vbls: int = 250) -> dict:
        """Count presented frames (changes of `flip_reg`) over `vbls` VBLs."""
        self.debug("b all", 0.3)
        self.cmd(f"hatari-debug b {self.flip_reg} ! {self.flip_reg} :trace")
        time.sleep(0.3)
        start = self._arm_vbl(vbls)
        out = self._wait_removed(start)
        self.debug("b all", 0.3)
        reg = re.search(r"\$([0-9a-f]+)", self.flip_reg).group(1)
        flips = len(re.findall(rf"\${reg} = ", out))
        return {"vbls": vbls, "flips": flips, "fps": flips * 50.0 / vbls,
                "vbls_per_frame": vbls / flips if flips else None}

    def world_rate(self, addr: int, vbls: int = 250, long: bool = False) -> dict:
        """fps plus the change per emulated second of a world-state word/long at
        `addr`. Use a position variable to prove game speed is CPU-independent."""
        rd = self.peekl if long else self.peekw
        v0, d0 = self.vbl(), rd(addr)
        f = self.fps(vbls)
        v1, d1 = self.vbl(), rd(addr)
        d = d1 - d0
        if not long and abs(d) > 0x8000:
            d -= 0x10000 if d > 0 else -0x10000
        f["units_per_sec"] = d * 50.0 / (v1 - v0)
        return f

    def profile(self, vbls: int = 250, top: int = 20000) -> list[tuple[int, int]]:
        """CPU cycles per instruction address over roughly `vbls` VBLs."""
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

    def capture_frames(self, out_dir: str, flip_addr: int, at_vbl: int, nth_flip: int = 20,
                       live: str | None = None, buffers: dict[str, tuple[int, int]] | None = None,
                       timeout: float = 300) -> dict:
        """Deterministic A/B capture for a snapshot run.

        At the first execution of the game's flip routine `flip_addr` after the
        absolute VBL `at_vbl`, optionally apply a live patch set (`live` = a
        <prefix>.img/.json pair with img_base and sites). Then, `nth_flip` flips
        later, save the `buffers` {name: (addr, len)} to out_dir/<name>.bin.
        Call it right after restoring a snapshot. With no input and a per-frame
        simulation, unpatched and patched captures are directly comparable."""
        buffers = buffers or {"buf60000": (0x60000, 0x8000), "buf70000": (0x70000, 0x8000)}
        od = Path(out_dir).resolve()
        od.mkdir(parents=True, exist_ok=True)
        cap = self.R / "cap.txt"
        cap.write_text("".join(f"savebin {od}/{n}.bin ${a:x} ${ln:x}\n" for n, (a, ln) in buffers.items()))
        cmds = []
        if live:
            spec = json.loads(Path(live + ".json").read_text())
            cmds.append(f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}")
            for s in spec["sites"]:
                cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s["new"])))
        cnt = f" :{nth_flip}" if nth_flip > 1 else ""   # Hatari rejects a skip count of 1
        cmds.append(f"b pc = ${flip_addr:x}{cnt} :trace :once :file {cap}")
        app = self.R / "apply.txt"
        app.write_text("\n".join(cmds) + "\n")
        if len(max(cmds, key=len)) > 240:
            raise ValueError("debugger command line too long (Hatari truncates silently)")
        if self.vbl() >= at_vbl:
            raise ValueError(f"at_vbl {at_vbl} already passed")
        start = len(self._logtext())
        self.cmd(f"hatari-debug b VBL > {at_vbl} && pc = ${flip_addr:x} :trace :once :file {app}")
        last = od / f"{list(buffers)[-1]}.bin"
        t = time.time()
        while not last.exists() or len(self._logtext()[start:].split("Removed CPU breakpoint")) < 3:
            if time.time() - t > timeout:
                raise TimeoutError(f"capture did not complete; log tail:\n{self._logtext()[-1500:]}")
            time.sleep(0.5)
        time.sleep(0.5)
        return {"log": self._logtext()[start:], "dir": str(od)}

    def shot(self, out: str | None = None) -> Path:
        before = set((self.R / "shots").iterdir())
        self.cmd("hatari-shortcut screenshot")
        new = set()
        for _ in range(30):
            new = set((self.R / "shots").iterdir()) - before
            if new:
                break
            time.sleep(0.1)
        if not new:
            raise RuntimeError("no screenshot (Hatari busy, e.g. a dialog, or dead)")
        p = sorted(new)[0]
        if out:
            shutil.copy(p, out)
            return Path(out)
        return p

    def savemem(self, out: str):
        """Write a memory snapshot to `out` (via the scratch memstate path)."""
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
        """Relative mouse motion. The host pointer is not grabbed: past the window edge
        (about +-400 x, +-290 y from the centre) motion is lost; use center() in menus."""
        for _ in range(steps):
            self._xdo("mousemove_relative", "--", str(dx // steps), str(dy // steps))
            time.sleep(0.04)

    def center(self):
        """Warp the host pointer to the window centre (the game sees the warp as motion)."""
        self._xdo("mousemove", "--window", self.win, "416", "294")
        time.sleep(0.2)

    def home(self):
        """Clamp the pointer to the top-left of the game's pointer range."""
        self.rel(-800, -600, 20)
        time.sleep(0.3)

    def goto(self, x: int, y: int, home_xy: tuple[int, int] = (114, 75)):
        """Move the game pointer to screenshot pixel (x, y): home first, then move
        relative. home_xy = where home() leaves the pointer (measure per game)."""
        self.home()
        self.rel(x - home_xy[0], y - home_xy[1])
        time.sleep(0.4)

    def click(self, button: str = "1", hold: float = 0.25):
        self._xdo("mousedown", button)
        time.sleep(hold)
        self._xdo("mouseup", button)

    def key(self, keysym: str, hold: float = 0.15):
        self._xdo("keydown", "--window", self.win, keysym)
        time.sleep(hold)
        self._xdo("keyup", "--window", self.win, keysym)

    def keypress(self, scancode: int):
        """ST scancode via Hatari (space 57, Return 28, Esc 1, M 50, J 36, K 37)."""
        self.cmd(f"hatari-event keypress {scancode}")

    def screen_matches(self, ref: Path, box: tuple[int, int, int, int], tol: float = 8.0) -> bool:
        """True if the screenshot region `box` (ST-screenshot coordinates: 832x588,
        picture at (96,58)) matches the image `ref`. Borderless TT/Falcon shots
        (640 wide) are shifted automatically."""
        from PIL import Image, ImageChops, ImageStat
        img = Image.open(self.shot()).convert("RGB")
        if img.width == 640:
            box = (box[0] - 96, box[1] - 58, box[2] - 96, box[3] - 58)
        diff = ImageChops.difference(img.crop(box), Image.open(ref).convert("RGB"))
        return sum(ImageStat.Stat(diff).mean) / 3 < tol

    def wait_for(self, ref: Path, box, timeout: float = 120, poll: float = 3,
                 nudge: int | None = None) -> bool:
        """Poll until the screen matches `ref` in `box`; optionally press scancode
        `nudge` between polls (e.g. 57 = space to skip intro pictures)."""
        t = time.time()
        while time.time() - t < timeout:
            if self.screen_matches(ref, box):
                return True
            if nudge is not None:
                self.keypress(nudge)
            time.sleep(poll)
        return False

    # ---- lifecycle --------------------------------------------------------
    @staticmethod
    def _reserve_display() -> int:
        """Atomically claim a free X display number (concurrent harnesses must not
        share an Xvfb). Stale X locks and claims from dead processes are reclaimed."""
        for n in range(100, 400):
            lock = Path(f"/tmp/.X{n}-lock")
            if lock.exists():
                try:
                    os.kill(int(lock.read_text().strip()), 0)
                    continue
                except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
                    lock.unlink(missing_ok=True)
                    Path(f"/tmp/.X11-unix/X{n}").unlink(missing_ok=True)
            if Path(f"/tmp/.X11-unix/X{n}").exists():
                continue
            claim = f"/tmp/.mw2harness-display-{n}"      # shared with the Midwinter 2 harness
            try:
                fd = os.open(claim, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                try:
                    os.kill(int(Path(claim).read_text() or 0), 0)
                    continue
                except (ValueError, ProcessLookupError, PermissionError, FileNotFoundError):
                    Path(claim).unlink(missing_ok=True)
                    continue
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
        shutil.rmtree(self.R / "C", ignore_errors=True)   # the game copy; logs/shots stay


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["fps", "profile", "shot", "dump"])
    ap.add_argument("--game", required=True, help="game folder (drive C:)")
    ap.add_argument("--snapshot", required=True)
    ap.add_argument("--vbls", type=int, default=250)
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--out")
    ap.add_argument("--wait", type=float, default=3.0)
    ap.add_argument("--cpuclock", type=int, choices=[8, 16, 32], default=8)
    a = ap.parse_args(argv)
    h = Hatari(game_dir=a.game, snapshot=a.snapshot)
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
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
