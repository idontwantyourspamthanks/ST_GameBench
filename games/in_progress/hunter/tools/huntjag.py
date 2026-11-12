#!/usr/bin/env python3
"""Jaguar pad tests for Hunter (patches/jag_pad.s + jag_stick.s; work/notes/jagpad.md).  Hatari emulates the STE/Falcon pads
(--configfile tools/jag_pad_{a,b,ab}.cfg: host keys are pad buttons).

    python3 tools/huntjag.py live  [--snapshot 1mb_foot_stand] [--cfg a|b|ab|none] [--pad a|b] [--keys 4|F5|..] [--stick] [--shots DIR]
    python3 tools/huntjag.py kbd   [--snapshot 1mb_foot_stand]       # pad button vs the same key typed on the keyboard: same game state
    python3 tools/huntjag.py prof  [--snapshot 1mb_foot_stand]       # cycles per VBL of the pad code, pad configured vs no pad
    python3 tools/huntjag.py cold  [--game build/jag_hd] [--machine st|ste|megaste|tt] [--mem 1024] [--cfg a] [--buttons] [--stick]
    python3 tools/huntjag.py floppy [--disk1 build/jag_fl/HUNTER_disk1.st] [--machine ste|falcon] [--blind --pb-at 35] [--cfg a] [--buttons]

Host keys.  Pad A (jag_pad_a.cfg): Up/Down/Left/Right, z = A, x = B, v = C, o = Option, p = Pause, F5 = *, F6 = #, 0-9 = keypad.
Pad B (jag_pad_b.cfg): w s a d, t = A, y = B, u = C, m = Option, l = Pause, F7 = *, F8 = #, KP_0-KP_9 = keypad.  jag_pad_ab.cfg = both.
--stick adds Hatari's keyboard joystick on port 1 (cursor keys + Control_R), i.e. the real joystick next to the pad.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from hunter import Hunter, SNAP  # noqa: E402
from stharness import MACHINE_TOS, TOS  # noqa: E402

JAG_ST, JAG_DIR, JAG_G, JAG_P, JAG_OLD, JAG_OLD2 = 0x8D9E0, 0x8D9E4, 0x8D9E8, 0x8D9EA, 0x8D9FA, 0x8D9FE      # state block (jag_pad.s: JAG + J_*)
CFG = {"a": str(HERE / "jag_pad_a.cfg"), "b": str(HERE / "jag_pad_b.cfg"), "ab": str(HERE / "jag_pad_ab.cfg")}
JAG = ["jag_pad", "jag_stick"]

# pad button -> expected effect, in the order of the tests; host keys per pad
BUTTONS = [("Up", "N"), ("Down", "S"), ("Left", "W"), ("Right", "E"), ("A", "fire"), ("B", "fire"), ("C", "Return $1c next weapon"),
           ("Option", "Space $39 leave vehicle"), ("Pause", "P $19 pause"), ("Pause", "P $19 un-pause"), ("1", "R $13 radar"),
           ("2", "Help $62 overlay map"), ("3", "L $26 log"), ("5", "F $21 flare"), ("6", "C $2e clock"), ("7", "cursor Up $48 (held)"),
           ("9", "cursor Down $50 (held)"), ("#", "unassigned"), ("0", "unassigned"), ("8", "unassigned")]
LEAVE_3D = [("4", "A $1e drone map (leaves the 3D loop)"), ("*", "Esc $01 game options (leaves the 3D loop)")]    # one per run
HOST = {"a": {"Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right", "A": "z", "B": "x", "C": "v", "Option": "o", "Pause": "p",
              "*": "F5", "#": "F6", **{str(i): str(i) for i in range(10)}},
        "b": {"Up": "w", "Down": "s", "Left": "a", "Right": "d", "A": "t", "B": "y", "C": "u", "Option": "m", "Pause": "l",
              "*": "F7", "#": "F8", **{str(i): f"KP_{i}" for i in range(10)}}}


def snap(name: str) -> str:
    return str(SNAP / (name if name.endswith(".sav") else name + ".sav"))


def pad_extra(cfg: str, stick: bool = False, mmu: bool = False) -> list[str]:
    return ((["--configfile", CFG[cfg]] if cfg != "none" else []) + (["--joy1", "keys"] if stick else ["--joy1", "none"])     # the config first: it resets joystick 1
            + (["--mmu", "true"] if mmu else []))


def live_set(only: list[str], ste: bool = True) -> tuple[str, dict]:
    out = GAME / "build" / "live" / "jag"
    subprocess.run([sys.executable, str(HERE / "huntpatch.py"), "live", "--only", *only, "--out", str(out)] + ([] if ste else ["--no-ste"]),
                   check=True, cwd=GAME, stdout=subprocess.DEVNULL)
    return str(out), json.loads(Path(str(out) + ".json").read_text())


def apply_live(h: Hunter, live: str, spec: dict):
    h.debug(f"loadbin {live}.img ${spec['img_base']:x}", 1.0)
    for s in sorted(spec["sites"], key=lambda s: s["name"] == "jag_pad"):      # the hook last: the probe of a plain ST restores both sites
        raw = bytes.fromhex(s["new"])
        for o in range(0, len(raw), 40):
            h.debug(f"w ${s['addr'] + o:x} " + " ".join(f"${b:02x}" for b in raw[o:o + 40]), 0.4)


def state(h: Hunter) -> dict:
    b = h.peek(0x806 + 0xCE, 4)
    k = h.peek(0x806 + 0x1C4, 2)
    j = h.peek(JAG_ST, 16) + h.peek(JAG_ST + 16, 16)
    return dict(ce=b[0], cf=b[1], d0=b[2], d1=b[3], mode=h.peek(0x899, 1)[0], sc=k[0], asc=k[1], st=j[0], jdir=j[4],
                s1=int.from_bytes(j[26:30], "big"), s2=int.from_bytes(j[30:32], "big"))


def fmt(s: dict) -> str:
    return (f"ce={s['ce']:02x} cf={s['cf']:02x} d0={s['d0']:02x} d1={s['d1']:02x} $93={s['mode']:02x} lastkey sc/ascii={s['sc']:02x}/{s['asc']:02x}  "
            f"JAG_ST={s['st']:02x} JAG_DIR={s['jdir']:02x} S1={s['s1']:08x} S2={s['s2']:04x}")


def press_table(h: Hunter, pad: str, rows, shots: str | None = None):
    for label, what in rows:
        key = HOST[pad][label]
        h.hold(key)
        time.sleep(0.8)
        s = state(h)
        if shots:
            Path(shots).mkdir(parents=True, exist_ok=True)
            h.shot(str(Path(shots) / f"pad{pad}_{label.replace('*', 'star').replace('#', 'hash')}.png"))
        h.release(key)
        time.sleep(0.5)
        print(f"pad {pad.upper()} {label:6s} ({key:7s}) {what:34s}", fmt(s))
    print("released".ljust(52), fmt(state(h)))


def rows_for(keys: str | None):
    if not keys:
        return BUTTONS
    want = keys.split(",")
    return [r for r in BUTTONS + LEAVE_3D if r[0] in want]


def cmd_live(a):
    live, spec = live_set(JAG)
    h = Hunter(snapshot=snap(a.snapshot), extra=pad_extra(a.cfg, a.stick))
    try:
        time.sleep(3)
        print("before patch:", fmt(state(h)))
        if a.hold_at_start:                                # a pad button held while the probe runs: the idle check must refuse the pad
            h.hold(HOST["a"][a.hold_at_start])
            time.sleep(0.5)
        apply_live(h, live, spec)
        time.sleep(1.5)
        if a.hold_at_start:
            h.release(HOST["a"][a.hold_at_start])
            time.sleep(0.5)
        print("idle (patched)".ljust(52), fmt(state(h)))
        for pad in a.pad.split(","):
            press_table(h, pad, rows_for(a.keys), a.shots)
        if a.stick and a.cfg == "b":                      # real joystick (cursor keys, Control_R fire) together with pad B
            for stick, padbtn in (("Up", "Left"), ("Left", "Up"), ("Control_R", "Right"), ("Up", "A")):
                h.hold(stick, HOST["b"][padbtn])
                time.sleep(0.8)
                s = state(h)
                h.release(stick, HOST["b"][padbtn])
                time.sleep(0.5)
                print(f"real stick {stick:9s} + pad B {padbtn:6s}".ljust(52), fmt(s))
    finally:
        h.close()


def cmd_kbd(a):
    """The same keys typed on the host keyboard (no pad configured) and pressed on the pad: the game must end up in the same state."""
    live, spec = live_set(JAG)
    pairs = [("C", "Return", "Return"), ("Option", "space", "space"), ("Pause", "p", "p"), ("Pause", "p", "p"), ("1", "r", "r"), ("3", "l", "l"),
             ("5", "f", "f"), ("6", "c", "c")]
    res = {}
    for tag, cfg in (("pad", "a"), ("keyboard", "none")):
        h = Hunter(snapshot=snap(a.snapshot), extra=pad_extra(cfg))
        try:
            time.sleep(3)
            apply_live(h, live, spec)
            time.sleep(1.5)
            rows = []
            for label, kb, _ in pairs:
                key = HOST["a"][label] if tag == "pad" else kb
                h.hold(key)
                time.sleep(0.8)
                h.release(key)
                time.sleep(0.6)
                s = state(h)
                g = h.peek(0x806 + 0x24A, 4).hex() + "/" + h.peek(0x806 + 0x252, 2).hex() + "/" + h.peek(0x806 + 0x92, 2).hex()
                rows.append((label, s["mode"], s["sc"], s["asc"], g))
            res[tag] = rows
        finally:
            h.close()
    ok = True
    print(f"{'button':8s} | {'pad: $93 lastkey sc/asc $24a/$252/$92':44s} | keyboard")
    for p, k in zip(res["pad"], res["keyboard"]):
        same = p[1:] == k[1:]
        ok &= same
        print(f"{p[0]:8s} | {p[1]:02x} {p[2]:02x}/{p[3]:02x} {p[4]:36s} | {k[1]:02x} {k[2]:02x}/{k[3]:02x} {k[4]:36s} {'same' if same else 'DIFFERENT'}")
    print("pad == keyboard" if ok else "MISMATCH")


def cmd_inject(a):
    """Cycles the game's key decoder ($b048, called from the poll inside the VBL handler) takes per pad button: the whole call, jsr to return."""
    import threading
    live, spec = live_set(JAG)
    img = Path(live + ".img").read_bytes()
    jsr = spec["img_base"] + img.index(bytes.fromhex("4eb90000b048"))
    h = Hunter(snapshot=snap(a.snapshot), extra=pad_extra("a"))
    try:
        time.sleep(3)
        apply_live(h, live, spec)
        time.sleep(1.0)
        print(f"jsr $b048 at ${jsr:x}, return at ${jsr + 6:x}")
        for label in a.keys.split(","):
            key = HOST["a"][label]

            def press():
                time.sleep(1.5)
                h.hold(key)
                time.sleep(0.5)
                h.release(key)
            t = threading.Thread(target=press)
            t.start()
            rows = h.site_trace([jsr, jsr + 6], vbls=90)
            t.join()
            calls = [(r0, r1) for r0, r1 in zip(rows[::2], rows[1::2]) if r0[0] == jsr and r1[0] == jsr + 6]
            print(f"pad {label:7s} ({key:5s}): {len(calls)} call(s) of $b048, cycles " + ", ".join(str(r1[1] - r0[1]) for r0, r1 in calls)
                  + f"   (an IKBD byte at 7812 baud arrives every 10240 cycles)")
            time.sleep(1.0)
    finally:
        h.close()


