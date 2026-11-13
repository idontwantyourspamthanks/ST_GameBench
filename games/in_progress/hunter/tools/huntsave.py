#!/usr/bin/env python3
r"""Hunter HD in-game Save / Load gates (patches sav_hook + sav_open; note work/notes/save.md).

    python3 tools/huntsave.py roundtrip   [--game build/sav_game] [--machine ste] [--mem 1024] [--slot 2]
    python3 tools/huntsave.py persist     [...]            save, cold boot the same disk image, load
    python3 tools/huntsave.py slots       [...]            several slots, overwrite, names, files on the disk
    python3 tools/huntsave.py errors      [...]            damaged / short / missing slot, read-only slot, full disk, Init Disk
    python3 tools/huntsave.py floppy      [--floppy-img FILE]   the floppy build: Save then Load through the cracker's loader

Every command cold-boots the HD build (or the floppy) in Hatari, drives the game's own menus (ESC -> Disk Operation -> Save/Load) with the mouse
and compares RAM dumps / the files on the disk image.  The disk image is read on the host with mtools (HDDRIVER writes back within ~10 s).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import struct
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
import hunter  # noqa: E402
from hunter import Hunter, TOS, build_hd  # noqa: E402
from huntfloppy import HunterFloppy  # noqa: E402

SLOTLEN, DIRLEN = 51328, 224
PART_OFF = 1024                           # the HD image's first partition (tools/hunter.py build_hd: 2 sectors)
# RAM the game saves into a slot (work/notes/save.md section 3): (address, length) from $10404 / $104dc, plus the world block ($7fe4 points at it)
SRC = [(0x8EFE, 0xAF), (0x8246, 0x20), (0xCDE8, 0x176), (0x8CE8, 0xC0), (0x9AB4, 0x3C0), (0x8266, 0x10)]
SLOT_OFF = {0x8EFE: 0x40, 0x8246: 0x240, 0xCDE8: 0x320, 0x8CE8: 0x260, 0x9AB4: 0x4BE, 0x8266: 0x4AC}   # offsets inside the slot file ($496 + $28 / $16: the second block's base is a4+$496, $10390)
WORLD_OFF, WORLD_LEN = 0x87E, 0xC000


def sh(*a, **k):
    return subprocess.run(list(map(str, a)), capture_output=True, text=True, **k)


def fsck_part(img: Path) -> tuple[bool, str]:
    """fsck.fat on the image's first partition (fsck.fat here has no --offset): copy it out and check it read-only.
    Returns (no errors, the summary line).  The only message the image always has is the volume label copied by HDDRIVER
    from the root directory (rc 1 for that alone), which is not a filesystem error."""
    part = Path(str(img) + ".part")
    part.write_bytes(img.read_bytes()[PART_OFF:])
    r = sh("fsck.fat", "-n", part)
    part.unlink(missing_ok=True)
    lines = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip()]
    bad = [ln for ln in lines if re.search(r"error|damaged|corrupt|orphan|differ|contains|bad", ln, re.I)
           and "volume label" not in ln.lower()]
    return not bad, (lines[-1] if lines else "")


class Menus:
    """Mixin: drive the game's disk menus (ESC -> Disk Operation -> Load / Save) with the mouse; used by the HD and the floppy rig."""
    ITEM_Y = [153, 185, 217, 249, 281, 313, 345, 377]       # menu rows in 832x588 screenshot coordinates (boxes are 32 px apart)
    tt = False

    def _hash(self):
        return hashlib.md5(Path(self.shot()).read_bytes()).hexdigest()

    def item(self, i: int, wait: float = 2.5, tries: int = 4):
        """Click row i of the game's current menu (0 = title); repeat until the screen changes."""
        before = self._hash()
        for _ in range(tries):
            x, y = 415, self.ITEM_Y[i] + 9
            if self.tt:
                x, y = x - 96, y - 58
            self.goto(x, y, home_xy=(self.HOME_XY[0] - (96 if self.tt else 0), self.HOME_XY[1] - (58 if self.tt else 0)))
            time.sleep(0.4)
            self.click()
            time.sleep(wait)
            if self._hash() != before:
                return
        raise RuntimeError(f"menu row {i}: the screen did not change")

    def menu_disk(self):
        """3D view -> ESC menu -> Disk Operation (the 'DISK OPTIONS' box)."""
        self.key("Escape", 0.2)
        time.sleep(2.5)
        self.item(3)

    def open_list(self, kind: str):
        self.menu_disk()
        self.item(2 if kind == "save" else 1, 3)

    def type_name(self, name: str, backspaces: int = 0):
        for _ in range(backspaces):
            self.key("BackSpace", 0.15)
            time.sleep(0.3)
        for c in name:
            self.key(c, 0.15)
            time.sleep(0.3)

    def slot_name(self, slot: int) -> str:
        """The name the game shows for slot 1..6: its own directory buffer ($7f54 -> $21a94, entry $20*slot, name at +$10)."""
        return self.peek(0x21A94 + 0x20 * slot + 0x10, 16).split(b"*")[0].decode("latin1")

    def save(self, slot: int, name: str, dump: Path | None = None) -> tuple:
        """slot 1..6.  The name field starts with the slot's old name: exactly that many backspaces empty it."""
        self.open_list("save")
        self.item(slot, 2.5)
        self.type_name(name, len(self.slot_name(slot)))
        if dump:
            self.dump(str(dump), 0, 0x100000)
            time.sleep(0.5)
        pos = (self.peekw(self.POS_X), self.peekw(self.POS_Z))
        self.key("Return", 0.2)
        time.sleep(6)                       # the save itself (a restored snapshot is already in the 3D view: wait_game is instant)
        self.wait_game(20)
        return pos

    def load(self, slot: int, dump: Path | None = None, snap: str | None = None) -> tuple:
        """Load slot 1..6; ends on the mission page (dump taken there), then clicks into the world (position returned)."""
        self.open_list("load")
        if snap:
            self.snap(snap)
        self.item(slot, 4)
        self.snap(f"load_slot{slot}")
        time.sleep(1.0)
        if dump:
            self.dump(str(dump), 0, 0x100000)
            time.sleep(0.5)
        self.click()
        self.wait_game(20)
        time.sleep(1.0)
        return (self.peekw(self.POS_X), self.peekw(self.POS_Z))

    def snap(self, name: str) -> Path:
        out = GAME / "work" / "shots" / f"save_{name}.png"
        shutil.copy(self.shot(), out)
        return out

    def back_to_game(self, tries: int = 5):
        """Leave whatever menu the last action left on screen (ESC out of the pause/disk menu) until the 3D view runs."""
        for _ in range(tries):
            if self.peek(self.MODE, 1)[0] & 0x80:
                return
            self.key("Escape", 0.2)
            time.sleep(2.5)
        if not self.peek(self.MODE, 1)[0] & 0x80:
            raise RuntimeError("could not get back to the 3D view")

    def wait_game(self, timeout: float = 20):
        t = time.time()
        while time.time() - t < timeout:
            try:
                if self.peek(self.MODE, 1)[0] & 0x80:
                    return
            except RuntimeError:
                pass
            time.sleep(1)
        raise RuntimeError("the 3D view did not come back")

    def walk(self, secs: float, *keys: str):
        self.hold(*(keys or ("Up",)))
        time.sleep(secs)
        self.release(*(keys or ("Up",)))
        time.sleep(0.5)


