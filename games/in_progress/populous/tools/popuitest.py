#!/usr/bin/env python3
"""PopUI gates: keys == clicks, tooltip pixel gate, phantom keys.  Helpers shared by the sub-commands (see work/notes/ui_impl.md).

    python3 tools/popuitest.py scan [--snap genesis_start] [--live PREFIX] [--mana N]   # click every icon centre, print the order bytes
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
from populous import Populous  # noqa: E402

SNAP = GAME / "work" / "snapshots"
SCR = GAME / "work" / "scratch" / "popui"
TURN = 0x3C506
WORLD, WORLD_LEN = 0x21100, 0x1C700
LEFT, RIGHT = "L", "R"

# icon name -> (scancode, x, y, button, what the notes say)
ICONS = {
    "flood":       (0x21, 16, 128, LEFT),
    "armageddon":  (0x1E, 32, 136, LEFT),
    "volcano":     (0x2F, 16, 144, LEFT),
    "earthquake":  (0x12, 48, 144, LEFT),
    "knight":      (0x25, 32, 152, LEFT),
    "swamp":       (0x11, 16, 160, LEFT),
    "to_magnet":   (0x32, 16, 176, LEFT),
    "settle":      (0x1F, 32, 184, LEFT),
    "gather":      (0x22, 48, 192, LEFT),
    "fight":       (0x14, 16, 192, LEFT),
    "query":       (0x10, 112, 176, LEFT),
    "raise":       (0x13, 96, 184, LEFT),
    "magnet_mode": (0x19, 80, 192, LEFT),
    "view_leader": (0x26, 128, 184, LEFT),
    "view_magnet": (0x2C, 128, 184, RIGHT),
    "view_battle": (0x30, 112, 192, LEFT),
    "view_knight": (0x31, 144, 192, LEFT),
    "view_house":  (0x23, 144, 192, RIGHT),
    "pause":       (0x39, 272, 192, LEFT),
    "music":       (0x16, 256, 184, LEFT),
    "effects":     (0x2D, 240, 192, LEFT),
}


def cell(x: int, y: int):
    """The game's own icon geometry ($c424-$c6c2): returns ('map'|'right'|'left'|None, i, j, u, v)."""
    def divs(a, b):
        q = abs(a) // b
        return -q if a < 0 else q
    u = y + (x >> 1) - 0x20
    v = y - (x >> 1) + 0x20
    if 0 <= u < 0x40 and 0 <= v < 0x40:
        return ("map", u, v, u, v)
    if u > 0x112:
        return ("right", divs(u - 0x110, 16), divs(v - 0x20, 16), u, v)
    if v < 0x92:
        return (None, 0, 0, u, v)
    return ("left", divs(u - 0x60, 16), divs(v - 0x90, 16), u, v)


def wb(addr: int, val: int, n: int = 2) -> str:
    return f"w ${addr:x} " + " ".join(f"${b:02x}" for b in val.to_bytes(n, "big"))


class Session:
    """One emulator run on a snapshot with scripted actions applied at chosen turns."""

    def __init__(self, snap: str, live: str | None = None, fast: bool = True):
        self.h = Populous(snapshot=SNAP / f"{snap}.sav")
        self.live = live
        self.fast = fast

    def close(self):
        self.h.close()

    def turn0(self) -> int:
        time.sleep(1.0)
        return self.h.peekw(TURN)

    def load_live(self):
        spec = json.loads(Path(self.live + ".json").read_text())
        out = [f"loadbin {Path(self.live + '.img').resolve()} ${spec['img_base']:x}"]
        for s in spec["sites"]:
            out.append(f"w ${s['addr']:x} " + " ".join(f"${x:02x}" for x in bytes.fromhex(s["new"])))
        return out


def click_cmds(x: int, y: int, btn: str) -> list[str]:
    c = [wb(0x3C556, x), wb(0x3C55A, y)]
    c.append(wb(0x3D566 if btn == LEFT else 0x3C514, 0))
    return c


def run_events(sess: "Session", events: list[dict], t0: int, spacing: int = 5, tag: str = "r", apply_pc: int = 0xBB7C,
               timeout: float = 900.0) -> dict:
    """events: [{'name', 'apply': [debugger commands run at $bb7c of turn t0 + k * spacing]}].  For each event the world RAM is saved at
    $bbfa of that turn (orders not yet executed: 'pre') and at $bb7c of turn +3 ('post').  Returns {name: (pre_bytes, post_bytes)}."""
    h = sess.h
    d = SCR / tag
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob("*"):
        f.unlink()
    h.debug("b all", 0.3)
    if sess.live:
        for c in sess.load_live():
            h.debug(c, 0.4)
    arm = []
    for k, ev in enumerate(events):
        T = t0 + k * spacing
        (d / f"a{k}.txt").write_text("\n".join(ev["apply"]) + "\n")
        (d / f"p{k}.txt").write_text(f"savebin {d}/pre{k}.bin ${WORLD:x} ${WORLD_LEN:x}\n")
        (d / f"q{k}.txt").write_text(f"savebin {d}/post{k}.bin ${WORLD:x} ${WORLD_LEN:x}\n")
        if ev.get("apply2"):
            (d / f"b{k}.txt").write_text("\n".join(ev["apply2"]) + "\n")
            arm.append(f"b pc = $bbc4 && (${TURN:x}).w = {T} :trace :once :file {d}/b{k}.txt")
        arm += [f"b pc = ${apply_pc:x} && (${TURN:x}).w = {T} :trace :once :file {d}/a{k}.txt",
                f"b pc = $bbfa && (${TURN:x}).w = {T} :trace :once :file {d}/p{k}.txt",
                f"b pc = $bb7c && (${TURN:x}).w = {T + 3} :trace :once :file {d}/q{k}.txt"]
    for c in arm:
        h.cmd("hatari-debug " + c)
        time.sleep(0.12)
    time.sleep(0.5)
    if sess.fast:
        h.cmd("hatari-option --fast-forward on")
    last = d / f"post{len(events) - 1}.bin"
    t = time.time()
    while not (last.exists() and last.stat().st_size == WORLD_LEN):
        if time.time() - t > timeout:
            raise TimeoutError(f"events did not finish; turn {h.peekw(TURN)}; log tail:\n{h._logtext()[-800:]}")
        time.sleep(0.5)
    time.sleep(0.5)
    if sess.fast:
        h.cmd("hatari-option --fast-forward off")
    return {ev["name"]: ((d / f"pre{k}.bin").read_bytes(), (d / f"post{k}.bin").read_bytes()) for k, ev in enumerate(events)}


def w16(b: bytes, addr: int) -> int:
    return struct.unpack_from(">H", b, addr - WORLD)[0]


def w32(b: bytes, addr: int) -> int:
    return struct.unpack_from(">I", b, addr - WORLD)[0]


def state(b: bytes, player: int = 0) -> dict:
    o = 0x21E4A + 0x2E * player
    return {"order": tuple(b[o - WORLD:o - WORLD + 3]), "mode": w16(b, 0x21D8E), "shape": w16(b, 0x2169A), "view": (w16(b, 0x37EB8), w16(b, 0x249EC)),
            "music": w16(b, 0x2203A), "fx": w16(b, 0x2195E), "pause": w16(b, 0x3B2B2), "mana": w32(b, 0x3B264 + 0xC), "latchL": w16(b, 0x3D566),
            "latchR": w16(b, 0x3C514), "click": (w16(b, 0x3C556), w16(b, 0x3C55A))}


