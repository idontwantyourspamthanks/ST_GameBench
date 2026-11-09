#!/usr/bin/env python3
r"""Hunter floppy cold-boot cells (Paper Bag base + our patches), on top of tools/stharness.Hatari.  Notes: work/notes/floppy.md.

    python3 tools/huntfloppy.py NAME [--disk1 PATH] [--disk2 PATH] [--machine ste] [--tos 1.62] [--mem 1024]
                                [--drives 2] [--path swap|b|skip] [--play SECONDS] [--peek ADDR:LEN ...] [--shots DIR]

The disks are COPIED to a scratch dir (originals untouched).  `--path` selects the sound-disk behaviour at the prompt:
  swap  one drive: at the prompt drive A is switched to disk 2 (Hatari `--disk-a`), then back to disk 1
  b     two drives: disk 2 goes into drive B before the prompt (no swap)
  skip  SPACE at the prompt (original sound)
  none  no prompt is expected (plain ST, or a lean set without disk 2)
"""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from stharness import Hatari, TOS  # noqa: E402,F401
from hunter import Hunter  # noqa: E402

MARKER, FLAGS = 0x8BFF8, 0x8BFF0


class HunterFloppy(Hunter):
    """Hatari with the floppy set in drive A (and B).  Reuses Hunter's screen gates and state helpers."""

    def __init__(self, disk1: str | Path, disk2: str | Path | None = None, in_b: bool = False, drives: int = 2,
                 machine: str = "ste", tos: Path = TOS["1.62"], memsize_kb: int = 1024, extra: list[str] | None = None,
                 snapshot: str | None = None, workdir: str | None = None, fastfdc: str = "yes"):
        sc = Path(workdir or tempfile.mkdtemp(prefix="hfl-"))
        sc.mkdir(parents=True, exist_ok=True)
        self.d1 = sc / "hunter_d1.st"                    # NOT A.st / B.st (Hatari's bAutoInsertDiskB)
        shutil.copy(disk1, self.d1)
        self.d2 = None
        if disk2:
            self.d2 = sc / "hunter_d2.st"
            shutil.copy(disk2, self.d2)
        empty = sc / "empty"
        empty.mkdir(exist_ok=True)
        ex = ["--disk-a", str(self.d1), "--joy1", "keys", "--fastfdc", fastfdc]
        if in_b and self.d2:
            ex += ["--disk-b", str(self.d2)]
        if drives < 2:
            ex += ["--drive-b", "false"]
        ex += extra or []
        Hatari.__init__(self, game_dir=empty, snapshot=snapshot, workdir=str(sc / "run"), machine=machine, tos=tos,
                        memsize_kb=memsize_kb, autorun="", files=[], overlay=Path("/nonexistent"),
                        flip_reg="($ff8203).b", extra=ex)

    def swap_a(self, path: Path):
        self.cmd(f"hatari-option --disk-a {path}")
        time.sleep(2)

    def marker(self) -> bytes:
        return self.peek(MARKER, 4)

    # ---- the loader screens (core_floppy.s): navy background (0,0,68), white text ------------------------------------
    def _pic(self):
        from PIL import Image
        return Image.open(self.shot()).convert("RGB")

    def on_prompt(self) -> bool:
        im = self._pic().crop((96, 58, 96 + 640, 58 + 400))
        navy = sum(c for c, p in im.getcolors(1 << 20) if p == (0, 0, 68))
        return navy > 0.8 * im.width * im.height

    def head(self) -> bytes:
        """The heading bar rows of the prompt screen (differs between the SOUND and the GAME DISK prompt)."""
        return self._pic().crop((96, 58, 96 + 640, 58 + 70)).tobytes()

    def wait_prompt(self, timeout: float = 90, differs_from: bytes | None = None) -> bool:
        t = time.time()
        while time.time() - t < timeout:
            try:
                if self.on_prompt() and (differs_from is None or self.head() != differs_from):
                    return True
            except Exception:  # noqa: BLE001  (a PNG still being written)
                pass
            time.sleep(1.5)
        return False

    def leave_title(self, blind: bool = False, timeout: float = 240) -> None:
        """The title ignores keys while the game loads from the floppy (30 s even with --fastfdc yes): press SPACE every 5 s
        until MAIN OPTIONS shows (blind: until the screen is no longer the title, judged by 25 s of presses)."""
        t = time.time()
        while time.time() - t < timeout:
            self.key("space", 0.3)
            time.sleep(5)
            if blind:
                if time.time() - t > 45:
                    return
            elif self.at("main"):
                return
        raise RuntimeError("MAIN OPTIONS not reached")

    def boot_floppy(self, path: str = "none", name: str = "bench", blind: bool = False, log=print, shots: Path | None = None,
                    pb_key_at: float = 12) -> bool:
        """Cold boot -> 'Paper Bag presents' key -> (sound disk prompt per `path`) -> title -> menus -> 3D view.
        path: swap | b | skip | none (see the module docstring).  blind: fixed waits instead of the STE reference crops."""
        t0 = time.time()

        def shot(tag):
            if shots:
                shots.mkdir(parents=True, exist_ok=True)
                self.shot(str(shots / f"{tag}.png"))
        if pb_key_at > 0:
            time.sleep(pb_key_at)
        else:                                  # auto: wait for the white 'Paper Bag presents' screen (slow TOS boots: 2.06 + 4 MB, TT, Falcon)
            t = time.time()
            while time.time() - t < 400:
                try:
                    c = self._pic().getcolors(1 << 20)
                    white = sum(n for n, p in c if p == (255, 255, 255))
                    if white > 0.5 * sum(n for n, _p in c):
                        break
                except Exception:  # noqa: BLE001
                    pass
                time.sleep(3)
            time.sleep(3)
            log(f"Paper Bag screen after {time.time() - t0:.0f} s")
        self.keypress(57)
        if path != "none":
            if not self.wait_prompt(90):
                raise RuntimeError("the sound disk prompt did not appear")
            log(f"prompt 1 after {time.time() - t0:.0f} s")
            h1 = self.head()
            shot("prompt1")
            if path == "skip":
                self.keypress(57)
            else:
                if path == "swap":
                    self.swap_a(self.d2)
                self.keypress(28)
                if path == "swap":
                    time.sleep(6)
                    shot("loading")
                    if not self.wait_prompt(60, differs_from=h1):
                        raise RuntimeError("the game disk prompt did not appear")
                    log(f"prompt 2 (game disk) after {time.time() - t0:.0f} s")
                    shot("prompt2")
                    self.keypress(28)            # RETURN without the disk: must be refused
                    time.sleep(4)
                    shot("prompt2_refused")
                    self.swap_a(self.d1)
                    self.keypress(28)
        if blind:
            time.sleep(30)
            self.leave_title(blind=True)
            self.goto(*self.START_XY, home_xy=self.HOME_XY)
            self.click()
            time.sleep(4)
            self.goto(*self.ACTION_XY, home_xy=self.HOME_XY)
            self.click()
            time.sleep(4)
            for c in name:
                self.key(c, 0.15)
                time.sleep(0.3)
            self.click()
            time.sleep(5)
            self.click()
            time.sleep(12)
        else:
            self._stage("title2", False, 22, 150)
            self.leave_title()
            self.goto(*self.START_XY, home_xy=self.HOME_XY)
            self.click()
            self._stage("games", False, 3)
            self.goto(*self.ACTION_XY, home_xy=self.HOME_XY)
            self.click()
            self._stage("name", False, 3)
            for c in name:
                self.key(c, 0.15)
                time.sleep(0.3)
            self.click()
            self._stage("mission", False, 4)
            self.click()
            self._stage("game", False, 9)
            time.sleep(1.0)
        ok = self.in_game()
        log(f"in 3D view: {ok} after {time.time() - t0:.0f} s")
        return ok

    START_PC = 0x6A124                       # HUNTER.TOS' final `jmp $800.w` (the copy that runs at $6a000); our `bsr stage2` is at $6a120

    def at_start(self, cmds: str):
        """Run debugger commands (a script file) the moment the loader is about to jump to the game: all patches are applied."""
        cf = self.R / "start.txt"
        cf.write_text(cmds)
        self.debug("b all", 0.3)
        self.cmd(f"hatari-debug b pc = ${self.START_PC:x} :trace :once :file {cf}")

    def close(self):
        try:
            super().close()
        finally:
            shutil.rmtree(self.d1.parent, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("name")
    ap.add_argument("--disk1", default=str(GAME / "build/floppy/HUNTER_disk1.st"))
    ap.add_argument("--disk2", default=str(GAME / "build/floppy/HUNTER_disk2_sound.st"))
    ap.add_argument("--no-disk2", action="store_true")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--drives", type=int, default=0, help="1 or 2 (default: 1 for swap/skip, 2 for b)")
    ap.add_argument("--path", default="none", choices=["swap", "b", "skip", "none"])
    ap.add_argument("--blind", action="store_true", help="fixed waits (plain ST, TT, Falcon: the reference crops are STE pictures)")
    ap.add_argument("--play", type=float, default=0, help="hold Up+Left this many seconds in the 3D view")
    ap.add_argument("--peek", nargs="*", default=[], help="ADDR:LEN (hex) RAM to print after the boot")
    ap.add_argument("--dump", default=None, help="save RAM $0..$fffff after the boot")
    ap.add_argument("--wav", default=None, help="record this many seconds of sound after the boot into work/snd/NAME.wav")
    ap.add_argument("--shots", default=None)
    ap.add_argument("--bp-save", default=None, help="save RAM $8BA00..$AEFFF to this file when the loader jumps to the game")
    ap.add_argument("--bp-load", default=None, help="load this file to $8BA00 at that moment (free-RAM poison pattern)")
    ap.add_argument("--fastfdc", default="no", help="Hatari --fastfdc yes|no (default no: real floppy timing)")
    ap.add_argument("--pb-at", type=float, default=12, help="seconds after power-on when the 'Paper Bag presents' key is pressed (TOS 2.06 + 4 MB: ~120)")
    a = ap.parse_args()
    sc = {}
    if a.wav:
        sys.path.insert(0, str(HERE))
        import os
        import snd_test
        snd_test.setup_home()
        os.environ["HOME"] = str(snd_test.HOME)
        os.environ["SDL_AUDIODRIVER"] = "dummy"
    drives = a.drives or (2 if a.path == "b" else 1)
    d2 = None if a.no_disk2 else a.disk2
    ex = ["--sound", "50066"] if a.wav else []
    h = HunterFloppy(a.disk1, d2, in_b=(a.path == "b"), drives=drives, machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=ex, fastfdc=a.fastfdc)
    stage = h._stage
    h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
    shots = Path(a.shots) if a.shots else None
    rc = 1
    try:
        if a.bp_save or a.bp_load:
            cmds = ""
            if a.bp_save:
                cmds += f"savebin {Path(a.bp_save).resolve()} $8ba00 $23600\n"
            if a.bp_load:
                shutil.copy(a.bp_load, h.R / "pat.bin")
                cmds += f"loadbin {h.R / 'pat.bin'} $8ba00\n"
            h.at_start(cmds)
        ok = h.boot_floppy(a.path, blind=a.blind, shots=shots, pb_key_at=a.pb_at)
        mk, fl = h.peek(MARKER, 4), h.peek(FLAGS, 4)
        print(f"BOOT {'OK' if ok else 'FAILED'} cell={a.name} machine={a.machine} tos={a.tos} mem={a.mem}K path={a.path} drives={drives} "
              f"in_game={ok} MARKER={mk!r} FLAGS={fl.hex()} fps={h.fps(250)['fps']:.2f}")
        for pk in a.peek:
            ad, _, n = pk.partition(":")
            print(f"  peek ${int(ad, 16):x}: {h.peek(int(ad, 16), int(n or 8)).hex()}")
        if a.play:
            h.hold("Up", "Left")
            time.sleep(a.play)
            h.release("Up", "Left")
        if a.wav:
            import snd_test
            sv = snd_test.pk(h, snd_test.SV, 8)
            print(f"  payload mode={sv[0]} (2 = DMA sound, 1 = original YM) in3d={sv[1]} dma_on={sv[2]}")
            if snd_test.CAP.exists():
                snd_test.CAP.unlink()
            h.cmd("hatari-shortcut recsound")
            t0 = time.time()
            time.sleep(0.5)
            snd_test.inject(h, 3, 1, 12)
            while time.time() - t0 < float(a.wav):
                time.sleep(0.1)
            h.cmd("hatari-shortcut recsound")
            time.sleep(1.0)
            out = GAME / "build" / "wav" / f"{a.name}.wav"      # build/ is git-ignored (Amiga sample material: never commit)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(snd_test.CAP, out)
            x, sr = snd_test.load_wav(out)
            print(f"  wrote {out}: {len(x) / sr:.1f} s, rms {x.std():.0f}, peak {abs(x).max():.0f}")
        if a.dump:
            Path(a.dump).parent.mkdir(parents=True, exist_ok=True)
            h.dump(a.dump, 0, 0x100000)
            print(f"  dumped RAM $0..$fffff to {a.dump}")
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            h.shot(str(shots / "final.png"))
        rc = 0 if ok else 1
    except Exception as e:  # noqa: BLE001
        print(f"BOOT FAILED cell={a.name}: {e!r}")
        if shots:
            try:
                shots.mkdir(parents=True, exist_ok=True)
                h.shot(str(shots / "fail.png"))
            except Exception:  # noqa: BLE001
                pass
    finally:
        h.close()
    return rc




def poison(manifest: Path, pre: Path, out: Path) -> None:
    """Write the poison pattern: the RAM $8BA00..$AEFFF as the loader left it (pre), with every byte that is neither payload,
    nor payload state, nor the sample bank replaced by a non-zero position dependent pattern (huntpatch.fill_byte)."""
    import json
    sys.path.insert(0, str(HERE))
    import huntpatch
    man = json.loads(manifest.read_text())
    img = bytearray(pre.read_bytes())
    used = [(a, b) for a, b in man["used"]]
    if man.get("bank"):
        used.append((man["bank"][0], man["bank"][0] + man["bank"][1]))
    free = 0
    for a in range(huntpatch.IMG_BASE, huntpatch.IMG_END):
        if not any(u0 <= a < u1 for u0, u1 in used):
            img[a - huntpatch.IMG_BASE] = huntpatch.fill_byte(a)
            free += 1
    out.write_bytes(bytes(img))
    print(f"pattern {out}: {free} free bytes of {huntpatch.IMG_END - huntpatch.IMG_BASE} poisoned")


def poison_check(manifest: Path, dump: Path) -> int:
    import json
    sys.path.insert(0, str(HERE))
    import huntpatch
    man = json.loads(manifest.read_text())
    d = dump.read_bytes()
    used = [(a, b) for a, b in man["used"]]
    if man.get("bank"):
        used.append((man["bank"][0], man["bank"][0] + man["bank"][1]))
    bad, free = [], 0
    for a in range(huntpatch.IMG_BASE, huntpatch.IMG_END):
        if any(u0 <= a < u1 for u0, u1 in used):
            continue
        free += 1
        if d[a] != huntpatch.fill_byte(a):
            bad.append(a)
    print(f"poison check {dump.name}: {free} pattern bytes in $8BA00..$AEFFF, {len(bad)} changed" + (f" (first ${bad[0]:x})" if bad else ""))
    nz = sum(1 for a in range(0xB8200, 0xC0000) if d[a])
    print(f"  $B8200..$BFFFF non-zero bytes: {nz}")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "poison":
        poison(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] == "poison-check":
        sys.exit(poison_check(Path(sys.argv[2]), Path(sys.argv[3])))
    sys.exit(main())
