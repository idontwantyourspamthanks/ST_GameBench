#!/usr/bin/env python3
r"""Hunter (Activision 1991, PP's 2010 Gamex hard-disk version) navigation + state access on top of tools/stharness.Hatari.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<gamebench>/games/done/hunter/tools')
    from hunter import Hunter
    h = Hunter()                        # cold boot, 1 MB STE, TOS 1.62, ACSI image + HDDRIVER boot, autoruns C:\START.TOS
    h.boot_to_game()                    # HW screen -> title pictures -> menus -> Action -> name -> in the 3D view
    h.savemem(path); h.close()
    h = Hunter(snapshot=path)           # restore (the scratch HD image is rebuilt in the new scratch dir)

WHY AN IMAGE (work/notes/boot.md): START.TOS does not work from a GEMDOS-HD (Hatari --harddrive) drive. It re-runs the
boot sector of the hard disk (root sector sum $1234) to install a private copy of the HD driver, and the game then reads
\FILES\0..F through its own FAT code on drive 2. So this class builds a 16 MB FAT16 ACSI image in the scratch dir:
  * root sector  = the boot code of an HDDRIVER-formatted disk (gamebench/hd/hddriver_root.bin) + our partition table,
  * partition boot sector = HDDRIVER's partition boot loader (gamebench/hd/hddriver_pboot.bin) + our BPB,
  * C:\HDDRIVER.SYS = gamebench/hd/HDDRIVER.SYS (tested: V10.15), the game files, and a DESKTOP.INF that autoruns C:\START.TOS.
  The three driver files are user-supplied (see gamebench/hd/README.md).
"""
from __future__ import annotations

import fcntl
import re
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

REF = GAME / "work" / "ref"
SNAP = GAME / "work" / "snapshots"
HD_DIR = BENCH / "hd"                                 # user-supplied HDDRIVER files (git-ignored), see hd/README.md
HDD_ROOT = HD_DIR / "hddriver_root.bin"
HDD_PBOOT = HD_DIR / "hddriver_pboot.bin"
HDDRIVER_SYS = HD_DIR / "HDDRIVER.SYS"
SKIP = {"work", "tools", "patches", "README.md", "PLAN.md", ".omp", "alt", "build", "dist"}   # not game files


def _fix_sum(sec: bytearray, want: int = 0x1234) -> None:
    sec[510:512] = b"\0\0"
    s = sum(struct.unpack(">256H", bytes(sec))) & 0xFFFF
    struct.pack_into(">H", sec, 510, (want - s) & 0xFFFF)