def cmd_scan(a):
    live = a.live
    sess = Session(a.snap, live)
    try:
        t0 = sess.turn0() + 60
        evs = []
        if a.mana:
            pre = [f"w $3b270 " + " ".join(f"${x:02x}" for x in a.mana.to_bytes(4, "big"))]
        for n, (sc, x, y, b) in ICONS.items():
            evs.append({"name": n, "apply": (pre if a.mana else []) + click_cmds(x, y, b)})
        res = run_events(sess, evs, t0, tag="scan")
        base = None
        for n, (pre_b, post_b) in res.items():
            s0, s1 = state(pre_b), state(post_b)
            print(f"{n:12s} order@bbfa={s0['order']} mode {s0['mode']}->{s1['mode']} shape {s1['shape']} view {s0['view']}->{s1['view']} "
                  f"music {s1['music']} fx {s1['fx']} pause {s1['pause']} mana {s0['mana']}")
    finally:
        sess.close()


KEYID = {"raise": 1, "query": 2, "magnet_mode": 3, "to_magnet": 4, "settle": 5, "gather": 6, "fight": 7, "earthquake": 8, "swamp": 9,
         "knight": 10, "volcano": 11, "flood": 12, "armageddon": 13, "view_leader": 14, "view_magnet": 15, "view_battle": 16,
         "view_knight": 17, "view_house": 18, "pause": 19, "music": 20, "effects": 21}
ORDER = ["query", "raise", "magnet_mode", "to_magnet", "settle", "gather", "fight", "view_leader", "view_magnet", "view_battle",
         "view_knight", "view_house", "music", "effects", "music", "effects", "swamp", "earthquake", "knight", "volcano", "flood",
         "armageddon_arm", "armageddon"]
KD = 0xC8000
MASK = [(0x24990, 0x249A4)]


CLICKPOS = (0x3C556, 0x3C55C)      # the click position words: the VBL copies the pointer into them again once the handler has run (idle latch)


def masked(b: bytes, extra=()) -> bytes:
    b = bytearray(b)
    for lo, hi in list(MASK) + list(extra):
        b[lo - WORLD:hi - WORLD] = bytes(hi - lo)
    return bytes(b)


def diff_ranges(a: bytes, b: bytes, gap: int = 8):
    out = []
    lo = hi = None
    for i in range(len(a)):
        if a[i] != b[i]:
            if lo is None:
                lo = hi = i
            elif i - hi > gap:
                out.append((lo + WORLD, hi + WORLD))
                lo = hi = i
            else:
                hi = i
    if lo is not None:
        out.append((lo + WORLD, hi + WORLD))
    return out


def mana_cmd(mana):
    return [] if mana is None else [wb(0x3B264 + 0xC, mana, 4)]


def key_events(mana, ref: bool):
    evs = []
    for k, n in enumerate(ORDER):
        pre = mana_cmd(mana) if k == 0 else []
        if n == "armageddon_arm":
            evs.append({"name": f"{k}:{n}", "apply": pre + ([] if ref else [wb(KD + 10, 0x0001), wb(KD + 12, KEYID["armageddon"], 1)])})
            continue
        key = "armageddon" if n == "armageddon" else n
        sc, x, y, b = ICONS[key]
        if ref:
            evs.append({"name": f"{k}:{n}", "apply": pre + click_cmds(x, y, b), "apply2": [wb(0x3C556, x), wb(0x3C55A, y)]})
        else:
            evs.append({"name": f"{k}:{n}", "apply": pre + [wb(KD + 10, 0x0001), wb(KD + 12, KEYID[key], 1)]})
    return evs


def cmd_keys(a):
    live = a.live
    if a.mutant:                                    # a deliberately broken copy of the key patches: the gate must fail
        fname, edits = MUT[a.mutant]
        live = live_variant(["pop_noprot", "pop_keys", "pop_keys2", "pop_keys3", "pop_keys4"], {fname: edits}, "mut_" + a.mutant)
    out = {}
    for label, mana in (("lowmana", None), ("highmana", 60000)):
        if a.only and label not in a.only:
            continue
        runs = {}
        t0 = None
        for kind in ("click", "key") + (("click2",) if a.selftest else ()):
            sess = Session(a.snap, live if kind == "key" else None)
            try:
                if t0 is None:
                    t0 = sess.turn0() + 80
                else:
                    time.sleep(1.0)
                runs[kind] = run_events(sess, key_events(mana, kind != "key"), t0, tag=f"keys_{label}_{kind}",
                                        apply_pc=0xBB7C if kind == "key" else 0xBBA6)
            finally:
                sess.close()
        print(f"== {label}: t0 {t0}")
        ref = runs["click"]
        for other in [k for k in runs if k != "click"]:
            bad = 0
            for n, (pre, post) in ref.items():
                p2, q2 = runs[other][n]
                s0, s1 = state(pre), state(p2)
                dpre = diff_ranges(masked(pre, [CLICKPOS]), masked(p2, [CLICKPOS]))
                dpost = diff_ranges(masked(post), masked(q2))
                ok = not dpre and not dpost
                bad += not ok
                print(f"  {other:6s} {n:15s} order click {s0['order']} key {s1['order']} mode {s0['mode']}/{s1['mode']} view {s0['view']}/{s1['view']} "
                      f"mana {s0['mana']}/{s1['mana']}  {'IDENTICAL' if ok else 'DIFF pre ' + ' '.join(f'${x:x}-${y:x}' for x, y in dpre[:6]) + ' post ' + ' '.join(f'${x:x}-${y:x}' for x, y in dpost[:6])}")
            print(f"  -> {label} {other}: {len(ref) - bad}/{len(ref)} identical")


def tooltip_strings(path: Path | None = None):
    """The (line 1, line 2) wording of pop_tooltip.s per icon number, expanded without and with key labels."""
    path = path or GAME / "patches" / "pop_tooltip.s"
    out = {}
    for ln in path.read_text().splitlines():
        m = re.match(r"^s(\d+):\s+dc\.b\s+(.*)$", ln)
        if not m:
            continue
        toks = re.findall(r'"([^"]*)"|(\d+)', m.group(2).split(";")[0])
        raw = b""
        for q, n in toks:
            raw += q.encode() if q or not n else bytes([int(n)])
        out[int(m.group(1))] = raw
    res = {}
    for n, raw in out.items():
        parts = raw.split(b"\0")
        pair = {}
        for keys in (0, 1):
            lines = []
            for seg in parts[:2]:
                t = b""
                i = 0
                while i < len(seg):
                    c = seg[i]
                    if c == 1:
                        if keys:
                            t += b" (" + seg[i + 1:] + b")"
                        break
                    if c == 2:
                        if keys:
                            t += seg[i + 1:]
                        break
                    t += bytes([c])
                    i += 1
                lines.append(t.decode())
            pair[keys] = lines
        res[n] = pair
    return res


