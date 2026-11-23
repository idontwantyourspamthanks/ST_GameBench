#!/usr/bin/env python3
"""NEBLEVEL.OVL (campaign file) tools.  Fixed file size OVSZ = 8192 (pre-created; the editor only rewrites it, never grows it).  Big endian:
  header 16 B: 'NCMP' | version.w = 1 | nlevels.w | ncamps.w | reserved
  8 campaign records x 32 B at offset 16: name[12] (NUL terminated, <= 11 chars) | count.b | pad.b | entry[16] | pad[2]
      entry byte: bit7 set = original tower  $80 | (mission-1)<<3 | tower(0..7);  bit7 clear = custom level index
  level records from offset 272, back to back (variable length), nlevels of them:
      mission.b (1|2) | tower.b (0..7: base tower = palette, backdrop, default time) | rows.b (= the game's $33912, rows decoded) | flags.b (high nibble = colour set 0..8, low nibble = enemy set 0..4; 0 = as the base tower)
      len.w | time.w (BCD, 0 = the base tower's) | name[12] (NUL terminated) | mask[rows*2] | stream[...]
  mask/stream = the game's own tower encoding (decoder $377a2/$37822): per row two mask bytes (bit n = angle n, 8+n), then the non-zero cells in
  (row, angle) order.  The game's decode loop is fed the record unchanged (hook ed_dec)."""
import struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "level/tools"))
OVSZ = 8192
LV0 = 272
NC = 8
REC = 20

def encode(grid, rows):
    """grid[angle][row] (16 x >= rows) -> mask + stream"""
    mask = bytearray(); stream = bytearray()
    for r in range(rows):
        for half in (0, 1):
            m = 0
            for bit in range(8):
                v = grid[half * 8 + bit][r]
                if v:
                    m |= 1 << bit; stream.append(v)
            mask.append(m)
    return bytes(mask + stream)

def level(mission, tower, rows, grid, time=0, name="LEVEL", colours=0, enemies=0):
    """colours (0..8) / enemies (0..4) -> flags.b: high nibble = colour set (0 = as the base tower, n = tower n's palette, raster, skyline, texture),
    low nibble = enemy set (0 = as the base tower, n = tower n's eye-disc design (n-1) & 3)."""
    assert 0 <= colours <= 8 and 0 <= enemies <= 4, (colours, enemies)
    body = encode(grid, rows)
    nm = name.encode("ascii")[:11].ljust(12, b"\0")
    return struct.pack(">BBBBHH", mission, tower, rows, colours << 4 | enemies, len(body), time) + nm + body

def camp(name, entries):
    assert len(entries) <= 16
    nm = name.encode("ascii")[:11].ljust(12, b"\0")
    return nm + bytes([len(entries), 0]) + bytes(entries).ljust(16, b"\0") + b"\0\0"

def orig(mission, tower):          # entry byte for an original tower (tower 0..7)
    return 0x80 | ((mission - 1) << 3) | tower

def build(levels=(), camps=()):
    assert len(camps) <= NC
    ctab = b"".join(camps).ljust(NC * 32, b"\0")
    out = b"NCMP" + struct.pack(">HHH", 1, len(levels), len(camps)) + bytes(6) + ctab + b"".join(levels)
    assert len(out) <= OVSZ, f"campaign file {len(out)} > {OVSZ}"
    return out.ljust(OVSZ, b"\0")

