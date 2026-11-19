#!/usr/bin/env python3
"""Regression gate for 'Options -> Game -> Retire' (work/notes/retire.md): the lose / win picture must appear (non-black pixels), the payload must
be intact, and the game must go on (click -> option screen -> START NEW CONQUEST -> map view, twice).

    python3 tools/pmretire.py --disk build/x/floppy/powermonger.st --machine megaste --tos 2.06 --mem 4096 [--win]
    python3 tools/pmretire.py --disk disks/protected.st ...                       # the unmodified original (expected OK)
    python3 tools/pmretire.py --hd build/x/hd [--acsi] ...                        # HD build (GEMDOS folder or ACSI + HDDRIVER)
    python3 tools/pmretire.py --img dist/AtariST_enhanced_games_<date>.img ...    # the all-games drive image (PMBOOT: key P), as the user runs it
    python3 tools/pmretire.py --disk ... --snap OUT.sav                           # stop at the map view and save a memstate of the Retire menu

`--win` forces the conquest balance to 'won' ($57fce = 4, which `$d2c8` tests) at the Retire check: the win picture path (`$1a4da`).
One `RESULT` line per check, `CELL DONE ... OK|CHECK` at the end (exit 0 = OK).  Evidence kept in --shots DIR.
"""
from __future__ import annotations

import argparse
import re
import shlex
import shutil
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent.parent.parent / "tools"), str(HERE)]
import pmpatch  # noqa: E402
from pm import TOS  # noqa: E402

OPTION_XY = (70, 137)          # the Option symbol (top-left of the command panel)
CURSOR, CAPLIM = 0x2C1BA, 0xB8000     # resource-cache cursor of the game's loader ($e000 / $e032), start of our payload
BALANCE = 0x57FCE              # conquest balance state; 4 = won ($d2d8: cmpi.w #4,$57fce)


def rd(h, addr):
    """peekl that returns None when the emulator no longer answers the debugger (a crashed game spams the log)."""
    try:
        return h.peekl(addr)
    except Exception:  # noqa: BLE001
        return None


def shot_stats(h):
    """(non-black fraction of the 320x200 game area, distinct colours) of a screenshot of the running game."""
    from PIL import Image
    im = Image.open(h.shot()).convert("RGB")
    ox, oy = {832: (96, 58), 640: (0, 0), 648: (2, 64)}.get(im.width, (96, 58))
    c = im.crop((ox, oy, ox + 640, oy + 400))
    px = list(c.getdata())
    nb = sum(1 for p in px if max(p) > 24)
    return nb / len(px), len(set(px))


def wait_btn(h, ref, timeout=40.0):
    """Centre (ST px) of a button once it has been at the same place in two reads (the Option panel slides in)."""
    t, last = time.time(), None
    while time.time() - t < timeout:
        p = pmpatch.find_btn(h, ref, quiet=True)
        if p is not None and p == last:
            return p
        last = p
        time.sleep(1.0)
    return None


def payload_report(h, man):
    """First 16 bytes of every blob of the build in RAM against the build's image: [(name, org, ok)]; plus the PMPO marker."""
    bad = []
    n = 0
    for name, org, b in man:
        n += 1
        try:
            same = h.ram(org, min(16, len(b))) == b[:16]
        except Exception:  # noqa: BLE001
            same = False
        if not same:
            bad.append((name, hex(org)))
    return n, bad


