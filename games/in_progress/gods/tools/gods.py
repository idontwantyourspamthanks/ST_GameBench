#!/usr/bin/env python3
r"""Gods (PP's Gamex hard-disk build) harness: bootable ACSI image + helpers.

Gamex/START.TOS requires a real ACSI hard disk (it re-runs the disk's root sector
to install a private HD driver). This builds a 16 MB FAT16 ACSI image with HDDRIVER
from gamebench/hd/ and autoruns C:\START.TOS.
"""
from __future__ import annotations

import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from stharness import Hatari, TOS  # noqa: E402,F401

ORIGIN = GAME / "originals/GODS"
HD_DIR = BENCH / "hd"
HDD_ROOT = HD_DIR / "hddriver_root.bin"
HDD_PBOOT = HD_DIR / "hddriver_pboot.bin"
HDDRIVER_SYS = HD_DIR / "HDDRIVER.SYS"
SKIP = {"work", "tools", "patches", "build", "dist", "README.md", "PLAN.md", ".omp"}


def _fix_sum(sec: bytearray, want: int = 0x1234) -> None:
    sec[510:512] = b"\0\0"
    s = sum(struct.unpack(">256H", bytes(sec))) & 0xFFFF
    struct.pack_into(">H", sec, 510, (want - s) & 0xFFFF)


def build_hd(img: str | Path, game: Path = ORIGIN, size_mb: int = 16,
             autorun: str = "C:\\START.TOS") -> Path:
    """16 MB FAT16 ACSI image, HDDRIVER boot chain, game files in C:\\, DESKTOP.INF autorun."""
    img = Path(img)
    root = bytearray(HDD_ROOT.read_bytes()[:512])
    vpb = bytearray(HDD_PBOOT.read_bytes()[:512])
    with open(img, "wb") as f:
        f.truncate(size_mb * 1024 * 1024)
    total, ps = size_mb * 2048, 2
    psz = total - ps
    subprocess.run(["mkfs.fat", "-F", "16", "-s", "2", "-S", "512", "-R", "1", "-f", "2", "-r", "512",
                    "--offset", str(ps), "-n", "GODS", str(img), str(psz // 2)], check=True, capture_output=True)
    with open(img, "rb") as f:
        f.seek(ps * 512)
        mk = f.read(512)
    root[0x1B6:0x200] = b"\0" * (0x200 - 0x1B6)
    struct.pack_into(">L", root, 0x1C2, total)
    root[0x1C6] = 0x81
    root[0x1C7:0x1CA] = b"BGM"
    struct.pack_into(">LL", root, 0x1CA, ps, psz)
    _fix_sum(root)
    pb = bytearray(vpb)
    pb[3:0x34] = mk[3:0x34]
    _fix_sum(pb)
    with open(img, "r+b") as f:
        f.write(root)
        f.seek(ps * 512)
        f.write(pb)
    tgt = f"{img}@@{ps * 512}"
    subprocess.run(["mcopy", "-i", tgt, str(HDDRIVER_SYS), "::HDDRIVER.SYS"], check=True)
    for p in sorted(Path(game).iterdir()):
        if p.name not in SKIP:
            subprocess.run(["mcopy", "-i", tgt, "-s", "-m", str(p), "::"], check=True)
    inf = ("#a000000\r\n#b000000\r\n#c" + "7" * 65 + "\r\n#d\r\n#E 9B 01\r\n#W 00 00 10 01 4A 16 0F 0A C:\\*.*@\r\n"
           "#M 00 00 00 FF C HARD DISK@ @\r\n#T 00 00 03 FF   TRASH@ @\r\n" f"#Z 01 {autorun}@ @\r\n")
    newdesk = ("#a000000\r\n#b000000\r\n#c7770007000600070055200505552220770557075055507703111103\r\n"
               "#d" + " " * 45 + "\r\n#E 18 03 00 06 43\r\n"
               "#M 00 01 00 FF C HARD DISK@ @ \r\n#T 00 07 02 FF   TRASH@ @ \r\n"
               f"#Z 01 {autorun}@ \r\n")
    tmp = Path(str(img) + ".inf")
    tmp.write_bytes(inf.encode())
    subprocess.run(["mcopy", "-i", tgt, str(tmp), "::DESKTOP.INF"], check=True)
    tmp.write_bytes(newdesk.encode())
    subprocess.run(["mcopy", "-i", tgt, str(tmp), "::NEWDESK.INF"], check=True)
    tmp.unlink()
    return img


class Gods(Hatari):
    def __init__(self, snapshot: str | None = None, workdir: str | None = None, machine: str = "ste",
                 tos: Path = TOS["1.62"], memsize_kb: int = 1024, extra: list[str] | None = None,
                 game: Path = ORIGIN, sound: bool | int = True, **kw):
        R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
        R.mkdir(parents=True, exist_ok=True)
        build_hd(R / "hd.img", game=game)
        kw.setdefault("overlay", Path("/nonexistent"))
        kw.setdefault("files", [])
        ex = ["--gemdos-drive", "skip", "--acsi", f"0={R / 'hd.img'}"] + (extra or [])
        if "--joy1" not in ex:
            ex += ["--joy1", "keys"]
        super().__init__(game_dir=game, snapshot=snapshot, workdir=str(R), machine=machine, tos=tos,
                         memsize_kb=memsize_kb, autorun="", extra=ex, sound=sound, **kw)


if __name__ == "__main__":
    shots = GAME / "work/shots"
    shots.mkdir(parents=True, exist_ok=True)
    h = Gods()
    try:
        for i in range(10):
            time.sleep(3.0)
            h.shot(str(shots / f"acsi_{i:02d}.png"))
            print(f"acsi_{i:02d} VBL={h.vbl()}", flush=True)
            if i == 2:
                h.keypress(57)  # space past Gamex trainer
            elif i == 5:
                h.key("Control_R", hold=0.5)  # fire at title / intro
            elif i == 7:
                h.key("Control_R", hold=0.5)  # fire to start game
    finally:
        h.close()
