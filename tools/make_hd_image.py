#!/usr/bin/env python3
r"""Build one raw Atari ST hard-disk image with all four enhanced games (current default builds).

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
  * C:\ = HDDRIVER.SYS, README.TXT, no DESKTOP.INF (TOS uses its own default desktop, no autorun), AUTO\PMBOOT.PRG (the boot
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
FIRST_LBA = 2                                           # as HDDRIVER's own formatter and gamebench/games/in_progress/hunter/tools/hunter.py
MAX_PART_SECTORS = 65535                                # TOS < 2.06 BPB: 16-bit sector count
DEFAULT_SIZE_KB = 32000                                 # one partition, 64000 sectors (31.25 MiB)
VOLUME = "GAMES"

# folder on C: -> game; versions/requirements for README.TXT are taken from the builds where possible (see readme_text)
FOLDERS = ("MIDWINTR", "MIDWINT2", "HUNTER", "POWERMON", "AUTO")


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
    g = GAMES / "midwinter2"
    out, dst = STAGE / "mw2_build", STAGE / "MIDWINT2"
    py("midwinter2", "mw2patch", "verify")
    shutil.rmtree(out, ignore_errors=True)
    py("midwinter2", "mw2patch", "build", "--out", out)
    shutil.rmtree(dst, ignore_errors=True)
    dst.mkdir(parents=True)
    # = what midwinter2/tools/package.sh puts into MW2PATCH/
    copy_names(out, dst, ["RUNME.TOS", "HAGA", "FF240R.BMP", "FFF273.HST", "LFF273.HST"])
    copy_names(g, dst, ["README.TXT", "LOG.TXT", "SOLUTION.TXT"])
    shutil.copytree(g / "FILES", dst / "FILES")               # originals: FFD stays the blank campaign disk
    shutil.copy2(g / "patches" / "PATCHES.TXT", dst / "PATCHES.TXT")
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
            "C:\\AUTO\\PMBOOT.PRG asks \"Powermonger? P = start, else desktop\"; P sets the current directory to C:\\POWERMON and\n"
            "starts WAR.PRG. The \"Installing\" text below is for a stand-alone install; WAR.PRG started from the desktop stops\n"
            "with \"cannot swap the low RAM of TOS\".\n\n")
    body = (g / "patches" / "README_HD.TXT").read_text().replace("@VER@", ver)
    (dst / "README.TXT").write_bytes((note + body).replace("\n", "\r\n").encode("latin-1", "replace"))
    return dst


def build_auto() -> Path:
    r"""AUTO\PMBOOT.PRG: the boot prompt that starts Powermonger (tools/hd_pmboot.s; the game must be started from the AUTO phase)."""
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


BUILDERS = {"MIDWINTR": build_midwinter, "MIDWINT2": build_midwinter2, "HUNTER": build_hunter, "POWERMON": build_powermonger,
            "AUTO": build_auto}


# ---- 2. the disk ---------------------------------------------------------------------------------------------------------------
def fix_sum(sec: bytearray, want: int = 0x1234) -> None:
    """Make the 256 big-endian words of a boot/root sector sum to `want` (TOS: $1234 = executable boot sector)."""
    sec[510:512] = b"\0\0"
    s = sum(struct.unpack(">256H", bytes(sec))) & 0xFFFF
    struct.pack_into(">H", sec, 510, (want - s) & 0xFFFF)


def readme_text(vers: dict[str, str], date: str) -> str:
    t = rf"""ATARI ST ENHANCED GAMES - HARD DISK  ({date})
==========================================================================

Four games with dad_prg's patches (speed, sound, fixes) on one bootable
hard disk image: HDDRIVER, one 31 MB partition = drive C:.  Nothing starts
by itself except a 3-second question about Powermonger at boot.

  FOLDER       GAME                   START                      VERSION
  -----------  ---------------------  -------------------------  -------
  C:\MIDWINTR  Midwinter              double-click RUNME.TOS     {vers['MIDWINTR']}
  C:\MIDWINT2  Midwinter 2            double-click RUNME.TOS     {vers['MIDWINT2']}
  C:\HUNTER    Hunter                 double-click START.TOS     {vers['HUNTER']}
  C:\POWERMON  Powermonger            press P at boot (below)    {vers['POWERMON']}

