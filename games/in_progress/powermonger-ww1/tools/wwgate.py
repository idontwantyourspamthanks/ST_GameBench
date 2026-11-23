#!/usr/bin/env python3
"""Regression gates for the WW1 floppy builds (cold boots in Hatari; every line `GATE <name> PASS|FAIL <evidence>`).

    python3 tools/wwgate.py cell --disk build/default/floppy.st [--manifest build/default/manifest.json] [--steps boot,map,lose,win,round3]
                              [--machine ste --tos 1.62 --mem 1024] [--tag NAME] [--workdir DIR]
    python3 tools/wwgate.py handover --disk build/core_only/floppy.st      # RAM at the hand-over vs the original (core only: game image identical)

Steps (each builds on the previous one; a failed step stops the cell):
  boot    cold boot -> name prompt -> option screen.  Marker $727F8, site bytes read back, credit line visible (iff pm_credit is in the build).
  map     START NEW CONQUEST (+ the game's own disk swap: original Powermonger disk, then the WW1 disk) -> chart -> island -> map view,
          world counter ticking.
  lose    Option -> GAME -> RETIRE: the lose picture is shown and stays (the master v1.1 crash happened AFTER it first showed),
          the resource-cache cursor moved, payload region unchanged.  Click -> option screen again.
  win     START NEW CONQUEST -> chart -> island (-> question) -> map view -> RETIRE with the 'conquered' balance forced: the win picture.
  round3  click -> option screen -> START NEW CONQUEST ('delete all conquered lands' dialog -> YES) -> chart -> map view again.
The payload check compares $72000..$77FFF with the build's expect.bin (payload + known fill pattern + zeros): ANY byte the game writes there
(a cache copy, a buffer, a stack) is a failure.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
from PIL import Image  # noqa: E402

SHOTS = ROOT / "work" / "shots" / "stage02"
IMG_BASE, IMG_END = 0x72000, 0x78000
MARKER = 0x727F8


class Gate:
    def __init__(self, tag):
        self.tag, self.ok = tag, True

    def line(self, name, ok, detail=""):
        self.ok &= bool(ok)
        print(f"GATE {self.tag} {name} {'PASS' if ok else 'FAIL'} {detail}", flush=True)
        return ok


def pic_stats(h, name=None):
    """(fraction of non-black pixels, number of distinct colours) of the 320x200 picture area of a screenshot."""
    p = h.shot(str(SHOTS / f"{name}.png") if name else None)
    im = Image.open(p).convert("RGB").crop((96, 58, 736, 458))
    px = list(im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata())
    nb = sum(1 for c in px if c != (0, 0, 0))
    return nb / len(px), len(set(px))


def diff_spans(got: bytes, ref: bytes, base: int, gap: int = 64):
    """Spans [a, b) (absolute addresses) where got != ref; spans closer than `gap` bytes are merged."""
    import numpy as np
    idx = np.nonzero(np.frombuffer(got, np.uint8) != np.frombuffer(ref, np.uint8))[0]
    spans = []
    for i in idx.tolist():
        if spans and i - spans[-1][1] < gap:
            spans[-1][1] = i + 1
        else:
            spans.append([i, i + 1])
    return [(base + a, base + b) for a, b in spans]


def payload_diff(h, expect: bytes, mask=()):
    """Spans of $72000..$77fff that differ from the expected image.  `mask` = [(addr, len)]: the patches' own run-time data blocks
    (declared with `; data:`), which the patch code legitimately writes; compared as equal here."""
    got = bytearray(h.ram(IMG_BASE, IMG_END - IMG_BASE))
    for a, ln in mask:
        got[a - IMG_BASE:a - IMG_BASE + ln] = expect[a - IMG_BASE:a - IMG_BASE + ln]
    return diff_spans(bytes(got), expect, IMG_BASE)


def fmt_spans(spans, k=6):
    return ", ".join(f"${a:x}-${b - 1:x}" for a, b in spans[:k]) + (f" (+{len(spans) - k} more)" if len(spans) > k else "")


def cell(a):
    SHOTS.mkdir(parents=True, exist_ok=True)
    man = json.loads(Path(a.manifest).read_text()) if a.manifest else None
    # the original disk (no manifest): the game itself must leave $72000..$77fff all zero
    expect = bytearray((Path(a.manifest).parent / "expect.bin").read_bytes()) if man else bytearray(IMG_END - IMG_BASE)
    tag = a.tag or Path(a.disk).parent.name
    g = Gate(f"{tag}/{a.machine}-{a.tos}-{a.mem}K")
    machine = a.machine
    kw = dict(machine=machine, tos=pmww.TOS[a.tos], memsize_kb=a.mem, extra=a.extra.split())
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, **kw)
    steps = a.steps.split(",")
    try:
        t0 = time.time()
        log = lambda s: print(f"  [{tag}] {s}", flush=True)
        # ---- boot
        h.boot_to_options(log=log)
        time.sleep(2.0)
        h.shot(str(SHOTS / f"{tag}_{machine}_options.png"))
        marker = bytes(h.ram(MARKER, 4))
        dmask = [(d["addr"], d["len"]) for d in man.get("data", [])] if man else []
        noprot = bool(man and "pm_noprot" in man["patches"] and not a.corrupt)      # a corrupt build refuses every optional site: the game stays original
        keydisk = bool(man and "pm_nokeydisk" in man["patches"] and not a.corrupt)
        def region(name):
            d = payload_diff(h, expect, dmask)
            g.line(f"payload@{name}", not d, ("unchanged" if man else "region $72000-$77fff all zero") if not d else fmt_spans(d))

        if man:
            want = b"PMPF" if a.corrupt else b"PMPO"
            expect[MARKER - IMG_BASE:MARKER - IMG_BASE + 4] = want          # the only byte the hook itself writes in the region
            g.line("marker", marker == want, f"${MARKER:x} = {marker!r} (want {want!r})")
            for s in man["sites"]:
                want_s = s["orig"][:len(s["new"])] if a.corrupt else s["new"]       # refused build: the game stays untouched
                got = h.ram(s["addr"], len(s["new"]) // 2).hex()
                g.line(f"site {s['name']}", got == want_s, f"${s['addr']:x} = {got} (want {want_s}{' = original, patch refused' if a.corrupt else ''})")
            region("options")
            if "pm_credit" in man["patches"]:
                im = Image.open(h.shot()).convert("RGB").crop((96, 58 + 2 * 194, 736, 58 + 2 * 200))
                cols = {}
                for c in im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata():
                    cols[c] = cols.get(c, 0) + 1
                nb = {c: n for c, n in cols.items() if c != (0, 0, 0)}
                vis = sum(nb.values()) > 100 and len(nb) <= 2
                g.line("credit visible" if not a.corrupt else "credit absent (patch refused)", vis != a.corrupt, f"rows 194-199: {sum(nb.values())} px of colours {sorted(nb)}")
                im.save(SHOTS / f"{tag}_{machine}_credit_rows.png")
        else:
            g.line("marker (original)", marker == b"\0\0\0\0", repr(marker))
            region("options")
        g.line("boot", True, f"{time.time() - t0:.0f}s")
        if "map" in steps:
            if noprot:
                g.line("noprot flag", h.peekl(0x15998) == 0x2C, f"$15998 = ${h.peekl(0x15998):08x} (want $0000002c) before the first land")
                h.watch_pcs([0xACC4, 0xAE20, 0xB232, 0xB39C, 0xBBD2, 0x1CF7C, 0x13CF2])           # check start, flag clear, answer check, wrong-answer box, 'Please wait' box
            h.options_to_map(log=log, noprot=noprot, swap=not keydisk)
            if noprot:
                hits = h.hits()
                g.line("noprot: the check never ran", all(hits.get(a, 0) == 0 for a in (0xACC4, 0xAE20, 0xB232, 0xB39C)),
                       "hits " + ", ".join(f"${a:x}:{hits.get(a, 0)}" for a in (0xACC4, 0xAE20, 0xB232, 0xB39C)))
                g.line("noprot: 'Please wait' box skipped (stub reached)", hits.get(0xBBD2, 0) >= 1, f"$bbd2 reached {hits.get(0xBBD2, 0)}x (an `rts` stub)")
                if keydisk:
                    g.line("nokeydisk: the key-disk routine never ran, the flow went on", hits.get(0x1CF7C, 0) == 0 and hits.get(0x13CF2, 0) >= 1,
                           f"$1cf7c hit {hits.get(0x1CF7C, 0)}x, next instruction $13cf2 hit {hits.get(0x13CF2, 0)}x; the Powermonger disk was never inserted")
                h.debug("b all", 0.3)
            else:
                log(f"flag $15998 after the correct answer: ${h.peekl(0x15998):08x}")
            h.shot(str(SHOTS / f"{tag}_{machine}_map.png"))
            g.line("map view", h.ticking(2.0) and h.peekw(pmww.WINDOW_OPEN) == 0, f"counter {h.counter()}, flag $15998 = ${h.peekl(0x15998):08x}")
            region("map")
        if "rate" in steps:
            import wwtick
            if a.mhz != 8:
                h.set_cpuclock(a.mhz)
            time.sleep(2)
            patched = bool(man and "tick_head" in man["patches"])
            line, r = wwtick.rate_numbers(h, None, a.vbls, patched, f"{tag}/{machine} {a.mhz} MHz cold boot map view")
            print(line, flush=True)
            g.line("rate", True, line[5:])
            if patched:
                g.line("world rate = 4.00/s (+-5 %)", 3.8 <= r <= 4.2, f"{r:.3f} world steps per emulated second")
            if a.mhz != 8:
                h.set_cpuclock(8)
        if "soak" in steps:
            c0, t_s, bad, n_win = h.counter(), time.time(), [], 0
            log0 = len(h._logtext())
            last = c0
            while time.time() - t_s < a.soak:
                time.sleep(15)
                c = h.counter()
                n_win += 1
                if c <= last:
                    bad.append((round(time.time() - t_s), last, c))
                last = c
            exc = re.findall(r"(?i)(bus error|address error|illegal instruction|double bus|exception)[^\n]*", h._logtext()[log0:])
            g.line("soak: the world advances in every 15 s window", not bad, f"{n_win} windows over {time.time() - t_s:.0f} s, clock {c0} -> {last} ({(last - c0) / (time.time() - t_s):.2f}/s), stalls {bad}")
            g.line("soak: no CPU exception in the Hatari log", not exc, f"{exc[:3]}")
            region("soak")
        if "saveload" in steps:
            r = h.saveload(log=log)
            g.line("save/load: loaded state == saved state", r["d_saved_loaded"] == 0, f"{r['n']} B: {r['d_saved_loaded']} differ")
            g.line("save/load: the world moved between save and load", r["d_saved_pre"] > 0, f"saved vs the state just before the load: {r['d_saved_pre']} differ")
            g.line("save/load: save disk slot A == saved state", r["disk_eq"] and r["disk_len"] == 800 * 512 and r["slot_flag"] == 0xFF,
                   f"sectors 1-198 equal: {r['disk_eq']}, slot flag ${r['slot_flag']:02x}, image {r['disk_len']} B")
            g.line("save/load: the game runs on after the load", r["ticking"], "")
            region("saveload")
        if "lose" in steps:
            c0 = h.peekl(pmww.CACHE_CURSOR)
            h.retire(win=False, log=log)
            ok, best, seen = _picture(h, f"{tag}_{machine}_lose")
            c1 = h.peekl(pmww.CACHE_CURSOR)
            g.line("lose picture", ok, f"non-black {best[0]:.2f}, {best[1]} colours, seen stable x{seen}; cache cursor ${c0:x} -> ${c1:x}")
            time.sleep(8)
            fr, nc = pic_stats(h)
            g.line("lose picture still there after 8 s", fr > 0.3 and nc >= 12, f"non-black {fr:.2f}, {nc} colours")
            region("lose")
            h.click_st(160, 100, wait=4)
            g.line("back to option screen", h.wait_text("Welcome to the World", timeout=20), "")
        if "win" in steps:
            h.click_st(*pmww.START_NEW_XY, wait=3.0)
            h.chart_to_map(log=log, noprot=noprot)
            g.line("map view (2nd land)", h.ticking(2.0), f"counter {h.counter()}")
            h.retire(win=True, log=log)
            ok, best, seen = _picture(h, f"{tag}_{machine}_win")
            g.line("win picture", ok, f"non-black {best[0]:.2f}, {best[1]} colours, seen stable x{seen}; cache cursor ${h.peekl(pmww.CACHE_CURSOR):x}")
            time.sleep(8)
            fr, nc = pic_stats(h)
            g.line("win picture still there after 8 s", fr > 0.3 and nc >= 12, f"non-black {fr:.2f}, {nc} colours")
            region("win")
            h.click_st(160, 100, wait=4)
            g.line("back to option screen (after win)", h.wait_text("Welcome to the World", timeout=20), "")
        if "round3" in steps:
            h.click_st(*pmww.START_NEW_XY, wait=3.0)
            h.shot(str(SHOTS / f"{tag}_{machine}_after_win_start.png"))
            dlg = h.peekw(pmww.WINDOW_OPEN) != 0 and "WELCOME" not in h.wtext().upper()
            log(f"confirm dialog after START NEW CONQUEST on a won land: {dlg} ({h.wtext().strip()[:60]!r})")
            if dlg:
                h.click_st(130, 111, wait=3.0)                       # YES (master: 'delete all of your conquered lands')
            h.chart_to_map(log=log, noprot=noprot)
            g.line("map view (3rd land)", h.ticking(2.0), f"counter {h.counter()}")
            region("round3")
        print(f"CELL DONE {g.tag}: {'OK' if g.ok else 'FAIL'} ({time.time() - t0:.0f}s)", flush=True)
        return 0 if g.ok else 2
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        try:
            h.shot(str(SHOTS / f"{tag}_{machine}_failure.png"))
        except Exception:  # noqa: BLE001
            pass
        print(f"CELL FAILED {g.tag}", flush=True)
        return 1
    finally:
        h.close()


def _picture(h, name):
    """Wait for a Retire picture (lots of non-black pixels and colours) to be stable on three consecutive shots."""
    t = time.time()
    best, seen = (0.0, 0), 0
    while time.time() - t < 75:
        try:
            fr, nc = pic_stats(h, None)
        except RuntimeError:
            fr, nc = 0.0, 0
        if nc >= 12:                                              # a mid-redraw frame (1 colour) must not be reported as the picture
            best = max(best, (fr, nc))
        if fr > 0.30 and nc >= 12:
            seen += 1
            if seen >= 3:
                break
        else:
            seen = 0
        time.sleep(2.0)
    try:
        h.shot(str(SHOTS / f"{name}.png"))
    except RuntimeError:
        pass
    return seen >= 3, best, seen


def handover(a):
    """RAM at the hand-over of a build vs the original's work/dumps/entry576.bin."""
    import hashlib
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir)
    tag = a.tag or Path(a.disk).parent.name
    try:
        out = h.R / "entry.bin"
        (h.R / "d1.txt").write_text(f"r\nsavebin {out} 0 $100000\n")
        h.cmd(f"hatari-debug b pc = $576 && ($576).w = $41f9 :trace :once :file {h.R / 'd1.txt'}")
        t = time.time()
        while not out.exists() or out.stat().st_size < 0x100000:
            if time.time() - t > 120:
                raise TimeoutError("hand-over not reached")
            time.sleep(1)
        time.sleep(2)
        got = out.read_bytes()
        log = h._logtext()
        regs = dict(re.findall(r"\b(D[0-7]|A[0-7]) ([0-9A-F]{8})", log[log.rfind("> r"):]))
        sr = re.search(r"SR=([0-9A-F]{4})", log[log.rfind("> r"):])
        regs["SR"] = sr.group(1) if sr else "?"
        # the original's register file when it enters $576 (delivery.md, measured with the unmodified disk)
        want = dict(D0="00070080", D1="FA114E73", D2="00000000", D3="00000000", D4="00000000", D5="00000000", D6="00000000", D7="00000000",
                    A0="0000053A", A1="00012EB6", A2="0001D4AA", A3="00000000", A4="0001D4AA", A5="0001D4AA", A6="000F7FC6", A7="000004F8", SR="2304")
        diff_r = {k: (regs.get(k), v) for k, v in want.items() if regs.get(k) != v}
        print(f"GATE {tag} handover registers + SR + a7 equal the original's: {'PASS' if not diff_r else 'FAIL'} {diff_r if diff_r else ''} "
              f"(A7={regs.get('A7')} SR={regs.get('SR')})")
        ref = (ROOT / "work" / "dumps" / "entry576.bin").read_bytes()
        (ROOT / "work" / "dumps" / f"entry576_{tag}.bin").write_bytes(got)
        lo, hi = 0x576, 0x1D2AE
        same = got[lo:hi] == ref[lo:hi]
        print(f"GATE {tag} handover game image ${lo:x}-${hi - 1:x} identical to the original's: {'PASS' if same else 'FAIL'} "
              f"(md5 {hashlib.md5(got[lo:hi]).hexdigest()})")
        spans = diff_spans(got, ref, 0)
        print("RAM differing from the original at the hand-over:", fmt_spans(spans, 40))
        return 0 if same else 2
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("cell", "handover"):
        p = sub.add_parser(n)
        p.add_argument("--disk", required=True)
        p.add_argument("--manifest")
        p.add_argument("--steps", default="boot,map,lose,win,round3")
        p.add_argument("--machine", default="ste")
        p.add_argument("--tos", default="1.62")
        p.add_argument("--mem", type=int, default=1024)
        p.add_argument("--tag")
        p.add_argument("--extra", default="", help='extra Hatari options as one string, e.g. "--mmu true --cpuclock 32" (TT)')
        p.add_argument("--mhz", type=int, default=8, help="rate step: CPU clock (hatari-option --cpuclock)")
        p.add_argument("--soak", type=int, default=300, help="soak step: seconds of play")
        p.add_argument("--vbls", type=int, default=800, help="rate step: VBLs measured")
        p.add_argument("--corrupt", action="store_true", help="the build has a deliberately corrupted site: expect PMPF and an unpatched game")
        p.add_argument("--workdir")
    a = ap.parse_args()
    return {"cell": cell, "handover": handover}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
