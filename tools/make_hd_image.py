#!/usr/bin/env python3
r"""Build one raw Atari ST hard-disk image with all the enhanced games (current default builds; Flood from its shipped release zip).

    python3 tools/make_hd_image.py                 # build the games, write dist/AtariST_enhanced_games_<date>.img (+ .md5, + .layout.txt)
    python3 tools/make_hd_image.py --no-build      # reuse the staged builds in dist/_stage (fast re-pack)
    python3 tools/make_hd_image.py --out X.img --size-kb 32000

What is on the image (see LAYOUT below; the .layout.txt written next to the image lists the real numbers):
  * a raw disk, one file = the whole disk, no container: write it to a real disk / SD card (`dd if=X.img of=/dev/sdX bs=1M`,
    Win32 Disk Imager, ...) for UltraSatan / ACSI2STM / SCSI2SD / Gotek-style HD emulators, or give it to Hatari
    (`--acsi 0=X.img`, with `--gemdos-drive skip` if you do not want a GEMDOS folder as well);
  * sector 0 = the HDDRIVER boot code (gamebench/hd/hddriver_root.bin) + an Atari AHDI partition table (BGM = 16-bit FAT, one
    partition, flag $81 = exists + bootable) + checksum $1234;
  * the partition boot sector = HDDRIVER's partition loader (gamebench/hd/hddriver_pboot.bin) with our BPB; it finds
    HDDRIVER.SYS in the root directory and runs it, which installs the driver and mounts the partition(s) as C:;
  * C:\ = HDDRIVER.SYS, README.TXT, DESKTOP.INF + NEWDESK.INF (the ROM's default desktop with windows that fit a 320-pixel screen,
    see desktop_inf_files; no autorun), AUTO\PMBOOT.PRG (the boot
    prompt that starts Powermonger, see tools/hd_pmboot.s) and one folder per game, each the
    output of that game's own build tool (`<game>/tools/*patch.py build`, plus what its package.sh adds), nothing else.
The partition is kept under 32 MB (65535 sectors) so that TOS 1.04 / 1.06 / 1.62 (16-bit sector numbers in the BPB) accept it.

The three HDDRIVER files in gamebench/hd/ (HDDRIVER.SYS, hddriver_root.bin, hddriver_pboot.bin) are user-supplied (hd/README.md).
Needs: mkfs.fat (dosfstools), mtools (mcopy, mdir), zip-less; the games' own prerequisites (original files in the game dirs, Hunter's
alt/amiga ADF for the sample bank, Powermonger's disks/protected.st).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # gamebench/
class _Games:
    """`GAMES / "midwinter"` finds a game in whichever stage folder it lives (in_progress, done, queue)."""
    def __truediv__(self, name: str) -> Path:
        for stage in ("in_progress", "done", "queue"):
            p = ROOT / "games" / stage / name
            if p.is_dir():
                return p
        return ROOT / "games" / "in_progress" / name


GAMES = _Games()
HD = ROOT / "hd"
DIST = ROOT / "dist"
STAGE = DIST / "_stage"                                 # build outputs of this script (git-ignored with dist/)
SECTOR = 512
FIRST_LBA = 2                                           # as HDDRIVER's own formatter and gamebench/games/done/hunter/tools/hunter.py
MAX_PART_SECTORS = 65535                                # TOS < 2.06 BPB: 16-bit sector count
DEFAULT_SIZE_KB = 32000                                 # one partition, 64000 sectors (31.25 MiB)
VOLUME = "GAMES"

# folder on C: -> game; versions/requirements for README.TXT are taken from the builds where possible (see readme_text)
FOLDERS = ("MIDWINTR", "MW1ORIG", "MIDWINT2", "MW2ORIG", "MOONSHR", "HUNTER", "HUNTORIG", "NEBULUS", "NEBORIG", "POWERMON", "PMWW1",
           "POPULOUS", "POPORIG", "POPS2", "POP2ORIG", "FLOOD", "OVERLAND", "AUTO")
FLOOD_VERSION = "1.0"                                   # the shipped release zip games/done/flood/dist/Flood_hd_v<this>.zip
OVERLANDER_VERSION = "1.0"                              # games/*/overlander/dist/Overlander_hd_v<this>.zip
PMWW1_VERSION = "1.0"                                   # games/*/powermonger-ww1/dist/PowermongerWW1_v<this>_patched_hd_<date>.zip (newest)


def run(cmd, cwd=None, quiet=True, env=None):
    r = subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, capture_output=quiet, text=True)
    if r.returncode:
        sys.exit(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stdout or ''}{r.stderr or ''}")
    return r.stdout if quiet else ""


def py(game: str, tool: str, *args: str) -> str:
    return run([sys.executable, f"tools/{tool}.py", *args], cwd=GAMES / game)


# ---- 1. build every game into dist/_stage/<folder> -----------------------------------------------------------------------------
def copy_names(src: Path, dst: Path, names):
    for n in names:
        shutil.copy2(src / n, dst / n)


def build_midwinter2() -> Path:
    """The default build; it includes the Amiga sound effects and music through the STE DMA sound (asn_* patches,
    FILES\\ASNBANK.BIN) when the user's Amiga disk 1 is at midwinter2/alt/amiga/disk1.adf (private image, like Hunter's sample
    bank); without it the build silently falls back to the non-asn set (YM)."""
    g = GAMES / "midwinter2"
    out, dst = STAGE / "mw2_build", STAGE / "MIDWINT2"
    py("midwinter2", "mw2patch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    amiga = (g / "alt" / "amiga" / "disk1.adf").is_file()
    if amiga:
        py("midwinter2", "asn_build")                          # -> build/asn_bank.bin (md5-checked against the ADF)
    run([sys.executable, "tools/mw2patch.py", "build", "--out", out], cwd=g)   # default set: asn_* included when the bank exists
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    # = what midwinter2/tools/package.sh puts into MW2PATCH/
    copy_names(out, dst, ["RUNME.TOS", "HAGA", "FF240R.BMP", "FFF273.HST", "LFF273.HST"])
    copy_names(g, dst, ["README.TXT", "LOG.TXT", "SOLUTION.TXT"])
    shutil.copytree(g / "FILES", dst / "FILES")               # originals: FFD stays the blank campaign disk
    if (out / "FILES" / "ASNBANK.BIN").is_file():
        shutil.copy2(out / "FILES" / "ASNBANK.BIN", dst / "FILES" / "ASNBANK.BIN")
    (dst / "PATCHES.TXT").write_text(py("midwinter2", "mw2patch", "doc", "patches/PATCHES.TXT"), encoding="latin-1", errors="replace")
    return dst


def build_moonshine() -> Path:
    r"""Moonshine Racers HD: `msrpatch.py build --out` output (patched RUNME.TOS + HAGA, original FILES\, its own README.TXT and
    PATCHES.TXT written by the tool). The tool needs the game's `originals/` and its verify dumps in the game folder."""
    g = GAMES / "moonshine-racers"
    out, dst = STAGE / "msr_build", STAGE / "MOONSHR"
    py("moonshine-racers", "msrpatch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    py("moonshine-racers", "msrpatch", "build", "--out", str(out))
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(out, dst)
    return dst


def build_midwinter() -> Path:
    g = GAMES / "midwinter"
    out, dst = STAGE / "mw1_build", STAGE / "MIDWINTR"
    py("midwinter", "mw1patch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    py("midwinter", "mw1patch", "build", "--out", out)
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    # = what midwinter/tools/package.sh puts into MW1PATCH/
    copy_names(out, dst, ["RUNME.TOS", "HAGA", "MW240R.BMP", "FMW273.HST", "LMW273.HST"])
    copy_names(g, dst, ["README.TXT", "LOG.TXT"])
    shutil.copytree(g / "FILES", dst / "FILES")               # originals (MWC = data/save disk)
    (dst / "PATCHES.TXT").write_text(py("midwinter", "mw1patch", "doc", "patches/PATCHES.TXT"), encoding="latin-1", errors="replace")
    return dst


def build_midwinter_orig() -> Path:
    """PP's unpatched Midwinter (for side-by-side comparison): the original files of the game dir, nothing patched."""
    g = GAMES / "midwinter"
    dst = STAGE / "MW1ORIG"
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    copy_names(g, dst, ["RUNME.TOS", "HAGA", "MW240R.BMP", "FMW273.HST", "LMW273.HST", "README.TXT", "LOG.TXT"])
    shutil.copytree(g / "FILES", dst / "FILES")               # its own copy of the data/save disk MWC
    return dst


def build_midwinter2_orig() -> Path:
    """PP's unpatched Midwinter 2 (for side-by-side comparison): the original files of the game dir, nothing patched."""
    g = GAMES / "midwinter2"
    dst = STAGE / "MW2ORIG"
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    copy_names(g, dst, ["RUNME.TOS", "HAGA", "FF240R.BMP", "FFF273.HST", "LFF273.HST", "README.TXT", "LOG.TXT", "SOLUTION.TXT"])
    shutil.copytree(g / "FILES", dst / "FILES")               # its own blank campaign disk FFD
    return dst


def build_orig(src: Path, name: str) -> Path:
    """An unpatched release for side-by-side comparison: every file of `src` except the bench's own scaffolding and notes."""
    dst = STAGE / name
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    for p in sorted(src.iterdir()):
        if p.name in ("alt", "build", "dist", "patches", "tools", "work", "originals", "tos") or p.suffix.lower() == ".md":
            continue
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, dst / p.name)
    return dst


def stage_zip_folder(zip_path: Path, member_dir: str, name: str) -> Path:
    r"""Copy one folder of a shipped release zip, as it is, to STAGE/<name>."""
    import zipfile
    dst = STAGE / name
    shutil.rmtree(dst, ignore_errors=True)
    tmp = STAGE / f"{name.lower()}_zip"
    shutil.rmtree(tmp, ignore_errors=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(tmp)
    if not (tmp / member_dir).is_dir():
        sys.exit(f"{zip_path.name}: no folder {member_dir}")
    shutil.move(tmp / member_dir, dst)
    shutil.rmtree(tmp)
    return dst


def build_flood() -> Path:
    r"""Flood: the shipped HD release (`dist/Flood_hd_v<FLOOD_VERSION>.zip`, made by its tools/package_flood.py), whose FLOOD\
    folder is copied as it is: FLO.PRG + the game's files + AM_MUS.BIN / AM_SFX.BIN (Amiga sound) + README.TXT."""
    return stage_zip_folder(GAMES / "flood" / "dist" / f"Flood_hd_v{FLOOD_VERSION}.zip", "FLOOD", "FLOOD")


def build_overlander() -> Path:
    r"""Overlander: the shipped HD release (`dist/Overlander_hd_v<OVERLANDER_VERSION>.zip`), OVERLAND\ copied as it is
    (OVERLAND.PRG + G.TOS + LOADSCR.IMG + Amiga sound files + README.TXT)."""
    return stage_zip_folder(GAMES / "overlander" / "dist" / f"Overlander_hd_v{OVERLANDER_VERSION}.zip", "OVERLAND", "OVERLAND")


def build_pmww1() -> Path:
    r"""Powermonger WW1: the newest shipped HD release zip; its POWERMONGER_WW1\ folder becomes C:\PMWW1\ with WW1.PRG moved up
    next to the data files (as POWERMON\WAR.PRG): it must be started from the AUTO phase, by AUTO\PMBOOT.PRG (W)."""
    zips = sorted((GAMES / "powermonger-ww1" / "dist").glob(f"PowermongerWW1_v{PMWW1_VERSION}_patched_hd_*.zip"))
    if not zips:
        sys.exit(f"no PowermongerWW1_v{PMWW1_VERSION}_patched_hd_*.zip in powermonger-ww1/dist")
    dst = stage_zip_folder(zips[-1], "POWERMONGER_WW1", "PMWW1")
    shutil.move(dst / "AUTO" / "WW1.PRG", dst / "WW1.PRG")
    (dst / "AUTO").rmdir()
    note = ("NOTE (all-games hard disk): here the game is C:\\PMWW1\\WW1.PRG next to its data files (not in AUTO\\). At boot,\n"
            "C:\\AUTO\\PMBOOT.PRG asks \"P Powermonger, W WW1, else desktop\"; W sets the current directory to C:\\PMWW1 and\n"
            "starts WW1.PRG. The installing text below is for a stand-alone install; WW1.PRG started from the desktop does not work.\n\n")
    body = (dst / "README.TXT").read_bytes().decode("latin-1")
    (dst / "README.TXT").write_bytes(note.replace("\n", "\r\n").encode("latin-1") + body.encode("latin-1"))
    return dst


def build_hunter() -> Path:
    g = GAMES / "hunter"
    out, dst, snd = STAGE / "hunter_build", STAGE / "HUNTER", STAGE / "hunter_snd.bin"
    py("hunter", "huntpatch", "verify")
    py("hunter", "snd_build", "--out", snd)
    shutil.rmtree(out, ignore_errors=True)
    py("hunter", "huntpatch", "build", "--samples", snd, "--out", out)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(out, dst)                                  # = package.sh: build/game/. plus PATCHES.TXT
    (dst / "PATCHES.TXT").write_text(py("hunter", "huntpatch", "doc", "patches/PATCHES.TXT"), encoding="latin-1", errors="replace")
    return dst


def build_nebulus() -> Path:
    r"""Nebulus HD: `nebrelease.py build --out` output (patched START.TOS + NEPATCH.BIN [+ NEBLEVEL.OVL], PP's game files, README.TXT, PATCHES.TXT)."""
    out, dst = STAGE / "nebulus_build", STAGE / "NEBULUS"
    py("nebulus", "nepatch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    py("nebulus", "nebrelease", "build", "--out", str(out))
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(out, dst)
    # the image holds only plain 8.3 upper-case names: the zip's blank campaign disk becomes NEBCAMP.ST
    cd = dst / "Nebulus_campaign_disk.st"
    if cd.exists():
        cd.rename(dst / "NEBCAMP.ST")
        with open(dst / "README.TXT", "a", newline="") as f:
            f.write("\r\n(On this drive image the blank campaign disk 'Nebulus_campaign_disk.st' is named NEBCAMP.ST.)\r\n")
    return dst


def build_nebulus_orig() -> Path:
    """PP's Nebulus Gamex files, unpatched, for comparison (the game folder's originals/NEBULGX)."""
    return build_orig(GAMES / "nebulus" / "originals" / "NEBULGX", "NEBORIG")


def build_powermonger() -> Path:
    g = GAMES / "powermonger"
    out, dst = STAGE / "pm_build", STAGE / "POWERMON"
    py("powermonger", "pmpatch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    py("powermonger", "pmpatch", "build", "--hd", "--out", out)
    hd = out / "hd"
    for need in ("AUTO/WAR.PRG", "DATA/SPRITE40.DAT", "SAVEDISK.DAT", "PMLATE.DAT"):
        if not (hd / need).is_file():
            sys.exit(f"powermonger build output incomplete: {need}")
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(hd, dst)
    # started from the desktop in its own folder, not from AUTO\ at boot: WAR.PRG moves up next to DATA\ (the loader looks for
    # DATA\ and PMLATE.DAT in the folder it was started from)
    shutil.move(dst / "AUTO" / "WAR.PRG", dst / "WAR.PRG")
    (dst / "AUTO").rmdir()
    ver = versions()["POWERMON"].lstrip("v")
    note = ("NOTE (all-games hard disk): here the game is C:\\POWERMON\\WAR.PRG next to DATA\\ (not in AUTO\\). At boot,\n"
            "C:\\AUTO\\PMBOOT.PRG asks \"P Powermonger, W WW1, else desktop\"; P sets the current directory to C:\\POWERMON and\n"
            "starts WAR.PRG. The \"Installing\" text below is for a stand-alone install; WAR.PRG started from the desktop stops\n"
            "with \"cannot swap the low RAM of TOS\".\n\n")
    body = (g / "patches" / "README_HD.TXT").read_text().replace("@VER@", ver)
    (dst / "README.TXT").write_bytes((note + body).replace("\n", "\r\n").encode("latin-1", "replace"))
    return dst


def build_auto() -> Path:
    r"""AUTO\PMBOOT.PRG: the boot prompt that starts Powermonger (P) or Powermonger WW1 (W) (tools/hd_pmboot.s; both must be
    started from the AUTO phase)."""
    dst = STAGE / "AUTO"
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    binf = STAGE / "pmboot.bin"
    run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", binf, ROOT / "tools" / "hd_pmboot.s"])
    code = binf.read_bytes()
    # GEMDOS .PRG: $601a, text, data, bss, symbols = 0, 3 longs/words of 0, then the fixup table (empty: position independent)
    hdr = struct.pack(">HLLLLLLH", 0x601A, len(code), 0, 0, 0, 0, 0, 0)
    (dst / "PMBOOT.PRG").write_bytes(hdr + code + b"\0\0\0\0")
    return dst


def build_populous() -> Path:
    r"""= what populous/tools/package.sh puts into POPULOUS\: `poppatch.py build --hd` output plus PATCHED.TXT."""
    out, dst = STAGE / "pop_build", STAGE / "POPULOUS"
    py("populous", "poppatch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    py("populous", "poppatch", "build", "--hd", "--out", out)
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(out, dst)
    doc = py("populous", "poppatch", "doc", "patches/README_HD.TXT")
    (dst / "PATCHED.TXT").write_bytes(doc.replace("\r\n", "\n").replace("\n", "\r\n").encode("latin-1", "replace"))
    return dst


def build_populous2() -> Path:
    r"""= what populous-2/tools/package.sh puts into POPS2\: RUNME.TOS, HAGA, the .HST/.BMP/.TXT files, FILES\, PATCHES.TXT."""
    out, dst = STAGE / "pop2_build", STAGE / "POPS2"
    py("populous-2", "pop2patch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    py("populous-2", "pop2patch", "build", "--out", out)
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    for pat in ("RUNME.TOS", "HAGA", "*.HST", "*.BMP", "*.TXT"):
        for f in sorted(out.glob(pat)):
            shutil.copy2(f, dst / f.name)
    shutil.copytree(out / "FILES", dst / "FILES")
    doc = py("populous-2", "pop2patch", "doc", "patches/PATCHES.TXT").replace("{DATE}", datetime.date.today().isoformat())
    (dst / "PATCHES.TXT").write_bytes(doc.replace("\r\n", "\n").replace("\n", "\r\n").encode("latin-1", "replace"))
    return dst


BUILDERS = {"MIDWINTR": build_midwinter, "MOONSHR": build_moonshine, "MW1ORIG": build_midwinter_orig, "MIDWINT2": build_midwinter2, "MW2ORIG": build_midwinter2_orig,
            "HUNTER": build_hunter, "HUNTORIG": lambda: build_orig(GAMES / "hunter", "HUNTORIG"),
            "NEBULUS": build_nebulus, "NEBORIG": build_nebulus_orig,
            "POWERMON": build_powermonger, "POPULOUS": build_populous,
            "POPORIG": lambda: build_orig(GAMES / "populous" / "originals" / "POPULOUS", "POPORIG"),
            "POPS2": build_populous2, "POP2ORIG": lambda: build_orig(GAMES / "populous-2" / "originals" / "POPUL2", "POP2ORIG"),
            "FLOOD": build_flood, "OVERLAND": build_overlander, "PMWW1": build_pmww1,
            "AUTO": build_auto}


# ---- 2. the disk ---------------------------------------------------------------------------------------------------------------
def fix_sum(sec: bytearray, want: int = 0x1234) -> None:
    """Make the 256 big-endian words of a boot/root sector sum to `want` (TOS: $1234 = executable boot sector)."""
    sec[510:512] = b"\0\0"
    s = sum(struct.unpack(">256H", bytes(sec))) & 0xFFFF
    struct.pack_into(">H", sec, 510, (want - s) & 0xFFFF)


# ---- the desktop: DESKTOP.INF (TOS 1.x) and NEWDESK.INF (TOS 2.x/3.x) --------------------------------------------------------------
# Without an INF file the desktop uses the INF text built into the TOS ROM, whose windows are 76 columns wide (`#W .. 4C ..`). TOS 1.04/
# 1.06/1.62 (ST, STE) do not clip that to a 320-pixel low-resolution screen: the C: window runs off the right edge, its scroll bars
# cannot be reached. TOS 2.06+ clips it (Mega STE, TT: no problem). The files below are those ROM default texts byte for byte
# (strings of TOS_1_62.img / TOS_2_06.img, which equals 3.06), except for the `#W` lines: windows at most 38 columns (304 pixels) wide
# and ending at x = 304, which fits every screen (the desktop aligns windows to 16 pixels). TOS 2.06+ reads NEWDESK.INF before
# DESKTOP.INF and TOS 1.x only reads DESKTOP.INF, so each gets its own ROM default: the `#E` line differs (TOS 1.x boots with
# the blitter on, 2.06 with it off), one shared file would switch the blitter at boot on one of them. work/hdimage/NOTES.md has the evidence.
_INF_1X = ("#a000000", "#b000000", "#c???000?000<00<?00;;400;0;;;4440??0;;?0?;0;;;0??03111103", "#d" + " " * 45, "#E 18 13 ",
           "#W 00 00 00 07 26 0C 00 @", "#W 00 00 02 0B 24 09 00 @", "#W 00 00 04 0F 22 09 00 @", "#W 00 00 06 01 20 09 00 @",
           "#C 01 01 00 FF c CARTRIDGE@ @ ", "#M 01 00 00 FF C HARD DISK@ @ ", "#M 00 00 00 FF A FLOPPY DISK@ @ ",
           "#M 00 01 00 FF B FLOPPY DISK@ @ ", "#T 00 07 02 FF   TRASH@ @ ", "#F FF 04   @ *.*@ ", "#D FF 01   @ *.*@ ",
           "#G 03 FF   *.APP@ @ ", "#G 03 FF   *.PRG@ @ ", "#P 03 FF   *.TTP@ @ ", "#F 03 04   *.TOS@ @ ")
_INF_2X = ("#a000000", "#b000000", "#c7770007000600070055200505552220770557075055507703111103", "#d" + " " * 45, "#E 18 03 00 06 43",
           "#W 00 00 00 07 26 0C 00 @", "#W 00 00 02 0B 24 09 00 @", "#W 00 00 04 0F 22 09 00 @", "#W 00 00 06 01 20 09 00 @",
           "#W 00 00 04 07 22 0C 00 @", "#W 00 00 0C 0B 1A 09 00 @", "#W 00 00 08 0F 1E 09 00 @", "#W 00 00 06 01 20 09 00 @",
           "#C 01 01 00 FF c CARTRIDGE@ @ ", "#M 00 01 00 FF C HARD DISK@ @ ", "#M 00 00 00 FF A FLOPPY DISK@ @ ",
           "#M 01 00 00 FF B FLOPPY DISK@ @ ", "#T 00 07 02 FF   TRASH@ @ ", "#F FF 04   @ *.*@ ", "#D FF 01   @ *.*@ ",
           "#G 03 FF   *.APP@ @ ", "#G 03 FF   *.PRG@ @ ", "#Y 03 FF   *.GTP@ @ ", "#P 03 FF   *.TTP@ @ ", "#F 03 04   *.TOS@ @ ")


def desktop_inf_files() -> dict[str, bytes]:
    """Root files DESKTOP.INF (TOS 1.x: ends with ^Z like the ROM text) and NEWDESK.INF (TOS 2.x/3.x). No `#Z` autorun line."""
    crlf = lambda lines: "".join(l + "\r\n" for l in lines).encode("latin-1")
    return {"DESKTOP.INF": crlf(_INF_1X) + b"\x1a", "NEWDESK.INF": crlf(_INF_2X)}


def readme_text(vers: dict[str, str], date: str) -> str:
    t = rf"""ATARI ST ENHANCED GAMES - HARD DISK  ({date})
==========================================================================

Eight games with dad_prg's patches (speed, sound, fixes) on one bootable
hard disk image, plus PP's unpatched releases of six of them (the *ORIG
folders) for side-by-side comparison:
HDDRIVER, one 31 MB partition = drive C:.  Nothing starts by itself except
a 3-second question about Powermonger at boot.

  FOLDER       GAME                   START                      VERSION
  -----------  ---------------------  -------------------------  -------
  C:\MIDWINTR  Midwinter              double-click RUNME.TOS     {vers['MIDWINTR']}
  C:\MW1ORIG   Midwinter (original)   double-click RUNME.TOS     PP's release, unpatched
  C:\MIDWINT2  Midwinter 2            double-click RUNME.TOS     {vers['MIDWINT2']}
  C:\MW2ORIG   Midwinter 2 (original) double-click RUNME.TOS     PP's release, unpatched
  C:\MOONSHR   Moonshine Racers       double-click RUNME.TOS     {vers['MOONSHR']}
  C:\HUNTER    Hunter                 double-click START.TOS     {vers['HUNTER']}
  C:\HUNTORIG  Hunter (original)      double-click START.TOS     PP's release, unpatched
  C:\NEBULUS   Nebulus                double-click START.TOS     {vers['NEBULUS']}
  C:\NEBORIG   Nebulus (original)     double-click START.TOS     PP's release, unpatched
  C:\POWERMON  Powermonger            press P at boot (below)    {vers['POWERMON']}
  C:\PMWW1     Powermonger WW1        press W at boot (below)    v{PMWW1_VERSION}
  C:\POPULOUS  Populous               double-click RUNME.TOS     {vers['POPULOUS']}
  C:\POPORIG   Populous (original)    double-click RUNME.TOS     PP's release, unpatched
  C:\POPS2     Populous 2             double-click RUNME.TOS     {vers['POPS2']}
  C:\POP2ORIG  Populous 2 (original)  double-click RUNME.TOS     PP's release, unpatched
  C:\FLOOD     Flood                  double-click FLO.PRG       v{FLOOD_VERSION}
  C:\OVERLAND  Overlander             double-click OVERLAND.PRG  v{OVERLANDER_VERSION}

Boot: HDDRIVER banner, then "P Powermonger, W WW1, else desktop". Press
P within 3 seconds for Powermonger, W for Powermonger: World War 1
Edition; any other key (or waiting) goes to the desktop. Open drive C:
and double-click the game's start file.

DESKTOP.INF / NEWDESK.INF only size the desktop windows to fit a 320x200
screen (TOS 1.x does not shrink wider ones); they start nothing.

Why the Powermongers are different: their hard-disk versions copy TOS's
memory aside while they run and only work when started from the AUTO
folder (before the desktop exists); started from the desktop they stop.
AUTO\PMBOOT.PRG is the small program that asks.

Requirements
 - Atari ST/STE, Mega ST/STE or TT with 1 MB RAM or more, and an ACSI hard
   disk or an emulator of one (UltraSatan, ACSI2STM, ...) holding this
   image. Boots through HDDRIVER (HDDRIVER.SYS in the root, do not delete).
 - Hunter: STE, Mega STE or TT for the sampled sound (DMA sound); a plain ST
   plays the original sound.
 - Moonshine Racers: STE or Mega STE for the extra in-between frames (the game
   runs at a fixed 10 steps per second on every machine; faster machines show
   more frames). A plain ST runs it at its own speed. Campaigns and the track
   editor (F10 on the title or the WELCOME PARTNERS screen) need 2 MB.
 - Populous needs 1 MB; on a TT start it from the desktop (it runs from
   this disk there). Populous 2 needs 2 MB (Mega STE / TT, or an STE with
   2 MB or more).
 - Flood: STE, Mega STE, TT or Falcon for the Amiga music and sound (DMA
   sound) and the blitter scrolling; a plain ST plays the original YM sound.
 - Overlander: STE, Mega STE, TT or Falcon for the Amiga music and sound
   (DMA sound) and the blitter; a plain ST plays the original YM sound.
 - Powermonger WW1: 1 MB; the same machines as Powermonger, plus the Falcon.
 - Tested in the Hatari emulator only (STE, Mega STE, TT; Hunter also on a
   plain ST). On a TT the Midwinters need the PMMU (Hatari: --mmu true, as
   run_tt.sh does); PP's unpatched Midwinter does not start on a TT.
 - Keep resident AUTO programs and desk accessories to a minimum: Powermonger
   needs the TOS/driver memory (about 80 KB with HDDRIVER) to stay small.
 - Each folder has the game's own README.TXT and PATCHES.TXT (what changed).

Saving
 - Midwinter: saves go to FILES\MWC (data disk image) in its folder (the
   original in MW1ORIG has its own copy).
 - Midwinter 2: create the campaign first (War Room -> Start New Campaign);
   it is written to FILES\FFD. Back that file up. The original in MW2ORIG
   has its own blank campaign disk.
 - Hunter: as in PP's release.
 - Nebulus: 1 MB or more. T / E in a tower freeze the timer / remove the enemies;
   the original's cheat code is in NEBULUS\NEBCHEAT.TXT; F9 leaves to the desktop
   (PP's Gamex). Tested in Hatari on the STE and Mega STE; NEBORIG is PP's original.
 - Powermonger: Option -> File -> Save/Load, in POWERMON\SAVEDISK.DAT.
 - Powermonger WW1: Option -> File -> Save/Load, in PMWW1\SAVEDISK.DAT.
 - Populous: the game's own Save/Load, into FILES\POP in its folder.
 - Populous 2: the game's own SAVE/LOAD GAME does not work in PP's
   conversion (it crashes, unpatched too); use HAGA's statesave on the
   keypad (/) instead, which writes GS00.TOS... next to the game.

The disk is a raw image: write it to a real disk / SD card (dd, Win32 Disk
Imager) or use it as is in an HD emulator. The partition is under 32 MB so
that TOS 1.04 - 1.62 accept it.
"""
    return t.replace("\n", "\r\n")


def check_83(tree: Path):
    bad = []
    for p in tree.rglob("*"):
        stem, dot, ext = p.name.partition(".")
        if p.name != p.name.upper() or len(stem) > 8 or len(ext) > 3 or "." in ext:
            bad.append(str(p.relative_to(tree)))
    if bad:
        sys.exit("not plain upper-case 8.3 names (mtools would write long names): " + ", ".join(bad))


def tree_kb(tree: Path) -> int:
    """Disk use with 1 KB clusters."""
    tot = 0
    for p in tree.rglob("*"):
        tot += 1 if p.is_dir() else (p.stat().st_size + 1023) // 1024
    return tot


def build_image(img: Path, folders: dict[str, Path], size_kb: int, date: str, files: dict[str, bytes] | None = None):
    """Write the raw disk `img`: root sector, one BGM partition (HDDRIVER boot sector), HDDRIVER.SYS, README.TXT, folders."""
    psz = size_kb * 2
    if psz > MAX_PART_SECTORS:
        sys.exit(f"partition of {size_kb} KB is over 32 MB; TOS 1.04 would not mount it")
    total = FIRST_LBA + psz
    root = bytearray((HD / "hddriver_root.bin").read_bytes()[:SECTOR])
    pboot = (HD / "hddriver_pboot.bin").read_bytes()[:SECTOR]
    with open(img, "wb") as f:
        f.truncate(total * SECTOR)
    run(["mkfs.fat", "-F", "16", "-s", "2", "-S", "512", "-R", "1", "-f", "2", "-r", "512", "-i", "41544d53", "--offset", FIRST_LBA,
         "-n", VOLUME, img, psz // 2])
    with open(img, "rb") as f:
        f.seek(FIRST_LBA * SECTOR)
        mk = f.read(SECTOR)
    # root sector: HDDRIVER boot code $0..$1b5 + our table; hd_siz at $1c2, partition 0 at $1c6 {flag, id[3], start, size}
    root[0x1B6:0x200] = b"\0" * (0x200 - 0x1B6)
    struct.pack_into(">L", root, 0x1C2, total)
    root[0x1C6] = 0x81                                        # bit 0 exists, bit 7 bootable
    root[0x1C7:0x1CA] = b"BGM"
    struct.pack_into(">LL", root, 0x1CA, FIRST_LBA, psz)
    fix_sum(root)
    pb = bytearray(pboot)
    pb[3:0x34] = mk[3:0x34]                                   # keep HDDRIVER's loader code from $34, take mkfs.fat's BPB
    fix_sum(pb)
    with open(img, "r+b") as f:
        f.write(root)
        f.seek(FIRST_LBA * SECTOR)
        f.write(pb)
    tgt = f"{img}@@{FIRST_LBA * SECTOR}"
    env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
    tmp = STAGE / "_tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    run(["mcopy", "-i", tgt, "-m", HD / "HDDRIVER.SYS", "::HDDRIVER.SYS"], env=env)   # first, so it is early in the root directory
    allfiles = {"README.TXT": readme_text(VERSIONS, date).encode("ascii"), **(files or {})}
    for name, data in allfiles.items():
        (tmp / name).write_bytes(data)
    check_83(tmp)
    for name in allfiles:
        run(["mcopy", "-i", tgt, "-m", tmp / name, f"::{name}"], env=env)
    for name, src in folders.items():
        run(["mmd", "-i", tgt, f"::{name}"], env=env)
        for p in sorted(src.iterdir()):
            run(["mcopy", "-i", tgt, "-s", "-m", p, f"::{name}/"], env=env)
    shutil.rmtree(tmp, ignore_errors=True)
    return tgt, total, psz


VERSIONS: dict[str, str] = {}


def versions() -> dict[str, str]:
    """Release versions as the games' own tools report them (each reads its credit patch)."""
    v = {}
    for key, game, tool in (("MIDWINTR", "midwinter", "mw1patch"), ("MIDWINT2", "midwinter2", "mw2patch"),
                            ("HUNTER", "hunter", "huntpatch"), ("NEBULUS", "nebulus", "nebrelease"), ("MOONSHR", "moonshine-racers", "msrpatch"), ("POPULOUS", "populous", "poppatch"), ("POPS2", "populous-2", "pop2patch")):
        try:
            v[key] = "v" + py(game, tool, "version").strip()
        except SystemExit:
            v[key] = "patched"
    try:
        import re
        t = (GAMES / "powermonger" / "patches" / "pm_credit.s").read_text()
        m = re.search(r'^TXT:.*"v([^ ]*) enhanced by ', t, re.M)
        v["POWERMON"] = f"v{m.group(1)}" if m else "patched"
    except OSError:
        v["POWERMON"] = "patched"
    v["FLOOD"] = f"v{FLOOD_VERSION}"
    v["OVERLAND"] = f"v{OVERLANDER_VERSION}"
    v["PMWW1"] = f"v{PMWW1_VERSION}"
    return v


def layout_text(img: Path, tgt: str, total: int, psz: int, folders: dict[str, Path], md5: str, date: str) -> str:
    env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
    listing = run(["mdir", "-/", "-i", tgt, "::"], env=env)
    free = [l for l in listing.splitlines() if "bytes free" in l]
    t = [f"{img.name}  ({img.stat().st_size} bytes = {total} sectors of 512, raw disk image, md5 {md5})",
         f"built {date} by tools/make_hd_image.py from the current default builds of the games", "",
         "Sector map",
         f"  LBA 0                 root sector: HDDRIVER boot code + AHDI partition table (checksum $1234)",
         f"  LBA 1                 unused",
         f"  LBA {FIRST_LBA}..{FIRST_LBA + psz - 1}   partition 0: BGM (FAT16, 1 KB clusters, 512 root entries), flag $81 = bootable, "
         f"{psz} sectors = {psz // 2} KB (< 32 MB: TOS 1.04 compatible), boot sector = HDDRIVER partition loader",
         "", "Partition table", f"  #  flag  id   start  sectors  size       drive  volume",
         f"  0  $81   BGM  {FIRST_LBA:<6} {psz:<8} {psz // 2} KB  C:     {VOLUME}", "",
         "Drive C: (root)",
         "  HDDRIVER.SYS   HDDRIVER 10.15, started by the partition boot sector (must stay in the root)",
         "  README.TXT     the games, how to start them, versions, requirements",
         "  DESKTOP.INF    the TOS 1.x default desktop (TOS_1_62 ROM text) with windows <= 38 columns, so the C: window fits a 320x200 screen",
         "  NEWDESK.INF    the same for TOS 2.x/3.x (read before DESKTOP.INF; TOS_2_06 ROM text); neither has an autorun entry, nothing starts by itself"]
    why = {"MIDWINTR": "Midwinter (HAGA by PP, patched)", "MW1ORIG": "Midwinter (HAGA by PP, unpatched, for comparison)",
           "MIDWINT2": "Midwinter 2 (HAGA by PP, patched)", "MW2ORIG": "Midwinter 2 (HAGA by PP, unpatched, for comparison)",
           "MOONSHR": "Moonshine Racers (HAGA by PP, patched)",
           "HUNTER": "Hunter (Gamex by PP, patched; FILES\\P = patch code + STE sample bank)",
           "POWERMON": "Powermonger (HD build, patched; start it from the boot prompt, see README.TXT)",
           "POPULOUS": "Populous (HAGA by PP, patched; PATCHED.TXT)", "POPS2": "Populous 2 (HAGA by PP, patched)",
           "NEBULUS": "Nebulus (Gamex by PP, patched; NEPATCH.BIN = patch code)", "NEBORIG": "Nebulus (Gamex by PP, unpatched, for comparison)",
           "HUNTORIG": "Hunter (Gamex by PP, unpatched, for comparison)", "POPORIG": "Populous (HAGA by PP, unpatched, for comparison)",
           "POP2ORIG": "Populous 2 (HAGA by PP, unpatched, for comparison)",
           "FLOOD": "Flood (shipped HD release, patched FLO.PRG + Amiga sound files)",
           "OVERLAND": "Overlander (shipped HD release, patched OVERLAND.PRG + Amiga sound files)",
           "PMWW1": "Powermonger WW1 (shipped HD release, WW1.PRG moved up from AUTO\\; start it from the boot prompt, see README.TXT)",
           "AUTO": "boot prompt PMBOOT.PRG (tools/hd_pmboot.s): P = Powermonger, W = Powermonger WW1, any other key / 3 s = desktop"}
    for name, src in folders.items():
        n = sum(1 for p in src.rglob("*") if p.is_file())
        t.append(f"  {name + chr(92):<14} {why[name]}: {n} files, {tree_kb(src)} KB" + (f", {VERSIONS[name]}" if name in VERSIONS else ""))
    t += ["", "Start of the games: see README.TXT in the root (Powermonger: P at the boot prompt, Powermonger WW1: W; the others: double-click",
          "  MIDWINTR\\RUNME.TOS, MIDWINT2\\RUNME.TOS, MOONSHR\\RUNME.TOS, POPULOUS\\RUNME.TOS, POPS2\\RUNME.TOS, HUNTER\\START.TOS, NEBULUS\\START.TOS,",
          "  FLOOD\\FLO.PRG, OVERLAND\\OVERLAND.PRG on the desktop).", "",
          "Use",
          f"  real disk / SD card (ACSI2STM, UltraSatan, SCSI2SD + ACSI/SCSI bridge, ...): dd if={img.name} of=/dev/sdX bs=1M conv=fsync",
          "    (check the target device first; a bigger card works, the rest stays unpartitioned)",
          f"  Hatari: --acsi 0={img.name}  (add --gemdos-drive skip when no GEMDOS folder is wanted); STE/Mega STE/TT, TOS 1.04-3.06",
          "  Gotek-style floppy emulators cannot hold a hard disk image: use an ACSI/SCSI/IDE bridge",
          "", "mdir ::  (end of listing):"] + ["  " + l for l in free]
    return "\n".join(t) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", help="image path (default dist/AtariST_enhanced_games_<date>.img)")
    ap.add_argument("--size-kb", type=int, default=DEFAULT_SIZE_KB, help=f"partition size, default {DEFAULT_SIZE_KB} (max 32767)")
    ap.add_argument("--no-build", action="store_true", help="reuse the folders staged in dist/_stage by an earlier run")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    a = ap.parse_args()
    for f in ("HDDRIVER.SYS", "hddriver_root.bin", "hddriver_pboot.bin"):
        if not (HD / f).is_file():
            sys.exit(f"hd/{f} is missing (see hd/README.md)")
    for tool in ("mkfs.fat", "mcopy", "mmd", "mdir"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found (dosfstools / mtools)")
    STAGE.mkdir(parents=True, exist_ok=True)
    folders = {}
    for name in FOLDERS:
        folders[name] = STAGE / name if a.no_build and name != "AUTO" else BUILDERS[name]()
        if not folders[name].is_dir():
            sys.exit(f"{folders[name]} missing: run without --no-build first")
        check_83(folders[name])
        print(f"{name}: {tree_kb(folders[name])} KB")
    need = sum(tree_kb(p) for p in folders.values())
    if need > a.size_kb * 0.8:
        print(f"warning: games use {need} KB of a {a.size_kb} KB partition")
    VERSIONS.update(versions())
    img = Path(a.out) if a.out else DIST / f"AtariST_enhanced_games_{a.date}.img"
    vhd = img.with_suffix(".vhd")
    busy = [p for p in (img, vhd) if p.exists() and in_use(p)]
    if busy:
        raise SystemExit(f"refusing to overwrite {', '.join(map(str, busy))}: a running program (e.g. Hatari) has it open. "
                         "Quit it first, or pass --out with a new file name.")
    img.parent.mkdir(parents=True, exist_ok=True)
    tgt, total, psz = build_image(img, folders, a.size_kb, a.date, files=desktop_inf_files())
    md5 = hashlib.md5(img.read_bytes()).hexdigest()
    Path(str(img) + ".md5").write_text(f"{md5}  {img.name}\n")
    Path(str(img.with_suffix("")) + ".layout.txt").write_text(layout_text(img, tgt, total, psz, folders, md5, a.date))
    shutil.copyfile(img, vhd)              # same raw image under the name MiSTer and the run_*.sh launchers use
    print(f"{img}  {img.stat().st_size} bytes  md5 {md5}  (also {vhd.name})")


def in_use(path: Path) -> bool:
    """True if any process on this machine has `path` open (Linux /proc), so it must not be rewritten under it."""
    target = path.resolve()
    for fd_dir in Path("/proc").glob("[0-9]*/fd"):
        try:
            for fd in fd_dir.iterdir():
                try:
                    if Path(os.readlink(fd)) == target:
                        return True
                except OSError:
                    pass
        except OSError:
            pass
    return False


if __name__ == "__main__":
    main()
