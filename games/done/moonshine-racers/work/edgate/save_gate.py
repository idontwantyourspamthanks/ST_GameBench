#!/usr/bin/env python3
r"""End-to-end Hatari gate for Track Editor saving (Milestone 4: HD + Floppy Drive A:).

Tests:
  1. Create NEW TRACK, edit a segment, KEEP -> CPSTORE valid v2 campaign.
  2. SAVE CAMPAIGN... > SAVE TO HARD DISK -> FILES/MSTRACKS.TRK written, byte-exact to CPSTORE,
     passes msrtrack.validate_campaign().
  3. SAVE CAMPAIGN... > SAVE TO FLOPPY DISK (DRIVE A:):
     - Screenshot of formatted campaign disk prompt.
     - Error: write-protected floppy -> DISK IS WRITE PROTECTED.
     - Error: unformatted floppy -> NO FORMATTED DISK IN DRIVE A.
     - Success: blank formatted 720 KB FAT12 floppy -> A:\MSTRACKS.TRK written, byte-exact to CPSTORE,
       passes msrtrack.validate_campaign().
  4. Back to F10 Campaign Menu:
     - LOAD CAMPAIGN FROM HARD DISK reloads the saved campaign cleanly.
     - LOAD CAMPAIGN FROM DRIVE A reloads the saved floppy campaign cleanly.
  5. Zero Bus/Address errors throughout.
"""
import os, sys, time, struct, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from ed2lib import *


def make_blank_fat12(label: str = "CAMPAIGN") -> bytes:
    """Create a blank formatted 720 KB Atari ST FAT12 floppy image (no files)."""
    img = bytearray(mt.NSEC * 512)
    img[0:512] = mt._boot(hashlib.md5(label.encode("ascii")).digest()[:3])
    fat = bytearray(mt.SPF * 512)
    fat[0:3] = b"\xf9\xff\xff"
    for k in range(mt.NFAT):
        img[512 + k * mt.SPF * 512:512 + (k + 1) * mt.SPF * 512] = fat
    dir0 = 512 + mt.NFAT * mt.SPF * 512
    d = bytearray(32)
    d[0:11] = label.upper().encode("ascii").ljust(11)[:11]
    d[11] = 0x08
    img[dir0:dir0 + 32] = d
    return bytes(img)


def read_vmsg(ed: Ed) -> str:
    p = ed.vl("msg")
    if not 0x130000 <= p < 0x140000:
        return ""
    return ed.r.mem(p, 48).split(b"\0")[0].decode("latin1")


def wait_msel(ed: Ed, target: int, tmo: float = 15) -> bool:
    for _ in range(12):
        s = ed.vu("msel")
        if s == target:
            return True
        ed.send(0x50 if s < target else 0x48)
        time.sleep(0.4)
    return ed.vu("msel") == target


