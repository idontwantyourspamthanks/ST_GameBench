#!/usr/bin/env python3
r"""Build standalone auto-booting Atari ST hard-disk (.vhd) release packages for every done game.

    python3 tools/make_game_vhds.py                  # build all 10 done games into games/done/<game>/dist/
    python3 tools/make_game_vhds.py hunter flood     # build only the named game(s)

Each .vhd is an 8 MB raw Atari ST ACSI/IDE/SCSI hard-disk image (same format as tools/make_hd_image.py):
  * LBA 0: HDDRIVER root sector + AHDI partition table (one 8 MB FAT16 BGM partition, bootable, checksum $1234)
  * LBA 2: HDDRIVER partition boot sector + FAT16 BPB
  * C:\HDDRIVER.SYS + DESKTOP.INF (TOS 1.x) + NEWDESK.INF (TOS 2.x/3.x)
  * Desktop-launched games sit in their folder (e.g. C:\HUNTER\START.TOS) with a `#Z` autorun line so they
    boot straight into the game on TOS 1.x/2.x/3.x.
  * Powermonger and Powermonger WW1 sit at C:\ root with C:\AUTO\WAR.PRG / C:\AUTO\WW1.PRG so they auto-boot
    directly from the AUTO phase as required.

Each game's output zip is written to games/done/<game>/dist/ matching that game's release naming, containing
the .vhd image and a README.TXT with Hatari, MiSTer, and real-hardware usage instructions.
"""
from __future__ import annotations

import argparse
import datetime
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HD = ROOT / "hd"
DONE = ROOT / "games" / "done"
SECTOR = 512
FIRST_LBA = 2
DEFAULT_SIZE_KB = 8192  # 8 MB: safely FAT16 (> 4085 clusters) with 4-7 MB free for saves; zeroes compress to ~0 in zip

# Same ROM-default DESKTOP.INF / NEWDESK.INF lines as tools/make_hd_image.py (windows <= 38 cols for 320px ST-Low).
_INF_1X = (
    "#a000000", "#b000000", "#c???000?000<00<?00;;400;0;;;4440??0;;?0?;0;;;0??03111103",
    "#d" + " " * 45, "#E 18 13 ",
    "#W 00 00 00 07 26 0C 00 @", "#W 00 00 02 0B 24 09 00 @",
    "#W 00 00 04 0F 22 09 00 @", "#W 00 00 06 01 20 09 00 @",
    "#C 01 01 00 FF c CARTRIDGE@ @ ", "#M 01 00 00 FF C HARD DISK@ @ ",
    "#M 00 00 00 FF A FLOPPY DISK@ @ ", "#M 00 01 00 FF B FLOPPY DISK@ @ ",
    "#T 00 07 02 FF   TRASH@ @ ", "#F FF 04   @ *.*@ ", "#D FF 01   @ *.*@ ",
    "#G 03 FF   *.APP@ @ ", "#G 03 FF   *.PRG@ @ ", "#P 03 FF   *.TTP@ @ ", "#F 03 04   *.TOS@ @ ",
)
_INF_2X = (
    "#a000000", "#b000000", "#c7770007000600070055200505552220770557075055507703111103",
    "#d" + " " * 45, "#E 18 03 00 06 43",
    "#W 00 00 00 07 26 0C 00 @", "#W 00 00 02 0B 24 09 00 @",
    "#W 00 00 04 0F 22 09 00 @", "#W 00 00 06 01 20 09 00 @",
    "#W 00 00 04 07 22 0C 00 @", "#W 00 00 0C 0B 1A 09 00 @",
    "#W 00 00 08 0F 1E 09 00 @", "#W 00 00 06 01 20 09 00 @",
    "#C 01 01 00 FF c CARTRIDGE@ @ ", "#M 00 01 00 FF C HARD DISK@ @ ",
    "#M 00 00 00 FF A FLOPPY DISK@ @ ", "#M 00 01 00 FF B FLOPPY DISK@ @ ",
    "#T 00 07 02 FF   TRASH@ @ ", "#F FF 04   @ *.*@ ", "#D FF 01   @ *.*@ ",
    "#G 03 FF   *.APP@ @ ", "#G 03 FF   *.PRG@ @ ", "#Y 03 FF   *.GTP@ @ ",
    "#P 03 FF   *.TTP@ @ ", "#F 03 04   *.TOS@ @ ",
)


