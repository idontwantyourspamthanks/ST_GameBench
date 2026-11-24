#!/usr/bin/env python3
"""
Package Overlander STE Enhanced v1.0 into:
  - dist/Overlander_hd_v1.0.zip      (Hard-drive folder: OVERLAND.PRG + G.TOS + LOADSCR.IMG + AM_MUS.BIN + AM_SFX.BIN)
  - dist/Overlander_floppy_v1.0.zip  (Auto-booting 720 KB Atari ST/STE floppy image Overlander_v1.0.st)
"""
import argparse
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OVERLAY = ROOT / "work" / "disk_overlay"
DIST = ROOT / "dist"


def make_readme(version: str) -> str:
    return f"""Overlander — Atari STE Enhanced ({version})
=========================================

Original game: Elite Systems International Ltd. (1988)
Target: 1 MB Atari STE (also runs cleanly on ST, Mega ST, Mega STE, TT, Falcon)

What's new in {version}:
- Unpacked & decrypted from original STX disk (instant floppy & hard-drive loading).
- Relocated all 230 hardcoded low-RAM ($0800-$8440) BSS references and triple
  screen buffers ($068900-$07ffff) into clean GEMDOS BSS — fixes the TOS 1.62+
  Address Error crash on STE/Mega STE/TT/Falcon.
- Removed 24-bit exception-vector hack and replaced all 4 self-modifying code
  sites (3x Timer B loops + sprite Y-scaler) for full 68030 I-cache safety on
  TT and Falcon; added automatic ST Low video mode switch on TT.
- STE Blitter acceleration for sky clear (1-line HOG chunks, zero Timer B
  jitter), parallax mountain horizon strip, and aligned masked sprites
  (automatic CPU fallback on plain ST and TT).
- Fixed 25.0 Hz VBL frame pacing on fast machines (Mega STE 16 MHz, TT 32 MHz,
  Falcon 16 MHz) instead of running 1.8x-2.6x too fast.
- Full Amiga 4-channel stereo audio on STE DMA (12,517 Hz, atomic cursor-tracked
  2,000-byte circular ring buffer — glitch-free at 50 Hz, 60 Hz, and 71 Hz):
  * Authentic Mark Cooksey Amiga music (5 tunes + 7 PCM instruments)
  * Authentic Amiga sampled SFX (engine RPM, gun, explosion, missile, menu)
  * Automatic fallback to original Jas. C. Brooke YM2149 sound on plain ST.

How to run:
- Hard drive: copy the OVERLAND folder anywhere on your hard drive and run OVERLAND.PRG.
- Floppy: boot from Overlander_{version}.st (auto-starts from \\AUTO\\OVERLAND.PRG).
"""


def package(version: str = "v1.0"):
    subprocess.run(["python3", str(ROOT / "tools" / "build_overlander.py")], check=True)
    DIST.mkdir(parents=True, exist_ok=True)

    overlay_files = [
        OVERLAY / "OVERLAND.PRG",
        OVERLAY / "G.TOS",
        OVERLAY / "LOADSCR.IMG",
        OVERLAY / "AM_MUS.BIN",
        OVERLAY / "AM_SFX.BIN",
    ]
    for p in overlay_files:
        assert p.exists(), f"Missing built file: {p}"

    readme_txt = make_readme(version)

    # 1. Hard-drive zip
    hd_zip = DIST / f"Overlander_hd_{version}.zip"
    with zipfile.ZipFile(hd_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("OVERLAND/README.TXT", readme_txt)
        for p in overlay_files:
            zf.write(p, f"OVERLAND/{p.name}")
    print(f"Created {hd_zip} ({hd_zip.stat().st_size:,} B)")

    # 2. Auto-booting 720 KB Atari ST floppy image (.st)
    with tempfile.TemporaryDirectory(prefix="overland_flp_") as td:
        st_img = Path(td) / f"Overlander_{version}.st"
        st_img.write_bytes(b"\x00" * (80 * 2 * 9 * 512))
        env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
        subprocess.run(
            ["mformat", "-i", str(st_img), "-f", "720", "-v", "OVERLAND", "::"],
            check=True,
            env=env,
        )
        subprocess.run(["mmd", "-i", str(st_img), "::/AUTO"], check=True, env=env)
        subprocess.run(
            ["mcopy", "-i", str(st_img), str(OVERLAY / "OVERLAND.PRG"), "::/AUTO/OVERLAND.PRG"],
            check=True,
            env=env,
        )
        for p in overlay_files[1:]:
            subprocess.run(["mcopy", "-i", str(st_img), str(p), f"::/{p.name}"], check=True, env=env)

        flp_zip = DIST / f"Overlander_floppy_{version}.zip"
        with zipfile.ZipFile(flp_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("README.TXT", readme_txt)
            zf.write(st_img, st_img.name)
        print(f"Created {flp_zip} ({flp_zip.stat().st_size:,} B)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v1.0")
    args = ap.parse_args()
    package(args.version)
