#!/usr/bin/env python3
"""End-to-end verification of Player Manager v1.1:
  --mode floppy : cold-boot dist/PlayerManager_v1.1_floppy_2026-11-26.st (--gemdos-drive skip --disk-a)
  --mode acsi   : cold-boot dist/AtariST_enhanced_games_2026-11-26_playmgr1.1.img (--gemdos-drive skip --acsi)
Tests cold boot -> scr3.men credit -> Demo Game -> Match day -> live Kick Off 2 match -> Full-Time clean exit back to PM!
"""
import argparse
import concurrent.futures
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from PIL import Image

REPO = Path(__file__).resolve().parents[4]
ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work"
ST_IMG = ROOT / "dist" / "PlayerManager_v1.1_floppy_2026-11-26.st"
HD_IMG = REPO / "dist" / "AtariST_enhanced_games_2026-11-26_playmgr1.1.img"

sys.path.insert(0, str(REPO / "tools"))
from stharness import Hatari, TOS


def screen_rgb(h, R, name):
    p = R / f"{name}.png"
    for _ in range(5):
        h.shot(str(p))
        time.sleep(0.15)
        try:
            with Image.open(p) as im:
                im.load()
                return im.convert("RGB")
        except Exception:
            time.sleep(0.25)
    return Image.open(p).convert("RGB")