@dataclass(frozen=True)
class GameSpec:
    slug: str                # directory under games/done/
    title: str               # display name
    version: str             # release version string
    hd_zip: str              # filename inside games/done/<slug>/dist/
    zip_root: str            # top-level folder inside hd_zip
    vhd_name: str            # .vhd filename inside the output zip
    out_zip_tmpl: str        # output zip filename template ({date} substituted if present)
    volume: str              # 11-char max FAT16 volume label
    autorun: str | None      # e.g. "C:\\HUNTER\\START.TOS", or None for AUTO\ booters
    root_install: bool = False  # True: extract zip_root contents directly to C:\ (Powermonger / WW1)
    renames: tuple[tuple[str, str], ...] = ()
    notes: str = ""


SPECS: tuple[GameSpec, ...] = (
    GameSpec(
        slug="flood",
        title="Flood",
        version="1.1",
        hd_zip="Flood_hd_v1.1.zip",
        zip_root="FLOOD",
        vhd_name="Flood_v1.1.vhd",
        out_zip_tmpl="Flood_vhd_v1.1.zip",
        volume="FLOOD",
        autorun="C:\\FLOOD\\FLO.PRG",
    ),
    GameSpec(
        slug="hunter",
        title="Hunter",
        version="1.4",
        hd_zip="Hunter_v1.4_patched_hd_2026-11-25.zip",
        zip_root="HUNTER",
        vhd_name="Hunter_v1.4.vhd",
        out_zip_tmpl="Hunter_v1.4_patched_vhd_{date}.zip",
        volume="HUNTER",
        autorun="C:\\HUNTER\\START.TOS",
        notes="Hunter's loader requires a real ACSI/IDE/SCSI hard-disk image with an HD driver (it cannot run from Hatari's GEMDOS folder emulation).",
    ),
    GameSpec(
        slug="midwinter",
        title="Midwinter",
        version="1.3",
        hd_zip="Midwinter_v1.3_patched_2026-11-26.zip",
        zip_root="MW1PATCH",
        vhd_name="Midwinter_v1.3.vhd",
        out_zip_tmpl="Midwinter_v1.3_patched_vhd_{date}.zip",
        volume="MIDWINTER",
        autorun="C:\\MW1PATCH\\RUNME.TOS",
    ),
    GameSpec(
        slug="midwinter2",
        title="Midwinter 2: Flames of Freedom",
        version="1.7",
        hd_zip="Midwinter2_v1.7_patched_2026-11-26.zip",
        zip_root="MW2PATCH",
        vhd_name="Midwinter2_v1.7.vhd",
        out_zip_tmpl="Midwinter2_v1.7_patched_vhd_{date}.zip",
        volume="MIDWINT2",
        autorun="C:\\MW2PATCH\\RUNME.TOS",
    ),
    GameSpec(
        slug="moonshine-racers",
        title="Moonshine Racers",
        version="1.4.1",
        hd_zip="MoonshineRacers_hd_v1.4.1.zip",
        zip_root="MOONSHR",
        vhd_name="MoonshineRacers_v1.4.1.vhd",
        out_zip_tmpl="MoonshineRacers_vhd_v1.4.1.zip",
        volume="MOONSHR",
        autorun="C:\\MOONSHR\\RUNME.TOS",
    ),
    GameSpec(
        slug="nebulus",
        title="Nebulus",
        version="1.2",
        hd_zip="Nebulus_hd_v1.2.zip",
        zip_root="NEBULUS",
        vhd_name="Nebulus_v1.2.vhd",
        out_zip_tmpl="Nebulus_vhd_v1.2.zip",
        volume="NEBULUS",
        autorun="C:\\NEBULUS\\START.TOS",
        renames=(("Nebulus_campaign_disk.st", "NEBCAMP.ST"),),
        notes="The blank campaign disk is stored on the drive as C:\\NEBULUS\\NEBCAMP.ST (8.3 filename).",
    ),
    GameSpec(
        slug="populous",
        title="Populous",
        version="1.1",
        hd_zip="Populous_v1.1_patched_hd_2026-11-25.zip",
        zip_root="POPULOUS",
        vhd_name="Populous_v1.1.vhd",
        out_zip_tmpl="Populous_v1.1_patched_vhd_{date}.zip",
        volume="POPULOUS",
        autorun="C:\\POPULOUS\\RUNME.TOS",
    ),
    GameSpec(
        slug="populous-2",
        title="Populous 2",
        version="1.1",
        hd_zip="Populous2_v1.1_patched_2026-11-25.zip",
        zip_root="POPS2",
        vhd_name="Populous2_v1.1.vhd",
        out_zip_tmpl="Populous2_v1.1_patched_vhd_{date}.zip",
        volume="POPULOUS2",
        autorun="C:\\POPS2\\RUNME.TOS",
    ),
    GameSpec(
        slug="powermonger",
        title="Powermonger",
        version="1.3",
        hd_zip="Powermonger_v1.3_patched_hd_2026-11-25.zip",
        zip_root="POWERMONGER",
        vhd_name="Powermonger_v1.3.vhd",
        out_zip_tmpl="Powermonger_v1.3_patched_vhd_{date}.zip",
        volume="POWERMON",
        autorun=None,
        root_install=True,
        notes="Powermonger boots automatically from C:\\AUTO\\WAR.PRG before the GEM desktop starts (required by the game).",
    ),
    GameSpec(
        slug="powermonger-ww1",
        title="Powermonger WW1 Edition",
        version="1.0",
        hd_zip="PowermongerWW1_v1.0_patched_hd_2026-11-25.zip",
        zip_root="POWERMONGER_WW1",
        vhd_name="PowermongerWW1_v1.0.vhd",
        out_zip_tmpl="PowermongerWW1_v1.0_patched_vhd_{date}.zip",
        volume="PMWW1",
        autorun=None,
        root_install=True,
        notes="Powermonger WW1 boots automatically from C:\\AUTO\\WW1.PRG before the GEM desktop starts (required by the game).",
    ),
    GameSpec(
        slug="seconds-out",
        title="Seconds Out",
        version="1.1",
        hd_zip="SecondsOut_Enhanced_v1.1_HD.zip",
        zip_root="SECONDS",
        vhd_name="SecondsOut_v1.1.vhd",
        out_zip_tmpl="SecondsOut_Enhanced_v1.1_VHD.zip",
        volume="SECOUT",
        autorun="C:\\SECONDS\\SECONDS.PRG",
    ),
)