def cmd_words(a):
    bad = 0
    for n, pair in sorted(tooltip_strings().items()):
        for keys, (l1, l2) in pair.items():
            ok = len(l1) <= 16 and len(l2) <= 9
            bad += not ok
            if keys or not ok:
                print(f"{n:2d} keys={keys} {l1!r:22} ({len(l1):2d})  {l2!r:12} ({len(l2)}) {'' if ok else 'TOO LONG'}")
    print("words:", "OK" if not bad else f"{bad} too long")
    return 1 if bad else 0


SHOTS = GAME / "work" / "shots"
# one hover point per icon number of pop_tooltip (cell centres, ui.md), plus points that must show nothing
HOVER = {1: (16, 128), 2: (32, 136), 3: (16, 144), 4: (48, 144), 5: (32, 152), 6: (16, 160), 7: (16, 176), 8: (32, 184), 9: (48, 192),
         10: (16, 192), 11: (112, 176), 12: (96, 184), 13: (80, 192), 14: (128, 184), 15: (112, 192), 16: (144, 192), 17: (80, 168),
         18: (64, 160), 19: (304, 160), 20: (304, 176), 21: (304, 192), 22: (256, 184), 23: (240, 192), 24: (272, 192)}
NOHOVER = [(200, 100), (150, 5), (30, 40), (60, 150), (300, 100), (160, 195)]
NOP_ACIA = "w $2003e " + " ".join(["$4e $71"] * 15)


def poke_pointer(h, x: int, y: int):
    h.debug(wb(0x24786, x), 0.15)
    h.debug(wb(0x24788, y), 0.15)


def crop_shot(src: Path, dst: Path, box=(96, 58, 736, 458), zoom: int = 1):
    from PIL import Image
    im = Image.open(src).crop(box)
    if zoom != 1:
        im = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
    im.save(dst)


def cmd_tt(a):
    """Tooltip screenshots: pointer poked onto every icon (the IKBD packet stores are nopped), one picture per icon number."""
    sess = Session(a.snap, a.live)
    h = sess.h
    try:
        time.sleep(1.0)
        h.debug("b all", 0.3)
        h.debug(NOP_ACIA, 0.3)
        for c in sess.load_live():
            h.debug(c, 0.4)
        out = SCR / "tt"
        out.mkdir(parents=True, exist_ok=True)
        targets = {k: v for k, v in HOVER.items() if not a.ids or k in a.ids}
        for n, (x, y) in list(targets.items()) + ([] if a.ids else [(f"none{i}", p) for i, p in enumerate(NOHOVER)]):
            poke_pointer(h, x, y)
            time.sleep(a.wait)
            f = h.shot(out / f"raw_{n}.png")
            print(n, (x, y), "pointer words", hex(h.peekw(0x24786)), hex(h.peekw(0x24788)), "->", f)
        if a.arm:                                    # the Armageddon arm of pop_keys: the hint replaces any hover for AWIN VBLs
            poke_pointer(h, 200, 100)
            v = h.peekl(0x16D2A)
            h.debug(wb(KD + 4, v + 1, 4), 0.1)
            time.sleep(0.4)
            f = h.shot(out / "raw_25.png")
            print(25, "arm hint, armed =", h.peekl(KD + 4) != 0, "->", f)
    finally:
        sess.close()


# ---- the pixel gates (popabtest machinery, our own input script) ----------------------------------------------------------
# icon number under (x, y) by the game's own geometry; 0 = none.  Mirrors pop_tooltip's tables (LT / RT) for the gate's bookkeeping.
LT = [[1, 0, 0, 0, 0], [2, 3, 0, 0, 0], [4, 5, 6, 0, 0], [17, 17, 17, 7, 0], [17, 18, 17, 8, 10], [17, 17, 17, 9, 0], [11, 12, 13, 0, 0],
      [14, 15, 0, 0, 0], [16, 0, 0, 0, 0]]
RT = [[19, 0, 0, 22, 23], [0, 20, 0, 24, 0], [0, 0, 21, 0, 0]]


def icon_at(x: int, y: int) -> int:
    kind, i, j, _, _ = cell(x, y)
    if kind == "left" and 0 <= i <= 8 and 0 <= j <= 4:
        return LT[i][j]
    if kind == "right" and 0 <= i <= 2 and 0 <= j <= 4:
        return RT[i][j]
    return 0


def away_script(pab):
    """popabtest's script with every row whose pointer is on an icon moved to (200, 100): the pointer never hovers an icon; clicks
    are kept off the icons too (a click row on a moved pointer clicks the map as the original script does)."""
    rows = []
    for (x, y, btn, key, fl) in pab.SCRIPT:
        if icon_at(x, y):
            x, y = 200, 100
        rows.append((x, y, btn, key, fl))
    return rows


def set_script(pab, rows):
    pab.SCRIPT = rows
    new, n = re.subn(r"(?m)^NENT\tequ\t\d+$", f"NENT\tequ\t{len(rows)}", pab.STUB_EQU)
    assert n == 1, "popabtest.STUB_EQU has no NENT line"
    pab.STUB_EQU = new


MUT = {
    "tt_always": ("pop_tooltip", [("        move.w  d7,tCID(a3)\n.have:", "        moveq   #1,d7\n        move.w  d7,tCID(a3)\n.have:")]),
    "tt_wide": ("pop_tooltip", [("        lea     40(a0),a0               ; line 1", "        lea     48(a0),a0               ; line 1")]),
    "key_pos": ("pop_keys", [("        dc.w    48,144                  ; 8  earthquake", "        dc.w    48,152                  ; 8  earthquake")]),
}


PRE_SCRIPT_FLIPS = 2      # flips 1-2 show the frame rendered before the first script row: the snapshot's own pointer (75, 175), an arrow cell


def cmd_gate(a):
    """popabtest's capture (both buffers + world RAM per flip, two mid-frame samples per flip) of a pointer script that never visits an icon,
    reference vs patched.  The frame rendered before the script's first row (flips 1-2) is drawn with the snapshot's own pointer, which stands
    on a scroll arrow: it legitimately shows a tooltip and is excluded from the verdict (reported separately)."""
    import popabtest as pab
    set_script(pab, away_script(pab) if a.away else list(pab.SCRIPT))
    pab.MUTANTS.update(MUT)
    pab.KEEP_STALE = False
    pab.SCRATCH = GAME / "build" / "PopUI"                      # not PopDisplay's scratch
    snaps = a.snap or pab.SNAPS
    rows = pab.SCRIPT
    print(f"script: {len(rows)} rows, rows on an icon: {sum(1 for r in rows if icon_at(r[0], r[1]))}", flush=True)

    def idx_of(x):
        if isinstance(x, tuple):
            return x[1] if len(x) == 3 else x[0]
        return x

    rc = 0
    for sn in snaps:
        t0 = pab.start_turn(sn)
        ref = pab.run_capture(sn, None, len(rows), f"{sn}/ref", t0)
        print(f"== {sn}: T0 {t0}; reference run {sum(1 for r in ref['recs'] if r.tag == 1)} flips, {sum(1 for r in ref['recs'] if r.tag != 1)} samples", flush=True)
        for spec in a.set:
            names = spec.split("+")
            live = pab.live_image(names, a.mutant, f"{sn}_{spec}_{a.mutant}".replace("+", "_"))
            new = pab.run_capture(sn, live, len(rows), f"{sn}/{spec}", t0)
            r = pab.compare(ref, new, verbose=False)
            early = [m for m in r["flip_bad"] + r["sample_bad"] if idx_of(m[0]) <= PRE_SCRIPT_FLIPS]
            fb = [m for m in r["flip_bad"] if idx_of(m[0]) > PRE_SCRIPT_FLIPS]
            sb = [m for m in r["sample_bad"] if idx_of(m[0]) > PRE_SCRIPT_FLIPS]
            wb_ = [m for m in r["world_bad"] if idx_of(m[0]) > PRE_SCRIPT_FLIPS]
            ok = r["flips"] > 0 and not fb and not sb and not wb_ and not r["only_ref"] and not r["only_new"]
            print(f"{sn:20s} {spec:55s} {'IDENTICAL' if ok else 'DIFFERENT'}: flips compared {r['flips']} (both buffers + world each), mid-frame samples {r['samples']}, "
                  f"bad flips {len(fb)}, bad samples {len(sb)}, world {len(wb_)}; excluded pre-script frames: {len(early)} diffs "
                  f"{sorted({m[1] for m in early})[:2]}", flush=True)
            for m in (fb + sb + wb_)[:8]:
                print("    ", m)
            rc |= 0 if ok else 1
    print("GATE", "IDENTICAL (exit 0)" if rc == 0 else "FAILED (exit 1)")
    return rc