def run_gate(machine="ste", mem=2048):
    tag = f"save_{machine}_{mem // 1024}m"
    build = os.environ.get("ED_BUILD", "/tmp/msr_save/hd")
    ed = Ed(tag, machine=machine, mem=mem, build=build, camp=None)
    r = ed.r
    # Find the GEMDOS drive directory Hatari mounted (stharness uses self.R / "C")
    drive_dir = r.h.R / "C"
    hd_trk = drive_dir / "FILES" / "MSTRACKS.TRK"
    if hd_trk.exists():
        hd_trk.unlink()
    log(f"GEMDOS drive dir: {drive_dir}")

    # Prepare floppy test images in ED_TMP
    fl_dir = ED_TMP / f"fl_{tag}"
    fl_dir.mkdir(parents=True, exist_ok=True)
    fl_wp = fl_dir / "wp.st"
    fl_unfmt = fl_dir / "unfmt.st"
    fl_ok = fl_dir / "camp_ok.st"
    for p in (fl_wp, fl_unfmt, fl_ok):
        if p.exists():
            os.chmod(p, 0o644)
            p.unlink()
    fl_wp.write_bytes(make_blank_fat12("WPTEST"))
    os.chmod(fl_wp, 0o444)                      # read-only -> Hatari reports write-protected floppy
    fl_unfmt.write_bytes(bytes(720 * 1024))     # all-zero unformatted image
    fl_ok.write_bytes(make_blank_fat12("MSRCAMP"))

    try:
        # 1. Boot to Track Editor (no campaign loaded yet)
        ed.boot_editor(load_camp=False, ntr=0)
        errs0 = r.errlines()
        check("top_list without campaign has 3 items (no Save yet)", ed.vu("mcnt") == 3)

        # 2. Open NEW TRACK (scenery 0), edit segment 0 (curve right), KEEP (F10)
        ok = ed.open_track("straight", level=0, ntr=0)
        check("NEW TRACK opened", ok)
        ed.send(0x34)  # '.' bend right on segment 0
        time.sleep(0.5)
        check("editor idle after bend", ed.idle())
        ed.send(0x44)  # F10 -> LEAVE AND KEEP THIS TRACK
        ok = ed.wait(lambda: ed.vu("state") == 0 and r.b(V["loaded"]) == 0xFF, 20)
        check("returned to top_list with campaign kept in RAM", ok)
        time.sleep(0.5)
        check("top_list with 1 track has 5 items (1 track + Copy + New + Save + Back)", ed.vu("mcnt") == 5)
        r.shot("01_toplist_kept")

        expected = ed.store()
        log(f"CPSTORE size = {len(expected)} B")
        parsed = mt.validate_campaign(expected, "cpstore")
        check("CPSTORE passes validate_campaign", parsed is not None)

        # 3. Select SAVE CAMPAIGN... > (index 3 = 1 track + Copy + New)
        check("select SAVE CAMPAIGN... >", wait_msel(ed, 3))
        ed.send(0x1C)  # Return -> save_menu (3 items: HD, Floppy, Back)
        ok = ed.wait(lambda: ed.vu("mcnt") == 3, 10)
        check("save_menu opened (3 items)", ok)
        time.sleep(0.5)
        r.shot("02_save_menu")

        # 4. Test 1: SAVE TO HARD DISK (item 0)
        check("HD item selected", wait_msel(ed, 0))
        ed.send(0x1C)
        ok = ed.wait(lambda: ed.vu("mcnt") == 5, 30)
        check("HD save returned to top_list", ok)
        time.sleep(0.5)
        r.shot("03_after_hd_save")
        m_hd = ed.msgtext()
        log(f"HD save msg: {m_hd!r}")
        check("HD save message says SAVED TO FILES\\MSTRACKS.TRK", m_hd == "SAVED TO FILES\\MSTRACKS.TRK")
        check("FILES/MSTRACKS.TRK exists on host drive", hd_trk.exists())
        if hd_trk.exists():
            disk_bytes = hd_trk.read_bytes()
            check(f"FILES/MSTRACKS.TRK byte-exact ({len(disk_bytes)} == {len(expected)})", disk_bytes == expected)
            check("FILES/MSTRACKS.TRK passes validate_campaign", mt.validate_campaign(disk_bytes, "hd") is not None)

        # 5. Test 2: SAVE TO FLOPPY DISK (DRIVE A:)
        check("select SAVE CAMPAIGN... > again", wait_msel(ed, 3))
        ed.send(0x1C)
        check("save_menu opened", ed.wait(lambda: ed.vu("mcnt") == 3, 10))
        check("select FLOPPY item (1)", wait_msel(ed, 1))
        ed.send(0x1C)
        time.sleep(1.0)
        r.shot("04_floppy_prompt")

        # 5a. Write-protected floppy (Hatari --protect-floppy on)
        log("Inserting write-protected floppy...")
        r.h.cmd("hatari-option --protect-floppy on")
        r.h.cmd(f"hatari-option --disk-a {fl_wp}")
        time.sleep(1.5)
        ed.send(0x1C)  # Return to save
        ok = ed.wait(lambda: ed.msgtext() == "DISK IS WRITE PROTECTED", 30)
        time.sleep(0.5)
        r.shot("05_floppy_wp_err")
        log(f"WP floppy msg: {ed.msgtext()!r}")
        check("write-protected floppy reports DISK IS WRITE PROTECTED", ok)
        check("write-protected floppy stayed on floppy prompt", ed.vu("mcnt") == 3)

        # 5b. Unformatted floppy
        log("Inserting unformatted floppy...")
        r.h.cmd("hatari-option --protect-floppy off")
        r.h.cmd(f"hatari-option --disk-a {fl_unfmt}")
        time.sleep(1.5)
        ed.send(0x1C)  # Return to save
        ok = ed.wait(lambda: ed.msgtext() == "NO FORMATTED DISK IN DRIVE A", 30)
        time.sleep(0.5)
        r.shot("06_floppy_unfmt_err")
        log(f"Unformatted floppy msg: {ed.msgtext()!r}")
        check("unformatted floppy reports NO FORMATTED DISK IN DRIVE A", ok)
        check("unformatted floppy stayed on floppy prompt", ed.vu("mcnt") == 3)

        # 5c. Formatted blank campaign disk (writable!)
        log("Inserting blank formatted campaign disk...")
        r.h.cmd(f"hatari-option --disk-a {fl_ok}")
        time.sleep(1.5)
        ed.send(0x1C)  # Return to save
        ok = ed.wait(lambda: ed.vu("mcnt") == 5 and ed.msgtext() == "SAVED TO A:\\MSTRACKS.TRK", 45)
        time.sleep(0.5)
        r.shot("07_after_floppy_save")
        log(f"Floppy save msg: {ed.msgtext()!r}")
        check("floppy save succeeded and returned to top_list", ok)
        # Eject drive A so Hatari flushes its in-memory .st buffer to the host file, then re-insert for reload test
        r.h.cmd("hatari-option --disk-a none")
        time.sleep(1.5)

        # Verify the .st image on host has MSTRACKS.TRK byte-exact!
        st_bytes = fl_ok.read_bytes()
        fl_trk = mt.disk_read_file(st_bytes)
        check(f"A:\\MSTRACKS.TRK on floppy byte-exact ({len(fl_trk)} == {len(expected)})", fl_trk == expected)
        check("A:\\MSTRACKS.TRK passes validate_campaign", mt.validate_campaign(fl_trk, "floppy") is not None)
        # Re-insert for reload test
        r.h.cmd(f"hatari-option --disk-a {fl_ok}")
        time.sleep(1.5)

        # 6. Leave Track Editor -> F10 Campaign Menu -> reload from HD and from Drive A!
        check("select < BACK TO THE CAMPAIGN MENU (item 4)", wait_msel(ed, 4))
        ed.send(0x1C)
        time.sleep(1.5)

        # Reload from Hard Disk (item 1): zero CPSTORE+0 first so we prove the reload really read the file
        r.poke(CPS, 0, 0, 0, 0)
        check("F10 menu: LOAD CAMPAIGN FROM HARD DISK", ed.goto_item(1))
        ed.send(0x1C)
        t0 = time.time()
        while time.time() - t0 < 30 and not (r.b(V["loaded"]) == 0xFF and r.l(CPS) == 0x4D53544B):
            time.sleep(0.3)
        time.sleep(1.5)
        check("reloaded saved campaign from Hard Disk", r.b(V["loaded"]) == 0xFF and r.w(V["count"]) == 1)
        check("reloaded HD CPSTORE byte-exact", ed.store() == expected)
        # Back from list_screen (< BACK is item 1 for 1 track)
        ed.goto_item(1); ed.send(0x1C); time.sleep(1.5)

        # Reload from Drive A (item 2): zero CPSTORE+0 first so we prove the reload really read Drive A
        r.poke(CPS, 0, 0, 0, 0)
        check("F10 menu: LOAD CAMPAIGN FROM DRIVE A", ed.goto_item(2))
        ed.send(0x1C)
        t0 = time.time()
        while time.time() - t0 < 45 and not (r.b(V["loaded"]) == 0xFF and r.l(CPS) == 0x4D53544B):
            time.sleep(0.3)
        time.sleep(1.5)
        check("reloaded saved campaign from Drive A", r.b(V["loaded"]) == 0xFF and r.w(V["count"]) == 1)
        check("reloaded Drive A CPSTORE byte-exact", ed.store() == expected)
        r.shot("08_reloaded_from_drive_a")

        errs = r.errlines() - errs0
        check(f"zero unexpected Bus/Address errors after boot ({errs})", errs == 0)
    finally:
        ed.close()
        if fl_wp.exists():
            os.chmod(fl_wp, 0o644)

    log(f"== {tag}: " + (f"FAIL ({len(FAILS)}): {FAILS}" if FAILS else "ALL CHECKS PASS"))
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    mach = sys.argv[1] if len(sys.argv) > 1 else "ste"
    run_gate(mach)
