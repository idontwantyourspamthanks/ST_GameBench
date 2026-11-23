#!/usr/bin/env python3
"""Tooltip tools for patches/pm_tooltip.s (stage 3): the reference renderer, the static checks and the live pixel gate.

    python3 tools/wwtt.py check                      wording table: every text <= 52 characters with and without key labels, entry shapes, key labels vs qol_keys' KT
    python3 tools/wwtt.py gate --disk build/default/floppy.st --manifest build/default/manifest.json [--workdir D] [--snapshot S.sav] [--machine ste --tos 1.62 --mem 1024]
                                                     live gate on a built floppy (cold boot to the map view, or --snapshot of a boot of the same floppy)
    python3 tools/wwtt.py sheet --out work/shots/stage03/sheet.png ...   side-by-side sheet with master's pictures

The reference rendering is composed in Python from the game's font (the file-derived resident image, `wwpatch.resident_image()`, glyph block 48 B at $8406 + 48 * (ch >> 2),
column ch & 3), glyph colour 1 (the window background) mapped to 0, planar 4 bpp exactly as the screen holds it: 6 rows x 13 sixteen-pixel words x 4 planes = 624 B for the
52-character line at screen byte 56 (column 7) of rows 0..5.  The gate compares the machine's pixels with it byte for byte (RAM of both screen buffers at the hook's entry and
exit, the displayed buffer, and a Hatari screenshot with the palette read from the shifter).
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
import wwgrid  # noqa: E402
import wwpatch  # noqa: E402

PATCH = ROOT / "patches" / "pm_tooltip.s"
KEYS = ROOT / "patches" / "qol_keys.s"
FONT = 0x8406
NCH = 52
S = 0x74800                      # tooltip state block (patch header)
S_ID, S_KEY, S_VAL, S_MAG = S + 4, S + 6, S + 8, S + 0xE
KF = 0x730C8
HOOK_ENTRY, HOOK_EXIT = 0x73400, 0x18570
POSTURE_WORD = lambda sel: 0x5574E + sel + 0x3C      # + [$5a834]
SEL = 0x5A834
SCREEN_A, SCREEN_B = 0x1D500, 0x25200
SHOTS = ROOT / "work" / "shots" / "stage03"

IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 19, 20, 21, 22, 23] + list(range(24, 33))   # the 29 ids that have a text (ET has 33 words, 4 blank)
LEVELED = {2, 3, 4, 6, 7, 8, 9, 10, 12, 13, 14}                                                      # ids with three effect strings (1 / 2 / 3 swords)


# ---- wording table ----------------------------------------------------------------------------------------------------------------------
def parse_table(src: str | None = None) -> dict[int, tuple[str, str, list[str]]]:
    """id -> (name, key label, [effect strings; an effect may hold a \\x03 keys-only variant])."""
    src = src if src is not None else PATCH.read_text()
    out = {}
    for m in re.finditer(r'^e(\d+):\s+dc\.b\s+(\d),(.*)$', src, re.M):
        cnt = int(m.group(2))
        toks = re.findall(r'"[^"]*"|\b0\b', m.group(3).replace('",3,"', "\x03"))
        strs, i = [], 0
        while i < len(toks):
            t = toks[i]
            if t.startswith('"'):
                strs.append(t[1:-1])
                if i + 1 < len(toks) and toks[i + 1] == "0":
                    i += 1
            else:
                strs.append("")
            i += 1
        if len(strs) != 2 + cnt:
            raise SystemExit(f"e{m.group(1)}: count {cnt} but {len(strs) - 2} effect strings ({strs})")
        out[int(m.group(1))] = (strs[0], strs[1], strs[2:])
    return out


def text_for(table, i: int, level: int, keys: bool) -> str:
    """The 52-character line the patch builds for icon id i, posture level 0..2 (0 = 1 sword) and key labels on/off (space padded)."""
    name, key, effs = table[i]
    e = effs[level if len(effs) == 3 else 0]
    off, _, on = e.partition("\x03")
    e = on if (keys and on) else off
    line = name + (f" ({key})" if keys and key else "") + ": " + e
    assert len(line) <= NCH, (i, line)
    return line.ljust(NCH)


def level_of_posture(word: int) -> int:
    """pm_tooltip: 4 -> 0 (1 sword), 3 -> 1, 2 -> 2; any other value -> 1 (neutral)."""
    return 4 - word if 2 <= word <= 4 else 1


# ---- reference rendering ---------------------------------------------------------------------------------------------------------------
_img = None


def font_image() -> bytes:
    global _img
    if _img is None:
        _img = wwpatch.resident_image()
    return _img


def glyph(ch: int) -> list[list[int]]:
    """6 rows x 4 pixels of colour indices (0..15) of character ch."""
    img, B = font_image(), wwpatch.GAME
    blk, col = FONT - B + 48 * (ch >> 2), ch & 3
    rows = []
    for y in range(6):
        pl = [(img[blk + y * 8 + 2 * p] << 8) | img[blk + y * 8 + 2 * p + 1] for p in range(4)]
        rows.append([sum(((pl[p] >> (15 - (col * 4 + x))) & 1) << p for p in range(4)) for x in range(4)])
    return rows


def render_idx(text: str) -> list[list[int]]:
    """6 rows x 208 colour indices; the glyph background (colour 1) is colour 0."""
    rows = [[] for _ in range(6)]
    for c in text.ljust(NCH)[:NCH]:
        g = glyph(ord(c))
        for y in range(6):
            rows[y] += [0 if v == 1 else v for v in g[y]]
    return rows


def pack_planar(idx_rows) -> bytes:
    """6 x 104 bytes: per row 13 words of 16 pixels, 4 planes each (plane 0 first), big endian: the screen format (rows 0..5, bytes 56..159)."""
    out = bytearray()
    for r in idx_rows:
        for w in range(13):
            px = r[w * 16:(w + 1) * 16]
            for p in range(4):
                v = 0
                for x, c in enumerate(px):
                    v |= ((c >> p) & 1) << (15 - x)
                out += v.to_bytes(2, "big")
    return bytes(out)


def expected_bytes(text: str) -> bytes:
    return pack_planar(render_idx(text))


def screen_region(buf: bytes) -> bytes:
    """rows 0..5, bytes 56..159 of a 32000-byte screen buffer (the tooltip area)."""
    return b"".join(buf[y * 160 + 56:y * 160 + 160] for y in range(6))


def pixels_of(buf: bytes, x0=0, x1=320, y0=0, y1=6):
    """colour index per pixel of rows y0..y1-1, x0..x1-1 from a planar screen buffer."""
    out = []
    for y in range(y0, y1):
        row = []
        for x in range(x0, x1):
            o = y * 160 + (x >> 4) * 8
            b = 15 - (x & 15)
            v = 0
            for p in range(4):
                v |= (((buf[o + 2 * p] << 8 | buf[o + 2 * p + 1]) >> b) & 1) << p
            row.append(v)
        out.append(row)
    return out


# ---- hit test (an independent copy of the game's rules, see the patch header) ----------------------------------------------------------
def hit_ref(x: int, y: int, window_open: bool = False) -> int:
    if y < 6:
        return 0 if (x >= 64 or window_open) else 24 + (x >> 4)
    for k, (x0, y0, x1, y1) in enumerate(wwgrid.RECTS):
        if x0 <= x < x1 and y0 <= y < y1:
            return 28 + k
    if x < 32:
        return 32 if y > 0xA7 else 0
    if x < 64 or y < 129:
        return 0
    i = wwgrid.icon(x, y)
    return i if i in IDS else 0


# ---- static checks ---------------------------------------------------------------------------------------------------------------------
SC_LABEL = {0x02: "1", 0x03: "2", 0x04: "3", 0x1E: "A", 0x20: "D", 0x12: "E", 0x21: "F", 0x22: "G", 0x23: "H", 0x17: "I", 0x26: "L", 0x32: "M", 0x31: "N", 0x18: "O",
            0x10: "Q", 0x13: "R", 0x1F: "S", 0x14: "T", 0x2D: "X", 0x15: "Y", 0x3B: "F1", 0x3C: "F2", 0x3D: "F3", 0x3E: "F4", 0x1A: "[", 0x1B: "]", 0x0D: "=",
            0x4E: "KP+", 0x0C: "-", 0x4A: "KP-"}                                  # scan code -> the label the tooltip shows; keypad 1-3 are not shown (the digit row is)
KEYPAD_DIGITS = {0x6D, 0x6E, 0x6F}


def key_ids() -> dict[int, set[str]]:
    """tooltip id -> set of key labels, from qol_keys' own table KT (scan code -> id by the game's hit test, tools/wwgrid.py)."""
    out: dict[int, set[str]] = {}
    for m in re.finditer(wwgrid.KEYPAT, KEYS.read_text(), re.M):
        sc, x, y = int(m.group(1), 16), int(m.group(3)), int(m.group(4))
        if sc in KEYPAD_DIGITS:
            continue
        out.setdefault(hit_ref(x, y), set()).add(SC_LABEL[sc])
    return out


def cmd_check(a) -> int:
    t = parse_table()
    bad = n = 0
    longest = (0, "")
    for i in IDS:
        if i not in t:
            print(f"MISSING entry for id {i}")
            bad += 1
            continue
        _, _, effs = t[i]
        if (len(effs) == 3) != (i in LEVELED):
            print(f"id {i}: {len(effs)} effect strings but LEVELED says {i in LEVELED}")
            bad += 1
        for lv in range(3):
            for keys in (False, True):
                n += 1
                try:
                    s = text_for(t, i, lv, keys)
                except AssertionError as e:
                    print(f"TOO LONG {e}")
                    bad += 1
                    continue
                if len(s.rstrip()) > longest[0]:
                    longest = (len(s.rstrip()), s.rstrip())
                if any(not (32 <= ord(c) < 127) for c in s):
                    print(f"id {i}: non-ASCII character in {s!r}")
                    bad += 1
    ET = re.search(r"^ETA:\s+dc\.w\s+0\n((?:\s+dc\.w .*\n)+)", PATCH.read_text(), re.M).group(1)
    words = [w.strip() for ln in ET.splitlines() for w in ln.split("dc.w")[1].split(",")]
    for k, w in enumerate(words, 1):                                                 # word k (k = 1..32) is the entry for id k
        want = f"e{k}-TXTA" if k in IDS else "0"
        if w != want:
            print(f"ET word for id {k}: {w!r}, want {want!r}")
            bad += 1
    if len(words) != 32:
        print(f"ET has {len(words) + 1} words, want 33")
        bad += 1
    ki = key_ids()
    for i in IDS:
        name, key, _ = t[i]
        want = ki.get(i, set())
        got = {k.strip() for k in key.split(" or ")} - {""}
        ok = got == want
        n += 1
        if not ok:
            print(f"KEY LABEL id {i} {name!r}: tooltip {sorted(got)} vs qol_keys KT {sorted(want)}")
            bad += 1
    print(f"WORDING {len(IDS)} ids, {n} checks (text <= {NCH} chars with and without key labels, ET words, labels vs KT), longest {longest[0]}: {longest[1]!r}, {bad} problems")
    return 1 if bad else 0


# ---- live gate -------------------------------------------------------------------------------------------------------------------------
def palette_rgb(words: list[int]):
    """Hatari's STE palette: 4 bits per channel (bit 3 = the low bit), x17."""
    out = []
    for v in words:
        ch = []
        for sh in (8, 4, 0):
            n = (v >> sh) & 0xF
            ch.append((((n & 7) << 1) | (n >> 3)) * 17)
        out.append(tuple(ch))
    return out