def parse(data):
    assert data[:4] == b"NCMP", "no magic"
    ver, nl, nc = struct.unpack(">HHH", data[4:10])
    camps = []
    for i in range(nc):
        c = data[16 + 32 * i:48 + 32 * i]
        camps.append((c[:12].split(b"\0")[0].decode(), list(c[14:14 + c[12]])))
    p = LV0; levels = []
    for _ in range(nl):
        m, t, rows, fl, ln, tm = struct.unpack(">BBBBHH", data[p:p + 8]); name = data[p + 8:p + 20].split(b"\0")[0].decode()
        body = data[p + 20:p + 20 + ln]
        grid = [[0] * rows for _ in range(16)]; ms = 0; ss = 2 * rows
        for r in range(rows):
            for half in (0, 1):
                mb = body[ms]; ms += 1
                for bit in range(8):
                    if mb >> bit & 1:
                        grid[half * 8 + bit][r] = body[ss]; ss += 1
        assert ss == ln, (ss, ln)
        levels.append(dict(mission=m, tower=t, rows=rows, flags=fl, time=tm, name=name, grid=grid, size=20 + ln)); p += 20 + ln
    return levels, camps

def original(mission, tower):
    import nebedit
    N = nebedit.Nebulus(str(Path(__file__).resolve().parents[2] / "originals/NEBULGX/NEBEXE.FIC"))
    g, _, _ = N.grid(mission, tower)
    return g, N.tower_hdr(mission, tower)[2] - 1      # grid, rows decoded by the game ($33912 = hdr byte)

def validate(data):
    """List of problems (empty = the in-game loader accepts the file).  Same rules as `ov_check` in patches/ed_editor.s; never raises."""
    pr = []
    if len(data) != OVSZ:
        pr.append(f"size {len(data)} != {OVSZ}")
    data = bytes(data[:OVSZ]).ljust(OVSZ, b"\0")
    if data[:4] != b"NCMP":
        return pr + ["bad magic (the game treats the file as absent)"]
    ver, nl, nc = struct.unpack(">HHH", data[4:10])
    if ver != 1: return pr + [f"unknown version {ver}"]
    if nl > 127: return pr + [f"nlevels {nl} > 127"]
    if nc > NC: return pr + [f"ncamps {nc} > {NC}"]
    for i in range(nc):
        if data[16 + 32 * i + 12] > 16: pr.append(f"campaign {i}: count {data[16 + 32 * i + 12]} > 16")
    p = LV0
    for i in range(nl):
        if p + REC > OVSZ: return pr + [f"level {i}: header beyond the file"]
        m, t, rows, fl, ln, tm = struct.unpack(">BBBBHH", data[p:p + 8])
        if m not in (1, 2): pr.append(f"level {i}: mission {m}")
        if t > 7: pr.append(f"level {i}: base tower {t}")
        if not 16 <= rows <= 120: pr.append(f"level {i}: rows {rows}")
        if ln < 2 * rows or p + REC + ln > OVSZ: return pr + [f"level {i}: length {ln} invalid"]
        pop = sum(bin(b).count("1") for b in data[p + REC:p + REC + 2 * rows])
        if pop != ln - 2 * rows: pr.append(f"level {i}: stream {ln - 2 * rows} != mask popcount {pop}")
        p += REC + ln
    return pr

def bad_looks(data):
    """Levels whose flags.b is outside the defined nibbles (colours > 8 or enemies > 4).  The game accepts any value (it masks the indices); the site parser rejects them."""
    out = []; p = LV0
    for i in range(struct.unpack(">H", data[6:8])[0]):
        fl = data[p + 3]
        if fl >> 4 > 8 or fl & 15 > 4: out.append(i)
        p += REC + struct.unpack(">H", data[p + 4:p + 6])[0]
    return out

def odd_starts(data):
    """Level indices whose record starts at an odd file offset (= an odd RAM address in the game: the store is at an even address).  Legal and common
    (records are packed back to back, any level with an odd number of non-zero cells makes the next record start odd); loaders must read len/time/mask
    bytewise.  The released v1.1 game (before NebOddFix) crashes on such a file at F10 (68000 address error); later builds accept it.  Informational."""
    out = []; p = LV0
    for i in range(struct.unpack(">H", data[6:8])[0]):
        if p & 1: out.append(i)
        p += REC + struct.unpack(">H", data[p + 4:p + 6])[0]
    return out