def build_hd(img: str | Path, game: Path = GAME, size_mb: int = 16, autorun: str = "C:\\START.TOS") -> Path:
    """Create the bootable ACSI hard-disk image `img` (see module docstring). ~1 s."""
    img = Path(img)
    root = bytearray(HDD_ROOT.read_bytes()[:512])
    vpb = HDD_PBOOT.read_bytes()[:512]
    with open(img, "wb") as f:
        f.truncate(size_mb * 1024 * 1024)
    total, ps = size_mb * 2048, 2
    psz = total - ps
    subprocess.run(["mkfs.fat", "-F", "16", "-s", "2", "-S", "512", "-R", "1", "-f", "2", "-r", "512", "--offset", str(ps),
                    "-n", "HUNTER", str(img), str(psz // 2)], check=True, capture_output=True)
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
    pb[3:0x34] = mk[3:0x34]                           # keep the HDDRIVER loader code from $34, take our BPB
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


class Hunter(Hatari):
    def __init__(self, snapshot: str | None = None, workdir: str | None = None, machine: str = "ste",
                 tos: Path = TOS["1.62"], memsize_kb: int = 1024, extra: list[str] | None = None,
                 bus: str | None = None, ttram_mb: int = 0, **kw):
        R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
        R.mkdir(parents=True, exist_ok=True)
        build_hd(R / "hd.img")
        kw.setdefault("overlay", Path("/nonexistent"))
        kw.setdefault("flip_reg", "($ff8203).b")        # the game flips between buffers that differ only in the mid byte
        kw.setdefault("files", [])                       # drive C of Hatari's GEMDOS emulation stays empty (and unmapped)
        # bus: where the HD image sits. acsi = ST/STE/Mega STE/TT (default); ide = Falcon (TOS 4.04 only boots IDE/SCSI,
        # not ACSI; default there); scsi = TT/Falcon SCSI (id 0).  See work/notes/ttfalcon.md.
        bus = bus or ("ide" if machine == "falcon" else "acsi")
        hd = {"acsi": ["--acsi", f"0={R / 'hd.img'}"], "scsi": ["--scsi", f"0={R / 'hd.img'}"],
              "ide": ["--ide-master", str(R / "hd.img")]}[bus]
        ex = ["--gemdos-drive", "skip"] + hd + (["--ttram", str(ttram_mb)] if ttram_mb else []) + (extra or [])
        if "--joy1" not in ex:
            # Without this the game sees a phantom joystick (it drives the boat/character on its own, ~100 units/s).
            # With 'keys' the cursor keys are joystick 1 (fire = Hatari's keyboard fire key).
            ex += ["--joy1", "keys"]
        super().__init__(game_dir=GAME, snapshot=snapshot, workdir=str(R), machine=machine, tos=tos,
                         memsize_kb=memsize_kb, autorun="", extra=ex, **kw)

    def savemem(self, out: str):
        """Hatari writes every memstate save to the shared /tmp/hatari.sav, so serialise concurrent savers.
        The saved state embeds this scratch dir (HD image path); Hunter(snapshot=) retargets it on restore."""
        with open("/tmp/hatari-savemem.lock", "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            super().savemem(out)

    # ---- navigation (see work/notes/boot.md) --------------------------------------------------------
    # Screens: (name, box in 832x588 screenshot coords). Reference crops are in work/ref/<name>.png.
    STAGES = {
        "hw":       (96, 52, 600, 82),      # HW-detect text screen ("Press U for unlimited stamina")
        "title1":   (320, 405, 505, 445),   # first picture (HUNTER / ACTIVISION photo)
        "title2":   (200, 85, 640, 170),    # animated title: static HUNTER logo (the side icons animate)
        "main":     (270, 135, 565, 300),   # MAIN OPTIONS menu
        "games":    (270, 135, 565, 300),   # AVAILABLE GAMES menu (Hunter / Missions / Action / CANCEL)
        "name":     (90, 52, 320, 82),      # "Please type in name-"
        "mission":  (330, 195, 510, 225),   # "MISSION 1 OBJECTIVE" header
        "game":     (470, 340, 740, 418),   # right half of the HUD of the 3D view (LIFE gauge, weapon, CREDITS, FUEL)
    }
    HOME_XY = (100, 66)                      # where home() leaves the game pointer (menus)
    START_XY, ACTION_XY = (415, 217), (415, 249)

    TOL = {"game": 4.0}                      # mean abs RGB difference allowed; default 1.5 (screens are static)

    def at(self, stage: str) -> bool:
        return self.screen_matches(REF / f"{stage}.png", self.STAGES[stage], tol=self.TOL.get(stage, 1.5))

    def wait_stage(self, stage: str, timeout: float = 120, poll: float = 2.0) -> bool:
        t = time.time()
        while time.time() - t < timeout:
            if self.at(stage):
                return True
            time.sleep(poll)
        return False

    def save_ref(self, stage: str):
        """Crop the current screenshot to the stage's box and store it as the reference image."""
        from PIL import Image
        REF.mkdir(parents=True, exist_ok=True)
        Image.open(self.shot()).convert("RGB").crop(self.STAGES[stage]).save(REF / f"{stage}.png")

    def _stage(self, stage: str, record, wait: float, timeout: float = 120):
        """record: True (all stages), or a set of stage names to (re)record; the others are gated on their crops."""
        if record is True or (record and stage in record):
            time.sleep(wait)
            self.save_ref(stage)
        elif not self.wait_stage(stage, timeout):
            raise RuntimeError(f"screen '{stage}' not reached (RAM word $5ff2 irrelevant; see shot)")

    def boot_to_game(self, name: str = "bench", record=False, dump_dir: str | None = None) -> bool:
        """Cold boot -> HW screen -> picture -> animated title -> MAIN OPTIONS -> Start new game -> Action -> name ->
        mission page -> 3D view (on foot at the HQ, nothing pressed). Each screen is gated on its reference crop
        (work/ref/<stage>.png); record=True instead sleeps fixed times and (re)writes the crops.
        Input rules (work/notes/boot.md): the loader (START.TOS) takes Hatari scancode events; once the game runs its own
        keyboard interrupt, `hatari-event keypress` hangs it ($afe6 loop), so use xdotool keys (self.key) from the title on."""
        def dump(tag):
            if dump_dir:
                Path(dump_dir).mkdir(parents=True, exist_ok=True)
                self.dump(f"{dump_dir}/ram_{tag}.bin", 0, 0x100000)

        self._stage("hw", record, 12, 90)
        dump("hw")
        self.keypress(57)                                   # skips the ~25 s countdown; no key = default settings
        self._stage("title1", record, 6)
        self.keypress(57)                                   # loader's "press a key"; the game is loaded next (~15 s)
        self._stage("title2", record, 22, 150)
        time.sleep(1.5)
        dump("title2")
        self.key("space", 0.3)
        self._stage("main", record, 3)
        dump("main")
        self.goto(*self.START_XY, home_xy=self.HOME_XY)
        self.click()
        self._stage("games", record, 3)
        self.goto(*self.ACTION_XY, home_xy=self.HOME_XY)
        self.click()
        self._stage("name", record, 3)
        for c in name:
            self.key(c, 0.15)
            time.sleep(0.3)
        self.click()                                        # click accepts the name
        self._stage("mission", record, 4)
        dump("mission")
        self.click()                                        # click again: into the world
        self._stage("game", record, 9)
        time.sleep(1.0)
        dump("game")
        if not self.in_game():
            raise RuntimeError("HUD matched but the 3D loop is not running (RAM $899 bit 7 / flips)")
        return True

    # ---- game state (RAM; see work/notes/frameloop.md) ------------------------------------------------
    A5 = 0x806                              # the game keeps its variables at (a5) = $806
    MODE = 0x899                            # byte = $93(a5): bit 7 set while the 3D view loop runs, 0 on every menu screen
    POS_X, POS_Z = 0xAB2, 0xAB6             # words: player world position; HUD X = (word & $ffff)>>8, HUD Y = Z>>8

    def peek(self, addr: int, n: int) -> bytes:
        """n bytes at addr via the debugger `m` command."""
        out = self.debug(f"m ${addr:x} {n}", 0.5)
        m = re.findall(rf"{addr:08X}:\s+((?:[0-9a-f]{{2}} ?)+)", out, re.I)
        if not m:
            raise RuntimeError(f"short read at {addr:#x}: {out!r}")
        return bytes(int(x, 16) for x in m[-1].split())[:n]

    def in_game(self, flips: int = 50) -> bool:
        """3D view running: $899 bit 7 set in at least 2 of 3 samples (the render briefly clears it) and the screen flips."""
        hits = sum(1 for _ in range(3) if self.peek(self.MODE, 1)[0] & 0x80)
        return hits >= 2 and self.fps(flips)["flips"] > 0

    # ---- input helpers ---------------------------------------------------------------------------------
    # Joystick = Hatari "keys" mode: cursor keys. A snapshot does NOT keep a held key: after a restore the stick is released.
    def hold(self, *keys: str):
        for k in keys:
            self._xdo("keydown", "--window", self.win, k)

    def release(self, *keys: str):
        for k in keys:
            self._xdo("keyup", "--window", self.win, k)

    # ---- measurements ----------------------------------------------------------------------------------
    FLIP_PC = 0x5FEE        # `move.b d1,$203(a6)` in the flip routine $5fd2: writes $ff8203 once per presented frame
    PLAYER = 0xAB2          # player object: words X, height, Z at +0 (record stride $a0; see work/notes/frameloop.md)

    def profile_cc(self, vbls: int = 250, top: int = 20000) -> dict[int, tuple[int, int]]:
        """CPU profile over ~vbls VBLs: {addr: (cycles, executions)} (Hatari `profile cycles` + `profile counts`)."""
        end = self.R / "prof_end.txt"
        end.write_text(f"profile cycles {top}\nprofile counts {top}\n")
        start = self._arm_vbl(vbls + 25, f" :file {end}")
        time.sleep(0.3)
        self.cmd("hatari-debug profile on")
        out = self._wait_removed(start)
        a, _, b = out.partition("> profile counts")
        cyc = {int(x, 16): int(c) for x, c in re.findall(r"^0x([0-9a-f]+)\s+[\d.]+%\s+(\d+)", a, re.M)}
        cnt = {int(x, 16): int(c) for x, c in re.findall(r"^0x([0-9a-f]+)\s+[\d.]+%\s+(\d+)", b, re.M)}
        return {x: (cyc.get(x, 0), cnt.get(x, 0)) for x in set(cyc) | set(cnt)}

    def site_trace(self, sites: list[int], vbls: int = 300, regions: tuple = ()) -> list[tuple]:
        """Breakpoint at each PC in `sites`; at each hit log (pc, CycleCounter, VBL, [bytes per region]) in execution order.
        The difference between consecutive hits is the cost of the code between the two sites (calls included)."""
        cf = self.R / "strace.txt"
        cf.write_text("e CycleCounter\ne VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in regions))
        self.debug("b all", 0.3)
        for s in sites:
            self.cmd(f"hatari-debug b pc = ${s:x} :trace :file {cf}")
            time.sleep(0.15)
        start = self._arm_vbl(vbls)
        out = self._wait_removed(start, timeout=600)
        self.debug("b all", 0.3)
        rows = []
        for blk in out.split("CPU breakpoint condition(s) matched")[1:]:
            pcm = re.search(r"pc = \$([0-9a-f]+)", blk)
            nums = re.findall(r"#(\d+) \(dec\)", blk)
            if pcm and len(nums) >= 2:
                mem = []
                for a, n in regions:
                    bs: list[int] = []
                    for ln in blk.splitlines():
                        m = re.match(r"([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", ln)
                        if m and a <= int(m.group(1), 16) < a + n:
                            bs += [int(x, 16) for x in m.group(2).split()]
                    mem.append(bytes(bs[:n]))
                rows.append((int(pcm.group(1), 16), int(nums[0]), int(nums[1]), mem))
        return rows
