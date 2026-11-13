"""PopMachines scratch driver (test scaffolding only)."""
import sys, time, re, tempfile, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parents[2]
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
sys.path.insert(0, str(GAME / "tools"))
from populous import Populous, HOME, CONQUEST_XY, START_XY
from stharness import TOS

EMPTY = HERE / "empty"
EMPTY.mkdir(exist_ok=True)

MACH = {  # name: (machine, tos, mem, extra)
 "tt":      ("tt", "3.06", 4096, ["--monitor", "vga", "--cpuclock", "32", "--mmu", "true"]),
 "falcon":  ("falcon", "4.04", 4096, ["--monitor", "vga", "--cpuclock", "16"]),
 "st":      ("st", "1.04", 1024, []),
 "ste":     ("ste", "1.62", 1024, []),
 "ste60":   ("ste", "1.62", 1024, []),
 "megaste": ("megaste", "2.06", 4096, []),
}

def start(name, medium, path, extra=(), mem=None, tos=None):
    m, t, mm, ex = MACH[name]
    ex = list(ex)
    import shutil
    if medium in ("floppy", "acsi", "ide"):
        cp = Path(tempfile.mkdtemp(prefix="pmimg-")) / Path(path).name
        shutil.copy(path, cp)
        path = cp
    if medium == "floppy":
        ex += ["--disk-a", str(path), "--drive-a", "true"]
        kw = dict(game_dir=EMPTY, autorun="", files=[])
    elif medium == "acsi":
        ex += ["--gemdos-drive", "skip", "--acsi", f"0={path}"]
        kw = dict(game_dir=EMPTY, autorun="", files=[])
    elif medium == "ide":
        ex += ["--gemdos-drive", "skip", "--ide-master", str(path)]
        kw = dict(game_dir=EMPTY, autorun="", files=[])
    elif medium == "gemdos":
        kw = dict(game_dir=Path(path))
    ex += list(extra)
    return Populous(machine=m, tos=TOS[tos or t], memsize_kb=mem or mm, extra=ex, **kw)

def mem(h, addr, n=4):
    out = h.debug(f"m ${addr:x} {n}", 0.6)
    hx = re.findall(rf"{addr:08x}:\s+((?:[0-9a-f]{{2}} ?)+)", out, re.I)
    return hx[-1].strip() if hx else out.strip()