_TILES = None
def tiles():
    """the in-game editor's 21 tile patterns (8 bytes + colour) read from patches/ed_editor.s"""
    global _TILES
    if _TILES is None:
        import re
        src = (Path(__file__).resolve().parents[2] / "patches/ed_editor.s").read_text()
        body = src[src.index("\ntiles:"):src.index("\nsHelp:")]
        _TILES = [([int(x[1:], 16) for x in m.group(1).split(",")[:8]], int(m.group(1).split(",")[8]))
                  for m in re.finditer(r"dc\.b\s+(\$[0-9a-f]{2}(?:,\$[0-9a-f]{2}){7},\d+)", body)]
        assert len(_TILES) == 21       # 17 shapes + lift end / lift stop (ids 17, 18) + conveyor left / right (19, 20); tile 3 = crumble ledge ($91)
    return _TILES

def classify(v):
    if v == 0: return 0
    if not v & 0x80:
        k = (v >> 4) & 7
        if k == 0 and v & 0x0c in (8, 12):
            return 17 if v & 0x0c == 8 else 18
        return 1 if k == 0 else 8 + k
    c = v & 3
    if c == 3: return 8 if v & 0x40 else 7
    if c == 0: return 4
    if c == 2: return 5
    if v & 0x0c: return 6
    return {0x10: 3, 0x20: 19, 0x30: 20}.get(v & 0x70, 2)   # $91 crumbling ledge, $a1 / $b1 conveyor left / right (ledge + arrow in the editor); the game draws all of them exactly like a ledge

# ---- lifts (work/notes/lifts.md).  A lift lives in ONE grid column: start slab $85 (lower row) .. end marker $08 (higher row), optional stop markers $0c in
# between.  Nothing else is stored; the game's own ride code ($3a3e6) and return queue ($339ee) do the rest.
LIFT_START, LIFT_END, LIFT_STOP = 0x85, 0x08, 0x0c

def lift_report(grid, rows):
    """-> (lifts, orphans).  lifts = [{col, bottom, top, top_kind, stops, warn, note}] (top None = no end marker above the start);
    orphans = [(col, row, value)] end/stop markers that no start slab reaches."""
    out, used = [], set()
    for c in range(16):
        cl = grid[c]
        for r in range(rows):
            if cl[r] != LIFT_START:
                continue
            top, kind, stops, warn, note = None, None, [], [], []
            for r2 in range(r + 1, rows):
                v = cl[r2]
                if v == LIFT_END:
                    top, kind = r2, "08"; break
                if v == LIFT_STOP:
                    stops.append(r2); continue
                if v == LIFT_START:
                    warn.append(f"row {r2}: another lift start inside the shaft"); break
            if top is None and stops:
                top, kind = stops.pop(), "0c"      # only stop markers: the last one ends the ride unless Up is held
                note.append("end is a $0c stop (the ride only goes on past it while Up is held)")
            if top is None:
                warn.append("no end marker ($08) above the start: the ride only ends by hitting terrain and then hurts the frog")
            for r2 in range(r + 1, top if top is not None else rows):
                v = cl[r2]
                if v == 0 or v == LIFT_STOP:
                    continue
                if v & 0x80 and (v & 3) == 2:
                    note.append(f"row {r2}: blue block ${v:02x} blocks the ride until the frog shoots it")
                elif v & 0x80 and (v & 3) == 0:
                    warn.append(f"row {r2}: ${v:02x} blocks the ride (the frog is hurt, the platform goes back)")
                elif v & 0x0c:
                    warn.append(f"row {r2}: ${v:02x} has bits 2-3 set: the ride takes it for a lift marker")
                else:
                    note.append(f"row {r2}: ${v:02x} is erased by the first ride")
            if r == 0 or not cl[r - 1] & 0x80:
                warn.append("no ledge cell under the start slab (the editor puts $81 there)")
            if not (grid[(c - 1) % 16][r - 1] & 0x80 or grid[(c + 1) % 16][r - 1] & 0x80 or grid[(c - 1) % 16][r] & 0x80 or grid[(c + 1) % 16][r] & 0x80):
                note.append("no terrain beside the start: the frog cannot walk onto the slab")
            if top is not None and not (grid[(c - 1) % 16][top] & 0x80 or grid[(c + 1) % 16][top] & 0x80):
                note.append("no ledge beside the end: nothing to step onto")
            out.append(dict(col=c, bottom=r, top=top, top_kind=kind, stops=stops, warn=warn, note=note))
            used.add((c, r))
            if top is not None:
                used.add((c, top))
            used.update((c, s) for s in stops)
    orphans = [(c, r, grid[c][r]) for c in range(16) for r in range(rows) if grid[c][r] in (LIFT_END, LIFT_STOP) and (c, r) not in used]
    return out, orphans