def tt_allowed():
    """Byte offsets (row * 160 + byte) a tooltip may change: line 1 rows 0-7 16-pixel groups 5-13, line 2 rows 8-15 groups 6-10."""
    ok = set()
    for r in range(8):
        ok.update(range(r * 160 + 40, r * 160 + 112))
    for r in range(8, 16):
        ok.update(range(r * 160 + 48, r * 160 + 88))
    return ok


def cmd_ttrect(a):
    """The original popabtest script (the pointer visits icons), unpatched vs patched: every differing screen byte of every flip must lie in
    the two tooltip rectangles, the world RAM must be identical, and the flips where the pointer is not on an icon (this pass or the last two; the older buffer holds the frame before)
    must be identical to the original (the backdrop is restored exactly when the tooltip clears)."""
    import popabtest as pab
    import zlib
    pab.SCRATCH = GAME / "build" / "PopUI"
    pab.KEEP_STALE = False
    pab.MUTANTS.update(MUT)
    set_script(pab, list(pab.SCRIPT))
    rows = pab.SCRIPT
    names = a.set.split("+")
    allowed = tt_allowed()
    snap = a.snap
    t0 = pab.start_turn(snap)
    ref = pab.run_capture(snap, None, len(rows), f"{snap}/ref", t0)
    live = pab.live_image(names, a.mutant, f"{snap}_ui")
    new = pab.run_capture(snap, live, len(rows), f"{snap}/ui", t0)
    ra = {r.idx: r for r in ref["recs"] if r.tag == 1}
    rb = {r.idx: r for r in new["recs"] if r.tag == 1}
    tot = with_diff = outside = quiet_bad = world_bad = 0
    icon_flips = quiet_flips = 0
    worst = []
    for i in sorted(set(ra) & set(rb)):
        if i <= PRE_SCRIPT_FLIPS:
            continue
        tot += 1
        x, y = ra[i], rb[i]

        def ptr(rec):                      # the pointer words in the world dump of a flip
            w = zlib.decompress(rec.world)
            return w16(w, 0x24786), w16(w, 0x24788)
        near_icon = any(icon_at(*ptr(ra[k])) for k in (i - 2, i - 1, i) if k in ra)
        diffs = set()
        for n in (0, 1):
            da, db = zlib.decompress(x.bufs[n]), zlib.decompress(y.bufs[n])
            if da != db:
                diffs |= {k for k in range(len(da)) if da[k] != db[k]}
        wa, wb_ = zlib.decompress(x.world), zlib.decompress(y.world)
        if masked(wa) != masked(wb_):
            world_bad += 1
            worst.append((i, "world", diff_ranges(masked(wa), masked(wb_))[:3]))
        if diffs:
            with_diff += 1
            if not diffs <= allowed:
                outside += 1
                worst.append((i, "outside the rectangles", sorted(diffs - allowed)[:6]))
            if not near_icon:
                quiet_bad += 1
                worst.append((i, "diff while the pointer is not near an icon", sorted(diffs)[:4]))
        if near_icon:
            icon_flips += 1
        else:
            quiet_flips += 1
    print(f"{snap} {a.set}{' @' + a.mutant if a.mutant else ''}: flips compared {tot}; flips with the pointer on / just left an icon {icon_flips}, others {quiet_flips}; "
          f"flips whose screen differs {with_diff}; flips with a differing byte outside the rectangles {outside}; diffs with the pointer away {quiet_bad}; "
          f"world RAM differs in {world_bad} flips")
    for w in worst[:10]:
        print("   ", w)
    ok = tot > 0 and not outside and not quiet_bad and not world_bad and with_diff > 0
    print("TTRECT", "OK" if ok else "FAILED")
    return 0 if ok else 1


REALKEYS = [  # (key name, ST scancode, what must be seen)
    ("Q", 0x10, "mode == 1"), ("R", 0x13, "mode == 2"), ("P", 0x19, "mode == 6"),
    ("M", 0x32, "behaviour == 0"), ("S", 0x1F, "behaviour == 1"), ("G", 0x22, "behaviour == 2"), ("T", 0x14, "behaviour == 3"),
    ("L", 0x26, "view changes"), ("Z", 0x2C, "view changes"), ("B", 0x30, "view same (no battle)"), ("N", 0x31, "view same (no knight)"),
    ("H", 0x23, "view changes"), ("U", 0x16, "music toggles"), ("U", 0x16, "music toggles"), ("X", 0x2D, "fx toggles"), ("X", 0x2D, "fx toggles"),
    ("W", 0x11, "mode & 8"), ("E", 0x12, "mana -2500"), ("K", 0x25, "mana -7500"), ("V", 0x2F, "mana -10000"), ("F", 0x21, "mana -40000"),
    ("Space", 0x39, "pause on"), ("Space", 0x39, "pause off"),
]


def rstate(h):
    return {"mode": h.peekw(0x21D8E), "beh": h.peekw(0x3B268), "view": (h.peekw(0x37EB8), h.peekw(0x249EC)), "music": h.peekw(0x2203A),
            "fx": h.peekw(0x2195E), "pause": h.peekw(0x3B2B2), "mana": h.peekl(0x3B270), "q": (h.peekw(KD + 10) >> 8, h.peekw(KD + 10) & 255),
            "arm": h.peekl(KD + 4), "armageddon": h.peekw(0x3D562)}