class Rig(Menus, Hunter):
    """Hunter HD build (ACSI image + HDDRIVER, tools/hunter.py) with the disk-menu helpers."""

    def __init__(self, game="build/sav_game", image: str | None = None, games_image: bool = False, **kw):
        g = (GAME / game).resolve()
        orig = hunter.build_hd

        def mk(img, **k):
            if image:
                shutil.copy(image, img)              # an existing image (a saved game, the all-games image)
            else:
                orig(img, game=g, **k)
        hunter.build_hd = mk
        try:
            Hunter.__init__(self, **kw)
        finally:
            hunter.build_hd = orig
        self.img = self.R / "hd.img"
        self.tt = kw.get("machine") == "tt"

    # ---- the disk image ----
    def flushed(self, name: str = "SAVES.DIR", timeout: float = 60) -> bool:
        """HDDRIVER writes back lazily: wait until the file can be read from the image."""
        t = time.time()
        probe = Path("/tmp/hsv_probe")
        while time.time() - t < timeout:
            probe.unlink(missing_ok=True)
            if sh("mcopy", "-i", f"{self.img}@@{PART_OFF}", f"::FILES/{name}", probe).returncode == 0 and \
                    fsck_part(self.img)[0]:
                return True
            time.sleep(3)
        return False

    def get(self, name: str, out: Path | None = None) -> bytes | None:
        out = out or Path(f"/tmp/hsv_{self.img.parent.name}_{name}")
        out.unlink(missing_ok=True)
        r = sh("mcopy", "-i", f"{self.img}@@{PART_OFF}", f"::FILES/{name}", out)
        return out.read_bytes() if r.returncode == 0 else None