def cmd_prof(a):
    live, spec = live_set(JAG, not a.plain_st)      # --plain-st: FLAGS as a plain ST (no DMA sound): the probe says no, as on an ST / Mega ST
    for tag, cfg in (("pad A configured", "a"), ("no pad", "none")):
        h = Hunter(snapshot=snap(a.snapshot), extra=pad_extra(cfg))
        try:
            time.sleep(3)
            apply_live(h, live, spec)
            time.sleep(1.0)
            if cfg != "none":
                h.hold("x")                                 # B held (fire): a busy pad costs no more
                time.sleep(0.5)
            prof = h.profile_cc(250)
            cyc = sum(c[0] for ad, c in prof.items() if 0x8D600 <= ad < 0x8D816)
            mer = sum(c[0] for ad, c in prof.items() if 0x8D9C0 <= ad < 0x8D9D4)
            nm = prof.get(0x8D9C0, (0, 0))[1]                  # merge calls: one per VBL at 50 Hz (world tick every VBL); the hook runs once per VBL too
            n = nm
            # net of what the unpatched game ran there: bclr (20) at $c616, two move.b (24) at $c64c; the sites' own jmp costs 12 each
            net = (cyc + 12 * n - 20 * n + mer + 12 * nm - 24 * nm) / max(n, 1)
            print(f"{tag:16s}: {n} VBL hook calls, {nm} merge calls: blob {cyc / max(n, 1):.1f} + merge {mer / max(n, 1):.1f} cycles per VBL; "
                  f"net added by the two splices {net:.1f} cycles per VBL = {100 * net / 160256:.3f} % of a 160256-cycle VBL")
            if cfg != "none":
                h.release("x")
        finally:
            h.close()