def cmd_realkeys(a):
    """Every key through the real chain (host key -> Hatari -> IKBD -> ACIA interrupt -> pop_keys2 -> ring -> pop_keys' pass hook).
    The orders are logged by a breakpoint at $bbfa (before $1e750 executes them) every pass; only non-zero commands are printed."""
    sess = Session(a.snap, a.live)
    h = sess.h
    try:
        time.sleep(1.0)
        h.debug("b all", 0.3)
        for c in sess.load_live():
            h.debug(c, 0.4)
        h.debug(wb(0x3B270, a.mana, 4), 0.3)
        (SCR / "rk").mkdir(parents=True, exist_ok=True)
        f = SCR / "rk" / "orders.txt"
        f.write_text("m $21e4a 3\n")
        h.cmd(f"hatari-debug b pc = $bbfa && ($21e4a).b ! 0 :trace :file {f}")
        time.sleep(0.5)
        for name, sc, expect in REALKEYS:
            before = rstate(h)
            n0 = len(h._logtext())
            h.keypress(sc)
            time.sleep(a.wait)
            after = rstate(h)
            log = h._logtext()[n0:]
            orders = [o for o in re.findall(r"(?im)^0*21e4a: ([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2})", log) if o[0] != "00"]
            chg = {k: (before[k], after[k]) for k in before if before[k] != after[k] and k not in ("q", "mana")}
            mana = (before["mana"], after["mana"]) if abs(before["mana"] - after["mana"]) > 500 else ""
            print(f"{name:5s} {expect:22s} orders {[tuple(int(x, 16) for x in o) for o in orders][:2]}  changes {chg} {('mana ' + str(mana)) if mana else ''}  ring {after['q']}", flush=True)
    finally:
        sess.close()


def live_variant(names: list[str], edits: dict, tag: str) -> str:
    """poppatch live for `names` from a scratch copy of patches/ with `edits` = {patch file stem: [(old, new)]} applied (each `old` once)."""
    import contextlib
    import io
    import shutil
    sys.path.insert(0, str(HERE))
    import poppatch
    pd = SCR / "variant" / tag
    shutil.rmtree(pd, ignore_errors=True)
    shutil.copytree(GAME / "patches", pd)
    for stem, eds in edits.items():
        t = (pd / f"{stem}.s").read_text()
        for old, new in eds:
            assert t.count(old) == 1, (stem, old)
            t = t.replace(old, new)
        (pd / f"{stem}.s").write_text(t)
    old_dir = poppatch.PATCHDIR
    poppatch.PATCHDIR = pd
    try:
        pats = [p for p in poppatch.load_patches() if p.name in set(names)]
        assert len(pats) == len(names), names
        out = SCR / f"live_{tag}"
        with contextlib.redirect_stdout(io.StringIO()):
            poppatch.cmd_live(pats, out)
    finally:
        poppatch.PATCHDIR = old_dir
    return str(out)


def cmd_misc(a):
    """(A) a key with the real pointer on land in raise / lower mode must not touch the land; (B) pause / un-pause with Space; (C) Armageddon needs
    the key twice: once (nothing), other key in between (nothing), second press after the arm ran out (nothing), twice (Armageddon)."""
    sess = Session(a.snap, a.live)
    h = sess.h
    try:
        time.sleep(1.0)
        h.debug("b all", 0.3)
        h.debug(NOP_ACIA, 0.3)                      # the pointer words are ours now
        for c in sess.load_live():
            h.debug(c, 0.4)
        h.debug(wb(0x3B270, 60000, 4), 0.3)
        (SCR / "misc").mkdir(parents=True, exist_ok=True)
        f = SCR / "misc" / "orders.txt"
        f.write_text("m $21e4a 3\n")
        h.cmd(f"hatari-debug b pc = $bbfa && ($21e4a).b ! 0 :trace :file {f}")
        time.sleep(0.4)

        def heights():
            out = h.debug("m $34c22 64", 0.9)
            return re.findall(r"(?im)^0*34c22: ((?:[0-9a-f]{2} ?){16})", out)

        def logged_orders(n0):
            log = h._logtext()[n0:]
            return [tuple(int(x, 16) for x in o) for o in re.findall(r"(?im)^0*21e4a: ([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2})", log) if o[0] != "00"]

        # (A) land
        poke_pointer(h, 200, 100)
        h.debug(wb(0x21D8E, 2), 0.2)
        time.sleep(1.5)
        hs = lambda: h.debug("m $34c22 128", 1.0)
        def hsum():
            t = hs()
            return re.findall(r"(?im)^0*34[0-9a-f]{3}: ((?:[0-9a-f]{2} ?)+)", t)
        before = hsum()
        s0 = rstate(h)
        n0 = len(h._logtext())
        h.keypress(SC["M"])
        time.sleep(2.0)
        after = hsum()
        s1 = rstate(h)
        print(f"(A) pointer words {hex(h.peekw(0x24786))},{hex(h.peekw(0x24788))} (on land), mode {s0['mode']}, key M: behaviour {s0['beh']} -> {s1['beh']}, "
              f"orders {logged_orders(n0)}, land bytes unchanged: {before == after}, mode {s1['mode']}")
        n0 = len(h._logtext())
        h.keypress(SC["Q"])
        time.sleep(1.5)
        h.keypress(SC["R"])
        time.sleep(1.5)
        after2 = hsum()
        print(f"    keys Q then R (modes only): land bytes unchanged: {before == after2}, mode {h.peekw(0x21D8E)}, orders {logged_orders(n0)}")
        # (B) pause
        for i in range(2):
            h.keypress(SC["Space"])
            time.sleep(1.5)
            print(f"(B) Space #{i + 1}: pause = {h.peekw(0x3B2B2)}")
        # (C) Armageddon
        def arm():
            return h.peekl(KD + 4) != 0
        n0 = len(h._logtext())
        h.keypress(SC["A"])
        time.sleep(1.0)
        print(f"(C1) A once: armed {arm()}, armageddon {h.peekw(0x3D562)}, orders {logged_orders(n0)}")
        h.shot(SCR / "misc" / "arm_hint_raw.png")
        h.keypress(SC["X"])
        time.sleep(1.0)
        print(f"(C2) then X: armed {arm()}, fx {h.peekw(0x2195E)}")
        h.keypress(SC["X"])
        time.sleep(1.0)
        h.keypress(SC["A"])
        time.sleep(1.0)
        print(f"(C3) A again after another key: armed {arm()}, armageddon {h.peekw(0x3D562)}, orders {logged_orders(n0)}")
        time.sleep(7.0)
        print(f"(C4) 7 s later: armed {arm()} (ran out)")
        h.keypress(SC["A"])
        time.sleep(1.0)
        print(f"(C5) A after the arm ran out: armed {arm()}, armageddon {h.peekw(0x3D562)}")
        h.keypress(SC["A"])
        time.sleep(2.5)
        print(f"(C6) A A: armed {arm()}, armageddon flag $3d562 = {h.peekw(0x3D562)}, orders {logged_orders(n0)}")
    finally:
        sess.close()


TEXT_STUB = """
        org     $76000
        movem.l d0-d7/a0-a6,-(sp)
        move.l  #$00220022,$76204.l     ; scaffold marker: the entry has started
        clr.l   -(sp)                   ; rect B ($1a)
        clr.l   -(sp)                   ; rect A ($16)
        move.w  #8,-(sp)                ; maximum length ($14)
        move.w  #100,-(sp)              ; y ($12)
        move.w  #100,-(sp)              ; x ($10)
        pea     $76100.l                ; the text buffer ($c)
        move.l  $3c50c.l,-(sp)          ; the screen ($8)
        jsr     $188ee.l                ; the game's own text entry (name / file name fields), returns at Return
        lea     26(sp),sp
        move.l  #$00110011,$76200.l     ; scaffold marker: the entry returned
        movem.l (sp)+,d0-d7/a0-a6
        jmp     $0bb7c.l
"""


