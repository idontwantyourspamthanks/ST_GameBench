#!/usr/bin/env python3
"""Moonshine Racers track tool: decode / encode / validate / render the game's track data, build campaign files and campaign disks.

Format spec: work/notes/trackformat.md.  Source of truth for the stock tracks: `FILES\\MS2` of the PP/HAGA conversion
(originals/MOONSHR/FILES/MS2; flat sector space, byte offset = sector * 512).  Pure Python 3 + PIL (render only).

  decode    [SRC|--all] [-o OUT]       stock level(s) (MS2) -> JSON, lossless
  encode    TRACK.json -o OUT.bin      JSON -> track block bytes in the game's native form (alias: build)
  validate  FILE...                    .json | .bin (--base N) | .trk campaign; exit 1 when any ERROR
  render    SRC -o OUT.png             top-down path, curve, elevation, widths, object strip (no minimap)
  campaign  new|add|remove|list|extract     build / read MSTRACKS.TRK
  disk      CAMP.trk -o OUT.st|.msa    720 KB FAT12 floppy image holding MSTRACKS.TRK in the root
  patch-ms2 CAMP.trk -o MS2.new        copy of MS2 whose track blocks are replaced (test aid: plays at 1 MB, no game patch)
  selftest                             the round-trip / format self checks (all 15 stock levels)

SRC = level number 0..14 (stock, read from MS2), a track .json, or FILE.trk with --entry N.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
DEFAULT_MS2 = GAME / "originals/MOONSHR/FILES/MS2"

FORMAT = "msr-track/1"
NLEV = 15

# ---------------------------------------------------------------- stock facts (verified against the game's MS2, `selftest`)
# per level: (track block sector, track sectors, minimap-header sector, race length, #object types, CRC32 of the 12-byte type table)
# race length = word 0 of the minimap header block ($57890 in RAM); not editable.  The type table CRC makes `validate` work
# without the game files: a custom track must carry its base level's type table unchanged.
LEVELS = [
    (163, 12, 155, 19472, 131, 0x76298587),
    (266, 9, 256, 19720, 77, 0x316F7D01),
    (365, 10, 357, 19800, 93, 0x0CD7D792),
    (459, 9, 451, 19000, 63, 0xA68B3A6A),
    (549, 9, 541, 19375, 37, 0xA621BBFF),
    (647, 8, 639, 18000, 31, 0xD77FE9B0),
    (743, 8, 736, 18626, 30, 0xD46BF523),
    (841, 8, 833, 20000, 34, 0x44241305),
    (943, 7, 935, 19000, 28, 0xEC3310DE),
    (1037, 8, 1030, 20000, 32, 0x35317057),
    (1122, 8, 1115, 20000, 42, 0xAAE7B4B2),
    (1215, 9, 1206, 22000, 40, 0x26CE6900),
    (1305, 8, 1298, 18500, 53, 0xAC1297D1),
    (1385, 9, 1377, 22000, 36, 0xFDCEAC9E),
    (1465, 10, 1454, 23000, 32, 0x9ED8F971),
]
LEV_SECTOR, LEV_NSECT, LEV_MM, LEV_LEN, LEV_NTYPES, LEV_TCRC = range(6)

RING = 32768            # every stock ring stream sums to exactly this
LOOKAHEAD = 1024        # ring length: the game keeps the next 1024 units filled
BLOCK_MAX = 8192        # campaign working-copy size per block (spec section 4)
MAX_ENTRIES = 15
NAME_LEN = 24
# stock-proven envelope (all 15 levels, work/notes/trackeditor.md 2.2)
CURVE_DELTA = (-9, 10)
WIDTH = (10, 85)
HILL_ACCEL = (-6000, 4000)
LATERAL = (-128, 127)
GAP_MAX = 32767
OBJ_POOL = 32           # scenery slots: stock density never exceeds 31 objects per 888 units
VIEW = 888              # furthest distance the camera sees

STREAMS = ("curve", "left", "right", "hill")
STREAM_LIMITS = {"curve": CURVE_DELTA, "left": WIDTH, "right": WIDTH, "hill": HILL_ACCEL}
STREAM_VALNAME = {"curve": "delta", "left": "half-width target", "right": "half-width target", "hill": "accel"}


class TrackError(Exception):
    """structural error: the bytes / JSON cannot be interpreted at all"""


# ---------------------------------------------------------------- block <-> track dict
def _w(b: bytes, o: int, what: str, signed=False) -> int:
    if o + 2 > len(b):
        raise TrackError(f"E-TERM: block ends inside {what} (offset {o}, block {len(b)} bytes): missing terminator")
    return struct.unpack_from(">h" if signed else ">H", b, o)[0]


def parse_block(b: bytes, base: int | None = None) -> tuple[dict, int]:
    """Parse the six streams. Returns (track dict, canonical length consumed).  Never guesses: truncated -> TrackError."""
    o = 0
    t: dict = {"format": FORMAT}
    for name in STREAMS:
        lst = []
        while True:
            cnt = _w(b, o, f"{name} stream")
            o += 2
            if cnt == 0:
                break
            lst.append([cnt, _w(b, o, f"{name} stream", True)])
            o += 2
        t[name] = lst
    first = _w(b, o, "object list")
    o += 2
    objs = []
    pos = first
    while True:
        ty = _w(b, o, "object list")
        lat = _w(b, o + 2, "object list", True)
        gap = _w(b, o + 4, "object list")
        o += 6
        objs.append({"at": pos, "type": ty, "lateral": lat})
        if gap == 0:
            break
        pos += gap
    t["objects"] = objs
    types = []
    while o + 12 <= len(b) and b[o:o + 2] == b"\xff\x00":
        k, sz, sp, w4, w5 = struct.unpack_from(">HHhHH", b, o + 2)
        types.append([k, sz, sp, w4, w5])
        o += 12
    t["types"] = types
    if _w(b, o, "type table") != 0:
        raise TrackError(f"E-TERM: type table at offset {o - 12 * len(types)} is not closed by a zero word (found {b[o:o+2].hex()})")
    o += 2
    return t, o


def encode_track(t: dict) -> bytes:
    """Track dict -> block bytes (S0..S4, type table, zero word).  Raises TrackError on anything that does not fit a word."""
    out = bytearray()

    def pack(fmt, *v, what=""):
        try:
            out.extend(struct.pack(fmt, *v))
        except struct.error as e:
            raise TrackError(f"E-FORM: {what}: value does not fit a 16-bit word {v}") from e
    for name in STREAMS:
        for i, p in enumerate(t[name]):
            if not (isinstance(p, (list, tuple)) and len(p) == 2):
                raise TrackError(f"E-FORM: {name}[{i}] must be [count, value]")
            if p[0] == 0:
                raise TrackError(f"E-STREAM: {name}[{i}] has count 0 (count 0 is the terminator word)")
            pack(">Hh", p[0], p[1], what=f"{name}[{i}]")
        out += b"\0\0"
    objs = t["objects"]
    if not objs:
        raise TrackError("E-OBJ: at least one object is required (the list has no empty form)")
    pack(">H", objs[0]["at"], what="objects[0].at")
    for i, ob in enumerate(objs):
        gap = 0 if i == len(objs) - 1 else objs[i + 1]["at"] - ob["at"]
        if gap < 0:
            raise TrackError(f"E-OBJ: objects[{i + 1}].at={objs[i + 1]['at']} is before objects[{i}].at={ob['at']} (objects must be in increasing order)")
        pack(">HhH", ob["type"], ob["lateral"], gap, what=f"objects[{i}]")
    for i, e in enumerate(t["types"]):
        if len(e) != 5:
            raise TrackError(f"E-FORM: types[{i}] must have 5 fields [kind, size, sprite, w4, w5]")
        pack(">HHHhHH", 0xFF00, e[0], e[1], e[2], e[3], e[4], what=f"types[{i}]")
    out += b"\0\0"
    return bytes(out)


# ---------------------------------------------------------------- stock access (MS2)
def read_ms2(path=None) -> bytes:
    p = Path(path) if path else DEFAULT_MS2
    if not p.exists():
        raise SystemExit(f"MS2 not found: {p}  (use --ms2 FILES/MS2 of the game folder)")
    return p.read_bytes()


def stock_block(ms2: bytes, lev: int) -> bytes:
    s, n = LEVELS[lev][LEV_SECTOR], LEVELS[lev][LEV_NSECT]
    return ms2[s * 512:(s + n) * 512]


def stock_race_length(ms2: bytes, lev: int) -> int:
    return struct.unpack_from(">H", ms2, LEVELS[lev][LEV_MM] * 512)[0]


def decode_stock(ms2: bytes, lev: int) -> tuple[dict, bytes]:
    """-> (track dict, canonical block bytes)."""
    b = stock_block(ms2, lev)
    t, n = parse_block(b)
    t2 = {"format": FORMAT, "name": f"STOCK {lev:02d}", "base_level": lev, "race_length": LEVELS[lev][LEV_LEN]}
    t2.update({k: t[k] for k in STREAMS + ("objects", "types")})
    return t2, b[:n]


# ---------------------------------------------------------------- JSON
def dumps_json(t: dict) -> str:
    """Hand-editable layout: scalar keys on a line each, one segment / object per line."""
    def inl(x):
        return json.dumps(x, separators=(", ", ": "))
    keys = [k for k in ("format", "name", "base_level", "race_length") if k in t]
    lines = ["{"]
    body = [f'  {json.dumps(k)}: {inl(t[k])}' for k in keys]
    for k in STREAMS:
        body.append(f'  {json.dumps(k)}: [\n' + ",\n".join("    " + inl(p) for p in t[k]) + "\n  ]")
    body.append('  "objects": [\n' + ",\n".join("    " + inl(o) for o in t["objects"]) + "\n  ]")
    body.append('  "types": [\n' + ",\n".join("    " + inl(e) for e in t["types"]) + "\n  ]")
    lines.append(",\n".join(body))
    lines.append("}")
    return "\n".join(lines) + "\n"


KNOWN_KEYS = {"format", "name", "base_level", "race_length", "objects", "types", *STREAMS}


def load_json(path) -> dict:
    try:
        t = json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise TrackError(f"E-FORM: {path}: cannot read JSON: {e}")
    return t


# ---------------------------------------------------------------- ring simulation (the game's own arithmetic)
def expand_curve(stream, n):
    out, v = [], 0
    for cnt, d in stream:
        for _ in range(cnt):
            v = (v + d) & 0xFFFF
            if v >= 0x8000:
                v -= 0x10000                       # word arithmetic (`add.w d4,d3`), harmless wrap
            out.append(v)
            if len(out) >= n:
                return out
    return out


def expand_width(stream, n):
    """$fe1c/$fe50: first target is the start value; the byte slews 1 unit/step toward the current target."""
    if not stream:
        return []
    out, v = [], stream[0][1]
    for cnt, tgt in stream:
        for _ in range(cnt):
            out.append(v & 0xFF)
            v += (v < tgt) - (v > tgt)
            if len(out) >= n:
                return out
    return out


def expand_hill(stream, n):
    """$ffe4/$1003c: d3 += d2; d2 += accel (32-bit); byte = clamp(d3>>16, 0..127).  Returns (bytes, overflow_unit | None)."""
    out, d2, d3, ovf = [], 0, 0, None
    for cnt, a in stream:
        for _ in range(cnt):
            d3 += d2
            d2 += a
            if ovf is None and (not -0x80000000 <= d3 <= 0x7FFFFFFF or not -0x80000000 <= d2 <= 0x7FFFFFFF):
                ovf = len(out)
            out.append(0 if d3 < 0 else min(d3 >> 16, 127))
            if len(out) >= n:
                return out, ovf
    return out, ovf


# ---------------------------------------------------------------- validation
class Issue:
    def __init__(self, level, code, msg):
        self.level, self.code, self.msg = level, code, msg

    def __str__(self):
        return f"{self.level} {self.code}: {self.msg}"


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate_track(t: dict, lenient=False, budget: int | None = None, block: bytes | None = None) -> list[Issue]:
    """All semantic rules (spec section 5).  `lenient` demotes the stock-envelope range rules to warnings."""
    I: list[Issue] = []
    E = lambda code, msg: I.append(Issue("ERROR", code, msg))
    W = lambda code, msg: I.append(Issue("WARN", code, msg))
    R = (lambda code, msg: W(code, msg + " [outside the stock-tested range, lenient]")) if lenient else E

    if not isinstance(t, dict):
        E("E-FORM", "track must be a JSON object")
        return I
    for k in t:
        if k not in KNOWN_KEYS:
            E("E-FORM", f"unknown key '{k}' (allowed: {', '.join(sorted(KNOWN_KEYS))})")
    if t.get("format", FORMAT) != FORMAT:
        E("E-FORM", f"format is '{t.get('format')}', this tool reads '{FORMAT}'")
    base = t.get("base_level")
    if not _int(base) or not 0 <= base < NLEV:
        E("E-BASE", f"base_level must be an integer 0..{NLEV - 1}, got {base!r}")
        base = None
    name = t.get("name", "")
    if not isinstance(name, str) or not name or len(name) > NAME_LEN or any(not 0x20 <= ord(c) < 0x7F for c in name):
        E("E-NAME", f"name must be 1..{NAME_LEN} printable ASCII characters, got {name!r}")
    for k in STREAMS + ("objects", "types"):
        if not isinstance(t.get(k), list):
            E("E-FORM", f"'{k}' is missing or not a list")
    if any(i.level == "ERROR" and i.code in ("E-FORM",) for i in I):
        return I
    rl = LEVELS[base][LEV_LEN] if base is not None else None
    if "race_length" in t and base is not None and t["race_length"] != rl:
        E("E-RACELEN", f"race_length {t['race_length']} differs from base level {base} ({rl}); the race length belongs to the base level and is not editable")

    # --- the four ring streams
    sums = {}
    for name_ in STREAMS:
        lo, hi = STREAM_LIMITS[name_]
        tot = 0
        ok = True
        for i, p in enumerate(t[name_]):
            if not (isinstance(p, list) and len(p) == 2 and _int(p[0]) and _int(p[1])):
                E("E-FORM", f"{name_}[{i}] must be [count, {STREAM_VALNAME[name_]}] with integers, got {p!r}")
                ok = False
                continue
            c, v = p
            if not 1 <= c <= 0xFFFF:
                E("E-STREAM", f"{name_}[{i}]: count {c} out of 1..65535 (count 0 is the stream terminator)")
            if not -0x8000 <= v <= 0x7FFF:
                E("E-FORM", f"{name_}[{i}]: {STREAM_VALNAME[name_]} {v} does not fit a signed word")
            elif not lo <= v <= hi:
                R("E-RANGE", f"{name_}[{i}] (starts at unit {tot}): {STREAM_VALNAME[name_]} {v} outside {lo}..{hi}")
            tot += c
        sums[name_] = tot
        if not t[name_]:
            E("E-STREAM", f"{name_} stream is empty")
        elif ok and rl is not None and tot < rl + LOOKAHEAD:
            E("E-SUM", f"{name_} stream covers {tot} units, needs at least {rl + LOOKAHEAD} "
                       f"(race length {rl} of base level {base} + {LOOKAHEAD} look-ahead); stock tracks cover {RING}")
    if len(set(sums.values())) > 1 and not any(i.code == "E-SUM" for i in I):
        W("W-SUM", "ring streams cover different lengths: " + ", ".join(f"{k} {v}" for k, v in sums.items()) + f" (stock: all {RING})")
    if rl is not None and t["curve"] and all(isinstance(p, list) and len(p) == 2 and _int(p[0]) and _int(p[1]) and p[0] > 0 for p in t["curve"]):
        cv = expand_curve(t["curve"], max(sums["curve"], 1))
        if cv and (min(cv) < -4473 or max(cv) > 8876):
            W("W-CURVE", f"curve value c reaches {min(cv)}..{max(cv)}, stock tracks stay within -4473..8876 (heading drift is untested beyond that)")

    # --- hill integrator
    if rl is not None and all(_int(p[0]) and _int(p[1]) for p in t["hill"] if isinstance(p, list) and len(p) == 2) and t["hill"]:
        try:
            h, ovf = expand_hill(t["hill"], max(sums["hill"], 1))
        except Exception:
            h, ovf = [], None
        if ovf is not None:
            E("E-HILL", f"hill integrator (32-bit slope/height) overflows at unit {ovf}: the height byte would wrap to garbage; add opposing accel segments")
        sat = sum(1 for x in h[:rl] if x >= 127)
        if sat > 300:
            W("W-HILL", f"height is clamped at 127 for {sat} of the {rl} race units: the hill accel stays integrated while clamped, so the slope can be far steeper than it looks")

    # --- objects
    objs = t["objects"]
    ntypes = LEVELS[base][LEV_NTYPES] if base is not None else None
    if not objs:
        E("E-OBJ", "at least one object is required")
    prev = None
    used_over = 0
    for i, ob in enumerate(objs):
        if not (isinstance(ob, dict) and set(ob) == {"at", "type", "lateral"} and all(_int(ob[k]) for k in ob)):
            E("E-FORM", f"objects[{i}] must be {{\"at\": int, \"type\": int, \"lateral\": int}}, got {ob!r}")
            prev = None
            continue
        at, ty, la = ob["at"], ob["type"], ob["lateral"]
        if i == 0:
            if not 1 <= at <= GAP_MAX:
                E("E-OBJ", f"objects[0].at = {at}: the first object must be at 1..{GAP_MAX} (the first gap is a word, 0 would end the list)")
        elif prev is not None:
            g = at - prev
            if g < 1:
                E("E-GAP", f"objects[{i}].at = {at} is not after objects[{i - 1}].at = {prev}: gaps must be 1..{GAP_MAX} (gap 0 would end the object list)")
            elif g > GAP_MAX:
                E("E-GAP", f"objects[{i}]: gap {g} to the previous object exceeds {GAP_MAX}")
        if ntypes is not None and not 1 <= ty <= ntypes:
            E("E-TYPE", f"objects[{i}] (at {at}): type {ty} is not in the type list of base level {base} (valid 1..{ntypes})")
        if not LATERAL[0] <= la <= LATERAL[1]:
            R("E-LAT", f"objects[{i}] (at {at}): lateral {la} outside {LATERAL[0]}..{LATERAL[1]}")
        prev = at
    # pool density
    if objs and all(isinstance(o, dict) and _int(o.get("at")) for o in objs):
        pos = [o["at"] for o in objs]
        j, worst, wat = 0, 0, 0
        for i in range(len(pos)):
            while pos[i] - pos[j] >= VIEW:
                j += 1
            if i - j + 1 > worst:
                worst, wat = i - j + 1, pos[j]
        if worst > OBJ_POOL - 1:
            W("W-DENS", f"{worst} objects within {VIEW} units at unit {wat}: only {OBJ_POOL} scenery slots exist, extra objects are skipped (stock max 31)")
        if rl is not None and pos[-1] > RING - 1 and pos[-1] > min(sums.values(), default=0):
            W("W-OBJEND", f"last object at {pos[-1]} is beyond the ring streams")

    # --- type table
    ty_ = t["types"]
    if base is not None:
        bad = False
        if len(ty_) != ntypes:
            E("E-TABLE", f"type table has {len(ty_)} entries, base level {base} has {ntypes}: custom tracks use their base level's object types unchanged")
            bad = True
        else:
            try:
                crc = zlib.crc32(b"".join(struct.pack(">HHHhHH", 0xFF00, *e) for e in ty_))
            except (struct.error, TypeError):
                E("E-FORM", "types entries must be [kind, size, sprite, w4, w5] integers")
                bad = True
            else:
                if crc != LEVELS[base][LEV_TCRC]:
                    E("E-TABLE", f"type table differs from base level {base} (CRC32 {crc:08x}, expected {LEVELS[base][LEV_TCRC]:08x}): it must be copied unchanged from the base level")

    # --- size
    if not any(i.level == "ERROR" for i in I):
        try:
            blk = encode_track(t) if block is None else block
        except TrackError as e:
            E("E-FORM", str(e))
        else:
            if len(blk) > BLOCK_MAX:
                E("E-SIZE", f"track block is {len(blk)} bytes, the campaign limit is {BLOCK_MAX}")
            if budget is not None and len(blk) > budget:
                E("E-SIZE", f"track block is {len(blk)} bytes, the sector budget of base level {base}'s slot in MS2 is {budget}")
    return I


def report(issues, label) -> bool:
    err = [i for i in issues if i.level == "ERROR"]
    for i in issues:
        print(f"{label}: {i}")
    print(f"{label}: {'FAIL' if err else 'OK'} ({len(err)} errors, {len(issues) - len(err)} warnings)")
    return not err


# ---------------------------------------------------------------- campaign file
MAGIC = b"MSTK"
VERSION = 1
HDR = 16
ENT = 40


def build_campaign(entries: list[tuple[str, int, bytes]]) -> bytes:
    """entries = (name, base_level, block bytes) in campaign order."""
    if not 1 <= len(entries) <= MAX_ENTRIES:
        raise TrackError(f"E-CAMP: a campaign holds 1..{MAX_ENTRIES} tracks, got {len(entries)}")
    off = HDR + ENT * len(entries)
    tab = bytearray()
    body = bytearray()
    for name, base, blk in entries:
        if len(blk) % 2 or not len(blk) or len(blk) > BLOCK_MAX:
            raise TrackError(f"E-SIZE: block of '{name}' is {len(blk)} bytes (must be even, 2..{BLOCK_MAX})")
        tab += struct.pack(">24sHHLLL", name.encode("ascii").ljust(NAME_LEN, b"\0"), base, 0, off + len(body), len(blk), zlib.crc32(blk))
        body += blk
    total = off + len(body)
    head = struct.pack(">4sHHL", MAGIC, VERSION, len(entries), total)
    crc = zlib.crc32(head + bytes(tab))
    return head + struct.pack(">L", crc) + bytes(tab) + bytes(body)


def parse_campaign(f: bytes) -> list[dict]:
    """Strict: raises TrackError('E-CAMP: ...') with a precise reason. Returns entries {name, base, block, crc, offset}."""
    if len(f) < HDR:
        raise TrackError(f"E-CAMP: file is {len(f)} bytes, shorter than the {HDR}-byte header")
    magic, ver, cnt, total, crc = struct.unpack_from(">4sHHLL", f, 0)
    if magic != MAGIC:
        raise TrackError(f"E-CAMP: bad magic {magic!r}, expected {MAGIC!r} (not a Moonshine Racers campaign file)")
    if ver != VERSION:
        raise TrackError(f"E-CAMP: version {ver}, this tool reads version {VERSION}")
    if not 1 <= cnt <= MAX_ENTRIES:
        raise TrackError(f"E-CAMP: entry count {cnt} out of 1..{MAX_ENTRIES}")
    if total != len(f):
        raise TrackError(f"E-CAMP: header says {total} bytes, file has {len(f)} (truncated or padded)")
    tend = HDR + ENT * cnt
    if zlib.crc32(f[:12] + f[HDR:tend]) != crc:
        raise TrackError("E-CAMP: header/table CRC mismatch")
    out = []
    end = tend
    for i in range(cnt):
        nm, base, flags, off, ln, bcrc = struct.unpack_from(">24sHHLLL", f, HDR + ENT * i)
        if flags:
            raise TrackError(f"E-CAMP: entry {i}: reserved flags {flags:#x} must be 0")
        name = nm.rstrip(b"\0")
        if b"\0" in name or any(not 0x20 <= c < 0x7F for c in name) or not name:
            raise TrackError(f"E-CAMP: entry {i}: name is empty or not printable ASCII")
        if base >= NLEV:
            raise TrackError(f"E-CAMP: entry {i} '{name.decode()}': base level {base} out of 0..{NLEV - 1}")
        if off != end:
            raise TrackError(f"E-CAMP: entry {i}: block offset {off}, expected {end} (blocks follow the table back to back, in entry order)")
        if ln % 2 or not 2 <= ln <= BLOCK_MAX:
            raise TrackError(f"E-CAMP: entry {i}: block length {ln} (must be even, 2..{BLOCK_MAX})")
        if off + ln > len(f):
            raise TrackError(f"E-CAMP: entry {i}: block runs past the end of the file")
        blk = f[off:off + ln]
        if zlib.crc32(blk) != bcrc:
            raise TrackError(f"E-CAMP: entry {i} '{name.decode()}': block CRC mismatch (stored {bcrc:08x}, computed {zlib.crc32(blk):08x})")
        out.append({"name": name.decode(), "base": base, "block": blk, "crc": bcrc, "offset": off})
        end = off + ln
    if end != len(f):
        raise TrackError(f"E-CAMP: {len(f) - end} unused bytes after the last block")
    return out


def entry_track(e: dict) -> tuple[dict, list[Issue]]:
    """Block -> track dict (+ issues, incl. 'block is not canonical')."""
    t, n = parse_block(e["block"])
    t = {"format": FORMAT, "name": e["name"], "base_level": e["base"], "race_length": LEVELS[e["base"]][LEV_LEN],
         **{k: t[k] for k in STREAMS + ("objects", "types")}}
    iss = []
    if n != len(e["block"]):
        iss.append(Issue("ERROR", "E-SIZE", f"block has {len(e['block']) - n} unused bytes after the type table (length {len(e['block'])}, streams end at {n})"))
    return t, iss


def validate_campaign(f: bytes, label: str, lenient=False) -> bool:
    try:
        ents = parse_campaign(f)
    except TrackError as e:
        print(f"{label}: ERROR {e}")
        print(f"{label}: FAIL")
        return False
    good = True
    for i, e in enumerate(ents):
        lab = f"{label}[{i}] '{e['name']}'"
        try:
            t, iss = entry_track(e)
        except TrackError as ex:
            print(f"{lab}: ERROR {ex}")
            good = False
            continue
        iss += validate_track(t, lenient, block=e["block"])
        good &= report(iss, lab)
    return good


# ---------------------------------------------------------------- FAT12 floppy (720 KB, deterministic; same geometry as the Nebulus campaign disk)
SPT, HEADS, TRACKS = 9, 2, 80
NSEC = SPT * HEADS * TRACKS
NFAT, SPF, NDIR = 2, 3, 112
CAMP_NAME = b"MSTRACKSTRK"


def _boot(serial: bytes) -> bytes:
    bs = bytearray(512)
    bs[0:3] = b"\xeb\x34\x90"
    bs[3:8] = b"MSRTK"
    bs[8:11] = serial
    struct.pack_into("<HBHBHHBHHH", bs, 11, 512, 2, 1, NFAT, NDIR, NSEC, 0xF9, SPF, SPT, HEADS)
    assert sum(struct.unpack(">256H", bytes(bs))) & 0xFFFF != 0x1234        # never an executable boot sector
    return bytes(bs)


def build_disk(camp: bytes, label: str = "MSRTRACKS") -> bytes:
    ncl = (len(camp) + 1023) // 1024
    if ncl > (NSEC - 14) // 2:
        raise TrackError("E-DISK: file too large for the floppy")
    img = bytearray(NSEC * 512)
    img[0:512] = _boot(hashlib.md5(camp).digest()[:3])
    fat = bytearray(SPF * 512)
    fat[0:3] = b"\xf9\xff\xff"

    def setfat(n, v):
        o = n * 3 // 2
        x = fat[o] | fat[o + 1] << 8
        x = (x & 0x000F) | (v << 4) if n & 1 else (x & 0xF000) | v
        fat[o], fat[o + 1] = x & 0xFF, x >> 8
    for k in range(ncl):
        setfat(2 + k, 3 + k if k < ncl - 1 else 0xFFF)
    for k in range(NFAT):
        img[512 + k * SPF * 512:512 + (k + 1) * SPF * 512] = fat
    dir0 = 512 + NFAT * SPF * 512
    data0 = dir0 + NDIR * 32
    d = bytearray(32)
    d[0:11] = label.upper().encode("ascii").ljust(11)[:11]
    d[11] = 0x08
    e = bytearray(32)
    e[0:11] = CAMP_NAME
    e[11] = 0x20
    struct.pack_into("<HH", e, 22, 0x6000, 0x5D72)            # fixed time/date: deterministic output
    struct.pack_into("<HL", e, 26, 2, len(camp))
    img[dir0:dir0 + 32] = d
    img[dir0 + 32:dir0 + 64] = e
    img[data0:data0 + len(camp)] = camp
    return bytes(img)


def disk_read_file(img: bytes, name11: bytes = CAMP_NAME) -> bytes:
    """Minimal FAT12 root-directory reader for our own images (and any 512 B/sector floppy)."""
    bps, spc, res, nfat, ndir, tot, media, spf, spt, heads = struct.unpack_from("<HBHBHHBHHH", img, 11)
    if bps != 512 or not spc:
        raise TrackError("E-DISK: not a FAT floppy image (bytes per sector != 512)")
    fat0 = res * bps
    dir0 = fat0 + nfat * spf * bps
    data0 = dir0 + ndir * 32

    def fat(n):
        o = fat0 + n * 3 // 2
        x = img[o] | img[o + 1] << 8
        return (x >> 4) if n & 1 else (x & 0xFFF)
    for i in range(ndir):
        e = img[dir0 + 32 * i:dir0 + 32 * i + 32]
        if e[0] == 0:
            break
        if e[0] == 0xE5 or e[11] & 0x18 or e[:11] != name11:
            continue
        c, size = struct.unpack_from("<H", e, 26)[0], struct.unpack_from("<L", e, 28)[0]
        out = bytearray()
        while 2 <= c < 0xFF8 and len(out) < size:
            o = data0 + (c - 2) * spc * bps
            out += img[o:o + spc * bps]
            c = fat(c)
        return bytes(out[:size])
    raise TrackError(f"E-DISK: no {name11[:8].decode().strip()}.{name11[8:].decode()} in the root directory (not a campaign disk)")


def to_msa(st: bytes) -> bytes:
    out = bytearray(struct.pack(">HHHHH", 0x0E0F, SPT, HEADS - 1, 0, TRACKS - 1))
    tl = SPT * 512
    for t in range(TRACKS * HEADS):
        out += struct.pack(">H", tl) + st[t * tl:(t + 1) * tl]
    return bytes(out)


def from_msa(m: bytes) -> bytes:
    magic, spt, sides, t0, t1 = struct.unpack(">HHHHH", m[:10])
    if magic != 0x0E0F:
        raise TrackError("E-DISK: not an MSA image")
    p, out, tl = 10, bytearray(), spt * 512
    for _ in range((t1 - t0 + 1) * (sides + 1)):
        n = struct.unpack(">H", m[p:p + 2])[0]
        p += 2
        raw = m[p:p + n]
        p += n
        if n == tl:
            out += raw
        else:
            q, trk = 0, bytearray()
            while q < len(raw):
                c = raw[q]
                q += 1
                if c == 0xE5:
                    trk += bytes([raw[q]]) * struct.unpack(">H", raw[q + 1:q + 3])[0]
                    q += 3
                else:
                    trk.append(c)
            out += trk
    return bytes(out)


# ---------------------------------------------------------------- MS2 patching
def patch_ms2(ms2: bytes, ents: list[dict]) -> tuple[bytes, list[str]]:
    out = bytearray(ms2)
    log, seen = [], {}
    for i, e in enumerate(ents):
        lev = e["base"]
        if lev in seen:
            raise TrackError(f"E-PATCH: entries {seen[lev]} and {i} both use base level {lev}: MS2 has one track slot per level "
                             f"(the per-level scenery/sky/colours are tied to the slot), so patch-ms2 can replace each level once")
        seen[lev] = i
        s, n = LEVELS[lev][LEV_SECTOR], LEVELS[lev][LEV_NSECT]
        if len(e["block"]) > n * 512:
            raise TrackError(f"E-PATCH: entry {i} '{e['name']}' is {len(e['block'])} bytes, slot {lev} has {n * 512} ({n} sectors); trim objects/segments")
        out[s * 512:s * 512 + len(e["block"])] = e["block"]      # bytes after the block (sector padding) stay as they were: the game never reads them
        log.append(f"slot {lev:2d} (sector {s}, {n} sectors = {n * 512} B): entry {i} '{e['name']}' {len(e['block'])} B, {n * 512 - len(e['block'])} B spare")
    assert len(out) == len(ms2)
    return bytes(out), log


# ---------------------------------------------------------------- render
def render_png(t: dict, out: str):
    from PIL import Image, ImageDraw
    base = t["base_level"]
    rl = LEVELS[base][LEV_LEN]
    N = rl + LOOKAHEAD
    curve = expand_curve(t["curve"], N)
    left = expand_width(t["left"], N)
    right = expand_width(t["right"], N)
    hill, _ = expand_hill(t["hill"], N)
    W, H = 1600, 1000
    img = Image.new("RGB", (W, H), (18, 20, 30))
    d = ImageDraw.Draw(img)
    TXT, GRID = (200, 200, 210), (60, 64, 80)

    def frame(x0, y0, w, h, title):
        d.rectangle([x0, y0, x0 + w, y0 + h], outline=(100, 104, 120))
        d.text((x0 + 5, y0 + 3), title, fill=TXT)

    # --- A: top-down path (heading = c/600: arbitrary visual scale, the game has no world geometry), road band from the widths
    K = 600.0
    xs, ys, th = [0.0], [0.0], 0.0
    hd = []
    for i in range(min(N, len(curve))):
        th = curve[i] / K
        xs.append(xs[-1] + math.sin(th))
        ys.append(ys[-1] + math.cos(th))
        hd.append(th)
    ax, ay, aw, ah = 0, 0, 760, 760
    frame(ax, ay, aw, ah, f"{t.get('name', '')}  base level {base}  race {rl} units  (top-down from curve; arbitrary scale; colour = elevation)")
    x0, x1, y0_, y1 = min(xs), max(xs), min(ys), max(ys)
    sc = min((aw - 60) / max(x1 - x0, 1), (ah - 80) / max(y1 - y0_, 1))
    T = lambda x, y: (ax + 30 + (x - x0) * sc + ((aw - 60) - (x1 - x0) * sc) / 2, ay + ah - 30 - (y - y0_) * sc - ((ah - 80) - (y1 - y0_) * sc) / 2)
    wpx = lambda w: w * 0.06                     # road drawn 0.06 px per half-width unit each side (visual only)
    prev = None
    n_draw = min(len(xs) - 1, N)
    for i in range(n_draw):
        p = T(xs[i], ys[i])
        hv = hill[i] if i < len(hill) else 0
        col = (60 + int(hv * 1.6), 120 + int(60 * (1 - hv / 127)), 255 - int(hv * 1.8)) if i < rl else (70, 70, 85)
        lw = (left[i] if i < len(left) else 30)
        rw = (right[i] if i < len(right) else 30)
        nx, ny = math.cos(hd[i]), -math.sin(hd[i])
        a = (p[0] - nx * wpx(lw) * 0.5, p[1] + ny * wpx(lw) * 0.5)
        b = (p[0] + nx * wpx(rw) * 0.5, p[1] - ny * wpx(rw) * 0.5)
        if i % 3 == 0:
            d.line([a, b], fill=(52, 54, 66) if i >= rl else (78, 80, 96))
        if prev is not None:
            d.line([prev, p], fill=col, width=2)
        prev = p
    for k in range(1000, rl, 1000):
        p = T(xs[k], ys[k])
        d.ellipse([p[0] - 2, p[1] - 2, p[0] + 2, p[1] + 2], fill=(255, 230, 80))
        if k % 5000 == 0:
            d.text((p[0] + 5, p[1] - 5), f"{k}", fill=(255, 230, 80))
    ps, pf = T(xs[0], ys[0]), T(xs[rl], ys[rl])
    d.ellipse([ps[0] - 6, ps[1] - 6, ps[0] + 6, ps[1] + 6], outline=(0, 255, 0), width=2)
    d.ellipse([pf[0] - 6, pf[1] - 6, pf[0] + 6, pf[1] + 6], outline=(255, 60, 60), width=2)
    d.text((ps[0] + 8, ps[1] + 4), "START", fill=(0, 255, 0))
    d.text((pf[0] + 8, pf[1] + 4), f"FINISH {rl}", fill=(255, 60, 60))

    # --- B/C/D: strips on the distance axis
    sx0, sw = 800, 780

    def strip(y, h, title, series, vmin, vmax, labels=None):
        frame(sx0, y, sw, h, title)
        fx = lambda u: sx0 + 6 + u * (sw - 12) / N
        fy = lambda v: y + h - 8 - (v - vmin) * (h - 28) / max(vmax - vmin, 1e-9)
        for k in range(0, N, 2000):
            d.line([fx(k), y + 16, fx(k), y + h - 2], fill=GRID)
            d.text((fx(k) + 2, y + h - 12), str(k), fill=(120, 124, 140))
        d.line([fx(rl), y + 16, fx(rl), y + h - 2], fill=(255, 60, 60))
        for vals, col in series:
            pts = [(fx(i), fy(vals[i])) for i in range(0, len(vals), 2)]
            if len(pts) > 1:
                d.line(pts, fill=col, width=1)
        d.text((sx0 + sw - 120, y + 3), f"{vmin}..{vmax}", fill=(130, 134, 150))
    strip(0, 250, "curve value c (running sum of S0 deltas)", [(curve, (90, 200, 255))], min(curve + [0]), max(curve + [1]))
    strip(260, 240, "elevation byte 0..127 (S3 hill, integrated as the game does)", [(hill, (255, 170, 70))], 0, 127)
    strip(510, 250, "half-width left (green) / right (magenta), slews 1 unit/step", [(left, (120, 255, 120)), (right, (255, 120, 255))], 0, max(WIDTH[1], max(left + right + [1])))

    # --- E: objects strip (distance x lateral)
    ey, eh = 775, 215
    frame(0, ey, W - 1, eh, f"objects: {len(t['objects'])} (x = distance, y = lateral {LATERAL[0]}..{LATERAL[1]}, colour = type 1..{len(t['types'])}); red line = finish")
    fx = lambda u: 8 + u * (W - 16) / N
    fy = lambda v: ey + eh - 10 - (v - LATERAL[0]) * (eh - 30) / (LATERAL[1] - LATERAL[0])
    for k in range(0, N, 1000):
        d.line([fx(k), ey + 18, fx(k), ey + eh - 2], fill=GRID)
        if k % 2000 == 0:
            d.text((fx(k) + 2, ey + eh - 12), str(k), fill=(120, 124, 140))
    d.line([8, fy(0), W - 8, fy(0)], fill=(80, 84, 100))
    d.line([fx(rl), ey + 18, fx(rl), ey + eh - 2], fill=(255, 60, 60))
    for o in t["objects"]:
        h = (o["type"] * 2654435761) & 0xFFFFFF
        col = (80 + (h & 0xFF) * 175 // 255, 80 + ((h >> 8) & 0xFF) * 175 // 255, 80 + ((h >> 16) & 0xFF) * 175 // 255)
        x, y = fx(o["at"]), fy(o["lateral"])
        d.rectangle([x - 1, y - 2, x + 1, y + 2], fill=col)
    img.save(out)


# ---------------------------------------------------------------- CLI
def resolve(spec: str, ms2path, entry: int | None) -> tuple[dict, bytes | None]:
    """level number | stock:N | track.json | FILE.trk(+--entry)  ->  (track dict, canonical block or None)"""
    s = spec[6:] if spec.startswith("stock:") else spec
    if s.isdigit():
        lev = int(s)
        if not 0 <= lev < NLEV:
            raise SystemExit(f"level {lev} out of 0..{NLEV - 1}")
        return decode_stock(read_ms2(ms2path), lev)
    p = Path(spec)
    if p.suffix.lower() == ".trk":
        ents = parse_campaign(p.read_bytes())
        k = entry or 0
        if not 0 <= k < len(ents):
            raise SystemExit(f"{spec}: entry {k} out of 0..{len(ents) - 1}")
        t, iss = entry_track(ents[k])
        return t, ents[k]["block"]
    return load_json(p), None


def cmd_decode(a):
    ms2 = read_ms2(a.ms2)
    levs = range(NLEV) if (a.all or a.src is None) else [int(a.src)]
    if len(levs) > 1 or a.all:
        outdir = Path(a.out or "tracks_json")
        outdir.mkdir(parents=True, exist_ok=True)
    for lev in levs:
        t, blk = decode_stock(ms2, lev)
        txt = dumps_json(t)
        if len(levs) > 1:
            p = outdir / f"level{lev:02d}.json"
            p.write_text(txt)
            print(f"{p}: level {lev}, block {len(blk)} B, curve {len(t['curve'])} left {len(t['left'])} right {len(t['right'])} hill {len(t['hill'])} objects {len(t['objects'])} types {len(t['types'])}")
        elif a.out:
            Path(a.out).write_text(txt)
            print(f"{a.out}: level {lev}, block {len(blk)} B")
        else:
            sys.stdout.write(txt)


def cmd_encode(a):
    t = load_json(a.track)
    iss = validate_track(t, a.lenient)
    if not report(iss, a.track) and not a.force:
        return 1
    blk = encode_track(t)
    Path(a.out).write_bytes(blk)
    print(f"{a.out}: {len(blk)} bytes (limit {BLOCK_MAX}), CRC32 {zlib.crc32(blk):08x}")
    return 0


def cmd_validate(a):
    ok = True
    for f in a.files:
        p = Path(f)
        try:
            if p.suffix.lower() == ".trk":
                ok &= validate_campaign(p.read_bytes(), f, a.lenient)
            elif p.suffix.lower() == ".st" or p.suffix.lower() == ".msa":
                raw = p.read_bytes()
                ok &= validate_campaign(disk_read_file(from_msa(raw) if raw[:2] == b"\x0e\x0f" else raw), f"{f}:MSTRACKS.TRK", a.lenient)
            elif p.suffix.lower() == ".bin":
                if a.base is None:
                    raise SystemExit(f"{f}: a raw block needs --base N")
                blk = p.read_bytes()
                t, n = parse_block(blk)
                t = {"format": FORMAT, "name": p.stem.upper()[:NAME_LEN], "base_level": a.base, **{k: t[k] for k in STREAMS + ("objects", "types")}}
                iss = validate_track(t, a.lenient, block=blk)
                if n != len(blk):
                    iss.append(Issue("ERROR", "E-SIZE", f"block has {len(blk) - n} unused bytes after the type table"))
                ok &= report(iss, f)
            else:
                ok &= report(validate_track(load_json(p), a.lenient), f)
        except TrackError as e:
            print(f"{f}: ERROR {e}")
            print(f"{f}: FAIL")
            ok = False
    return 0 if ok else 1


def cmd_render(a):
    t, _ = resolve(a.src, a.ms2, a.entry)
    iss = [i for i in validate_track(t, True) if i.level == "ERROR" and i.code in ("E-FORM", "E-BASE")]
    if iss:
        for i in iss:
            print(i)
        return 1
    render_png(t, a.out)
    print(f"{a.out}: rendered '{t.get('name', '')}' (base level {t['base_level']})")


def _camp_read(path):
    return parse_campaign(Path(path).read_bytes())


def _entry_from_json(path, a):
    t = load_json(path)
    iss = validate_track(t, a.lenient)
    if not report(iss, path) and not a.force:
        raise SystemExit(1)
    return (t["name"], t["base_level"], encode_track(t))


def cmd_campaign(a):
    if a.sub == "new":
        ents = []
        if a.stock:
            ms2 = read_ms2(a.ms2)
            ents = [(f"STOCK {lev:02d}", lev, decode_stock(ms2, lev)[1]) for lev in range(NLEV)]
        ents += [_entry_from_json(j, a) for j in a.tracks]
        Path(a.out).write_bytes(build_campaign(ents))
        print(f"{a.out}: {len(ents)} tracks, {Path(a.out).stat().st_size} bytes")
    elif a.sub == "add":
        ents = [(e["name"], e["base"], e["block"]) for e in _camp_read(a.camp)]
        new = _entry_from_json(a.track, a)
        ents.insert(len(ents) if a.at is None else a.at, new)
        Path(a.camp).write_bytes(build_campaign(ents))
        print(f"{a.camp}: {len(ents)} tracks (added '{new[0]}' at position {ents.index(new)})")
    elif a.sub == "remove":
        ents = [(e["name"], e["base"], e["block"]) for e in _camp_read(a.camp)]
        if not 0 <= a.index < len(ents):
            raise SystemExit(f"index {a.index} out of 0..{len(ents) - 1}")
        gone = ents.pop(a.index)
        Path(a.camp).write_bytes(build_campaign(ents))
        print(f"{a.camp}: removed '{gone[0]}', {len(ents)} tracks left")
    elif a.sub == "list":
        f = Path(a.camp).read_bytes()
        ents = parse_campaign(f)
        print(f"{a.camp}: MSTK v{VERSION}, {len(ents)} tracks, {len(f)} bytes")
        print(f"{'#':>2} {'name':<24} {'base':>4} {'race':>6} {'block':>6} {'crc32':>8}  curve left right hill objs  status")
        for i, e in enumerate(ents):
            try:
                t, iss = entry_track(e)
                iss += validate_track(t, a.lenient, block=e["block"])
                err = sum(x.level == "ERROR" for x in iss)
                st = "OK" if not err else f"{err} ERRORS"
                print(f"{i:>2} {e['name']:<24} {e['base']:>4} {LEVELS[e['base']][LEV_LEN]:>6} {len(e['block']):>6} {e['crc']:08x}  "
                      f"{len(t['curve']):>5} {len(t['left']):>4} {len(t['right']):>5} {len(t['hill']):>4} {len(t['objects']):>4}  {st}")
            except TrackError as ex:
                print(f"{i:>2} {e['name']:<24} {e['base']:>4} {'':>6} {len(e['block']):>6} {e['crc']:08x}  unreadable: {ex}")
    elif a.sub == "extract":
        ents = _camp_read(a.camp)
        if not 0 <= a.index < len(ents):
            raise SystemExit(f"index {a.index} out of 0..{len(ents) - 1}")
        e = ents[a.index]
        if a.bin:
            Path(a.out).write_bytes(e["block"])
            print(f"{a.out}: {len(e['block'])} bytes (raw block, base level {e['base']})")
        else:
            t, _ = entry_track(e)
            Path(a.out).write_text(dumps_json(t))
            print(f"{a.out}: '{e['name']}' base level {e['base']}")
    return 0


def cmd_disk(a):
    camp = Path(a.camp).read_bytes()
    parse_campaign(camp)
    st = build_disk(camp, a.label)
    Path(a.out).write_bytes(to_msa(st) if a.out.lower().endswith(".msa") else st)
    assert disk_read_file(st) == camp
    print(f"{a.out}: {len(st)} B floppy image ({SPT} sec x {HEADS} sides x {TRACKS} tracks), MSTRACKS.TRK {len(camp)} B in the root, serial {hashlib.md5(camp).hexdigest()[:6]}")


def cmd_patch(a):
    ms2 = read_ms2(a.ms2)
    ents = parse_campaign(Path(a.camp).read_bytes())
    for i, e in enumerate(ents):                                    # refuse broken tracks
        t, iss = entry_track(e)
        iss += validate_track(t, a.lenient, budget=LEVELS[e["base"]][LEV_NSECT] * 512, block=e["block"])
        if not report(iss, f"{a.camp}[{i}] '{e['name']}'") and not a.force:
            return 1
    new, log = patch_ms2(ms2, ents)
    for l in log:
        print(l)
    if not a.check_only:
        Path(a.out).write_bytes(new)
        diff = sum(1 for x, y in zip(ms2, new) if x != y)
        print(f"{a.out}: {len(new)} bytes (same size as the input), {diff} bytes differ")
    return 0


def selftest(a):
    ms2 = read_ms2(a.ms2)
    bad = 0
    for lev in range(NLEV):
        t, blk = decode_stock(ms2, lev)
        slice_ok = stock_block(ms2, lev)[:len(blk)] == blk
        # JSON text round trip
        t2 = json.loads(dumps_json(t))
        blk2 = encode_track(t2)
        rl_ok = stock_race_length(ms2, lev) == LEVELS[lev][LEV_LEN]
        crc_ok = zlib.crc32(b"".join(struct.pack(">HHHhHH", 0xFF00, *e) for e in t["types"])) == LEVELS[lev][LEV_TCRC]
        iss = validate_track(t2, budget=LEVELS[lev][LEV_NSECT] * 512, block=blk2)
        errs = [i for i in iss if i.level == "ERROR"]
        ok = blk2 == blk and slice_ok and rl_ok and crc_ok and not errs
        bad += not ok
        print(f"level {lev:2d}: block {len(blk):5d} B (slot {LEVELS[lev][LEV_NSECT] * 512:5d})  MS2->JSON->encode {'IDENTICAL' if blk2 == blk else 'DIFFERENT'}"
              f"  racelen {'ok' if rl_ok else 'BAD'}  types crc {'ok' if crc_ok else 'BAD'}  validate {'OK' if not errs else 'FAIL ' + str(errs[0])}"
              f"  warnings {len(iss) - len(errs)}")
    ents = [(f"STOCK {lev:02d}", lev, decode_stock(ms2, lev)[1]) for lev in range(NLEV)]
    camp = build_campaign(ents)
    back = parse_campaign(camp)
    ok = [(e["name"], e["base"], e["block"]) for e in back] == ents
    st = build_disk(camp)
    ok &= disk_read_file(st) == camp and from_msa(to_msa(st)) == st
    new, _ = patch_ms2(ms2, back)
    ok &= new == ms2
    bad += not ok
    print(f"campaign: {len(ents)} tracks {len(camp)} B -> parse identical, disk {len(st)} B readback identical, patch-ms2 of the stock campaign == original MS2: {'OK' if ok else 'FAIL'}")
    print("SELFTEST " + ("PASS" if not bad else f"FAIL ({bad})"))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ms2", help=f"FILES/MS2 of the game folder (default {DEFAULT_MS2.relative_to(GAME)})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, force=True):
        p.add_argument("--lenient", action="store_true", help="demote the stock-envelope range errors to warnings")
        if force:
            p.add_argument("--force", action="store_true", help="write the output even when validation fails")
    p = sub.add_parser("decode", help="stock level(s) -> JSON")
    p.add_argument("src", nargs="?", help="level 0..14 (default / --all: all 15 into -o DIR)")
    p.add_argument("--all", action="store_true")
    p.add_argument("-o", "--out")
    p = sub.add_parser("encode", aliases=["build"], help="JSON -> track block bytes")
    p.add_argument("track")
    p.add_argument("-o", "--out", required=True)
    common(p)
    p = sub.add_parser("validate", help="check .json / .bin / .trk / .st")
    p.add_argument("files", nargs="+")
    p.add_argument("--base", type=int, help="base level of a raw .bin block")
    common(p, False)
    p = sub.add_parser("render", help="PNG of a track")
    p.add_argument("src")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--entry", type=int)
    p = sub.add_parser("campaign", help="build / read MSTRACKS.TRK")
    cs = p.add_subparsers(dest="sub", required=True)
    q = cs.add_parser("new")
    q.add_argument("out")
    q.add_argument("tracks", nargs="*", help="track .json files in campaign order")
    q.add_argument("--stock", action="store_true", help="start from the 15 stock tracks")
    common(q)
    q = cs.add_parser("add")
    q.add_argument("camp")
    q.add_argument("track")
    q.add_argument("--at", type=int, help="insert position (default: append)")
    common(q)
    q = cs.add_parser("remove")
    q.add_argument("camp")
    q.add_argument("index", type=int)
    q = cs.add_parser("list")
    q.add_argument("camp")
    common(q, False)
    q = cs.add_parser("extract")
    q.add_argument("camp")
    q.add_argument("index", type=int)
    q.add_argument("-o", "--out", required=True)
    q.add_argument("--bin", action="store_true", help="raw block instead of JSON")
    p = sub.add_parser("disk", help="campaign file -> floppy image")
    p.add_argument("camp")
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--label", default="MSRTRACKS")
    p = sub.add_parser("patch-ms2", help="copy of MS2 with the campaign's tracks in their base-level slots")
    p.add_argument("camp")
    p.add_argument("-o", "--out")
    p.add_argument("--check-only", action="store_true")
    common(p)
    sub.add_parser("selftest")
    a = ap.parse_args()
    try:
        if a.cmd == "decode":
            return cmd_decode(a)
        if a.cmd in ("encode", "build"):
            return cmd_encode(a)
        if a.cmd == "validate":
            return cmd_validate(a)
        if a.cmd == "render":
            return cmd_render(a)
        if a.cmd == "campaign":
            return cmd_campaign(a)
        if a.cmd == "disk":
            return cmd_disk(a)
        if a.cmd == "patch-ms2":
            if not a.out and not a.check_only:
                ap.error("patch-ms2 needs -o OUT (or --check-only)")
            return cmd_patch(a)
        if a.cmd == "selftest":
            return selftest(a)
    except TrackError as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
