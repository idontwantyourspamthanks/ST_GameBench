#!/usr/bin/env python3
"""Keyboard-shortcut gate (master's keygate idea): a key writes the SAME click words as a real mouse click on its cell.

    python3 tools/wwkeys.py --disk build/default/floppy.st --manifest build/default/manifest.json [--workdir DIR] [--phantom]

Cold boot of the built floppy to the map view; for every entry of the key table KT (patches/qol_keys.s) the pass-time click state is captured at
`$13e82` (`tst.w $2edb6`, the first instruction after the dispatcher call the hook sits in front of): click position words $2edae/$2edb0, left latch
$2edb6, right latch $2edb8, right-held $2edbe.  Once for a REAL click (pointer closed in on the exact table point, tolerance 0; xdotool button) and once for the
real KEY (xdotool, Shift for the right-button variants).  Gate = all five words equal.  Then the command word $5a836 is followed through click, key, key, click
(a command icon toggles: [2*id, 0, 2*id, 0]) so the key is also proven to act through the game's own handler.
`--phantom`: the phantom-click gate (master work/notes/phantom_click.md): letters typed at the name prompt must not be replayed as icon clicks.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
import wwgrid  # noqa: E402

DISPATCH = 0x13E82
WORDS = ["($2edae).w", "($2edb0).w", "($2edb6).w", "($2edb8).w", "($2edbe).w"]
CMD = 0x5A836
SC2SYM = {0x02: "1", 0x03: "2", 0x04: "3", 0x6D: "KP_1", 0x6E: "KP_2", 0x6F: "KP_3", 0x1E: "a", 0x20: "d", 0x12: "e", 0x21: "f", 0x22: "g", 0x23: "h", 0x17: "i",
          0x26: "l", 0x32: "m", 0x31: "n", 0x18: "o", 0x10: "q", 0x13: "r", 0x1F: "s", 0x14: "t", 0x2D: "x", 0x15: "y", 0x3B: "F1", 0x3C: "F2", 0x3D: "F3", 0x3E: "F4",
          0x1A: "bracketleft", 0x1B: "bracketright", 0x0D: "equal", 0x4E: "KP_Add", 0x0C: "minus", 0x4A: "KP_Subtract"}
CLOSE_XY = (57, 4)                                     # the tick in the top-right corner of the option window closes it
TOGGLE_IDS = {1, 3, 4, 6, 7, 8, 13, 14, 15, 16}      # command icons that select / deselect `$5a836 = 2 * id` (icon 2, Transfer Men: neither click nor key sets the word on the start position)


def parse_kt():
    src = (ROOT / "patches" / "qol_keys.s").read_text()
    return [(int(m.group(1), 16), int(m.group(2)), int(m.group(3)), int(m.group(4))) for m in re.finditer(wwgrid.KEYPAT, src, re.M)]


def capture(h, left_cond, action, wait=2.0):
    """Arm breakpoints at the dispatch point for each latch condition, run `action()`, return the first captured word list (or None)."""
    f = h.R / "kw.txt"
    f.write_text("".join(f"e {w}\n" for w in WORDS))
    h.debug("b all", 0.3)
    n = len(h._logtext())
    for cond in left_cond:
        h.cmd(f"hatari-debug b pc = ${DISPATCH:x} && {cond} :trace :file {f}")
        time.sleep(0.1)
    action()
    time.sleep(wait)
    out = h._logtext()[n:]
    h.debug("b all", 0.3)
    blks = out.split("Reading debugger commands")[1:]
    got = []
    for b in blks:
        vals = [int(v, 16) for v in re.findall(r"\$([0-9a-f]+) \(hex\)", b)]
        if len(vals) >= 5:
            got.append(vals[:5])
    return got


def exact_goto(h, x, y):
    for _ in range(4):
        p = h.goto_st(x, y, tol=0)
        if tuple(p) == (x, y):
            return p
    return h.mpos()


def key_press(h, sym, shift):
    h._xdo("windowfocus", h.win)
    h._xdo("mousemove", "--window", h.win, "416", "294")
    time.sleep(0.1)
    if shift:
        h._xdo("keydown", "Shift_L")
        time.sleep(0.05)
    h._xdo("keydown", sym)
    time.sleep(0.12)
    h._xdo("keyup", sym)
    if shift:
        time.sleep(0.05)
        h._xdo("keyup", "Shift_L")


def phantom(h, a, man, line, ok):
    """Name typed at the name prompt = shortcut letters.  After the map view starts nothing may have been replayed as an icon click: command word
    $5a836 = 0, the key-pending bytes (qol_keys data $73040..$730c8) are all zero, the first real key afterwards still works."""
    t0 = time.time()
    h.boot_to_options(name=a.phantom)
    h.options_to_map(noprot="pm_noprot" in man["patches"], swap="pm_nokeydisk" not in man["patches"], t0=t0)
    time.sleep(6)
    cmd = h.peekw(CMD)
    pend = h.ram(0x73040, 0x90)
    lastv = int.from_bytes(h.ram(0x730C4, 4), "big")
    nz = [i for i, b in enumerate(pend[4:0x84]) if b]
    line(f"phantom: name {a.phantom!r}: no command replayed", cmd == 0, f"$5a836 = {cmd}, pending key bytes set: {[hex(i) for i in nz]}")
    got = capture(h, ["($2edb6).w = 1"], lambda: key_press(h, "f", False))
    line("phantom: a real key afterwards works", bool(got) and got[0][:3] == [202, 181, 1], f"click words {got[:1]}")
    h.shot(str(ROOT / "work" / "shots" / "stage02" / f"{a.tag}_phantom.png"))
    print(f"CELL DONE {a.tag}: {'OK' if ok() else 'FAIL'}", flush=True)
    return 0 if ok() else 2


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--workdir")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--tag", default="keys")
    ap.add_argument("--only", help="comma separated scan codes (hex) to test")
    ap.add_argument("--phantom", metavar="NAME", help="phantom-click gate: boot with this player name (letters = shortcut keys) and check that nothing was replayed")
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text()) if a.manifest else {"patches": []}
    noprot = "pm_noprot" in man["patches"]
    keydisk = "pm_nokeydisk" in man["patches"]
    ok_all = True

    def line(name, ok, detail=""):
        nonlocal ok_all
        ok_all &= bool(ok)
        print(f"GATE {a.tag} {name} {'PASS' if ok else 'FAIL'} {detail}", flush=True)

    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=a.mem)
    try:
        if a.phantom:
            return phantom(h, a, man, line, lambda: ok_all)
        h.boot_to_map(noprot=noprot, swap=not keydisk)
        line("map view", h.ticking(2.0), f"counter {h.counter()}")
        time.sleep(3)
        kt = parse_kt()
        todo = [e for e in kt if not a.only or e[0] in {int(v, 16) for v in a.only.split(",")}]
        seen = {}
        n_ok = 0
        for sc, fl, x, y in todo:
            sym = SC2SYM[sc]
            variants = [(False, "left")] + ([(True, "shift (right button)")] if fl & 1 else [])
            for shift, label in variants:
                latch = "($2edb8).w = 1" if shift else "($2edb6).w = 1"
                conds = [latch] if shift else ["($2edb6).w = 1"]
                if shift:
                    conds = ["($2edb8).w = 1"]
                # real click (the right button variant: xdotool button 3)
                def click():
                    exact_goto(h, x, y)
                    h.click(button="3" if shift else "1", hold=0.3)
                real = capture(h, conds, click)
                real_win = h.peekw(pmww.WINDOW_OPEN) != 0
                if real_win:
                    h.click_st(*CLOSE_XY, wait=2.0)
                h.home()
                # a second real click would toggle commands: first record, then the key
                key = capture(h, conds, lambda: key_press(h, sym, shift))
                if not real or not key:
                    line(f"key {sym}{' +Shift' if shift else ''} == click ({x},{y})", False, f"no capture: real {real} key {key}")
                    continue
                r, k = real[0], key[0]
                same = r == k
                n_ok += same
                line(f"key {sym}{' +Shift' if shift else ''} == click ({x},{y})", same, f"click words {r} key words {k}")
                time.sleep(1.0)
                key_win = h.peekw(pmww.WINDOW_OPEN) != 0
                if key_win or real_win:
                    line(f"key {sym} opens the same window as the click", key_win == real_win, f"click opened a window: {real_win}, key: {key_win}")
                if key_win:
                    swallowed = capture(h, ["($2edb6).w = 1"], lambda: key_press(h, "h", False), wait=2.0)
                    line("keys are swallowed while a window is open (h)", not swallowed, f"captured {swallowed}")
                    h.click_st(*CLOSE_XY, wait=2.0)
                    line("window closed", h.peekw(pmww.WINDOW_OPEN) == 0, "click on the window's tick (57,4)")
        print(f"KEYS {n_ok} of {sum(2 if e[1] & 1 else 1 for e in todo)} key/click pairs identical")
        # command word through the game's own handler: click, key, key, click
        for sc, fl, x, y in todo:
            i = wwgrid.icon(x, y)
            if sc in (0x03, 0x04) or i not in TOGGLE_IDS or sc in seen:
                continue
            seen[sc] = 1
            seq = []
            def read():
                time.sleep(1.5)
                seq.append(h.peekw(CMD))
            exact_goto(h, x, y)
            h.click(hold=0.3)
            read()
            key_press(h, SC2SYM[sc], False)
            read()
            key_press(h, SC2SYM[sc], False)
            read()
            exact_goto(h, x, y)
            h.click(hold=0.3)
            read()
            want = [2 * i, 0, 2 * i, 0]
            line(f"command word through click/key/key/click: {SC2SYM[sc]} (icon {i})", seq == want, f"$5a836 = {seq} want {want}")
        h.shot(str(ROOT / "work" / "shots" / "stage02" / f"{a.tag}_end.png"))
        print(f"CELL DONE {a.tag}: {'OK' if ok_all else 'FAIL'}", flush=True)
        return 0 if ok_all else 2
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