def cold_boot(game: str, machine: str, cfg: str, mem: int, tos: str | None, stick: bool = False):
    import hunter as hmod
    orig = hmod.build_hd
    hmod.build_hd = lambda img, **k: orig(img, game=GAME / game, **k)
    h = hmod.Hunter(machine=machine, tos=TOS[tos] if tos else MACHINE_TOS[machine], memsize_kb=mem,
                    extra=pad_extra(cfg, stick, mmu=machine == "tt"))
    return h, (hmod, orig)


def cmd_cold(a):
    h, (hmod, orig) = cold_boot(a.game, a.machine, a.cfg, a.mem, a.tos, a.stick)
    try:
        stage = h._stage
        h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
        if a.machine in ("st", "megast"):
            from huntpatch import blind_boot          # the reference crops are STE pictures
            blind_boot(h)
        else:
            h.boot_to_game()
        print(f"BOOT OK machine={a.machine} mem={a.mem}K in_game={h.in_game()} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()} sites $c616={h.peek(0xC616, 6).hex()} $c64c={h.peek(0xC64C, 8).hex()}", fmt(state(h)),
              "fps", h.fps(250))
        if a.buttons:
            for pad in a.pad.split(","):
                press_table(h, pad, rows_for(a.keys), a.shots)
        if a.stick:
            for key, what in (("Up", "stick N"), ("Left", "stick W"), ("Control_R", "stick fire")):
                h.hold(key)
                time.sleep(0.8)
                s = state(h)
                h.release(key)
                time.sleep(0.4)
                print(f"real stick {key:9s} {what:12s}", fmt(s))
        if a.shot:
            h.shot(a.shot)
    finally:
        hmod.build_hd = orig
        h.close()