def drive_to_match_and_exit(h, R, tag, prefix, wait_load=14.0, do_exit=True):
    # 1. Wait for PMOK ($0b2ff8 == 0x504d4f4b)
    t0 = time.time()
    while time.time() - t0 < 60:
        if h.peekl(0x0b2ff8) == 0x504d4f4b:
            break
        h.keypress(57)
        time.sleep(1.5)
    pmok = h.peekl(0x0b2ff8)
    if pmok != 0x504d4f4b:
        h.shot(str(WORK / f"{prefix}_{tag}_fail_boot.png"))
        return False, f"[{tag:12s}] FAIL boot: PMOK=${pmok:08x}"

    # Wait for scr3.men (dark green bg at (20,20)); NEVER click before scr3.men so we don't hit Continue Game!
    for _ in range(55):
        im = screen_rgb(h, R, "wait_scr3")
        bg = im.getpixel((20, 20))
        if bg[1] > 70 and bg[0] < 25 and bg[2] < 25:
            break
        # On scr2.men (teal copyright screen, g>60 & b>60), press Space (never triggers scr3 buttons)
        if bg[1] > 50 and bg[2] > 50:
            h.keypress(57)
        time.sleep(1.0)
    time.sleep(1.5)
    h.shot(str(WORK / f"{prefix}_{tag}_scr3.png"))

    # 2. Click Demo Game at abs (320, 340) until hidx == 44
    a4 = 0x02969a
    for _ in range(5):
        h.rel(-700, -500, steps=10); time.sleep(0.08)
        h.rel(320, 340, steps=10); time.sleep(0.12)
        h.click(hold=0.25); time.sleep(6.0)
        if h.peekw(a4 - 0x2e42) == 44:
            break
    hidx = h.peekw(a4 - 0x2e42)
    if hidx != 44:
        h.shot(str(WORK / f"{prefix}_{tag}_fail_demo.png"))
        return False, f"[{tag:12s}] FAIL Demo Game: hidx={hidx}"
    pool = h.peekl(a4 - 0x2e80)
    tbase = h.peekl(a4 - 0x2e94)

    # 3. Click Match day at abs (320, 305) -> wait for "The Opponents"
    time.sleep(1.5)
    h.rel(-700, -500, steps=10); time.sleep(0.05)
    h.rel(320, 305, steps=10); time.sleep(0.08)
    h.click(hold=0.2)
    for _ in range(25):
        time.sleep(1.0)
        im = screen_rgb(h, R, "opp")
        if im.getpixel((462, 300))[2] < 40 and im.getpixel((595, 395))[2] > 120:
            break

    # 4. Click Done on "The Opponents" at (540, 340) -> Select Team
    h.rel(-700, -500, steps=10); time.sleep(0.04)
    h.rel(270, 170, steps=8); time.sleep(0.04)
    h.rel(270, 170, steps=8); time.sleep(0.1)
    h.click(hold=0.25); time.sleep(3.0)
    im = screen_rgb(h, R, "sel")
    if im.getpixel((250, 200))[1] <= 90:
        h.shot(str(WORK / f"{prefix}_{tag}_fail_sel.png"))
        return False, f"[{tag:12s}] FAIL Select Team (green={im.getpixel((250,200))[1]})"

    # 5. Assign shirts 1..12, 14 to human team
    tptr = tbase + hidx * 0x64
    shirts = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14]
    for i in range(18):
        pi = h.peekw(tptr + 0x2c + i * 2)
        if pi == 0xffff:
            break
        p = pool + pi * 0x2a
        b = h.peekw(p + 0x14) & 0xff
        sh = shirts[i] if i < 13 else 0
        nb = (b & 0xf0) | sh
        h.debug(f"w b ${p+0x15:x} ${nb:02x}", wait=0.015)

    # 6. Click Done on Select Team -> The Line-Up -> Done -> KO2 Pre-Match (ko6.men) -> Space -> LIVE MATCH!
    h.rel(-700, -500, steps=10); time.sleep(0.04)
    h.rel(230, 376, steps=8); time.sleep(0.12)
    h.click(hold=0.25); time.sleep(2.5)
    h.click(hold=0.25)

    # Wait for ko6.men pre-match screen (red REFEREE bar at (160, 104)!) before screenshotting & pressing Space!
    ko2_a4 = 0x0284aa
    for _ in range(int(wait_load)):
        time.sleep(1.0)
        im = screen_rgb(h, R, "wait_ko6")
        px = im.getpixel((160, 104))
        if px[0] > 150 and px[1] < 40 and px[2] < 40:
            break
    time.sleep(0.8)
    h.shot(str(WORK / f"{prefix}_{tag}_ko6.png"))
    h.keypress(57)  # Space -> KICK OFF!

    # Wait for KO2 live match frame counter -$4f4e(a4_ko2) to advance!
    frm1 = 0
    for _ in range(int(wait_load)):
        time.sleep(1.0)
        frm1 = h.peekl(ko2_a4 - 0x4f4e)
        if 2 < frm1 < 50000:
            break
    time.sleep(1.5)
    frm2 = h.peekl(ko2_a4 - 0x4f4e)
    h.shot(str(WORK / f"{prefix}_{tag}_match.png"))

    br_ste = h.peekw(0x0b6c78)
    ste_ok = h.peekw(0x0ae940 + 0x24) if br_ste == 1 else 0
    snd_base = h.peekl(0x0ae940 + 0x10) if br_ste == 1 else 0
    snd_sz = h.peekl(0x0ae940 + 0x08) if br_ste == 1 else 0
    proc_lives = h.peekl(0x380)
    exc = (h.peekl(0x3c4) >> 24) if proc_lives == 0x12345678 else 0
    match_ok = (exc == 0 and frm2 > frm1 and frm2 < 50000)

    exit_info = "exit=SKIP"
    exit_ok = True
    if match_ok and do_exit:
        # Force clean KO2 Half-Time -> Fire -> Full-Time exit ($01b4b2 -> bra.w $01b75e)
        # to test full ko2_bridge_match return + PMCODE.BIN reload + reapply_pm_hooks + PM post-match!
        h.debug("w $1b4b2 $60 $00 $02 $aa", wait=0.1)
        # Press Joystick 1 Fire ($0284aa - $df0 + 2 = $0276bc) to pass Half-Time & Full-Time screens
        for _ in range(24):
            time.sleep(1.8)
            if h.peekw(0x018ebe) == 0x4ef9:
                break
            h.debug("w $276bc $00 $01", wait=0.12)
            h.debug("w $276bc $00 $00", wait=0.12)
            h.keypress(57)
        time.sleep(2.5)
        h.shot(str(WORK / f"{prefix}_{tag}_postmatch.png"))
        pmok_after = h.peekl(0x0b2ff8)
        # Verify PM hook at $018ebe was re-applied ($4ef9 = jmp.l ko2_bridge_match) & no exception!
        hook_op = h.peekw(0x018ebe)
        pl2 = h.peekl(0x380)
        exc2 = (h.peekl(0x3c4) >> 24) if pl2 == 0x12345678 else 0
        regs = h.debug("r", wait=0.12)
        pc_line = [l.strip() for l in regs.splitlines() if "Next PC" in l]
        exit_ok = (exc2 == 0 and pmok_after == 0x504d4f4b and hook_op == 0x4ef9)
        exit_info = f"exit_ok={exit_ok} hook=${hook_op:04x} exc2={exc2} {pc_line}"

    ok = match_ok and exit_ok
    msg = (f"[{tag:12s}] {'PASS' if ok else 'FAIL'} | STE={br_ste} STE_OK={ste_ok} "
           f"SND=${snd_base:06x}({snd_sz}B) frm={frm1}->{frm2} exc={exc} | {exit_info}")
    return ok, msg


