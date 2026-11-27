#!/usr/bin/env python3
"""Build a self-booting 1.44 MB Atari ST/STE floppy image (.st) for Player Manager v1.1.

    python3 tools/mkfloppy.py

Layout (standard 80-track, 18-sector, 2-side FAT12 1.44 MB .st image):
  A:\\DESKTOP.INF + NEWDESK.INF : auto-runs A:\\RUNME.TOS on cold boot (TOS 1.04/1.62/2.06)
  A:\\RUNME.TOS, HAGA, PLAYMA.PCH, PATCHED.TXT, README.TXT
  A:\\FILES\\*                   : all game + Kick Off 2 + STE Amiga pitch/sound files
  ~210 KB free on disk for career save games!
"""
import os
import shutil
import struct
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build" / "game"
DIST = ROOT / "dist"
VER = "1.1"
DATE = os.environ.get("DATE", "2026-11-27")

# Minimal Atari TOS DESKTOP.INF (TOS 1.x) and NEWDESK.INF (TOS 2.x/3.x) that auto-run A:\RUNME.TOS
DESKTOP_INF = (
    "#a000000\r\n"
    "#b000000\r\n"
    "#c???000?000<00<?00;;400;0;;;4440??0;;?0?;0;;;0??03111103\r\n"
    "#d                                             \r\n"
    "#Z 01 A:\\RUNME.TOS@\r\n"
    "#E 18 13 \r\n"
    "#W 00 00 02 06 26 0C 00 @\r\n"
    "#M 00 00 00 FF A FLOPPY DISK@ @ \r\n"
    "#M 00 01 00 FF B FLOPPY DISK@ @ \r\n"
    "#T 00 03 02 FF   TRASH@ @ \r\n"
    "#F FF 04   @ *.*@ \r\n"
    "#D FF 01   @ *.*@ \r\n"
    "#G 03 FF   *.APP@ @ \r\n"
    "#G 03 FF   *.PRG@ @ \r\n"
    "#P 03 FF   *.TTP@ @ \r\n"
    "#F 03 04   *.TOS@ @ \r\n"
    "\x1a"
).encode("latin-1")

NEWDESK_INF = (
    "#a000000\r\n"
    "#b000000\r\n"
    "#c7770007000600070055200505552220770557075055507703111103\r\n"
    "#d                                             \r\n"
    "#Z 01 A:\\RUNME.TOS@\r\n"
    "#E 18 03 00 06 43\r\n"
    "#W 00 00 02 06 26 0C 00 @\r\n"
    "#M 00 00 00 FF A FLOPPY DISK@ @ \r\n"
    "#M 00 01 00 FF B FLOPPY DISK@ @ \r\n"
    "#T 00 03 02 FF   TRASH@ @ \r\n"
    "#F FF 04   @ *.*@ \r\n"
    "#D FF 01   @ *.*@ \r\n"
    "#G 03 FF   *.APP@ @ \r\n"
    "#G 03 FF   *.PRG@ @ \r\n"
    "#Y 03 FF   *.GTP@ @ \r\n"
    "#P 03 FF   *.TTP@ @ \r\n"
    "#F 03 04   *.TOS@ @ \r\n"
).encode("latin-1")

FLOPPY_README = f"""Player Manager v{VER} enhanced by dad_prg - Floppy Edition ({DATE})
================================================================

Self-booting 1.44 MB HD Atari ST / STE floppy image (.st).
Works on MiSTerFPGA, Hatari, Gotek / FlashFloppy / HxC, Mega STE, and Falcon.

Requirements:
  - 2 MB RAM minimum (verified on 2 MB and 4 MB Atari STE / ST on MiSTerFPGA & Hatari)
  - Atari STE (2 MB+): triple-buffered 50 FPS Amiga striped pitches (4 conditions),
    hardware fine scroll, Blitter HUD, active player underline, and 6.25 kHz DMA audio!
  - Plain Atari ST (2 MB+): automatically runs classic ST Kick Off 2 match visuals & YM audio.

How to run:
  - Insert PlayerManager_v{VER}.st into Drive A: and cold-boot (auto-runs A:\\RUNME.TOS).
  - Or double-click A:\\RUNME.TOS from the TOS Desktop.
  - ~200 KB is left free on the disk for saving career games.

See PATCHED.TXT on the disk for the full feature list.
""".replace("\n", "\r\n")


