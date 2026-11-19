"""Private harness for the F9/F10 investigation: launches Hatari with EXACTLY dist/run_ste.sh's options
(+ --cmd-fifo/--screenshot-dir only), fresh default config (HOME=scratch), real XTEST key events (no --window)."""
import os, re, subprocess, sys, time, shutil, tempfile
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from stharness import Hatari, TOS

class KH(Hatari):
    def __init__(self, img_src, workdir=None, machine='ste', extra=None, mem=1024, tos=None, cpu=8, copy=True, auto=None, joy=False):
        self.R = Path(workdir or tempfile.mkdtemp(prefix='kh-')); self.R.mkdir(parents=True, exist_ok=True)
        (self.R/'shots').mkdir(exist_ok=True)
        self.img = self.R/'disk.img'
        if copy: shutil.copy(img_src, self.img)
        self.fifo = self.R/'fifo'
        if self.fifo.exists(): self.fifo.unlink()
        self.logpath = self.R/'log.txt'
        n = 90
        while Path(f'/tmp/.X11-unix/X{n}').exists(): n += 1
        for k in range(n, n+200):
            if not Path(f'/tmp/.X11-unix/X{k}').exists(): n = k; break
        self.env = dict(os.environ, DISPLAY=f':{n}', SDL_VIDEODRIVER='x11', SDL_AUDIODRIVER='dummy', HOME=str(self.R/'home'))
        (self.R/'home').mkdir(exist_ok=True)
        if os.environ.get('USERCFG'):
            cd=self.R/'home'/'.config'/'hatari'; cd.mkdir(parents=True, exist_ok=True)
            shutil.copy(os.path.expanduser('~/.config/hatari/1040stfm.cfg'), cd/'hatari.cfg')
        self.env.pop('WAYLAND_DISPLAY', None)
        self.xvfb = subprocess.Popen(['Xvfb', f':{n}', '-screen', '0', '1024x768x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if Path(f'/tmp/.X11-unix/X{n}').exists(): break
            time.sleep(0.1)
        t = tos or TOS['1.62']
        args = ['hatari', '--machine', machine, '--tos', str(t), '--memsize', str(mem), '--cpuclock', str(cpu), '--monitor', 'rgb',
                '--gemdos-drive', 'skip', '--acsi', f'0={self.img}', '--confirm-quit', 'no',
                '--cmd-fifo', str(self.fifo), '--screenshot-dir', str(self.R/'shots'), '--screenshot-format', 'png']
        if joy: args += ['--joy1', 'keys']
        if auto: args += ['--auto', auto]
        args += extra or []
        self.args = args
        self.log = open(self.logpath, 'w')
        self.proc = subprocess.Popen(args, stdout=self.log, stderr=subprocess.STDOUT, env=self.env)
        self.win = None
        for _ in range(100):
            if self.fifo.exists():
                ids = self._xdo('search', '--name', 'Hatari').stdout.split()
                if ids: self.win = ids[0]; break
            if self.proc.poll() is not None: break
            time.sleep(0.1)
        if self.win is None:
            raise RuntimeError(self._logtext()[-2000:])
        time.sleep(1.0)
        self._xdo('windowfocus', self.win)
        self.t0 = time.time()
    def close(self):
        try: self.proc.terminate(); self.proc.wait(5)
        except Exception: self.proc.kill()
        self.xvfb.terminate()
    # XTEST (focused-window) keys, human taps
    def tap(self, keysym, hold=0.1):
        self._xdo('keydown', keysym); time.sleep(hold); self._xdo('keyup', keysym)
    def peekb(self, a):
        out = self.debug(f'm ${a:x} 1', 0.5)
        return int(re.findall(rf'{a:08x}:\s+([0-9a-f]{{2}})', out, re.I)[-1], 16)
    def mem(self, a, n=4):
        out = self.debug(f'm ${a:x} {n}', 0.5)
        return out