class Gate:
    def __init__(self, tag):
        self.tag, self.ok, self.n_pass, self.n_fail = tag, True, 0, 0

    def line(self, name, ok, detail=""):
        self.ok &= bool(ok)
        self.n_pass += bool(ok)
        self.n_fail += not ok
        print(f"GATE {self.tag} {name} {'PASS' if ok else 'FAIL'} {detail}", flush=True)
        return ok


def peek_block(h, addr: int, n: int) -> bytes:
    out = h.debug(f"m ${addr:x} {n}", 0.6)
    res = bytearray()
    for ln in out.splitlines():
        m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} ?)+)", ln)
        if m and int(m.group(1), 16) >= addr and len(res) < n:
            res += bytes.fromhex(m.group(2).replace(" ", ""))
    return bytes(res[:n])


def shifter_base(h) -> int:
    b = peek_block(h, 0xFF8201, 1)[0], peek_block(h, 0xFF8203, 1)[0]
    return (b[0] << 16) | (b[1] << 8)


def read_palette(h):
    b = peek_block(h, 0xFF8240, 32)
    return palette_rgb([(b[2 * i] << 8) | b[2 * i + 1] for i in range(16)])


def screen_crop_rgb(png: Path, x0, x1, y0, y1):
    """ST pixel -> RGB from a Hatari screenshot (picture area at (96,58), 2x2 host pixels per ST pixel); also checks the 2x2 blocks are uniform."""
    from PIL import Image
    im = Image.open(png).convert("RGB")
    out, uniform = [], True
    for y in range(y0, y1):
        row = []
        for x in range(x0, x1):
            px = [im.getpixel((96 + 2 * x + dx, 58 + 2 * y + dy)) for dy in (0, 1) for dx in (0, 1)]
            uniform &= len(set(px)) == 1
            row.append(px[0])
        out.append(row)
    return out, uniform