def vasm_bin(src: str) -> bytes:
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "a.s").write_text(src)
        r = subprocess.run(["vasmm68k_mot", "-Fbin", "-quiet", "-o", str(Path(d) / "a.bin"), str(Path(d) / "a.s")], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stdout + r.stderr)
        return (Path(d) / "a.bin").read_bytes()


SC = {"R": 0x13, "Q": 0x10, "P": 0x19, "M": 0x32, "S": 0x1F, "G": 0x22, "T": 0x14, "E": 0x12, "W": 0x11, "K": 0x25, "V": 0x2F, "F": 0x21,
      "A": 0x1E, "L": 0x26, "Z": 0x2C, "B": 0x30, "N": 0x31, "H": 0x23, "U": 0x16, "X": 0x2D, "Space": 0x39, "Return": 0x1C, "Esc": 0x01}


def cmd_phantom(a):
    """Typed text and keys pressed in dialogs must never act.  (1) the game's own text entry ($188ee, the routine behind the name / file name
    fields) is started in the map loop by a scaffold stub and letters that are shortcut keys are typed into it; (2) the Options dialog is
    opened by an injected click on the scales icon and the same letters are typed while it is open.  After each, the ring, the arm and the
    game state are compared with the state before.  Run with the full key set and (control) without the two guards."""
    names = a.set.split("+")
    tag = ("wide_" if a.wide else "std_") + "_".join(n.replace("pop_", "") for n in names)
    live = live_variant(names, {"pop_keys": [("WIN     equ     150", "WIN     equ     1500")], "pop_keys2": [("WIN     equ     150", "WIN     equ     1500")]}
                        if a.wide else {}, tag)
    sess = Session(a.snap, live)
    h = sess.h
    typed = "RPMTQ"
    try:
        time.sleep(1.0)
        h.debug("b all", 0.3)
        for c in sess.load_live():
            h.debug(c, 0.4)
        h.debug(wb(0x3B270, 99999, 4), 0.3)
        f = h.R / "stub.bin"
        f.write_bytes(vasm_bin(TEXT_STUB))
        h.debug(f"loadbin {f} $76000", 0.4)
        h.debug("w $76200 $00 $00 $00 $00 $00 $00 $00 $00", 0.2)
        time.sleep(2.5)
        s0 = rstate(h)
        print("before:", {k: s0[k] for k in ("mode", "beh", "view", "music", "fx", "pause")}, "ring", s0["q"], "arm", s0["arm"])
        # ---- (1) the text entry
        h.cmd("hatari-debug b pc = $bb7c :trace :once :file " + str(h.R / "go.txt"))
        (h.R / "go.txt").write_text("r pc=$76000\n")
        t = time.time()
        while h.peekl(0x76204) != 0x00220022:          # the stub starts at the next pass
            assert time.time() - t < 30, "the text entry did not start"
        for ch in typed:
            h.keypress(SC[ch])
            time.sleep(0.25)
        time.sleep(0.3)
        s1 = rstate(h)
        print("text entry running (started marker", hex(h.peekl(0x76204)), "returned marker", hex(h.peekl(0x76200)), ")")
        print(f"after typing {typed!r} into the text entry: ring {s1['q']} arm {s1['arm']} state {{k: s1[k] for k in ('mode','beh','view','music','fx','pause')}}".replace("{k: s1[k] for k in ('mode','beh','view','music','fx','pause')}", str({k: s1[k] for k in ('mode', 'beh', 'view', 'music', 'fx', 'pause')})))
        t = time.time()
        while h.peekl(0x76200) != 0x00110011:          # a key event can be lost under host load: press again until the entry returns
            h.keypress(SC["Return"])
            time.sleep(0.6)
            assert time.time() - t < 40, "the text entry did not return at Return"
        print("text entry returned:", hex(h.peekl(0x76200)))
        time.sleep(6.0)
        s2 = rstate(h)
        same = all(s2[k] == s0[k] for k in ("mode", "beh", "view", "music", "fx", "pause"))
        print(f"after Return + 6 s of map passes: ring {s2['q']} arm {s2['arm']} state {{k: s2[k] for k in ('mode','beh','view','music','fx','pause')}}".replace("{k: s2[k] for k in ('mode','beh','view','music','fx','pause')}", str({k: s2[k] for k in ('mode', 'beh', 'view', 'music', 'fx', 'pause')})), "->", "UNCHANGED" if same else "CHANGED (keys acted)")
        res1 = same
        # ---- (2) the Options dialog
        g = h.R / "c.txt"
        g.write_text("\n".join(click_cmds(304, 160, "L")) + "\n")
        g2 = h.R / "g.txt"
        g2.write_text(wb(0x3C556, 304) + "\n" + wb(0x3C55A, 160) + "\n")
        h.cmd(f"hatari-debug b pc = $bba6 :trace :once :file {g}")
        h.cmd(f"hatari-debug b pc = $bbc4 :trace :once :file {g2}")
        time.sleep(1.5)
        for ch in typed:
            h.keypress(SC[ch])
            time.sleep(0.25)
        time.sleep(0.3)
        h.shot(SCR / "phantom_dialog.png")
        s4 = rstate(h)
        print(f"after typing {typed!r} with the Options dialog open: ring {s4['q']} arm {s4['arm']} state", {k: s4[k] for k in ("mode", "beh", "view", "music", "fx", "pause")})
        from populous import HOME
        h.goto(590, 425, home_xy=HOME)
        h.click(hold=0.4)
        time.sleep(7.0)
        s5 = rstate(h)
        same2 = all(s5[k] == s0[k] for k in ("mode", "beh", "view", "music", "fx", "pause"))
        print(f"after closing the dialog + 7 s: ring {s5['q']} arm {s5['arm']} state", {k: s5[k] for k in ("mode", "beh", "view", "music", "fx", "pause")}, "->", "UNCHANGED" if same2 else "CHANGED (keys acted)")
        h.shot(SCR / "phantom_after.png")
        print("PHANTOM", names, "text entry:", "no key acted" if res1 else "KEYS ACTED", "| dialog:", "no key acted" if same2 else "KEYS ACTED")
    finally:
        sess.close()


SHEETS = {  # group name -> icon numbers (pop_tooltip order)
    "spells": [1, 2, 3, 4, 5, 6], "behaviour": [7, 8, 9, 10], "modes": [11, 12, 13], "views": [14, 15, 16, 17, 18],
    "panel": [19, 20, 21, 22, 23, 24], "armageddon_hint": [25]}


