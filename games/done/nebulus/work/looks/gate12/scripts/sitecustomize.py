# scratch-only: make Hatari.savemem use the PRIVATE HOME's hatari.sav instead of the shared /tmp/hatari.sav
import sys, os
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
try:
    import stharness, time, shutil
    from pathlib import Path
    def savemem(self, out):
        tmp = Path(os.environ['HOME']) / '.config/hatari/hatari.sav'
        tmp.parent.mkdir(parents=True, exist_ok=True)
        if tmp.exists(): tmp.unlink()
        self.cmd("hatari-shortcut savemem")
        for _ in range(100):
            if tmp.exists() and tmp.stat().st_size > 0: break
            time.sleep(0.1)
        time.sleep(1.5)
        shutil.copy(tmp, out)
    stharness.Hatari.savemem = savemem
except Exception as e:
    print('sitecustomize failed', e, file=sys.stderr)