def cmd_floppy(a):
    """Cold boot the FLOPPY build (HunterFloppy, real FDC timing unless --fastfdc yes), then the pad table in the 3D view."""
    from huntfloppy import HunterFloppy
    default_tos = {"ste": "1.62", "st": "1.04", "falcon": "4.04", "tt": "3.06", "megaste": "2.06"}
    h = HunterFloppy(GAME / a.disk1, None, drives=1, machine=a.machine, tos=TOS[a.tos or default_tos[a.machine]], memsize_kb=a.mem,
                     extra=pad_extra(a.cfg, a.stick, mmu=a.machine == "tt"), fastfdc=a.fastfdc)
    stage = h._stage
    h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
    try:
        ok = h.boot_floppy("none", blind=a.blind, pb_key_at=a.pb_at)
        print(f"BOOT {'OK' if ok else 'FAILED'} machine={a.machine} mem={a.mem}K MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()} sites $c616={h.peek(0xC616, 6).hex()} $c64c={h.peek(0xC64C, 8).hex()}", fmt(state(h)))
        for i in range(a.settle):                          # watch the game for a while without any input
            time.sleep(5)
            print(f"  +{5 * (i + 1)} s", fmt(state(h)))
            if a.shot:
                h.shot(a.shot.replace(".png", f"_{5 * (i + 1)}.png"))
        if a.buttons:
            for pad in a.pad.split(","):
                press_table(h, pad, rows_for(a.keys), a.shots)
        if a.shot:
            h.shot(a.shot)
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, cold=False):
        p.add_argument("--cfg", default="a", choices=["a", "b", "ab", "none"])
        p.add_argument("--pad", default="a", help="pad(s) whose host keys are pressed: a, b or a,b")
        p.add_argument("--keys", default=None, help="comma list of pad buttons (default: every button except 4 and *, which leave the 3D loop)")
        p.add_argument("--stick", action="store_true", help="Hatari's keyboard joystick on port 1 as well")
        p.add_argument("--shots", default=None)
    for n in ("live", "kbd", "prof", "inject"):
        p = sub.add_parser(n)
        p.add_argument("--snapshot", default="1mb_foot_stand")
        p.add_argument("--plain-st", action="store_true", help="prof: FLAGS says plain ST (probe = no)")
        p.add_argument("--hold-at-start", default=None, help="live: pad A button held while the patch goes live (layer 3 test)")
        common(p)
    c = sub.add_parser("cold")
    c.add_argument("--game", default="build/jag_hd")
    c.add_argument("--machine", default="ste")
    c.add_argument("--tos", default=None)
    c.add_argument("--mem", type=int, default=1024)
    c.add_argument("--buttons", action="store_true")
    c.add_argument("--shot", default=None)
    common(c)
    f = sub.add_parser("floppy")
    f.add_argument("--disk1", default="build/jag_fl/HUNTER_disk1.st")
    f.add_argument("--machine", default="ste")
    f.add_argument("--tos", default=None)
    f.add_argument("--mem", type=int, default=1024)
    f.add_argument("--buttons", action="store_true")
    f.add_argument("--blind", action="store_true")
    f.add_argument("--pb-at", type=float, default=12)
    f.add_argument("--fastfdc", default="no")
    f.add_argument("--settle", type=int, default=0, help="watch the game for N x 5 s after the boot, no input")
    f.add_argument("--shot", default=None)
    common(f)
    a = ap.parse_args()
    {"live": cmd_live, "kbd": cmd_kbd, "prof": cmd_prof, "inject": cmd_inject, "cold": cmd_cold, "floppy": cmd_floppy}[a.cmd](a)


if __name__ == "__main__":
    main()