def cmd_sheets(a):
    """work/shots/ui_tt_<group>.png: the whole screen with the first icon of the group hovered (pointer on it), under it the top strip (x 60-232,
    rows 0-18, 4x) of every icon of the group; plus ui_tt_nokeys.png (pop_tooltip alone) and ui_tt_none.png (the same strip with no hover)."""
    from PIL import Image, ImageDraw
    d = SCR / "tt"
    SHOTS.mkdir(parents=True, exist_ok=True)
    box = (96, 58, 736, 458)

    def strip(png):
        return Image.open(png).crop(box).crop((60 * 2, 0, 232 * 2, 19 * 2)).resize((172 * 2 * 3, 19 * 2 * 3), Image.NEAREST)
    for g, ids in SHEETS.items():
        first = Image.open(d / f"raw_{ids[0]}.png").crop(box)
        strips = [strip(d / f"raw_{i}.png") for i in ids]
        W = max(first.width, strips[0].width)
        H = first.height + sum(s.height + 4 for s in strips)
        sheet = Image.new("RGB", (W, H), (0, 0, 0))
        sheet.paste(first, (0, 0))
        y = first.height
        for s in strips:
            sheet.paste(s, (0, y))
            y += s.height + 4
        sheet.save(SHOTS / f"ui_tt_{g}.png")
        print("wrote", SHOTS / f"ui_tt_{g}.png", sheet.size)
    pair = [strip(d / f"rawnokeys_{i}.png") for i in (1, 14)] + [strip(d / "raw_1.png"), strip(d / "raw_14.png")] + [strip(d / "raw_none0.png")]
    sheet = Image.new("RGB", (pair[0].width, sum(p.height + 4 for p in pair)), (0, 0, 0))
    y = 0
    for p in pair:
        sheet.paste(p, (0, y))
        y += p.height + 4
    sheet.save(SHOTS / "ui_tt_keys_off_on_none.png")
    print("wrote ui_tt_keys_off_on_none.png (rows: pop_tooltip alone: flood, leader; with pop_keys: flood, leader; no hover)")


def cmd_cold(a):
    """Cold boot of a patched build (HD folder or floppy image) to the map and the checks that matter for this patch set: payload header and
    marker, the five site words, real keys Q / R / M, the tooltip with the pointer on the flood icon and away from it (screenshots in work/shots)."""
    import shutil
    import tempfile
    from populous import HOME, CONQUEST_XY, START_XY
    from stharness import TOS
    tos = TOS[a.tos]
    kw = dict(machine=a.machine, tos=tos, memsize_kb=a.mem)
    if a.medium == "hd":
        h = Populous(game_dir=GAME / a.path, snapshot=None, **kw)
    else:
        empty = GAME / "work" / "scratch" / "popui" / "empty"
        empty.mkdir(parents=True, exist_ok=True)
        cp = Path(tempfile.mkdtemp(prefix="pmimg-")) / Path(a.path).name
        shutil.copy(GAME / a.path, cp)
        h = Populous(game_dir=empty, autorun="", files=[], extra=["--disk-a", str(cp), "--drive-a", "true"], snapshot=None, **kw)

    def mem(addr, n=4):
        out = h.debug(f"m ${addr:x} {n}", 0.7)
        hx = re.findall(rf"{addr:08x}:\s+((?:[0-9a-f]{{2}} ?)+)", out, re.I)
        return hx[-1].strip() if hx else out.strip()
    try:
        if a.medium == "hd":
            time.sleep(16)
            h.key("space", 0.5)             # PP's hardware screen
            time.sleep(28)
        else:
            time.sleep(14)                  # the original DEMO.TOS title and menu are up after ~13 s (and run into the attract mode after ~40 s)
        h.goto(*CONQUEST_XY, home_xy=HOME)
        h.click(hold=0.4)
        time.sleep(9 if a.medium == "hd" else 20)      # the floppy loads the world page slowly
        for _ in range(6):
            h.goto(*START_XY, home_xy=HOME)
            h.click(hold=0.4)
            time.sleep(12)
            if h.in_play():
                break
        print("in play:", h.in_play())
        hdr = mem(0xB3000, 16)
        print("payload header:", hdr, "-> marker", bytes.fromhex(hdr.replace(" ", "")[8:16]).decode("latin1"))
        for name, addr, n in (("pop_keys $bb7c", 0xBB7C, 6), ("pop_keys2 $2008c", 0x2008C, 6), ("pop_keys3 $200a6", 0x200A6, 10),
                              ("pop_keys4 $1a508", 0x1A508, 10), ("pop_tooltip $b93a", 0xB93A, 6)):
            print(f"{name:18s} {mem(addr, n)}")
        print("turn counter:", h.peekw(TURN), "->", (time.sleep(2), h.peekw(TURN))[1])
        h.debug(wb(0x3B270, 99999, 4), 0.3)
        for k, expect in (("Q", "mode"), ("R", "mode"), ("M", "beh"), ("T", "beh"), ("L", "view")):
            before = rstate(h)
            h.keypress(SC[k])
            time.sleep(2.0)
            after = rstate(h)
            print(f"real key {k}: mode {before['mode']}->{after['mode']} behaviour {before['beh']}->{after['beh']} view {before['view']}->{after['view']} ring {after['q']}")
        h.goto(96 + 2 * 16, 58 + 2 * 128, home_xy=HOME)          # the flood icon
        time.sleep(1.5)
        print("pointer words", hex(h.peekw(0x24786)), hex(h.peekw(0x24788)))
        SHOTS.mkdir(parents=True, exist_ok=True)
        h.shot(str(SCR / f"cold_{a.name}_hover_raw.png"))
        crop_shot(SCR / f"cold_{a.name}_hover_raw.png", SHOTS / f"ui_cold_{a.name}_hover.png")
        h.goto(96 + 2 * 200, 58 + 2 * 100, home_xy=HOME)
        time.sleep(1.5)
        h.shot(str(SCR / f"cold_{a.name}_away_raw.png"))
        crop_shot(SCR / f"cold_{a.name}_away_raw.png", SHOTS / f"ui_cold_{a.name}_away.png")
        print("shots:", SHOTS / f"ui_cold_{a.name}_hover.png", SHOTS / f"ui_cold_{a.name}_away.png")
    finally:
        h.close()


def cmd_cost(a):
    """CPU cycles spent inside the patch blobs ($c7000-$c7fff) per pass, from the emulator's profiler, on a busy snapshot at 8 MHz: pointer away
    from the icons, on an icon (tooltip up, steady), and with a key press every few passes is not measured (a key is a rare event)."""
    sess = Session(a.snap, a.live)
    h = sess.h
    try:
        time.sleep(1.0)
        h.debug("b all", 0.3)
        h.debug(NOP_ACIA, 0.3)
        for c in sess.load_live():
            h.debug(c, 0.4)
        for label, (x, y) in (("pointer away (200,100)", (200, 100)), ("pointer on flood icon (16,128)", (16, 128)), ("pointer on the scroll arrows (80,168)", (80, 168)),
                              ("pointer away again", (200, 100))):
            poke_pointer(h, x, y)
            time.sleep(1.5)
            t0 = h.peekw(TURN)
            prof = h.profile(a.vbls)
            t1 = h.peekw(TURN)
            blob = sum(c for ad, c in prof if 0xC7000 <= ad < 0xC8000)
            tot = sum(c for ad, c in prof)
            passes = (t1 - t0) & 0xFFFF
            print(f"{label:40s} blob cycles {blob:9d} over {passes} turns ({blob // max(passes, 1)} per pass); all profiled cycles {tot} "
                  f"({tot // max(passes, 1)} per pass, {100.0 * blob / max(tot, 1):.3f} %)")
    finally:
        sess.close()


FINAL_SEQ = ["knight", "view_knight", "view_battle", "query", "raise", "magnet_mode", "to_magnet", "settle", "gather", "fight", "view_leader", "view_magnet",
             "view_house", "music", "music", "effects", "effects", "swamp", "earthquake", "volcano", "flood", "pause", "pause", "armageddon"]


