#!/usr/bin/env python3
"""
Package Flood STE Enhanced v1.0 into:
  - dist/Flood_hd_v1.0.zip      (Hard-drive folder: FLO.PRG + AM_MUS.BIN + AM_SFX.BIN + game data)
  - dist/Flood_floppy_v1.0.zip  (Auto-booting 720 KB Atari ST/STE floppy image Flood_v1.0.st)
"""
import argparse
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG_FILES = ROOT / "originals" / "FLOODGX" / "FILES"
OVERLAY = ROOT / "work" / "disk_overlay"
DIST = ROOT / "dist"

SKIP_ORIG = {"FLO.FIC", "INTRO.TOS", "LOADER.PRG"}


def make_readme(version: str) -> str:
    return f"""Flood — Atari STE Enhanced ({version})
======================================

Original game: Bullfrog Productions / Electronic Arts (1990)
Target: 1 MB Atari STE (also runs cleanly on ST, Mega ST, Mega STE, TT, Falcon)

What's new in {version}:
- STE Blitter acceleration for tilemap redraw (with 21-tile cached-background
  fast path) and 32x32 masked sprites (automatic CPU fallback on plain ST).
- Smooth 1-pixel horizontal scrolling following Quiffy continuously via the
  STE Blitter barrel shifter (FXSR) + pixel-aligned water overlay (replaces
  the ST original's jerky 128-pixel chunk jumps).
- Fixed 25.0 Hz VBL frame pacing: eliminates 8 MHz slowdowns (17.5 -> 25.0 fps)
  and caps fast machines (16 MHz Mega STE, 32 MHz TT, Falcon) to authentic speed
  instead of running at 2.5x-2.9x speed.
- Full Amiga 4-channel stereo audio on STE DMA (12,517 Hz):
  * Authentic Amiga title, high-score, and ending music (TRACK.DA + INSTR.DA)
  * Authentic Amiga 4-channel stereo in-game SFX (FLDFX.DU + FLDFX.IN)
  * Automatic fallback to ST YM audio on plain ST (with Falcon YM-mirror fix).
- Restored Amiga 12-bit STE palettes for tilesets B and C (ST originally
  duplicated tileset A's palette across all three slots).

How to run:
- Hard drive: copy the FLOOD folder anywhere on your hard drive and run FLO.PRG.
- Floppy: boot from Flood_{version}.st (auto-starts from \\AUTO\\FLO.PRG).
"""


def package(version: str = "v1.0"):
    # Ensure fresh build
    subprocess.run(["python3", str(ROOT / "tools" / "build_flood.py")], check=True)
    DIST.mkdir(parents=True, exist_ok=True)

    data_files = sorted(p for p in ORIG_FILES.iterdir() if p.is_file() and p.name not in SKIP_ORIG)
    overlay_files = [OVERLAY / "FLO.PRG", OVERLAY / "AM_MUS.BIN", OVERLAY / "AM_SFX.BIN"]
    for p in overlay_files:
        assert p.exists(), f"Missing built file: {p}"

    readme_txt = make_readme(version)

    # 1. Hard-drive zip
    hd_zip = DIST / f"Flood_hd_{version}.zip"
    with zipfile.ZipFile(hd_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("FLOOD/README.TXT", readme_txt)
        for p in overlay_files + data_files:
            zf.write(p, f"FLOOD/{p.name}")
    print(f"Created {hd_zip} ({hd_zip.stat().st_size:,} B)")

    # 2. Auto-booting 720 KB Atari ST floppy image (.st)
    with tempfile.TemporaryDirectory(prefix="flood_flp_") as td:
        st_img = Path(td) / f"Flood_{version}.st"
        # Create blank 720 KB image (80 tracks, 2 heads, 9 sectors/track = 737,280 B)
        st_img.write_bytes(b"\x00" * (80 * 2 * 9 * 512))
        env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
        subprocess.run(
            ["mformat", "-i", str(st_img), "-f", "720", "-v", "FLOOD_STE", "::"],
            check=True,
            env=env,
        )
        subprocess.run(["mmd", "-i", str(st_img), "::/AUTO"], check=True, env=env)
        # Put FLO.PRG in \AUTO\ so it auto-boots, with data files in root A:\
        subprocess.run(["mcopy", "-i", str(st_img), str(OVERLAY / "FLO.PRG"), "::/AUTO/FLO.PRG"], check=True, env=env)
        for p in [OVERLAY / "AM_MUS.BIN", OVERLAY / "AM_SFX.BIN"] + data_files:
            subprocess.run(["mcopy", "-i", str(st_img), str(p), f"::/{p.name}"], check=True, env=env)

        flp_zip = DIST / f"Flood_floppy_{version}.zip"
        with zipfile.ZipFile(flp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.TXT", readme_txt)
            zf.write(st_img, st_img.name)
        print(f"Created {flp_zip} ({flp_zip.stat().st_size:,} B)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1.0")
    args = ap.parse_args()
    package(args.version)
