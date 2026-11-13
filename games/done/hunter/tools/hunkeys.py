#!/usr/bin/env python3
"""Hunter one-key items / weapon keys (patches/key_item.s, work/notes/keys.md): key vs icon-table click, in a restored 3D-view snapshot.

    python3 tools/hunkeys.py table            # key-by-key RAM comparison (key route vs click on the icon table), owned and not owned
    python3 tools/hunkeys.py menus            # keys do nothing in the icon table, the log book (typing), game options, pause
    python3 tools/hunkeys.py pad              # Jaguar pad buttons #, 0, 8 (Hatari pad emulation, tools/jag_pad_a.cfg) -> h, g, j
    python3 tools/hunkeys.py cold [--machine st|ste|tt] [--floppy] [--game build/key_hd] [--mem 1024]   # cold boot, then h/g/j/1 in the 3D view

Icon route = the game's own item table (mouse up into the top of the 3D view opens it; $93 bit 7 is clear while it is open), cell (n%10)*32, (n/10)*16
(`$a28c` rectangle table).  Everything is read through the debugger; the harness copies the game, nothing on disk is written.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
import huntjag as J  # noqa: E402
from hunter import Hunter  # noqa: E402

A5, TAB = 0x806, 0x9AB4
OWNED = 0x24A
LIVE = Path("/tmp/hunkeys/live")
ONLY = ["key_item", "jag_pad", "jag_stick"]
KEYS = [("1", 0), ("2", 1), ("3", 2), ("4", 3), ("5", 4), ("6", 5), ("7", 6), ("8", 7), ("9", 8), ("h", 14), ("g", 15), ("j", 18)]
REG = [(A5 + 0x90, 0x30), (A5 + 0x200, 0x100), (TAB, 0x280)]
# bytes that differ for reasons that are not the key's effect (explained in work/notes/keys.md)
EXC = set(range(A5 + 0xD8 - 0, A5 + 0xE8)) | set(range(0x9C8, 0x9CC)) | {0x896, 0x899}


class T:
    def __init__(self, cfg="none", h=None):
        LIVE.parent.mkdir(exist_ok=True)
        if h is not None:                              # an already booted game (cold boot gates)
            self.h = h
            return
        subprocess.run([sys.executable, str(HERE / "huntpatch.py"), "live", "--only", *ONLY, "--out", str(LIVE)], check=True, cwd=GAME,
                       stdout=subprocess.DEVNULL)
        self.spec = json.loads(LIVE.with_suffix(".json").read_text())
        self.h = Hunter(snapshot=J.snap("1mb_foot_stand"), extra=J.pad_extra(cfg))
        time.sleep(3)
        J.apply_live(self.h, str(LIVE), self.spec)
        time.sleep(1.5)

    def rd(self, a, n):
        f = "/tmp/hunkeys/rd.bin"
        if os.path.exists(f):
            os.remove(f)
        self.h.dump(f, a, n)
        return open(f, "rb").read()

    def load(self, a, data):
        f = "/tmp/hunkeys/ld.bin"
        Path(f).write_bytes(data)
        self.h.debug(f"loadbin {f} ${a:x}", 0.3)

    def mpos(self):
        b = self.h.peek(A5 + 0xD8, 4)
        return int.from_bytes(b[:2], "big"), int.from_bytes(b[2:], "big")

    def gmove(self, x, y):
        for _ in range(12):
            cx, cy = self.mpos()
            dx, dy = x - cx, y - cy
            if abs(dx) <= 1 and abs(dy) <= 1:
                break
            sx, sy = int(dx * 1.6), int(dy * 1.6)
            if 0 < abs(sy) < 18:                              # moves under ~16 host px are lost: overshoot, the loop comes back
                sy = 18 if sy > 0 else -18
            if 0 < abs(sx) < 18:
                sx = 18 if sx > 0 else -18
            self.h.rel(sx, sy, 3)
            time.sleep(0.3)
        return self.mpos()

    def mode(self):
        return self.h.peek(0x899, 1)[0]

    def close_table(self):
        for _ in range(4):
            if self.mode() & 0x80:
                return
            self.gmove(150, 60)
            time.sleep(0.8)

    def open_table(self):
        self.gmove(150, 2)
        self.h.rel(0, -40, 4)
        time.sleep(0.6)

    def setstate(self, mask=0x000FFFFF, life=0x20, cnt=5, cur=0, zero=None, fuelcan=False, para=False):
        t = b"".join(bytes(32) if i == zero else cnt.to_bytes(2, "big") + (9).to_bytes(2, "big") + bytes(28) for i in range(20))
        self.load(TAB, t)
        self.load(A5 + OWNED, mask.to_bytes(4, "big"))
        self.load(A5 + 0x252, (0).to_bytes(2, "big"))
        self.load(A5 + 0x212, cur.to_bytes(2, "big"))
        self.load(A5 + 0x23C, life.to_bytes(2, "big"))
        fl = int.from_bytes(self.rd(A5 + 0x268, 4), "big")      # the handlers' own preconditions: fuel can needs bit $1a of $268, parachute byte $26a bit 7 (long bit 15) clear
        fl = (fl | 0x04000000) if fuelcan else fl & ~0x04000000
        fl = (fl & ~0x8000) if para else (fl | 0x8000)
        self.load(A5 + 0x268, fl.to_bytes(4, "big"))
        self.load(A5 + 0x296, (0).to_bytes(2, "big"))
        self.load(A5 + 0x281, b"\0")
        time.sleep(0.4)

    def st(self):
        out = {}
        for a, n in REG:
            for i, b in enumerate(self.rd(a, n)):
                out[a + i] = b
        return out

    def trial(self, kind, item, key, **s):
        for _ in range(3):
            self.close_table()
            self.setstate(**s)
            if kind == "click":
                self.open_table()
                if not self.mode() & 0x80:
                    break
            else:
                break
        if kind == "click":
            for _ in range(6):                                  # hover until the game's own hover code says this cell ($252)
                x, y = self.gmove((item % 10) * 32 + 16, (item // 10) * 16 + 8)
                time.sleep(0.5)
                if int.from_bytes(self.h.peek(A5 + 0x252, 2), "big") == item:
                    break
        a = self.st()
        if kind == "key":
            self.h.hold(key)
            time.sleep(0.4)
            self.h.release(key)
        else:
            self.h.click()
        time.sleep(1.0)
        return a, self.st()


def fields(s):
    c = lambda a, n=2: int.from_bytes(bytes(s[a + i] for i in range(n)), "big")
    return dict(count=[c(TAB + 32 * i) for i in range(20)], cur=c(A5 + 0x212), sel=c(A5 + 0x252), life=c(A5 + 0x23C), disp=c(A5 + 0x294), fuel=c(A5 + 0x296), chute=c(A5 + 0x281, 1), owned=c(A5 + OWNED, 4))


def cmd_table(a):
    t = T()
    try:
        for key, item in [k for k in KEYS if not a.keys or k[0] in a.keys]:
            for lab, mask in (("owned", 0xFFFFF), ("not owned", 0xFFFFF & ~(1 << item))):
                z = None if lab == "owned" else item
                ctx = dict(fuelcan=(key == "g"), para=(key == "j"))
                ka, kb = t.trial("key", item, key, mask=mask, cur=(1 if item == 0 else 0), zero=z, **ctx)
                ca, cb = t.trial("click", item, key, mask=mask, cur=(1 if item == 0 else 0), zero=z, **ctx)
                fk, fc, f0, c0 = fields(kb), fields(cb), fields(ka), fields(ca)
                eff = {k: (f0[k], fk[k]) for k in fk if fk[k] != f0[k] and k not in ("sel", "owned")}
                ceff = {k: (c0[k], fc[k]) for k in fc if fc[k] != c0[k] and k not in ("sel", "owned")}
                same = eff == ceff
                other = sorted(hex(x) for x in ka if ka[x] != kb[x] and x not in EXC and ka[x] == ka[x] and (kb[x] != cb[x]))
                print(f"key {key} item {item:2d} {lab:9s} key effect {eff}\n      click effect {ceff}   identical: {same}", flush=True)
                print(f"      other bytes where key-route and click-route end states differ: {other}", flush=True)
    finally:
        t.h.close()



def pressed(t, host, hold=0.4):
    t.h.hold(host)
    time.sleep(hold)
    t.h.release(host)
    time.sleep(1.0)


def f4(t):
    f = fields(t.st())
    return {k: f[k] for k in ("count", "cur", "life", "owned")}


def cmd_menus(a):
    """Keys do nothing where the game is not in the 3D loop: item table open, log book, game options, pause."""
    keys = ["h", "g", "j", "1", "2", "5", "9", "KP_3"]
    for ctx in ("table", "log", "options", "pause", "control"):
        t = T()
        try:
            t.close_table()
            t.setstate(life=0x20)
            if ctx == "table":
                t.open_table()
            elif ctx == "log":
                pressed(t, "l")
            elif ctx == "options":
                t.h.keypress(1)
                time.sleep(1.5)
            elif ctx == "pause":
                pressed(t, "p")
            m0 = t.mode()
            s0 = f4(t)
            t.h.shot(f"/tmp/hunkeys/menu_{ctx}_a.png")
            for k in keys:
                pressed(t, k, 0.3)
            s1 = f4(t)
            ring = t.h.peek(0x9C8, 4).hex()
            t.h.shot(f"/tmp/hunkeys/menu_{ctx}_b.png")
            print(f"{ctx:8s} $93={m0:02x}->{t.mode():02x} keys {keys}: counts/cur/life/owned unchanged = {s0 == s1}   key ring $9c8={ring}", flush=True)
            if s0 != s1:
                print("   BEFORE", s0, "\n   AFTER ", s1, flush=True)
        finally:
            t.h.close()


def cmd_chute(a):
    """The parachute leaves no lasting RAM (the game consumes $281 within a frame): count executions of `$a284 move.b #$7f,$281(a5)` per route."""
    t = T()
    try:
        for kind in ("key", "click"):
            t.close_table()
            t.setstate(para=True)
            if kind == "click":
                t.open_table()
            t.h.debug("b all", 0.3)
            cf = t.h.R / "bp.txt"
            cf.write_text("r\n")
            n0 = t.h._logtext().count("condition(s) matched")
            t.h.cmd(f"hatari-debug b pc = $a284 :trace :once :file {cf}")
            time.sleep(0.4)
            if kind == "key":
                pressed(t, "j", 0.4)
            else:
                for _ in range(6):
                    t.gmove(8 * 32 + 16, 24)
                    time.sleep(0.5)
                    if int.from_bytes(t.h.peek(A5 + 0x252, 2), "big") == 18:
                        break
                t.h.click()
                time.sleep(1.0)
            print(f"parachute {kind}: breakpoint $a284 hits = {t.h._logtext().count('condition(s) matched') - n0}", flush=True)
    finally:
        t.h.close()


def pad_rows(t, rows):
    """rows: (host key, what, item).  Same state before each (the fuel can's precondition for item 15); the pad must give the key's effect."""
    for host, what, item in rows:
        t.close_table()
        t.setstate(life=0x20, cur=0, fuelcan=(item == 15), para=(item == 18))
        f0 = fields(t.st())
        pressed(t, host, 0.8)
        f1 = fields(t.st())
        eff = {k: (f0[k], f1[k]) for k in f0 if f0[k] != f1[k] and k not in ("sel", "owned", "count")}
        eff["count"] = [(i, f0["count"][i], f1["count"][i]) for i in range(20) if f0["count"][i] != f1["count"][i]]
        k = t.h.peek(A5 + 0x1C4, 2)
        print(f"host {host:6s} {what:34s} effect {eff}  last key scancode/ascii in the game's buffer = {k[0]:02x}/{k[1]:02x}", flush=True)


def cmd_pad(a):
    t = T("a")
    try:
        print("JAG state", J.fmt(J.state(t.h)), flush=True)
        pad_rows(t, [("F6", "pad #  -> h medical kit (item 14)", 14), ("0", "pad 0  -> g fuel can (item 15)", 15), ("8", "pad 8  -> j parachute (item 18)", 18),
                     ("h", "keyboard h (reference)", 14), ("g", "keyboard g (reference)", 15), ("j", "keyboard j (reference)", 18)])
        # in the item table (not the 3D loop) the pad buttons do nothing
        t.close_table()
        t.setstate(life=0x20)
        t.open_table()
        f0 = f4(t)
        for host in ("F6", "0", "8"):
            pressed(t, host, 0.8)
        print("item table open: pad # 0 8 -> unchanged =", f0 == f4(t), "$93 =", hex(t.mode()), flush=True)
    finally:
        t.h.close()


def cmd_cold(a):
    from stharness import MACHINE_TOS, TOS
    if a.floppy:
        from huntfloppy import HunterFloppy
        h = HunterFloppy(GAME / a.game, None, drives=1, machine=a.machine, tos=TOS[a.tos or {"ste": "1.62", "st": "1.04", "tt": "3.06", "falcon": "4.04"}[a.machine]],
                         memsize_kb=a.mem, extra=J.pad_extra("a", False, mmu=a.machine == "tt"), fastfdc="no")
        stage = h._stage
        h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
        hmod = orig = None
        ok = h.boot_floppy("none", blind=a.blind, pb_key_at=a.pb_at)
        print("BOOT", "OK" if ok else "FAILED", flush=True)
    elif a.machine == "tt":                          # hunt_ttf's HD boot (HDDRIVER on ACSI, TOS 3.06, --mmu true); keep its Hatari alive
        import hunt_ttf as TF
        cap = []
        init0, close0 = TF.HD.__init__, TF.HD.close

        def init(self, *x, **k):
            init0(self, *x, **k)
            cap.append(self)
        TF.HD.__init__, TF.HD.close = init, lambda self: None
        try:
            rc = TF.boot_hd("tt", a.tos or "3.06", a.mem, GAME / a.game, "acsi", None, ["--mmu", "true", "--configfile", J.CFG["a"], "--joy1", "none"],
                            0, None, ["a534:6", "c616:6"])
        finally:
            TF.HD.__init__, TF.HD.close = init0, close0
        h, hmod, orig = cap[0], None, None
        print("TT BOOT rc", rc, flush=True)
    else:
        h, (hmod, orig) = J.cold_boot(a.game, a.machine, "a", a.mem, a.tos, False)
        stage = h._stage
        h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
        if a.machine in ("st", "megast"):
            from huntpatch import blind_boot
            blind_boot(h)
        else:
            h.boot_to_game()
    try:
        print(f"machine={a.machine} mem={a.mem}K in_game={h.in_game()} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()} "
              f"$a534={h.peek(0xA534, 6).hex()} $c616={h.peek(0xC616, 6).hex()} $c64c={h.peek(0xC64C, 8).hex()}", flush=True)
        t = T(h=h)
        rows = [("h", "keyboard h", 14), ("g", "keyboard g", 15), ("j", "keyboard j", 18), ("KP_2", "keypad 2 (weapon 1)", 1), ("F6", "pad #", 14),
                ("0", "pad 0", 15), ("8", "pad 8", 18)]
        pad_rows(t, rows)
    finally:
        if orig:
            hmod.build_hd = orig
        if a.machine == "tt" and not a.floppy:
            import hunt_ttf as TF
            TF.HD.close(h)
        else:
            h.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["table", "menus", "pad", "cold", "chute"])
    p.add_argument("--keys", default="", help="table: only these keys, e.g. hgj")
    p.add_argument("--machine", default="ste")
    p.add_argument("--tos", default=None)
    p.add_argument("--mem", type=int, default=1024)
    p.add_argument("--game", default="build/key_hd")
    p.add_argument("--floppy", action="store_true")
    p.add_argument("--blind", action="store_true")
    p.add_argument("--pb-at", type=float, default=12)
    a = p.parse_args()
    {"table": cmd_table, "menus": cmd_menus, "pad": cmd_pad, "cold": cmd_cold, "chute": cmd_chute}[a.cmd](a)


if __name__ == "__main__":
    main()