def run_floppy_cell(cfg):
    mach, tos_k, mem_kb, tag = cfg
    R = Path(tempfile.mkdtemp(prefix=f"v11flp-{tag}-"))
    st_copy = R / "pm11.st"
    shutil.copy2(ST_IMG, st_copy)
    h = None
    try:
        ex_args = ["--gemdos-drive", "skip", "--disk-a", str(st_copy)]
        if mach != "megaste":
            ex_args += ["--fastfdc", "yes"]
        h = Hatari(
            game_dir=R, workdir=str(R), files=[], autorun="",
            extra=ex_args,
            machine=mach, tos=TOS[tos_k], memsize_kb=mem_kb,
            sound=(mach in ("ste", "megaste")),
        )
        return drive_to_match_and_exit(h, R, tag, "v11_flop", wait_load=45.0, do_exit=True)
    except Exception as e:
        return False, f"[{tag:12s}] EXCEPTION: {e}"
    finally:
        if h:
            h.close()
        shutil.rmtree(R, ignore_errors=True)


def run_acsi_cell(cfg, base_hd):
    mach, tos_k, mem_kb, tag = cfg
    R = Path(tempfile.mkdtemp(prefix=f"v11acsi-{tag}-"))
    hd = R / "hd.img"
    shutil.copy2(base_hd, hd)
    h = None
    try:
        h = Hatari(
            game_dir=R, workdir=str(R), files=[], autorun="",
            extra=["--gemdos-drive", "skip", "--acsi", f"0={hd}"],
            machine=mach, tos=TOS[tos_k], memsize_kb=mem_kb,
            sound=(mach in ("ste", "megaste")),
        )
        return drive_to_match_and_exit(h, R, tag, "v11_acsi", wait_load=22.0, do_exit=True)
    except Exception as e:
        return False, f"[{tag:12s}] EXCEPTION: {e}"
    finally:
        if h:
            h.close()
        shutil.rmtree(R, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["floppy", "acsi"], required=True)
    args = ap.parse_args()

    if args.mode == "floppy":
        cfgs = [
            ("ste",     "1.62", 1024, "1mb_ste162"),
            ("ste",     "1.62", 4096, "4mb_ste162"),
            ("st",      "1.04", 1024, "1mb_st104"),
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
            results = list(ex.map(run_floppy_cell, cfgs))
    else:
        tmp_hd_dir = Path(tempfile.mkdtemp(prefix="v11hd-base-"))
        base_hd = tmp_hd_dir / "base.img"
        shutil.copy2(HD_IMG, base_hd)
        # Add #Z autorun on temp copy only so cold-boot enters PLAYERME\RUNME.TOS automatically
        off = 2 * 512
        for fn in ("DESKTOP.INF", "NEWDESK.INF"):
            r = subprocess.run(["mtype", "-i", f"{base_hd}@@{off}", f"::{fn}"], capture_output=True)
            if r.returncode == 0:
                txt = r.stdout.decode("latin-1")
                lines = [l for l in txt.splitlines() if not l.startswith("#Z")]
                lines.insert(1, "#Z 01 C:\\PLAYERME\\RUNME.TOS@")
                tf = tmp_hd_dir / fn
                tf.write_bytes(("\r\n".join(lines) + "\r\n").encode("latin-1"))
                subprocess.run(["mcopy", "-o", "-i", f"{base_hd}@@{off}", str(tf), f"::{fn}"], check=True)
        cfgs = [
            ("ste", "1.62", 4096, "4mb_ste162"),
            ("ste", "1.62", 1024, "1mb_ste162"),
            ("ste", "2.06", 1024, "1mb_ste206"),
            ("st",  "1.04", 1024, "1mb_st104"),
        ]
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                results = list(ex.map(lambda c: run_acsi_cell(c, base_hd), cfgs))
        finally:
            shutil.rmtree(tmp_hd_dir, ignore_errors=True)

    all_ok = True
    for ok, msg in results:
        print(msg, flush=True)
        all_ok = all_ok and ok
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