def sum_ok(slot: bytes) -> bool:
    w = list(struct.unpack(f">{len(slot) // 2}H", slot))
    tw = w[0x3E // 2]
    w[0x3E // 2] = 0xB241
    return (0x1B0 + sum(w)) & 0xFFFF == tw


def ranges(ram: bytes):
    wp = struct.unpack(">I", ram[0x7FE4:0x7FE8])[0]
    return [(a, n) for a, n in SRC] + [(wp, WORLD_LEN)]


def cmp_ranges(a: bytes, b: bytes, what: str) -> bool:
    ok = True
    for ad, n in ranges(a):
        eq = a[ad:ad + n] == b[ad:ad + n]
        nd = sum(1 for i in range(n) if a[ad + i] != b[ad + i])
        print(f"  {what} ${ad:05x}+{n:<6d} {'equal' if eq else f'DIFFERS in {nd} bytes'}")
        ok &= eq
    return ok


def file_vs_ram(slot: bytes, ram: bytes, what: str) -> bool:
    ok = True
    for ad, n in SRC:
        o = SLOT_OFF[ad]
        eq = slot[o:o + n] == ram[ad:ad + n]
        print(f"  {what}: slot file +${o:x}+{n:x} vs RAM ${ad:x}: {'equal' if eq else 'DIFFERS'}")
        ok &= eq
    wp = struct.unpack(">I", ram[0x7FE4:0x7FE8])[0]
    eq = slot[WORLD_OFF:WORLD_OFF + WORLD_LEN] == ram[wp:wp + WORLD_LEN]
    print(f"  {what}: slot file +${WORLD_OFF:x}+${WORLD_LEN:x} vs RAM ${wp:x}: {'equal' if eq else 'DIFFERS'}")
    return ok and eq


def state(h: Rig) -> tuple:
    return (h.peekw(h.POS_X), h.peekw(h.POS_Z))


def rig(a, **kw) -> Rig:
    extra = (["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"] if a.machine == "tt" else [])
    return Rig(game=a.game, machine=a.machine, tos=TOS[a.tos or {"ste": "1.62", "st": "1.04", "megaste": "2.06", "tt": "3.06", "megast": "1.04"}[a.machine]],
               memsize_kb=a.mem, extra=extra, **kw)


def boot(a, **kw) -> Rig:
    h = rig(a, **kw)
    h.STAGES = dict(h.STAGES)
    stage = h._stage
    h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
    h.boot_to_game()
    return h


def parse_dir(b: bytes):
    """(used, name) for the 6 entries of a 224-byte directory file ($ff in byte 0 = free)."""
    out = []
    for k in range(6):
        e = b[0x20 + 0x20 * k:0x40 + 0x20 * k]
        out.append((e[0] < 0x80, e[0x10:].split(b"*")[0].decode("latin1")))
    return out


def pos_of(r: bytes):
    return struct.unpack(">H", r[0xAB2:0xAB4])[0], struct.unpack(">H", r[0xAB6:0xAB8])[0]


def settle_and_close(h, secs: float = 15) -> Path:
    """HDDRIVER writes back lazily, and mtools on a live image can see a half-written directory.  So: give the driver time,
    copy the image, and accept the copy only when fsck finds it consistent; in the worst case fall back to closing first and
    taking the image as it is.  The returned path is a finished image, and the emulator is closed either way."""
    img = h.img
    for wait in (max(secs, 15), 15, 20):
        time.sleep(wait)
        copy = Path(str(img) + f".snap{int(time.time())}")
        shutil.copy(img, copy)
        good, _msg = fsck_part(copy)
        if good and any(read_file(copy, n) is not None for n in ("SAVES.DIR", "SLOT1.SAV", "SLOT2.SAV", "SLOT3.SAV")):
            h.close()
            return copy
        copy.unlink(missing_ok=True)
    h.close()
    return img


def read_file(img: Path, name: str) -> bytes | None:
    out = Path(f"/tmp/hsv_read_{os.getpid()}")
    out.unlink(missing_ok=True)
    r = sh("mcopy", "-i", f"{img}@@{PART_OFF}", f"::FILES/{name}", out)
    return out.read_bytes() if r.returncode == 0 else None


def cmd_roundtrip(a) -> int:
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    h = boot(a)
    img = None
    try:
        print("marker", h.peek(0x8BFF8, 4), "site $d542", h.peek(0xD542, 6).hex(), "site $c0268", h.peek(0xC0268, 8).hex())
        h.walk(2.5, "Up")
        s0 = h.save(a.slot, "rt", d / "A.bin")
        h.walk(4, "Up", "Left")
        s1 = state(h)
        sb = h.load(a.slot, d / "B.bin")
        print("player at the save", pos_of((d / "A.bin").read_bytes()), "| moved to", s1, "| after the load, 3D view running", sb)
        ok = s1 != s0 and sb == pos_of((d / "A.bin").read_bytes())
    finally:
        img = settle_and_close(h) if h.proc.poll() is None else h.img
    A, B = (d / "A.bin").read_bytes(), (d / "B.bin").read_bytes()
    ok &= cmp_ranges(A, B, "RAM save-time vs RAM after-load")
    slot = read_file(img, "SLOT%d.SAV" % a.slot)
    print("slot file on the disk image:", None if slot is None else (len(slot), "game checksum ok" if sum_ok(slot) else "CHECKSUM BAD"))
    ok &= slot is not None and len(slot) == SLOTLEN and sum_ok(slot)
    if slot:
        ok &= file_vs_ram(slot, A, "save-time RAM")
    print("  filesystem:", fsck_part(img), "| SAVES.DIR", None if read_file(img, "SAVES.DIR") is None else parse_dir(read_file(img, "SAVES.DIR")))
    diff = [i for i in range(0x806, 0x12004) if A[i] != B[i]]
    print(f"  (info) $806..$12003: {len(diff)} bytes differ between the two dumps (menu vs mission page state, timers)")
    shutil.copy(img, d / "after_roundtrip.img")
    print("ROUNDTRIP", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_persist(a) -> int:
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    h = boot(a)
    try:
        h.walk(2, "Up")
        h.save(3, "persist", d / "A.bin")
    finally:
        img = settle_and_close(h)
    shutil.copy(img, d / "persist.img")
    print("first session closed; the disk image is", d / "persist.img")
    print("  filesystem:", fsck_part(img), "| SAVES.DIR", parse_dir(read_file(img, "SAVES.DIR")))
    h = boot(a, image=str(d / "persist.img"))
    try:
        h.open_list("load")
        h.snap("load_list_after_coldboot")
        h.item(3, 4)
        time.sleep(1.0)
        h.dump(str(d / "B.bin"), 0, 0x100000)
        time.sleep(0.5)
        h.click()
        h.wait_game(20)
        time.sleep(1.0)
        sb = state(h)
    finally:
        h.close()
    A, B = (d / "A.bin").read_bytes(), (d / "B.bin").read_bytes()
    print("player at the save", pos_of(A), "| after the cold boot + load, 3D view running", sb)
    ok = pos_of(A) == sb and cmp_ranges(A, B, "RAM before-shutdown vs RAM after-cold-boot-load")
    print("PERSIST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_slots(a) -> int:
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    h = boot(a)
    try:
        pos = {}
        h.walk(1.5, "Up")
        pos["one"] = h.save(1, "one")
        h.walk(2, "Up", "Left")
        pos["six"] = h.save(6, "six")
        h.walk(2, "Left")
        pos["uno"] = h.save(1, "uno")                       # overwrite slot 1
        h.open_list("save")
        h.snap("save_list_three")
        h.key("Escape", 0.2)
        time.sleep(1.5)
    finally:
        img = settle_and_close(h)
    print("positions at the saves:", pos)
    dr = read_file(img, "SAVES.DIR")
    names = parse_dir(dr)
    print("SAVES.DIR:", names, "| fsck:", fsck_part(img))
    ok = dr is not None and len(dr) == DIRLEN and names[0] == (True, "uno") and names[5] == (True, "six") \
        and all(not u for u, _ in names[1:5]) and fsck_part(img)[0]
    for n in (1, 6):
        f = read_file(img, "SLOT%d.SAV" % n)
        print(f"SLOT{n}.SAV {None if f is None else len(f)} B checksum {'ok' if f and sum_ok(f) else 'BAD'}")
        ok &= f is not None and len(f) == SLOTLEN and sum_ok(f)
    shutil.copy(img, d / "slots.img")
    h = boot(a, image=str(d / "slots.img"))
    try:
        got6 = h.load(6, snap="load_list_two_saves")
        got1 = h.load(1)
    finally:
        h.close()
    print("load slot 6 ->", got6, "(saved", pos["six"], ") | load slot 1 ->", got1, "(overwritten value", pos["uno"],
          ", first value", pos["one"], ")")
    ok &= got6 == pos["six"] and got1 == pos["uno"] and got1 != pos["one"]
    print("SLOTS", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def make_image(a, d: Path, name: str, files: dict[str, bytes] | None = None, ro: tuple = (), free_left: int | None = None) -> Path:
    """A fresh HD image of the game build with extra files in FILES\\ (slot/dir files crafted by the test)."""
    img = d / f"{name}.img"
    build_hd(img, game=(GAME / a.game).resolve())
    tgt = f"{img}@@{PART_OFF}"
    for fn, data in (files or {}).items():
        t = d / "_f"
        t.write_bytes(data)
        sh("mcopy", "-o", "-i", tgt, t, f"::FILES/{fn}")
    for fn in ro:
        sh("mattrib", "+r", "-i", tgt, f"::FILES/{fn}")
    if free_left is not None:
        out = sh("mdir", "-i", tgt, "::").stdout
        free = int(out.strip().splitlines()[-1].split("bytes")[0].replace(" ", "").replace("\xa0", ""))
        n = (free - free_left) // 1024 * 1024
        (d / "_f").write_bytes(bytes(n))
        sh("mcopy", "-o", "-i", tgt, d / "_f", "::FILL.BIN")
    return img


def dir_bytes(used: list[int], names: list[str]) -> bytes:
    b = bytearray(b"HUNTER SAVES 1.1".ljust(32, b"\0"))
    for k in range(6):
        e = bytearray(32)
        e[0:2] = struct.pack(">H", k) if k in used else b"\xff\0"
        e[0x10:0x10 + len(names[k]) + 1] = names[k].encode() + b"*"
        b += e
    return bytes(b)


def cmd_errors(a) -> int:
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    good = Path(a.good_slot).read_bytes()
    assert len(good) == SLOTLEN and sum_ok(good), "give a valid slot file (one saved by `roundtrip`) in --good-slot"
    ok = True
    # ---- load errors: one case per session (the game's menus are mouse driven, so after a dialog the disk menu is on screen and
    #      a fresh boot is simpler and more honest than guessing the next click) -----------------------------------------------
    if a.case in ("missing", "zeros", "short", "valid"):
        img = make_image(a, d, "loaderr", {
            "SAVES.DIR": dir_bytes([0, 1, 2, 3], ["gone", "zeros", "short", "good", "x", "y"]),
            "SLOT2.SAV": bytes(SLOTLEN), "SLOT3.SAV": good[:1000], "SLOT4.SAV": good})
        slot = {"missing": 1, "zeros": 2, "short": 3, "valid": 4}[a.case]
        h = boot(a, image=str(img))
        try:
            h.open_list("load")
            h.snap("load_list_crafted")
            before = state(h)
            h.item(slot, 3)
            if a.case == "valid":
                h.snap("load_valid_slot")
                time.sleep(1.5)
                pos = (h.peekw(h.POS_X), h.peekw(h.POS_Z))
                h.click()
                h.wait_game(20)
                print(f"load slot 4 (valid file): loaded, 3D view running, position {pos}")
                ok &= h.in_game()
            else:
                h.snap(f"dialog_load_{a.case}")
                h.item(1, 3)                                 # the dialog's single button
                time.sleep(1.5)
                pos = state(h)
                print(f"load slot {slot} ({a.case}): message shown and dismissed; position {pos} (before {before}); "
                      f"3D loop bit {h.peek(h.MODE, 1)[0] >> 7}; nothing of the slot was applied: {pos == before}")
                ok &= pos == before
        finally:
            img = settle_and_close(h)
    # ---- save errors: read-only slot file, full disk; Init Disk (one case per session) --------------------------------
    if a.case == "ro":
        img = make_image(a, d, "saverr_ro", {"SLOT4.SAV": good}, ro=("SLOT4.SAV",))
        h = boot(a, image=str(img))
        try:
            h.open_list("save")
            h.item(4, 2.5)
            h.type_name("ro", len(h.slot_name(4)))
            h.key("Return", 0.2)
            time.sleep(4)
            h.snap("dialog_save_readonly")
            h.item(1, 3)
        finally:
            img = settle_and_close(h)
        dr = read_file(img, "SAVES.DIR")
        print("read-only slot: message shown; SAVES.DIR after the attempt:", None if dr is None else parse_dir(dr))
        ok &= dr is None or not parse_dir(dr)[3][0]
    if a.case == "full":
        img = make_image(a, d, "saverr_full", free_left=20000)
        h = boot(a, image=str(img))
        try:
            h.open_list("save")
            h.item(2, 2.5)
            h.type_name("full", len(h.slot_name(2)))
            h.key("Return", 0.2)
            time.sleep(4)
            h.snap("dialog_save_full")
            h.item(1, 3)
        finally:
            img = settle_and_close(h)
        dr, f2 = read_file(img, "SAVES.DIR"), read_file(img, "SLOT2.SAV")
        print("full disk: message shown; SAVES.DIR:", None if dr is None else parse_dir(dr),
              "| SLOT2.SAV:", None if f2 is None else len(f2), "B")
        ok &= dr is None or not parse_dir(dr)[1][0]
    if a.case == "init":
        img = make_image(a, d, "initdisk", {"SAVES.DIR": dir_bytes([0, 1, 2, 3, 4, 5], ["a", "b", "c", "d", "e", "f"]),
                                            "SLOT1.SAV": good})
        h = boot(a, image=str(img))
        try:
            h.menu_disk()
            h.item(3, 3)                                   # Init Disk
            h.snap("initdisk_confirm")
            h.item(1, 3)                                   # 'Yes'
            time.sleep(3)
            h.snap("initdisk_after")
        finally:
            img = settle_and_close(h)
        dr = read_file(img, "SAVES.DIR")
        print("Init Disk: SAVES.DIR now", None if dr is None else parse_dir(dr), "| fsck ok:", fsck_part(img)[0])
        ok &= dr is not None and not any(u for u, _ in parse_dir(dr)) and fsck_part(img)[0]
    print("ERRORS", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_kill(a) -> int:
    """Power-off test: save, then SIGKILL Hatari `--delay` seconds later (a switched-off machine), and check that the image's
    directory and FAT are consistent and the slot is intact.  Repeats `--runs` times."""
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    bad = 0
    for i in range(a.runs):
        if a.snapshot:                                  # fast repeat: restore a 3D-view snapshot instead of a cold boot
            h = rig(a, snapshot=str((GAME / "work" / "snapshots" / a.snapshot).resolve()))
            h.STAGES = dict(h.STAGES)
            if not h.in_game():
                raise RuntimeError("the snapshot is not in the 3D view")
        else:
            h = boot(a)
        try:
            h.walk(1.5, "Up")
            pos = h.save(a.slot, "kill")
            time.sleep(a.delay)
            img = h.img
        finally:
            h.close()
        good, msg = fsck_part(img)
        dr = read_file(img, "SAVES.DIR")
        sl = read_file(img, f"SLOT{a.slot}.SAV")
        used = dr is not None and len(dr) == DIRLEN and parse_dir(dr)[a.slot - 1][0]
        ok = good and used and sl is not None and len(sl) == SLOTLEN and sum_ok(sl)
        bad += not ok
        print(f"kill +{a.delay}s run {i + 1}/{a.runs}: fsck={'clean' if good else 'ERRORS'} dir={'ok' if used else 'BAD/MISSING'} "
              f"slot={None if sl is None else len(sl)}B checksum={'ok' if sl and sum_ok(sl) else 'BAD'} -> {'OK' if ok else 'LOST'}"
              f"   [{msg}]")
        shutil.copy(img, d / f"kill_{a.delay}s_{i + 1}.img")
    print(f"KILL +{a.delay}s: {a.runs - bad}/{a.runs} durable")
    return 0 if bad == 0 else 1


def cmd_allgames(a) -> int:
    """The all-games hard-disk image (dist/AtariST_enhanced_games_*.img, ACSI + HDDRIVER, HUNTER folder): boot our build from
    HUNTER\\START.TOS, save into HUNTER\\FILES, cold boot the image again and load."""
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    img = d / "allgames.img"
    shutil.copy(Path(a.allgames).resolve(), img)
    tgt = f"{img}@@{PART_OFF}"
    build = (GAME / a.game).resolve()
    inf = img.parent / "desktop.inf"
    inf.write_bytes(("#a000000\r\n#b000000\r\n#c" + "7" * 65 + "\r\n#d\r\n#E 9B 01\r\n#W 00 00 10 01 4A 16 0F 0A C:\\*.*@\r\n"
                     "#M 00 00 00 FF C HARD DISK@ @\r\n#T 00 00 03 FF   TRASH@ @\r\n"
                     "#Z 01 C:\\HUNTER\\START.TOS@ @\r\n").encode())
    sh("mcopy", "-o", "-i", tgt, inf, "::DESKTOP.INF")
    sh("mcopy", "-o", "-i", tgt, build / "START.TOS", "::HUNTER/START.TOS")
    for f in sorted((build / "FILES").iterdir()):
        sh("mcopy", "-o", "-i", tgt, f, "::HUNTER/FILES/")
    h = boot(a, image=str(img), games_image=True)
    try:
        h.walk(2, "Up")
        p0 = h.save(5, "allimg", d / "A.bin")
        h.walk(3, "Up", "Left")
    finally:
        img = settle_and_close(h)
    shutil.copy(img, d / "allgames_after.img")
    print("saved on the all-games image at", p0, "| SLOT5.SAV present:", read_file(img, "SLOT5.SAV") is not None,
          "| fsck ok:", fsck_part(img)[0])
    h = boot(a, image=str(img), games_image=True)
    try:
        got = h.load(5, d / "B.bin")
    finally:
        h.close()
    A, B = (d / "A.bin").read_bytes(), (d / "B.bin").read_bytes()
    print("cold boot from the all-games image, load slot 5 ->", got, "(saved", p0, ")")
    ok = got == p0 and cmp_ranges(A, B, "all-games image: RAM save-time vs RAM after-cold-boot-load")
    print("ALLGAMES", "PASS" if ok else "FAIL")
    return 0 if ok else 1


class FloppyRig(Menus, HunterFloppy):
    """The floppy build: Paper Bag disk in drive A; the same menu helpers (the game's own Save/Load path through the crack's loader)."""

    def __init__(self, disk1, **kw):
        HunterFloppy.__init__(self, disk1, **kw)
        self.img = self.d1

    def boot(self, name="bench"):
        self.boot_floppy("none", name=name)
        return self

    def get(self, name: str, out: Path | None = None) -> bytes | None:
        out = out or Path(f"/tmp/hsv_fl_{os.getpid()}_{name}")
        out.unlink(missing_ok=True)
        r = sh("mcopy", "-i", self.img, f"::{name}", out)
        return out.read_bytes() if r.returncode == 0 else None


def cmd_floppy(a) -> int:
    """The floppy build's own saving still works (and loading too): Save, move, Load, compare RAM."""
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    img = a.floppy_img
    if not img:
        out = GAME / "build" / "sav_fl"
        r = sh(sys.executable, GAME / "tools" / "huntpatch.py", "build", "--floppy", "--out", out)
        if r.returncode:
            print(r.stdout, r.stderr)
            return 1
        img = out / "HUNTER_disk1.st"
    print("floppy image", img)
    h = FloppyRig(img, machine=a.machine, tos=TOS[a.tos or "1.62"], memsize_kb=a.mem)
    try:
        h.boot()
        print("marker", h.peek(0x8BFF8, 4), "in game", h.in_game())
        h.walk(2, "Up")
        p0 = h.save(2, "flop", d / "A.bin")
        h.walk(3, "Up", "Left")
        p1 = state(h)
        got = h.load(2, d / "B.bin")
    finally:
        time.sleep(10)
        img = h.img
        keep = d / "floppy_after.st"
        shutil.copy(img, keep)                      # the floppy rig's scratch dir goes away with the emulator
        h.close()
        img = keep
    A, B = (d / "A.bin").read_bytes(), (d / "B.bin").read_bytes()
    print("player at the save", pos_of(A), "moved to", p1, "loaded to", got)
    ok = got == pos_of(A) and p1 != p0 and cmp_ranges(A, B, "floppy: RAM save-time vs RAM after-load")
    fs = sh("fsck.fat", "-n", img)                     # informational: the copy can be torn (Hatari writes the .st in place)
    lines = [ln for ln in (fs.stdout + fs.stderr).splitlines() if ln.strip()]
    print("disk image copy, fsck (info only):", fs.returncode, lines[-1] if lines else "")
    for n in ("13", "0F"):
        out = Path(f"/tmp/hsv_fl_{n}")
        out.unlink(missing_ok=True)
        r = sh("mcopy", "-i", img, f"::{n}", out)
        print(f"  disk file {n}:", out.stat().st_size if r.returncode == 0 else "missing")
        ok &= r.returncode == 0
    print("FLOPPY", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["roundtrip", "persist", "slots", "errors", "allgames", "floppy", "kill"])
    ap.add_argument("--game", default="build/sav_game")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default=None)
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--work", default="/tmp/hsv_work")
    ap.add_argument("--delay", type=float, default=1.0, help="kill: seconds between the save and the power-off")
    ap.add_argument("--runs", type=int, default=3, help="kill: repetitions")
    ap.add_argument("--snapshot", default=None, help="kill: restore this work/snapshots/<name> instead of cold booting")
    ap.add_argument("--case", default="missing", choices=["missing", "zeros", "short", "valid", "ro", "full", "init"],
                    help="errors: which failure to run (one session each)")
    ap.add_argument("--good-slot", default="/tmp/hsv_good_slot.bin", help="errors: a valid slot file (a save made by roundtrip)")
    ap.add_argument("--allgames", default="/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-12.img",
                    help="allgames: the all-games image to copy and put the build into")
    ap.add_argument("--floppy-img", default=None, help="floppy: an existing HUNTER_disk1.st (default: build it)")
    a = ap.parse_args()
    return {"roundtrip": cmd_roundtrip, "persist": cmd_persist, "slots": cmd_slots, "errors": cmd_errors,
            "allgames": cmd_allgames, "floppy": cmd_floppy, "kill": cmd_kill}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