def build_floppy() -> tuple[Path, Path]:
    assert (BUILD / "RUNME.TOS").is_file(), "Run tools/package.sh first!"
    DIST.mkdir(parents=True, exist_ok=True)
    st_path = DIST / f"PlayerManager_v{VER}_floppy_{DATE}.st"
    zip_path = DIST / f"PlayerManager_v{VER}_floppy_{DATE}.zip"

    # Skip large text manuals so ~200 KB stays free on disk for career saves
    # (D15RH.FIC / D15RF.FIC are required by PP's HAGA loader at boot!)
    skip_root = {"MANUAL.TXT", "LOG.TXT"}
    skip_files = set()

    env = dict(os.environ, MTOOLS_SKIP_CHECK="1", TZ="UTC")
    with tempfile.TemporaryDirectory(prefix="pmflop-") as td:
        td_p = Path(td)
        img = td_p / f"PlayerManager_v{VER}.st"
        # Standard 1.44 MB HD floppy: 80 tracks * 2 heads * 18 sectors * 512 bytes = 1,474,560 bytes
        # CRITICAL: Atari TOS 1.04 / 1.62 / 2.06 GEMDOS requires 2 sectors/cluster (1024-byte clusters, spc=2)!
        # (`mformat -f 1440` defaults to PC spc=1 which breaks TOS 1.x!)
        img.write_bytes(b"\x00" * (80 * 2 * 18 * 512))
        subprocess.run(
            ["mkfs.fat", "-F", "12", "-s", "2", "-S", "512", "-R", "1", "-f", "2", "-r", "112",
             "-n", "PLAYMGR11", str(img)],
            check=True,
            env=env,
        )
        # Ensure Atari-clean BPB geometry (18 spt, 2 heads, media $F0) and non-executable checksum (!= $1234)
        bpb = bytearray(img.read_bytes())
        struct.pack_into("<HHH", bpb, 24, 18, 2, 0)
        bpb[21] = 0xF0
        if (sum(struct.unpack(">256H", bpb[:512])) & 0xFFFF) == 0x1234:
            bpb[511] ^= 1
        img.write_bytes(bpb)
        # Write DESKTOP.INF (TOS 1.x) & NEWDESK.INF (TOS 2.x/3.x) for cold-boot autorun
        for inf_name, inf_data in (("DESKTOP.INF", DESKTOP_INF), ("NEWDESK.INF", NEWDESK_INF)):
            p = td_p / inf_name
            p.write_bytes(inf_data)
            subprocess.run(["mcopy", "-i", str(img), str(p), f"::/{inf_name}"], check=True, env=env)
        # Copy PATCHED.TXT (CRLF)
        patched_txt = td_p / "PATCHED.TXT"
        patched_txt.write_text(
            (ROOT / "patches" / "README_HD.TXT").read_text().replace("\n", "\r\n"),
            encoding="latin-1",
        )
        subprocess.run(["mcopy", "-i", str(img), str(patched_txt), "::/PATCHED.TXT"], check=True, env=env)
        # Copy root files
        for p in sorted(BUILD.iterdir()):
            if p.is_file() and p.name not in skip_root:
                subprocess.run(["mcopy", "-i", str(img), str(p), f"::/{p.name}"], check=True, env=env)
        # Create FILES/ and copy all game + KO2 + STE Amiga files
        subprocess.run(["mmd", "-i", str(img), "::/FILES"], check=True, env=env)
        for p in sorted((BUILD / "FILES").iterdir()):
            if p.is_file() and p.name not in skip_files:
                subprocess.run(["mcopy", "-i", str(img), str(p), f"::/FILES/{p.name}"], check=True, env=env)

        # Print directory listing & free space
        out = subprocess.run(["mdir", "-i", str(img), "::/", "::/FILES"], capture_output=True, text=True, check=True, env=env)
        print(out.stdout)

        shutil.copy2(img, st_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.TXT", FLOPPY_README)
            zf.write(st_path, f"PlayerManager_v{VER}.st")
    print(f"Built {st_path} ({st_path.stat().st_size:,} B)")
    print(f"Built {zip_path} ({zip_path.stat().st_size:,} B)")
    return st_path, zip_path


if __name__ == "__main__":
    build_floppy()