Boot: HDDRIVER banner, then "Powermonger? P = start, else desktop". Press
P within 3 seconds to start Powermonger; any other key (or waiting) goes
to the desktop. Open drive C: and double-click the game's start file.

Why Powermonger is different: its hard-disk version copies TOS's memory
aside while it runs and only works when started from the AUTO folder
(before the desktop exists); started from the desktop it says "cannot swap
the low RAM of TOS". AUTO\PMBOOT.PRG is the small program that asks.

Requirements
 - Atari ST/STE, Mega ST/STE (or TT, see below) with 1 MB RAM or more, and an ACSI hard
   disk or an emulator of one (UltraSatan, ACSI2STM, ...) holding this
   image. Boots through HDDRIVER (HDDRIVER.SYS in the root, do not delete).
 - Hunter: STE, Mega STE or TT for the sampled sound (DMA sound); a plain ST
   plays the original sound.
 - Tested in the Hatari emulator only (STE, Mega STE, TT; Hunter also on a
   plain ST). On a TT the Midwinters did not start from an ACSI/HDDRIVER
   disk there (PP's unpatched versions neither); use an ST/STE/Mega STE.
 - Keep resident AUTO programs and desk accessories to a minimum: Powermonger
   needs the TOS/driver memory (about 80 KB with HDDRIVER) to stay small.
 - Each folder has the game's own README.TXT and PATCHES.TXT (what changed).

Saving
 - Midwinter: saves go to FILES\MWC (data disk image) in its folder.
 - Midwinter 2: create the campaign first (War Room -> Start New Campaign);
   it is written to FILES\FFD. Back that file up.
 - Hunter: as in PP's release.
 - Powermonger: Option -> File -> Save/Load, in POWERMON\SAVEDISK.DAT.

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
                            ("HUNTER", "hunter", "huntpatch")):
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
    return v


def layout_text(img: Path, tgt: str, total: int, psz: int, folders: dict[str, Path], md5: str, date: str) -> str:
    env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
    listing = run(["mdir", "-/", "-i", tgt, "::"], env=env)
    free = [l for l in listing.splitlines() if "bytes free" in l]
    t = [f"{img.name}  ({img.stat().st_size} bytes = {total} sectors of 512, raw disk image, md5 {md5})",
         f"built {date} by tools/make_hd_image.py from the current default builds of the four games", "",
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
         "  (no DESKTOP.INF: TOS uses its built-in default desktop; nothing starts by itself)"]
    why = {"MIDWINTR": "Midwinter (HAGA by PP, patched)", "MIDWINT2": "Midwinter 2 (HAGA by PP, patched)",
           "HUNTER": "Hunter (Gamex by PP, patched; FILES\\P = patch code + STE sample bank)",
           "POWERMON": "Powermonger (HD build, patched; start it from the boot prompt, see README.TXT)",
           "AUTO": "boot prompt PMBOOT.PRG (tools/hd_pmboot.s): P = start Powermonger, any other key / 3 s = desktop"}
    for name, src in folders.items():
        n = sum(1 for p in src.rglob("*") if p.is_file())
        t.append(f"  {name + chr(92):<14} {why[name]}: {n} files, {tree_kb(src)} KB" + (f", {VERSIONS[name]}" if name in VERSIONS else ""))
    t += ["", "Start of the games: see README.TXT in the root (Powermonger: press P at the boot prompt; the others: double-click",
          "  MIDWINTR\\RUNME.TOS, MIDWINT2\\RUNME.TOS, HUNTER\\START.TOS on the desktop).", "",
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
    img.parent.mkdir(parents=True, exist_ok=True)
    tgt, total, psz = build_image(img, folders, a.size_kb, a.date)
    md5 = hashlib.md5(img.read_bytes()).hexdigest()
    Path(str(img) + ".md5").write_text(f"{md5}  {img.name}\n")
    Path(str(img.with_suffix("")) + ".layout.txt").write_text(layout_text(img, tgt, total, psz, folders, md5, a.date))
    print(f"{img}  {img.stat().st_size} bytes  md5 {md5}")


if __name__ == "__main__":
    main()