def run_menu_retire(h, win: bool, shots: Path | None, tag: str, expect_cap: bool, final: bool = False):
    """Option symbol -> GAME -> RETIRE (win: forced balance); returns the dict of observations."""
    r = {}
    h.click_st(*OPTION_XY, wait=1.0)
    p = wait_btn(h, "pm_btn_game.png")
    r["game_btn"] = p
    if p is None:
        return r
    h.click_st(*p, wait=1.0)
    p = wait_btn(h, "pm_btn_retire.png")
    r["retire_btn"] = p
    if p is None:
        return r
    r["cursor_before"] = rd(h, CURSOR)
    if win:        # the check at $d2d8 reads $57fce right then: write it from a breakpoint on that instruction
        pokes = f"w ${BALANCE:x} $00 $04\n" + ("w $2df6e $00 $04\nw $580a4 $00 $c2\n" if final else "")
        (h.R / "win.txt").write_text(pokes)
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b pc = $d2d8 :trace :once :file {h.R / 'win.txt'}")
    h.click_st(*p, wait=1.0)
    t = time.time()
    best = (0.0, 0)
    seen = 0
    while time.time() - t < 75:
        try:
            frac, ncol = shot_stats(h)
        except RuntimeError:
            frac, ncol = 0.0, 0
        best = max(best, (frac, ncol))
        if frac > 0.30 and ncol >= 12:
            seen += 1
            if seen >= 3:
                break
        else:
            seen = 0
        time.sleep(2.0)
    r["picture_s"] = time.time() - t
    r["shown"] = seen >= 3
    if r["shown"]:       # the crash of the broken build comes AFTER the picture first shows (the cache copy runs when the picture is decompressed): look again
        time.sleep(8.0)
        try:
            frac, ncol = shot_stats(h)
        except RuntimeError:
            frac, ncol = 0.0, 0
        r["still_shown"] = frac > 0.30 and ncol >= 12
        best = (frac, ncol)
    r["frac"], r["colours"] = best
    r["cursor_after"] = rd(h, CURSOR)
    if shots:
        try:
            h.shot(str(shots / f"{tag}_picture.png"))
        except RuntimeError:
            pass
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk")
    ap.add_argument("--hd")
    ap.add_argument("--img")
    ap.add_argument("--acsi", action="store_true")
    ap.add_argument("--machine", default="megaste")
    ap.add_argument("--tos", default="2.06")
    ap.add_argument("--mem", type=int, default=4096)
    ap.add_argument("--hopts", default="")
    ap.add_argument("--win", action="store_true")
    ap.add_argument("--final", action="store_true", help="also force the last island ($2df6e = 4, $580a4 = $c2: `$1a4ec` / `$1a4f6`): the ending pictures (resources 12, 13) instead of the win picture")
    ap.add_argument("--rounds", type=int, default=2)
    ap.add_argument("--shots")
    ap.add_argument("--snap", help="save a memstate of the open Retire menu here and stop")
    ap.add_argument("--manifest", help="build/<kind>.json of the build under test: its blobs are compared with RAM after the Retire")
    a = ap.parse_args()
    a.win = a.win or a.final
    kind = "img" if a.img else ("HD" + ("-acsi" if a.acsi else "-gemdos") if a.hd else "floppy")
    name = f"{kind} {a.machine} TOS {a.tos} {a.mem} KB {'FINAL' if a.final else 'WIN' if a.win else 'LOSE'}"
    print(f"CELL {name}", flush=True)
    shots = Path(a.shots) if a.shots else None
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    h, ok = None, True
    try:
        extra = shlex.split(a.hopts)
        if a.img:
            h = make_img_pm(Path(a.img).resolve(), machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=extra)
        else:
            h = pmpatch.make_pm(Path(a.disk).resolve() if a.disk else None, Path(a.hd).resolve() if a.hd else None, acsi=a.acsi,
                                machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=extra)
        t0 = time.time()
        h.boot_to_game()
        marker = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
        print(f"RESULT boot: {time.time() - t0:.0f} s, in_game {h.in_game()}, MARKER {marker!r}, resource cache cursor ${h.peekl(CURSOR):x}, "
              f"RAM above the cursor's limit ${CAPLIM:x}", flush=True)
        blobs = []
        if a.manifest:
            import json
            man = json.loads(Path(a.manifest).read_text())
            ps = [p for p in pmpatch.load_all() if p.name in man["patches"]]
            for p in ps:
                for org, lines in p.segments:
                    if org != p.site:
                        blobs.append((p.name, org, pmpatch.assemble(org, lines, "\n".join(p.preamble))))
            n, bad = payload_report(h, blobs)
            print(f"RESULT payload before: {n} blobs compared (first 16 B), {len(bad)} differ {bad}", flush=True)
        for rnd in range(1, a.rounds + 1):
            if a.snap and rnd == 1:
                h.click_st(*OPTION_XY, wait=1.0)
                p = wait_btn(h, "pm_btn_game.png")
                h.click_st(*p, wait=1.0)
                wait_btn(h, "pm_btn_retire.png")
                h.savemem(a.snap)
                print(f"RESULT snapshot of the Retire menu: {a.snap}", flush=True)
                return 0
            tag = f"r{rnd}"
            r = run_menu_retire(h, a.win, shots, tag, True, a.final)
            print(f"RESULT round {rnd} retire: {r}", flush=True)
            good = bool(r.get("shown")) and bool(r.get("still_shown"))
            if blobs:
                n, bad = payload_report(h, blobs)
                print(f"RESULT round {rnd} payload after the picture: {n} blobs, {len(bad)} differ {bad}", flush=True)
                good &= not bad
            print(f"RESULT round {rnd}: picture on screen (non-black {r.get('frac', 0):.2f}, {r.get('colours', 0)} colours): {'yes' if good else 'NO'}", flush=True)
            ok &= good
            if not good:
                try:
                    print("  cpu:", h.debug("r", 0.8)[-420:].replace("\n", " | "), flush=True)
                except Exception:  # noqa: BLE001
                    pass
                break
            if a.final:    # the ending of the game: its pictures and the payload are the whole check (what follows is the end sequence, not a menu)
                break
            time.sleep(2.0)
            h.click(hold=0.3)                                   # 'Click with the left mouse button to go back to the Option Screen'
            back = h.wait_gate("options", 90, 2.0)
            print(f"RESULT round {rnd}: option screen again: {back}", flush=True)
            ok &= back
            if not back:
                break
            h.click_st(160, 85, wait=2.5)                       # START NEW CONQUEST
            if a.win:      # a won island is on the list of conquered lands: the game asks 'are you sure you want to delete all of your conquered lands' (YES / NO)
                dlg = not h.at("options")
                print(f"RESULT round {rnd}: confirm dialog (screen no longer the option screen): {dlg}", flush=True)
                ok &= dlg
                h.click_st(130, 111, wait=2.5)                  # YES
            ch = h.wait_gate("chart", 90, 2.0)
            print(f"RESULT round {rnd}: territory chart: {ch}", flush=True)
            ok &= ch
            if not ch:
                break
            h.click_st(20, 18, wait=1.0)                        # the top-left island
            t1 = time.time()
            while not h.at("game"):
                if time.time() - t1 > 150:
                    break
                time.sleep(3.0)
            g = h.at("game") and h.in_game()
            print(f"RESULT round {rnd}: map view of the next level: {g} (cache cursor ${rd(h, CURSOR) or 0:x})", flush=True)
            ok &= g
            if not g:
                break
        if shots:
            try:
                h.shot(str(shots / "end.png"))
            except RuntimeError:
                pass
        print(f"CELL DONE {name}: {'OK' if ok else 'FAIL'}", flush=True)
        return 0 if ok else 2
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        print(f"CELL FAILED {name}: {e!r}", flush=True)
        return 1
    finally:
        if h is not None:
            h.close()