def run(cmd, env=None):
    r = subprocess.run([str(c) for c in cmd], env=env, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"command failed ({r.returncode}): {' '.join(map(str, cmd))}\n{r.stdout}{r.stderr}")
    return r.stdout


def fix_sum(sec: bytearray, want: int = 0x1234) -> None:
    sec[510:512] = b"\0\0"
    s = sum(struct.unpack(">256H", bytes(sec))) & 0xFFFF
    struct.pack_into(">H", sec, 510, (want - s) & 0xFFFF)


def check_83(tree: Path) -> None:
    bad = []
    for p in tree.rglob("*"):
        stem, _, ext = p.name.partition(".")
        if p.name != p.name.upper() or len(stem) > 8 or len(ext) > 3 or "." in ext:
            bad.append(str(p.relative_to(tree)))
    if bad:
        sys.exit("not plain upper-case 8.3 names: " + ", ".join(bad))


def inf_files(autorun: str | None) -> dict[str, bytes]:
    extra = (f"#Z 01 {autorun}@ @",) if autorun else ()
    crlf = lambda lines: "".join(l + "\r\n" for l in lines).encode("latin-1")
    return {
        "DESKTOP.INF": crlf(_INF_1X + extra) + b"\x1a",
        "NEWDESK.INF": crlf(_INF_2X + extra),
    }


def make_readme(spec: GameSpec, date: str) -> str:
    boot_line = (
        f"Auto-boots straight into {spec.title} via {spec.autorun}."
        if spec.autorun
        else f"Auto-boots straight into {spec.title} from C:\\AUTO\\."
    )
    extra = f"\nNote:\n  {spec.notes}\n" if spec.notes else ""
    text = f"""{spec.title} v{spec.version} (enhanced by dad_prg) - Bootable Hard-Disk Image (.vhd)
Built {date}

Contents:
  {spec.vhd_name}   8 MB bootable Atari ST hard-disk image (HDDRIVER + FAT16 BGM partition).
  {boot_line}
  Saves persist directly inside the .vhd image.

How to use:
  Hatari (important: disable GEMDOS hard-drive emulation so C: boots from the VHD):
    hatari --machine ste --tos TOS_1_62.img --memsize 4096 --gemdos-drive skip --acsi 0={spec.vhd_name}
    (Also works with --machine st/megast/megaste/tt and TOS 1.04 - 3.06; on Falcon use --ide-master {spec.vhd_name}.)

  MiSTer (Atari ST core):
    Copy {spec.vhd_name} into games/ATARI_ST/ and mount it as the ACSI hard disk.

  Real Atari ST/STE/Mega STE/TT (UltraSatan, ACSI2STM, SCSI2SD, etc.):
    Write the raw image directly to an SD card or mount it as an ACSI disk image:
      dd if={spec.vhd_name} of=/dev/sdX bs=1M conv=fsync
{extra}
For the full patch list and controls, see README.TXT / PATCHES.TXT inside the game folder on C:.
"""
    return text.replace("\n", "\r\n")


