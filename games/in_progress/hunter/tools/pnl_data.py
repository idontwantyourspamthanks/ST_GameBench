"""Amiga panel art from the user's ADF (nothing is stored in git): decode externs/panfile / storepic."""
import struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from amiga_extract import DEFAULT_ADF, file_table, read_file, TRACK_DATA


def unpackbits(b, n):
    out = bytearray(); i = 0
    while len(out) < n and i < len(b):
        c = b[i]; i += 1
        if c < 128:
            out += b[i:i + c + 1]; i += c + 1
        elif c > 128:
            out += bytes([b[i]]) * (257 - c); i += 1
    return bytes(out[:n])


def parse_ilbm(d, off=0):
    assert d[off:off + 4] == b'FORM'
    L = struct.unpack('>I', d[off + 4:off + 8])[0]
    p = off + 12; pal = body = bmhd = None
    while p < off + 8 + L:
        tag = d[p:p + 4]; n = struct.unpack('>I', d[p + 4:p + 8])[0]; c = d[p + 8:p + 8 + n]
        if tag == b'CMAP': pal = c
        if tag == b'BMHD': bmhd = c
        if tag == b'BODY': body = c
        p += 8 + n + (n & 1)
    w, h, x, y, npl, mask, comp = struct.unpack('>HHhhBBB', bmhd[:11])
    raw = unpackbits(body, h * npl * (w // 8)) if comp else body
    return dict(w=w, h=h, np=npl, pal=pal, raw=raw)


def pixels(pic):
    w, h, npl = pic['w'], pic['h'], pic['np']; rb = w // 8; raw = pic['raw']
    px = []
    for y in range(h):
        row = [0] * w
        for pl in range(npl):
            o = (y * npl + pl) * rb
            for x in range(w):
                if raw[o + x // 8] >> (7 - x % 8) & 1:
                    row[x] |= 1 << pl
        px.append(row)
    return px


def st_planar(px, y0=0, y1=None):
    out = bytearray()
    for row in px[y0:y1]:
        for wx in range(len(row) // 16):
            for pl in range(4):
                v = 0
                for b in range(16):
                    v = (v << 1) | ((row[wx * 16 + b] >> pl) & 1)
                out += struct.pack('>H', v)
    return bytes(out)


def amiga_pic(adf_path=DEFAULT_ADF, name='externs/panfile'):
    adf = Path(adf_path).read_bytes()
    t, sz, n, fl = file_table(adf)[name]
    return parse_ilbm(read_file(adf, t, n * TRACK_DATA))


def cmap_amiga_words(pic):
    """16 colours as Amiga $0RGB words (4 bits per gun; CMAP holds the nibble in the high half of each byte)."""
    p = pic['pal']
    return [((p[i * 3] >> 4) << 8) | ((p[i * 3 + 1] >> 4) << 4) | (p[i * 3 + 2] >> 4) for i in range(16)]


# ---- the packed panel block (appended to the sample bank, loaded with it at PANDATA) -----------------------------
PANDATA = 0xAE4E0                    # absolute address of the block (patches/sky2_pnl.s uses the same number)
PAN_ROWS = 60                        # panel = rows 0..59 of externs/panfile
PAN_BYTES = PAN_ROWS * 160


def lz_encode(data: bytes) -> bytes:
    """Optimal parse of the panel's own byte-LZ ('HLZ'; the 68000 decoder is sky2_pnl.s `pnl_unpack`):
        0                 end
        1..127  n         n literal bytes follow
        $80|c   o         copy c+2 bytes from o bytes back (o = 1..255)
        $c0|c   oh ol     copy c+3 bytes from oh:ol bytes back (c = 0..63)"""
    n = len(data)
    INF = 10 ** 9
    best = [INF] * (n + 1)
    choice = [None] * (n + 1)
    best[n] = 1
    pos = {}
    cand = [None] * n                          # per position: {offset: longest match length (<= 66)}
    for i in range(n):
        d = {}
        if i + 1 < n:
            for j in reversed(pos.get(data[i:i + 2], [])):
                off = i - j
                if off > 65535:
                    break
                l = 2
                while i + l < n and l < 66 and data[i + l] == data[i + l - off]:
                    l += 1
                d[off] = l
        cand[i] = d
        if i + 1 < n:
            pos.setdefault(data[i:i + 2], []).append(i)
    for i in range(n - 1, -1, -1):
        for L in range(1, min(127, n - i) + 1):
            c = 1 + L + best[i + L]
            if c < best[i]:
                best[i], choice[i] = c, ("lit", L)
        for off, l in cand[i].items():
            for cnt in range(2, l + 1):
                if off <= 255 and cnt <= 65:
                    c = 2 + best[i + cnt]
                    if c < best[i]:
                        best[i], choice[i] = c, ("s", cnt, off)
                if 3 <= cnt <= 66:
                    c = 3 + best[i + cnt]
                    if c < best[i]:
                        best[i], choice[i] = c, ("l", cnt, off)
    out = bytearray()
    i = 0
    while i < n:
        ch = choice[i]
        if ch[0] == "lit":
            out.append(ch[1]); out += data[i:i + ch[1]]; i += ch[1]
        elif ch[0] == "s":
            out.append(0x80 | (ch[1] - 2)); out.append(ch[2]); i += ch[1]
        else:
            out.append(0xC0 | (ch[1] - 3)); out += bytes([ch[2] >> 8, ch[2] & 255]); i += ch[1]
    out.append(0)
    return bytes(out)


def lz_decode(src: bytes) -> bytes:
    out = bytearray()
    i = 0
    while True:
        c = src[i]; i += 1
        if c == 0:
            return bytes(out)
        if c < 0x80:
            out += src[i:i + c]; i += c
            continue
        if c & 0x40:
            cnt = (c & 0x3F) + 3; off = (src[i] << 8) | src[i + 1]; i += 2
        else:
            cnt = (c & 0x3F) + 2; off = src[i]; i += 1
        for _ in range(cnt):
            out.append(out[-off])


def panel_block(adf_path=DEFAULT_ADF) -> bytes:
    """'HPAN' | word 9600 | word additive checksum of the 9600 bytes | 16 x Amiga $0RGB words (CMAP) | HLZ stream."""
    pic = amiga_pic(adf_path)
    raw = st_planar(pixels(pic), 0, PAN_ROWS)
    stream = lz_encode(raw)
    assert lz_decode(stream) == raw
    csum = sum(struct.unpack(">4800H", raw)) & 0xFFFF
    return b"HPAN" + struct.pack(">HH", len(raw), csum) + b"".join(struct.pack(">H", w) for w in cmap_amiga_words(pic)) + stream