class Live:
    """Everything the gate does to the running machine."""

    def __init__(self, h):
        self.h = h
        self.n = 0

    def state(self):
        """(LX, LY, ID, KEY, VAL) of the tooltip's state block."""
        b = peek_block(self.h, S, 12)
        w = [(b[2 * i] << 8) | b[2 * i + 1] for i in range(6)]
        return tuple(w[:5])

    def capture_hook(self, timeout=40):
        """One-shot breakpoints at the hook's entry ($73400) and its exit ($18570, the routine it tail-jumps to); each saves both screen buffers and the registers,
        the exit one also the shifter's video base.  Returns dict(in=(a, b), out=(a, b), regs_in, regs_out, base)."""
        h = self.h
        self.n += 1
        tag = f"cap{self.n}"
        files = {}
        for ph in ("in", "out"):
            files[ph] = [h.R / f"{tag}_{ph}_{k}.bin" for k in "ab"]
            for f in files[ph]:
                f.unlink(missing_ok=True)
            extra = "m $ff8201 1\nm $ff8203 1\n" if ph == "out" else ""
            (h.R / f"{tag}_{ph}.txt").write_text(f"savebin {files[ph][0]} ${SCREEN_A:x} 32000\nsavebin {files[ph][1]} ${SCREEN_B:x} 32000\nr\n{extra}")
        h.debug("b all", 0.3)
        mark = len(h._logtext())
        h.cmd(f"hatari-debug b pc = ${HOOK_ENTRY:x} :trace :once :file {h.R}/{tag}_in.txt")
        h.cmd(f"hatari-debug b pc = ${HOOK_EXIT:x} :trace :once :file {h.R}/{tag}_out.txt")
        t = time.time()
        while not all(f.exists() and f.stat().st_size == 32000 for ph in files.values() for f in ph):
            if time.time() - t > timeout:
                raise TimeoutError("the hook breakpoints never fired")
            time.sleep(0.2)
        time.sleep(0.6)
        log = h._logtext()[mark:]
        secs = {}
        for ph in ("in", "out"):
            k = log.index(f"{tag}_{ph}.txt'...")
            nxt = log.find("Reading debugger commands", k + 10)
            secs[ph] = log[k:nxt if nxt > 0 else len(log)]

        def regs(sec):
            return dict(re.findall(r"\b([DA][0-7]) ([0-9A-F]{8})", sec))
        b = peek_hex(secs["out"], 0xFF8201), peek_hex(secs["out"], 0xFF8203)
        return dict(inn=[f.read_bytes() for f in files["in"]], out=[f.read_bytes() for f in files["out"]], regs_in=regs(secs["in"]), regs_out=regs(secs["out"]),
                    base=(b[0] << 16) | (b[1] << 8))