def add_lift(grid, col, r0, r1, stops=(), floor=True):
    """what the in-game 'Lift' command does: slab $85 at the lower row, end marker $08 at the higher one, $0c at each stop; floor = ledge $81 under an empty start"""
    lo, hi = sorted((r0, r1))
    assert hi > lo and all(lo < s < hi for s in stops)
    if floor and lo > 0 and grid[col][lo - 1] == 0:
        grid[col][lo - 1] = 0x81
    grid[col][lo], grid[col][hi] = LIFT_START, LIFT_END
    for s in stops:
        grid[col][s] = LIFT_STOP

def print_lifts(grid, rows, indent="  "):
    lf, orph = lift_report(grid, rows)
    print(f"{indent}lifts {len(lf)}")
    for L in lf:
        print(f"{indent}lift col {L['col']} rows {L['bottom']}..{L['top']} stops {L['stops']}" + "".join(f"\n{indent}  WARN {w}" for w in L["warn"]) + "".join(f"\n{indent}  note {w}" for w in L["note"]))
    for c, r, v in orph:
        print(f"{indent}WARN orphan marker ${v:02x} at col {c} row {r} (no lift start $85 below it in the column)")

PAL = [(0, 0, 0), (0x33 * 5 // 3 * 0 + 68, 68, 68), (0, 170, 0), (85, 170, 34), (102, 102, 102), (51, 85, 255), (255, 238, 170), (255, 68, 0)]
def render(grid, rows, out, scale=3):
    """PNG of the 16 x rows grid like the in-game editor: 16x8 px cells, row 0 at the bottom, frog start marked at column 0, row 2"""
    from PIL import Image
    T = tiles(); W_, H_ = 16 * 16, rows * 8
    im = Image.new("RGB", (W_, H_))
    for r in range(rows):
        for c in range(16):
            v = grid[c][r]; tid = classify(v)
            if v == 0 and r == 2 and c == 0: tid = 16
            pat, col = T[tid]; pat = list(pat)
            if 9 <= tid <= 15:
                k = tid - 8; neg = v & 1; vert = k in (4, 5)
                ex = [sum(((b >> (7 - i)) & 1) * (3 << (14 - 2 * i)) for i in range(8)) for b in pat]
                if vert: ex[7 if neg else 0] |= 0x0ff0
                else:
                    for rr in (3, 4): ex[rr] |= 0xc000 if neg else 0x0003
            else:
                ex = [sum(((b >> (7 - i)) & 1) * (3 << (14 - 2 * i)) for i in range(8)) for b in pat]
            rgb = PAL[col]
            for y in range(8):
                for x in range(16):
                    if ex[y] >> (15 - x) & 1:
                        im.putpixel((c * 16 + x, (rows - 1 - r) * 8 + y), rgb)
                    elif tid == 0 and x == 0: pass
    from PIL import ImageDraw
    d = ImageDraw.Draw(im)                  # lifts: a line from the start slab to the end marker, arrow head at the end, ring per stop; magenta = has warnings
    for L in lift_report(grid, rows)[0]:
        x = L["col"] * 16 + 8; y0 = (rows - 1 - L["bottom"]) * 8 + 4
        top = L["top"] if L["top"] is not None else min(rows - 1, L["bottom"] + 3)
        y1 = (rows - 1 - top) * 8 + 4; rgb = (255, 0, 255) if L["warn"] else (255, 255, 0)
        d.line([(x, y0), (x, y1)], fill=rgb)
        d.polygon([(x, y1 - 3), (x - 3, y1 + 1), (x + 3, y1 + 1)], fill=rgb)
        for s in L["stops"]:
            ys = (rows - 1 - s) * 8 + 4; d.ellipse([x - 3, ys - 3, x + 3, ys + 3], outline=rgb)
    im.resize((W_ * scale, H_ * scale), Image.NEAREST).save(out)

def import_original(mission, tower, name=None):
    """level record of a shipped tower (base tower = itself): a starting point for a new level"""
    g, rows = original(mission, tower)
    return level(mission, tower, rows, g, name=name or f"ORIG M{mission} T{tower + 1}")

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "test3":      # stage (b): campaign 'TEST REMIX' = original M1 T1, custom 0, original M1 T3; level 0 = tower 1 grid + 4 cells changed, base tower 4
        g, rows = original(1, 0)
        for (a, h, v) in [(3, 1, 0), (4, 1, 0), (3, 2, 0x85), (4, 2, 0x85)]:
            g[a][h] = v
        lv = level(1, 3, rows, g, time=0x0300, name="MY LEVEL")
        Path(sys.argv[2]).write_bytes(build([lv], [camp("TEST REMIX", [orig(1, 0), 0, orig(1, 2)])]))
    elif cmd == "empty":
        Path(sys.argv[2]).write_bytes(bytes(OVSZ))
    elif cmd == "dump":
        lv, cs = parse(Path(sys.argv[2]).read_bytes())
        off = [LV0 + sum(x["size"] for x in lv[:i]) for i in range(len(lv))]
        for i, l in enumerate(lv):
            print(f"level {i} {l['name']!r} @{off[i]}{' (odd offset)' if off[i] & 1 else ''} mission {l['mission']} base tower {l['tower']} rows {l['rows']} colours {l['flags'] >> 4} enemies {l['flags'] & 15} time {l['time']:04x} size {l['size']} cells {sum(1 for c in l['grid'] for v in c if v)}")
            print_lifts(l["grid"], l["rows"])
        for i, (n, e) in enumerate(cs):
            print(f"campaign {i} {n!r}: " + ", ".join(f"orig M{((x>>3)&1)+1} T{(x&7)+1}" if x & 0x80 else f"custom {x}" for x in e))
    elif cmd == "validate":
        raw = Path(sys.argv[2]).read_bytes(); pr = validate(raw); print("OK" if not pr else "\n".join(pr))
        if not pr and odd_starts(raw): print(f"note: levels {odd_starts(raw)} start at an odd offset (valid; the v1.1 game before the odd-alignment fix crashes on such a file)", file=sys.stderr)
        sys.exit(1 if pr else 0)
    elif cmd == "render":              # render FILE LEVEL out.png
        lv, cs = parse(Path(sys.argv[2]).read_bytes()); l = lv[int(sys.argv[3])]; render(l["grid"], l["rows"], sys.argv[4])
    elif cmd == "import-original":     # import-original MISSION TOWER out.ovl   (a file with that one level + a campaign playing it)
        lv = import_original(int(sys.argv[2]), int(sys.argv[3]) - 1)
        Path(sys.argv[4]).write_bytes(build([lv], [camp(f"ORIG M{sys.argv[2]}T{sys.argv[3]}", [0])]))
    elif cmd == "lifts":               # lifts FILE LEVEL
        lv, cs = parse(Path(sys.argv[2]).read_bytes()); l = lv[int(sys.argv[3])]; print_lifts(l["grid"], l["rows"], "")
    elif cmd == "lifts-orig":          # lifts-orig MISSION TOWER(1..8): the shipped towers
        g, rows = original(int(sys.argv[2]), int(sys.argv[3]) - 1); print_lifts(g, rows, "")
