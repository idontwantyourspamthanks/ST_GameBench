#!/usr/bin/env python3
"""Scratch driver (HdWindowFix): boot a copy of the HD image in headless Hatari, take screenshots, open drive C:.
usage: hh.py NAME MACHINE TOS MEM MONITOR IMG [--dbl] [--keep]
  writes work/hdimage/shots/NAME_*.png ; IMG is copied to work/hdimage/scratch/NAME.img first (never touches IMG)."""
from __future__ import annotations
import os, shutil, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "tools"))
from stharness import Hatari, TOS, hatari_bin  # noqa: E402

SHOTS = HERE / "shots"
SCR = HERE / "scratch"


class H:
    def __init__(self, name, machine, tos, mem, monitor, img, extra=()):
        SHOTS.mkdir(exist_ok=True); SCR.mkdir(exist_ok=True)
        self.name = name
        self.img = SCR / f"{name}.img"
        shutil.copyfile(img, self.img)
        self.R = Path(f"/tmp/hh-{name}")
        shutil.rmtree(self.R, ignore_errors=True)
        (self.R / "shots").mkdir(parents=True)
        self.fifo = self.R / "fifo"
        n = Hatari._reserve_display()
        self.env = dict(os.environ, DISPLAY=f":{n}", SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy")
        self.env.pop("WAYLAND_DISPLAY", None)
        self.xvfb = subprocess.Popen(["Xvfb", f":{n}", "-screen", "0", "1280x1024x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if Path(f"/tmp/.X11-unix/X{n}").exists():
                break
            time.sleep(0.1)
        args = [hatari_bin(machine), "--confirm-quit", "no", "--machine", machine, "--tos", str(TOS[tos]), "--memsize", str(mem),
                "--monitor", monitor, "--gemdos-drive", "skip", "--acsi", f"0={self.img}", "--fast-boot", "yes", "--sound", "off",
                "--borders", "false", "--zoom", "2", "--statusbar", "false", "--cmd-fifo", str(self.fifo),
                "--screenshot-dir", str(self.R / "shots"), "--screenshot-format", "png", *extra]
        if machine in ("tt",):
            args += ["--mmu", "true"]
        self.log = open(self.R / "log.txt", "w")
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=self.env)
        self.win = None
        for _ in range(100):
            if self.fifo.exists():
                ids = self.xdo("search", "--name", "Hatari").stdout.split()
                if ids:
                    self.win = ids[0]
                    break
            time.sleep(0.1)
        assert self.win, "no window"
        time.sleep(1)
        self.xdo("windowfocus", self.win)

    def xdo(self, *a):
        return subprocess.run(["xdotool", *a], env=self.env, capture_output=True, text=True)

    def cmd(self, s):
        fd = os.open(self.fifo, os.O_WRONLY | os.O_NONBLOCK)
        os.write(fd, (s + "\n").encode())
        os.close(fd)

    def shot(self, tag):
        before = set((self.R / "shots").iterdir())
        self.cmd("hatari-shortcut screenshot")
        for _ in range(50):
            new = set((self.R / "shots").iterdir()) - before
            if new:
                time.sleep(0.3)
                p = sorted(new)[0]
                out = SHOTS / f"{self.name}_{tag}.png"
                shutil.copy(p, out)
                return out
            time.sleep(0.1)
        raise RuntimeError("no screenshot")

    def geom(self):
        return self.xdo("getwindowgeometry", self.win).stdout

    def move(self, x, y):
        """pointer to window pixel (x, y) (host px in the Hatari window)"""
        self.xdo("mousemove", "--window", self.win, str(x), str(y))
        time.sleep(0.3)

    def click(self, hold=0.2):
        self.xdo("mousedown", "1"); time.sleep(hold); self.xdo("mouseup", "1"); time.sleep(0.3)

    def dblclick(self):
        self.cmd("hatari-event doubleclick")
        time.sleep(0.5)

    def key(self, sym, hold=0.15):
        self.xdo("keydown", "--window", self.win, sym); time.sleep(hold); self.xdo("keyup", "--window", self.win, sym)

    def close(self):
        self.proc.kill(); self.proc.wait()
        self.xvfb.terminate()
        try:
            self.xvfb.wait(5)
        except Exception:
            self.xvfb.kill()
        shutil.rmtree(self.R, ignore_errors=True)


if __name__ == "__main__":
    name, machine, tos, mem, mon, img = sys.argv[1:7]
    h = H(name, machine, tos, int(mem), mon, img)
    try:
        time.sleep(float(os.environ.get("BOOT", "25")))
        print(h.geom())
        print(h.shot("boot"))
    finally:
        h.close()