def cmd_final(a):
    """One clean real-key pass on a cold-booted HD build: every mapped key through IKBD/ACIA, orders logged at $bbfa for each, then the same icon
    clicked (debugger-injected, as the gate's reference) for comparison."""
    from populous import HOME, CONQUEST_XY, START_XY
    from stharness import TOS
    h = Populous(game_dir=GAME / a.path, snapshot=None, machine="ste", tos=TOS["1.62"], memsize_kb=1024)
    for nm in ("peekw",):
        orig = getattr(h, nm)
        def robust(addr, _o=orig):
            for _ in range(6):
                try:
                    return _o(addr)
                except Exception:
                    time.sleep(0.5)
            raise RuntimeError(f"peek {addr:x} failed")
        setattr(h, nm, robust)
    try:
        time.sleep(16); h.key("space", 0.5); time.sleep(28)
        h.goto(*CONQUEST_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(9)
        for _ in range(4):
            h.goto(*START_XY, home_xy=HOME); h.click(hold=0.4); time.sleep(12)
            if h.in_play():
                break
        print("in play:", h.in_play(), "marker", hex(h.peekl(0xB3004)))
        h.debug(wb(0x3B270, 99999, 4), 0.3)
        f = h.R / "o.txt"; f.write_text("m $21e4a 3\n")
        h.cmd(f"hatari-debug b pc = $bbfa && ($21e4a).b ! 0 :trace :file {f}")
        time.sleep(0.5)

        def orders(n0):
            return [tuple(int(x, 16) for x in o) for o in re.findall(r"(?im)^0*21e4a: ([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2})", h._logtext()[n0:]) if o[0] != "00"]

        def snap():
            r = rstate(h)
            return {k: r[k] for k in ("mode", "beh", "view", "music", "fx", "pause", "mana")}

        def delta(b, c):
            return {k: (b[k], c[k]) for k in b if b[k] != c[k] and k != "mana"} | ({"mana": c["mana"] - b["mana"]} if abs(c["mana"] - b["mana"]) > 500 else {})
        print(f"{'key':12s} {'REAL KEY: orders / change':60s} CLICK: orders / change")
        scs = {n: ICONS[n] for n in ICONS}
        for n in FINAL_SEQ:
            sc, x, y, btn = ICONS[n]
            nA = 2 if n == "armageddon" else 1
            n0 = len(h._logtext()); b = snap()
            for _ in range(nA):
                h.keypress(sc); time.sleep(1.2)
            time.sleep(1.5)
            c = snap(); oa = orders(n0)
            n1 = len(h._logtext())
            g = h.R / "c.txt"; g.write_text("\n".join(click_cmds(x, y, btn)) + "\n")
            g2 = h.R / "g.txt"; g2.write_text(wb(0x3C556, x) + "\n" + wb(0x3C55A, y) + "\n")
            h.cmd(f"hatari-debug b pc = $bba6 :trace :once :file {g}"); h.cmd(f"hatari-debug b pc = $bbc4 :trace :once :file {g2}")
            time.sleep(3.0)
            d = snap(); ob = orders(n1)
            print(f"{n:12s} {str(oa):14s} {str(delta(b, c)):45s} | {str(ob):14s} {delta(c, d)}", flush=True)
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("geom")
    sc = sub.add_parser("scan")
    sc.add_argument("--snap", default="genesis_start")
    sc.add_argument("--live")
    sc.add_argument("--mana", type=int)
    ky = sub.add_parser("keys")
    ky.add_argument("--snap", default="genesis_start")
    ky.add_argument("--live", required=True)
    ky.add_argument("--mutant", choices=["key_pos"])
    ky.add_argument("--only", nargs="*")
    ky.add_argument("--selftest", action="store_true")
    sub.add_parser("words")
    fn = sub.add_parser("final")
    fn.add_argument("--path", default="build/PopUI/hd_final")
    co = sub.add_parser("cost")
    co.add_argument("--snap", default="busy_castles")
    co.add_argument("--live", required=True)
    co.add_argument("--vbls", type=int, default=400)
    cd = sub.add_parser("cold")
    cd.add_argument("name")
    cd.add_argument("--medium", choices=["hd", "floppy"], default="hd")
    cd.add_argument("--path", default="build/PopUI/hd")
    cd.add_argument("--machine", default="ste")
    cd.add_argument("--tos", default="1.62")
    cd.add_argument("--mem", type=int, default=1024)
    sub.add_parser("sheets")
    ms = sub.add_parser("misc")
    ms.add_argument("--snap", default="genesis_start")
    ms.add_argument("--live", required=True)
    ph = sub.add_parser("phantom")
    ph.add_argument("--snap", default="genesis_start")
    ph.add_argument("--set", default="pop_noprot+pop_keys+pop_keys2+pop_keys3+pop_keys4")
    ph.add_argument("--wide", action="store_true", help="WIN = 1500 VBLs: only the guards (not the time window) can stop a typed key")
    tr = sub.add_parser("ttrect")
    tr.add_argument("--snap", default="busy_castles")
    tr.add_argument("--set", default="pop_keys+pop_keys2+pop_keys3+pop_keys4+pop_tooltip")
    tr.add_argument("--mutant", choices=sorted(MUT))
    rk = sub.add_parser("realkeys")
    rk.add_argument("--snap", default="genesis_start")
    rk.add_argument("--live", required=True)
    rk.add_argument("--mana", type=int, default=99999)
    rk.add_argument("--wait", type=float, default=2.5)
    gt = sub.add_parser("gate")
    gt.add_argument("--snap", nargs="*")
    gt.add_argument("--set", nargs="+", required=True, help="patch names joined by +, one set per argument")
    gt.add_argument("--away", action="store_true")
    gt.add_argument("--mutant", choices=sorted(MUT))
    gt.add_argument("--keep")
    tt = sub.add_parser("tt")
    tt.add_argument("--snap", default="genesis_start")
    tt.add_argument("--live", required=True)
    tt.add_argument("--ids", nargs="*", type=int)
    tt.add_argument("--wait", type=float, default=1.5)
    tt.add_argument("--arm", action="store_true")
    a = ap.parse_args()
    if a.cmd == "realkeys":
        return cmd_realkeys(a)
    if a.cmd == "ttrect":
        return cmd_ttrect(a)
    if a.cmd == "final":
        return cmd_final(a)
    if a.cmd == "cost":
        return cmd_cost(a)
    if a.cmd == "cold":
        return cmd_cold(a)
    if a.cmd == "sheets":
        return cmd_sheets(a)
    if a.cmd == "misc":
        return cmd_misc(a)
    if a.cmd == "phantom":
        return cmd_phantom(a)
    if a.cmd == "gate":
        return cmd_gate(a)
    if a.cmd == "tt":
        return cmd_tt(a)
    if a.cmd == "words":
        return cmd_words(a)
    if a.cmd == "keys":
        return cmd_keys(a)
    if a.cmd == "scan":
        return cmd_scan(a)
    if a.cmd == "geom":
        for n, (sc, x, y, b) in ICONS.items():
            print(f"{n:12s} key ${sc:02x} at ({x:3d},{y:3d}) {b}: {cell(x, y)}")


if __name__ == "__main__":
    main()
