#!/usr/bin/env python3
"""Mega STE bank-tail investigation helpers (work/notes/banktail.md).  Own workdir /tmp/mw2tail/<name>, private HOME /tmp/mw2tail/home."""
import os, re, sys, time, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
TOSD = ROOT.parent.parent.parent / "tos"
TOS = {"162": TOSD / "TOS_1_62.img", "206": TOSD / "TOS_2_06.img", "306": TOSD / "TOS_3_06_uk.img"}
T = Path("/tmp/mw2tail")
BANKF = Path(os.environ.get("BT_BANK", ROOT / "build" / "asn_bank.bin"))     # BT_BANK: the bank file to compare against (prototype builds)
BANK = 0xBB000
FIRST = 0xE2B6A
DYN = [(0xE00, 0x1800)]
GAME = T / "game"
HOME = T / "home"

def setup_home(cap):
    cfg = HOME / ".config" / "hatari"
    cfg.mkdir(parents=True, exist_ok=True)
    src = Path("/home/ryan/.config/hatari/1040stfm.cfg")
    txt = re.sub(r"(?m)^szYMCaptureFileName.*$", f"szYMCaptureFileName = {cap}", src.read_text())
    (cfg / "hatari.cfg").write_text(txt)
    nv = Path("/home/ryan/.config/hatari/hatari.nvram")
    if nv.exists():
        shutil.copy(nv, cfg / "hatari.nvram")

def start(name, machine, tos, mem, game=GAME, extra=(), sound=True):
    from mw2harness import Hatari
    wd = T / name
    shutil.rmtree(wd, ignore_errors=True)
    setup_home(wd / "cap.wav")
    os.environ["HOME"] = str(HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    ex = (["--sound", "50066"] if sound else []) + list(extra)
    return Hatari(snapshot=None, workdir=str(wd), memsize_kb=int(mem), machine=machine, tos=TOS[tos], game_dir=Path(game), extra=ex)

def dump_bank(h, tag, n=None):
    bank = BANKF.read_bytes()
    p = h.R / f"bk_{tag}.bin"
    if p.exists(): p.unlink()
    h.debug(f"savebin {p} ${BANK:x} ${len(bank):x}", 3.0)
    ram = p.read_bytes()
    return diff(ram, bank), ram

def diff(ram, bank):
    bad = [i for i in range(len(bank)) if i >= len(ram) or (ram[i] != bank[i] and not any(x <= i < y for x, y in DYN))]
    return bad

def summ(bad):
    if not bad: return "0 differ"
    runs = []; s = p = bad[0]
    for i in bad[1:]:
        if i != p + 1: runs.append((s, p)); s = i
        p = i
    runs.append((s, p))
    return f"{len(bad)} differ; first ${BANK+bad[0]:x} last ${BANK+bad[-1]:x}; runs " + ", ".join(f"${BANK+a:x}-${BANK+b:x}" for a, b in runs[:8]) + (" ..." if len(runs) > 8 else "")