def build_vhd(spec: GameSpec, date: str, size_kb: int = DEFAULT_SIZE_KB) -> Path:
    gdir = DONE / spec.slug
    if not gdir.is_dir():
        alt = ROOT / "games" / "in_progress" / spec.slug
        if alt.is_dir():
            gdir = alt
    src_zip = gdir / "dist" / spec.hd_zip
    if not src_zip.is_file():
        sys.exit(f"missing source HD zip: {src_zip}")

    env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
    with tempfile.TemporaryDirectory(prefix=f"vhd-{spec.slug}-") as td:
        tmp = Path(td)
        extract = tmp / "extract"
        with zipfile.ZipFile(src_zip) as z:
            z.extractall(extract)
        src_root = extract / spec.zip_root
        if not src_root.is_dir():
            sys.exit(f"{src_zip}: expected folder {spec.zip_root}")

        for old_rel, new_rel in spec.renames:
            p = src_root / old_rel
            if p.exists():
                p.rename(src_root / new_rel)

        check_83(src_root)

        vhd = tmp / spec.vhd_name
        psz = size_kb * 2
        total = FIRST_LBA + psz
        root = bytearray((HD / "hddriver_root.bin").read_bytes()[:SECTOR])
        pboot = (HD / "hddriver_pboot.bin").read_bytes()[:SECTOR]
        with open(vhd, "wb") as f:
            f.truncate(total * SECTOR)

        run([
            "mkfs.fat", "-F", "16", "-s", "2", "-S", "512", "-R", "1", "-f", "2", "-r", "512",
            "-i", "41544d53", "--offset", FIRST_LBA, "-n", spec.volume, vhd, psz // 2,
        ])
        with open(vhd, "rb") as f:
            f.seek(FIRST_LBA * SECTOR)
            mk = f.read(SECTOR)

        root[0x1B6:0x200] = b"\0" * (0x200 - 0x1B6)
        struct.pack_into(">L", root, 0x1C2, total)
        root[0x1C6] = 0x81
        root[0x1C7:0x1CA] = b"BGM"
        struct.pack_into(">LL", root, 0x1CA, FIRST_LBA, psz)
        fix_sum(root)

        pb = bytearray(pboot)
        pb[3:0x34] = mk[3:0x34]
        fix_sum(pb)
        with open(vhd, "r+b") as f:
            f.write(root)
            f.seek(FIRST_LBA * SECTOR)
            f.write(pb)

        tgt = f"{vhd}@@{FIRST_LBA * SECTOR}"
        run(["mcopy", "-i", tgt, "-m", HD / "HDDRIVER.SYS", "::HDDRIVER.SYS"], env=env)

        infs = tmp / "infs"
        infs.mkdir()
        for name, data in inf_files(spec.autorun).items():
            (infs / name).write_bytes(data)
            run(["mcopy", "-i", tgt, "-m", infs / name, f"::{name}"], env=env)

        if spec.root_install:
            for p in sorted(src_root.iterdir()):
                run(["mcopy", "-i", tgt, "-s", "-m", p, "::"], env=env)
        else:
            run(["mmd", "-i", tgt, f"::{spec.zip_root}"], env=env)
            for p in sorted(src_root.iterdir()):
                run(["mcopy", "-i", tgt, "-s", "-m", p, f"::{spec.zip_root}/"], env=env)

        out_zip = gdir / "dist" / spec.out_zip_tmpl.format(date=date)
        readme = make_readme(spec, date).encode("ascii")
        with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            z.write(vhd, arcname=spec.vhd_name)
            z.writestr("README.TXT", readme)

        print(f"OK {spec.slug:<18} -> {out_zip.relative_to(ROOT)} ({out_zip.stat().st_size:,} bytes)")
        return out_zip


def main() -> None:
    ap = argparse.ArgumentParser(description="Build standalone auto-booting VHD release zips for done games.")
    ap.add_argument("games", nargs="*", help="optional game slugs (default: all done games)")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--size-kb", type=int, default=DEFAULT_SIZE_KB)
    a = ap.parse_args()

    for f in ("HDDRIVER.SYS", "hddriver_root.bin", "hddriver_pboot.bin"):
        if not (HD / f).is_file():
            sys.exit(f"hd/{f} is missing")
    for tool in ("mkfs.fat", "mcopy", "mmd"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found")

    wanted = set(a.games)
    by_slug = {s.slug: s for s in SPECS}
    unknown = wanted - set(by_slug)
    if unknown:
        sys.exit(f"unknown game(s): {', '.join(sorted(unknown))}")

    selected = [s for s in SPECS if not wanted or s.slug in wanted]
    for spec in selected:
        build_vhd(spec, a.date, a.size_kb)


if __name__ == "__main__":
    main()
