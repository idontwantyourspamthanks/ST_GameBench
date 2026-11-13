"""PopTTPtr: Hatari started with EXACTLY dist/run_tt.sh's flags (no --harddrive, no --fast-boot, no --grab, no --sound off, monitor vga, cpuclock 32, mmu true)
plus only the remote-control options (--cmd-fifo, --screenshot-dir).  The harness' remote control (stharness.Hatari methods) is reused."""
import os, subprocess, sys, time, tempfile, shutil
from pathlib import Path
GP = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/populous"); ROOT = GP.parent.parent.parent
sys.path[:0] = [str(ROOT / "tools"), str(GP / "tools")]
from stharness import Hatari

class RawTT(Hatari):
    def __init__(self, image, tos="TOS_3_06_uk.img", extra=(), machine="tt", memsize=4096, cpuclock=32, mmu=True, monitor="vga", rt_flags=True):
        self.game_dir = GP
        self.flip_reg = "($ff8201).b"
        self.R = Path(tempfile.mkdtemp(prefix="strun-")); (self.R / "shots").mkdir()
        self.fifo = self.R / "fifo"; self.logpath = self.R / "log.txt"; self.state = Path("/tmp/hatari.sav")
        display = self._reserve_display()
        self.env = dict(os.environ, DISPLAY=f":{display}", SDL_VIDEODRIVER="x11", SDL_AUDIODRIVER="dummy"); self.env.pop("WAYLAND_DISPLAY", None)
        self.xvfb = subprocess.Popen(["Xvfb", f":{display}", "-screen", "0", "1024x768x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if Path(f"/tmp/.X11-unix/X{display}").exists(): break
            time.sleep(0.1)
        args = ["hatari", "--machine", machine, "--tos", str(ROOT / "tos" / tos), "--memsize", str(memsize), "--cpuclock", str(cpuclock), "--monitor", monitor]
        if mmu: args += ["--mmu", "true"]
        args += ["--gemdos-drive", "skip"] + (["--acsi", f"0={image}"] if image else []) + ["--confirm-quit", "no",
                 "--cmd-fifo", str(self.fifo), "--screenshot-dir", str(self.R / "shots"), "--screenshot-format", "png"] + list(extra)
        self.args = args
        self.log = open(self.logpath, "w")
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=self.env)
        self.win = None
        for _ in range(100):
            if self.fifo.exists():
                ids = self._xdo("search", "--name", "Hatari").stdout.split()
                if ids: self.win = ids[0]; break
            if self.proc.poll() is not None: break
            time.sleep(0.1)
        if self.win is None:
            self.close(); raise RuntimeError("Hatari did not start: " + self._logtext()[-1500:])
        time.sleep(1.5)
        self._xdo("windowfocus", self.win); self._xdo("mousemove", "--window", self.win, "320", "200"); time.sleep(0.5)