def peek_hex(sec: str, addr: int) -> int:
    m = re.search(rf"{addr:08X}:\s+([0-9A-Fa-f]{{2}})", sec)
    return int(m.group(1), 16)


def probe(h, live, g, name, x, y, pal, keys_on=True, window=False, shot=None):
    """Hover at ST pixel (x, y) and check everything about the tooltip the machine shows: id, key, the pixels of the line in both buffers at the hook's
    exit, the hook's write footprint, registers, the displayed buffer and a screenshot."""
    px, py = h.goto_st(x, y)
    want_id = hit_ref(px, py, window)
    word = h.peekw(POSTURE_WORD(h.peekw(SEL)))
    level = level_of_posture(word)
    want_key = (want_id * 4 + level + (0x100 if keys_on else 0)) if want_id else 0
    t = time.time()
    st = None
    while time.time() - t < 25:
        st = live.state()
        if st[0] == px and st[1] == py and st[2] == want_id and st[3] == want_key:
            break
        time.sleep(0.5)
    ok_state = st is not None and st[0] == px and st[1] == py and st[2] == want_id and st[3] == want_key
    g.line(f"{name} hover state", ok_state, f"pointer ({px},{py}) id {st[2]} want {want_id}, KEY ${st[3]:x} want ${want_key:x} (posture word {word}, level {level}, keys {keys_on})")
    time.sleep(2.0)                                      # at least one more rendered pass so that both buffers hold the line
    cap = live.capture_hook()
    if shot:
        h.shot(str(shot))
    text = text_for(TABLE, want_id, level, keys_on) if want_id else " " * NCH
    exp = expected_bytes(text)
    black = bytes(len(exp))
    a_in, b_in = cap["inn"]
    a_out, b_out = cap["out"]
    back_is_a = a_in != a_out
    back_is_b = b_in != b_out
    if want_id == 0:
        g.line(f"{name} no tooltip: the hook wrote nothing", not back_is_a and not back_is_b, f"changed buffers a={back_is_a} b={back_is_b}")
        back_in, back_out = (a_in, a_out)
    else:
        g.line(f"{name} the hook wrote exactly one buffer", back_is_a != back_is_b, f"changed a={back_is_a} b={back_is_b}")
        back_in, back_out = (a_in, a_out) if back_is_a else (b_in, b_out)
    # the hook's footprint: every changed byte inside rows 0..5, bytes 56..159
    diff = [i for i in range(32000) if back_in[i] != back_out[i]]
    outside = [i for i in diff if not (i // 160 < 6 and (i % 160) >= 56)]
    g.line(f"{name} footprint", not outside, f"{len(diff)} bytes changed, {len(outside)} outside rows 0-5 / byte 56..159" + (f": first {[hex(o) for o in outside[:6]]}" if outside else ""))
    g.line(f"{name} the line was composed on a clean bar", screen_region(back_in) == black, "region before the hook is all colour 0")
    got = screen_region(back_out)
    nbad = sum(1 for p, q in zip(got, exp) if p != q)
    g.line(f"{name} pixels == reference rendering", got == exp, f"text {text.rstrip()!r}: {nbad} of {len(exp)} bytes differ")
    same = {k: v for k, v in cap["regs_in"].items() if cap["regs_out"].get(k) != v}
    g.line(f"{name} registers and stack pointer preserved", not same and len(cap["regs_in"]) == 16, f"differences {same}")
    front = a_out if cap["base"] == SCREEN_A else b_out if cap["base"] == SCREEN_B else None
    if front is None:
        g.line(f"{name} displayed buffer found", False, f"video base ${cap['base']:x}")
    else:
        g.line(f"{name} displayed buffer pixels == reference", screen_region(front) == exp, f"base ${cap['base']:x}, {sum(1 for p, q in zip(screen_region(front), exp) if p != q)} bytes differ")
    if shot:
        rgb, uni = screen_crop_rgb(Path(shot), 112, 320, 0, 6)
        want = [[pal[c] for c in row] for row in render_idx(text)]
        nb = sum(1 for r1, r2 in zip(rgb, want) for p, q in zip(r1, r2) if p != q)
        g.line(f"{name} screenshot == reference (colours of the machine's palette)", nb == 0 and uni, f"{nb} of {208 * 6} pixels differ, 2x2 blocks uniform {uni}")
        allowed = {pal[0]} | {pal[c] for row in render_idx(text) for c in row}
        stray = sum(1 for row in rgb for p in row if p not in allowed)
        g.line(f"{name} no stray colours (khaki box, junk) in the line area", stray == 0, f"{stray} pixels outside black + the text's own colours")
    return cap


TABLE = None


POINTS = {24: (8, 2), 25: (24, 2), 26: (40, 2), 27: (56, 2), 28: (28, 158), 29: (37, 165), 30: (53, 166), 31: (53, 185), 32: (15, 185)}     # qol_keys' own click points
POSTURE_CLICK = {2: (97, 157), 3: (95, 145), 4: (92, 135)}                                                                                  # posture word -> icon centre (KT): 3 / 2 / 1 sword
NONE_POINTS = [(30, 80), (150, 60), (150, 128), (48, 150), (200, 3), (319, 0), (64, 6), (10, 100), (100, 128), (319, 100)]


def hover_points():
    """id -> a centre point of its icon, from the game's own hit test (wwgrid); the extra points are the first / last pixel of each cell."""
    cells = wwgrid.cells()
    cen, extra = {}, {}
    for i in IDS:
        if i in POINTS:
            cen[i] = POINTS[i]
            extra[i] = []
            continue
        pts = cells[i]
        cen[i] = wwgrid.centre(pts)
        extra[i] = [pts[0], pts[-1]]
    for i, p in cen.items():
        assert hit_ref(*p) == i, (i, p, hit_ref(*p))
    return cen, extra


def quick(h, live, g, name, x, y, keys_on=True):
    """Hit test only: pointer at (x, y), the tooltip's id / key as the machine computed them."""
    px, py = h.goto_st(x, y)
    want_id = hit_ref(px, py)
    word = h.peekw(POSTURE_WORD(h.peekw(SEL)))
    want_key = (want_id * 4 + level_of_posture(word) + (0x100 if keys_on else 0)) if want_id else 0
    t = time.time()
    st = None
    while time.time() - t < 20:
        st = live.state()
        if st[0] == px and st[1] == py and st[2] == want_id and st[3] == want_key:
            break
        time.sleep(0.5)
    ok = st[0] == px and st[1] == py and st[2] == want_id and st[3] == want_key
    g.line(f"hit {name} ({px},{py})", ok, f"machine id {st[2]} key ${st[3]:x}, reference id {want_id} key ${want_key:x}")


def set_posture(h, g, word):
    x, y = POSTURE_CLICK[word]
    h.click_st(x, y, wait=1.5)
    got = h.peekw(POSTURE_WORD(h.peekw(SEL)))
    g.line(f"posture click ({x},{y}) sets the captain's posture word", got == word, f"word {got} want {word}")
    return got == word


def run_gate(a) -> int:
    global TABLE
    sys.path.insert(0, str(HERE))
    import pmww
    TABLE = parse_table()
    man = json.loads(Path(a.manifest).read_text()) if a.manifest else {"patches": []}
    noprot = "pm_noprot" in man["patches"]
    keydisk = "pm_nokeydisk" in man["patches"]
    keys_on = "qol_keys" in man["patches"]
    g = Gate(a.tag)
    SHOTS.mkdir(parents=True, exist_ok=True)
    cen, extra = hover_points()
    kw = dict(disk=Path(a.disk), workdir=a.workdir, machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=a.mem)
    if a.snapshot:
        kw["snapshot"] = a.snapshot
    h = pmww.PMW(**kw)
    t0 = time.time()
    try:
        if not a.snapshot:
            h.boot_to_map(noprot=noprot, swap=not keydisk)
        g.line("map view", h.ticking(2.0), f"counter {h.counter()}")
        time.sleep(2)
        live = Live(h)
        g.line("tooltip hook alive", live.state()[4] == 1 and h.peekl(S_MAG) == 0x50544950, f"state {live.state()} MAG ${h.peekl(S_MAG):x}")
        kf = h.peekw(KF)
        g.line("key labels flag follows qol_keys", (kf == 1) == keys_on, f"KF = {kf}, qol_keys in the build: {keys_on}")
        ram_font = h.ram(FONT, 1536)
        ref_font = font_image()[FONT - wwpatch.GAME:FONT - wwpatch.GAME + 1536]
        nd = [i for i in range(1536) if ram_font[i] != ref_font[i]]
        g.line("font in RAM == the file-derived resident image", not nd, f"{len(nd)} bytes differ")
        pal = read_palette(h)
        g.line("palette: colour 0 black, text colours 2..5 differ from each other and from black", pal[0] == (0, 0, 0) and len({pal[c] for c in (0, 2, 3, 4, 5)}) == 5, f"{pal[:6]}")
        sw_ids = [i for i in IDS if i in LEVELED]
        shotn = 0

        def full(name, i, x, y, tag=None):
            nonlocal shotn
            shot = SHOTS / f"{a.tag}_{tag}.png" if (tag or a.shots) else h.R / "probe.png"
            if a.shots and not tag:
                shot = SHOTS / f"{a.tag}_{re.sub(r'[^A-Za-z0-9]+', '_', name)}.png"
            probe(h, live, g, name, x, y, pal, keys_on, shot=shot)

        # ---- every icon, the neutral posture (the default), then the leveled ones at 3 and 1 sword -------------------------------------
        word0 = h.peekw(POSTURE_WORD(h.peekw(SEL)))
        order = [2, 3, 4] if word0 == 3 else [3, 2, 4]
        if a.quick:
            order = [3] if word0 == 3 else [3]
        for word in order:
            if h.peekw(POSTURE_WORD(h.peekw(SEL))) != word:
                set_posture(h, g, word)
            lv = level_of_posture(word)
            ids = ([3, 6, 24, 28, 32] if a.quick else IDS) if word == 3 else sw_ids
            for i in ids:
                x, y = cen[i]
                full(f"id {i:2d} {TABLE[i][0]} level {lv + 1} sword{'s' if lv else ''}", i, x, y, tag=f"id{i}_lv{lv}" if i in (3, 6, 2, 28, 30, 14, 7, 32) else None)
        if h.peekw(POSTURE_WORD(h.peekw(SEL))) != 3:
            set_posture(h, g, 3)
        # ---- erase: move off an icon, the bar must be clean (both buffers) -----------------------------------------------------------
        full("erase after id 3 -> (150,100)", 0, 150, 100, tag="erase")
        # ---- text replaced by a shorter one leaves no residue (exact equality of the whole line) -------------------------------------------
        for i in (6, 5, 3, 1, 24):                      # long -> short sequence
            x, y = cen[i]
            full(f"sequence id {i} ({TABLE[i][0]})", i, x, y)
        # ---- the level follows the posture word while the pointer rests ----------------------------------------------------------------------
        x, y = cen[3]
        h.goto_st(x, y)
        time.sleep(3)
        for word in (4, 2, 3):
            sel = h.peekw(SEL)
            h.debug(f"w ${POSTURE_WORD(sel):x} $00 ${word:02x}", 0.5)
            t = time.time()
            exp_key = 3 * 4 + level_of_posture(word) + (0x100 if keys_on else 0)
            while time.time() - t < 20 and live.state()[3] != exp_key:
                time.sleep(0.5)
            g.line(f"live posture change to {word} while hovering Get Food", live.state()[3] == exp_key, f"KEY ${live.state()[3]:x} want ${exp_key:x}")
        # ---- an open window suppresses the map-icon tooltips ----------------------------------------------------------------------------------------
        h.click_st(*cen[23], wait=2.0)
        win = h.peekw(pmww.WINDOW_OPEN) != 0
        g.line("Option window opened", win, f"$74c0 = {h.peekw(pmww.WINDOW_OPEN):#x}")
        if win:
            probe(h, live, g, "map icon 1 with the Option window open (no tooltip)", 24, 2, pal, keys_on, window=True)
            h.click_st(57, 4, wait=2.0)
            g.line("Option window closed", h.peekw(pmww.WINDOW_OPEN) == 0, "tick at (57,4)")
        # ---- hit test coverage ---------------------------------------------------------------------------------------------------------------------------------
        for i in ([] if a.quick else IDS):
            for k, (x, y) in enumerate(extra[i]):
                quick(h, live, g, f"id {i} extra point {k}", x, y, keys_on)
        for k, (x, y) in enumerate([] if a.quick else NONE_POINTS):
            quick(h, live, g, f"none point {k}", x, y, keys_on)
        h.shot(str(SHOTS / f"{a.tag}_end.png"))
        print(f"TOOLTIP GATE {a.tag}: {g.n_pass} lines PASS, {g.n_fail} FAIL")
        print(f"CELL DONE {a.tag}: {'OK' if g.ok else 'FAIL'}", flush=True)
        return 0 if g.ok else 2
    except Exception:
        import traceback
        traceback.print_exc()
        print(f"CELL DONE {a.tag}: FAIL (exception)", flush=True)
        return 3
    finally:
        h.close()


MASTER_SHOTS = ROOT.parent.parent / "done" / "powermonger" / "work" / "shots"


def cmd_sheet(a) -> int:
    """Pairs of strips: master's tooltip bar (its own screenshot) above WW1's (this gate's screenshot of the same icon and posture)."""
    from PIL import Image, ImageDraw
    pairs = [("Get Food, 2 swords, key labels on", "qol_icon_getfood_keys.png", f"{a.tag}_id3_lv1.png"),
             ("Invent / Build, 3 swords, key labels on", "qol_icon_invent_3sword_keys.png", f"{a.tag}_id7_lv2.png"),
             ("Rotate left, key labels on", "qol_icon_rotate_left_keys.png", f"{a.tag}_id28_lv1.png"),
             ("Compass, key labels on", "qol_icon_compass.png", f"{a.tag}_id32_lv1.png")]
    W, H = 640 * 2, 22 * 2
    sheet = Image.new("RGB", (W, len(pairs) * (2 * (H + 14) + 10)), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    y = 4
    for cap, m, w in pairs:
        for who, path in (("master Powermonger", MASTER_SHOTS / m), ("WW1 port", SHOTS / w)):
            im = Image.open(path).convert("RGB").crop((96, 58, 96 + 640, 58 + 22))
            d.text((4, y), f"{cap}: {who}", fill=(255, 255, 255))
            sheet.paste(im.resize((W, H), Image.NEAREST), (0, y + 12))
            y += H + 14
        y += 10
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(f"SHEET {a.out} {sheet.size}")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    g = sub.add_parser("gate")
    g.add_argument("--disk", required=True)
    g.add_argument("--manifest")
    g.add_argument("--workdir")
    g.add_argument("--snapshot")
    g.add_argument("--machine", default="ste")
    g.add_argument("--tos", default="1.62")
    g.add_argument("--mem", type=int, default=1024)
    g.add_argument("--tag", default="tt")
    g.add_argument("--quick", action="store_true", help="a few icons at the neutral posture, the erase, live level and window checks (other machines)")
    g.add_argument("--shots", action="store_true", help="a screenshot per probe (the pixel comparison of the screenshot is always done)")
    sh = sub.add_parser("sheet")
    sh.add_argument("--out", required=True)
    sh.add_argument("--tag", default="tt")
    a = ap.parse_args()
    return {"check": cmd_check, "gate": run_gate, "sheet": cmd_sheet}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