def make_img_pm(img: Path, **kw):
    """The all-games hard disk image as the user runs it (run_megaste.sh): a private copy as ACSI disk 0, key P at the PMBOOT prompt."""
    sys.path.insert(0, str(HERE))
    import pm  # noqa: E402

    class ImgPM(pm.PM):
        def __init__(self, **kw2):
            R = Path(tempfile.mkdtemp(prefix="strun-"))
            home = R / "home"
            (home / ".config/hatari").mkdir(parents=True, exist_ok=True)
            txt = (Path.home() / ".config/hatari/hatari.cfg").read_text()
            txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
            (home / ".config/hatari/hatari.cfg").write_text(txt)
            shutil.copy(img, R / "hd.img")
            kw2.setdefault("overlay", Path("/nonexistent"))
            kw2.setdefault("autorun", None)
            kw2["files"] = []
            extra = list(kw2.pop("extra", [])) + ["--gemdos-drive", "skip", "--acsi", f"0={R / 'hd.img'}", "--fast-boot", "no"]
            import os
            import subprocess
            real_popen = subprocess.Popen

            def popen(args, *a, **k):           # the harness always adds `--harddrive <dir>`: with that GEMDOS drive HDDRIVER's start-up halts the Mega STE (double bus error)
                if isinstance(args, list) and "--harddrive" in args:
                    i = args.index("--harddrive")
                    args = args[:i] + args[i + 2:]
                return real_popen(args, *a, **k)

            old = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            subprocess.Popen = popen
            try:
                pm.Hatari.__init__(self, game_dir=pm.GAME, workdir=str(R), extra=extra, **kw2)
            finally:
                subprocess.Popen = real_popen
                os.environ["HOME"] = old
            self.state = R / "state.sav"

        def boot_to_game(self, *args, **kwargs):
            """TOS 2.06 memory test + HDDRIVER + PMBOOT: press P (PMBOOT waits about 3 s for it) once a second until the screen, white until then
            (memory test, desktop), turns dark (the game's intro); then the usual navigation."""
            from PIL import Image, ImageStat
            t0, bright = time.time(), False
            while time.time() - t0 < 420:
                self.key("p")
                try:
                    m = ImageStat.Stat(Image.open(self.shot()).convert("L").crop((100, 60, 700, 400))).mean[0]
                except RuntimeError:
                    if time.time() - t0 < 60:          # Hatari is still starting
                        time.sleep(2.0)
                        continue
                    raise RuntimeError("Hatari does not answer during the boot of the image (CPU halted?)")
                bright |= m > 150
                if bright and m < 60:
                    break
                time.sleep(1.0)
            print(f"image: game screen after {time.time() - t0:.0f} s", flush=True)
            return super().boot_to_game(*args, **kwargs)

    h = ImgPM(**kw)
    orig_key = h.key

    def key(keysym, hold=0.15):
        if keysym == "space" and h.peekw(0x10A6) == 0x41F9:
            return
        orig_key(keysym, hold)

    h.key = key
    return h


if __name__ == "__main__":
    sys.exit(main())
