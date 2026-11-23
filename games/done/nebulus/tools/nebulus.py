#!/usr/bin/env python3
r"""Nebulus (PP's Gamex hard-disk build) harness: bootable ACSI image + boot_to_game().

Gamex/START.TOS does not run from Hatari's GEMDOS --harddrive drive: it re-runs the hard disk's
root sector to install a private HD driver (see games/done/hunter/work/notes/boot.md ss1).
So this builds a 16 MB FAT16 ACSI image with HDDRIVER's root sector + partition loader (the same
user-supplied files Hunter uses, gamebench/hd/) and autoruns C:\START.TOS.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, 'games/done/nebulus/tools')
    from nebulus import Nebulus
    h = Nebulus(); h.boot_to_game(); h.close()
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

ORIGIN = GAME / "originals/NEBULGX"
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
                    "--offset", str(ps), "-n", "NEBULUS", str(img), str(psz // 2)], check=True, capture_output=True)
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
    tmp = Path(str(img) + ".inf")
    tmp.write_bytes(inf.encode())
    subprocess.run(["mcopy", "-i", tgt, str(tmp), "::DESKTOP.INF"], check=True)
    tmp.unlink()
    return img


class Nebulus(Hatari):
    def __init__(self, snapshot: str | None = None, workdir: str | None = None, machine: str = "ste",
                 tos: Path = TOS["1.62"], memsize_kb: int = 1024, extra: list[str] | None = None,
                 game: Path = ORIGIN, **kw):
        R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
        R.mkdir(parents=True, exist_ok=True)
        build_hd(R / "hd.img", game=game)
        kw.setdefault("overlay", Path("/nonexistent"))
        kw.setdefault("files", [])
        ex = ["--gemdos-drive", "skip", "--acsi", f"0={R / 'hd.img'}"] + (extra or [])
        if "--joy1" not in ex:
            ex += ["--joy1", "keys"]
        super().__init__(game_dir=game, snapshot=snapshot, workdir=str(R), machine=machine, tos=tos,
                         memsize_kb=memsize_kb, autorun="", extra=ex, **kw)

    TITLE_MARK = (0x3D00F, b"Higl")   # "High Scorers" text: the game's own title data is resident in RAM
    TIMER = 0x3AD98                  # hundreds digit * 8; non-zero once a tower runs (400 -> 0x20)
    TOWER = 0x3390C                  # tower index (0 = first)

    def _marker_present(self) -> bool:
        out = self.debug("m $3d00f 4", 0.4)
        return "48 69 67 68" in out.upper()

    def boot_to_title(self, timeout: float = 90.0, shots: Path | None = None, space_until: float = 20.0):
        """Loader screens -> the game's title. Space is pressed while the loader screens are up (only until
        `space_until` s, and only while the RAM marker is absent): spaces during the game's own title leave it
        unable to start a game by fire (measured). The verified run pressed space at 2 s intervals, saw the
        marker at 15 s, then started the tower."""
        if shots:
            shots = Path(shots); shots.mkdir(parents=True, exist_ok=True)
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(2)
            if self._marker_present():
                return True
            if time.time() - t0 < space_until:
                self.keypress(57)
        return False

    def boot_to_game(self, shots: Path | None = None, timeout: float = 90.0, settle: float = 2.0):
        """Cold boot straight into a running tower (verified 3x on STE 1.62 1 MB):
        one space at 16 s, wait for the RAM marker, 2 s, Right 0.5 s (not required), fire (Right Ctrl) 1 s.
        Returns True when the timer word becomes non-zero."""
        if not self.boot_to_title(timeout=timeout, shots=shots):
            return False
        time.sleep(settle)
        self.key("Right", hold=0.5); time.sleep(0.5)
        self.key("Control_R", hold=1.0); time.sleep(4.0)
        if self.peekw(self.TIMER):
            if shots:
                self.shot(str(Path(shots) / "99_tower.png"))
            return True
        return False


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else GAME / "work/shots"
    h = Nebulus()
    try:
        h.boot_to_game(shots=out)
    finally:
        h.close()
