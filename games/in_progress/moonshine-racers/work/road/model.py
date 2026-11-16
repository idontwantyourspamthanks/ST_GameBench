"""Clean slot model of the stock span draw ($17c42) for one record, checked against the stock code in Musashi."""
from rdlib import *
import random, struct

def stock_rows(emu, recs, buf=0x100000, a5=None):
    """Run the stock draw on records [(w0,A,B,F)] (A,B signed words); returns (rows[160B each, row k = k-th record from the bottom], a0_final, $12f4)."""
    strm = 0x60000
    data = b''.join(struct.pack('>HhhH', *r) for r in recs) + bytes(16)
    emu.wr(strm, data); emu.wr(0x4b84, strm.to_bytes(4, 'big')); emu.wr(0x1008, buf.to_bytes(4, 'big'))
    emu.wr(buf, bytes([0x55]) * 0x7d00)
    cyc = emu.call(0x17c42)
    out = emu.rd(buf, 0x7d00)
    rows = [out[(199 - k) * 160:(200 - k) * 160] for k in range(len(recs))]
    return rows, int.from_bytes(emu.rd(0x12f0, 4), 'big'), int.from_bytes(emu.rd(0x12f4, 2), 'big'), cyc

def window_tables(emu):
    """WA[combo][w0idx][s] / WB[...] = 16 bytes: the stock $1058a applied to the pattern-table masks, for both edge orientations."""
    a5 = int.from_bytes(emu.rd(0x135a, 4), 'big')
    tab = emu.rd(0x4ff8, 0xc00)
    WA = {}; WB = {}
    for combo in range(8):
        d7 = combo << 13
        for k in range(1, 12):
            for s in range(16):
                o = k * 256 + s * 16
                L0, L4, L8 = (u32(tab, o + 4 * i) for i in range(3))
                for orient, store in (('A', WA), ('B', WB)):
                    if orient == 'A': d4, d5, d6 = L8, L4, L0
                    else: d4, d5, d6 = L0, L4, L8
                    emu.call(0x1058a, {'d4': d4, 'd5': d5, 'd6': d6, 'd7': d7, 'a5': a5, 'd1': 0, 'd3': 0})
                    d0, d2, d4o, d6o = emu.reg('d0'), emu.reg('d2'), emu.reg('d4'), emu.reg('d6')
                    w = struct.pack('>HHHH', d0 >> 16, d2 >> 16, d4o >> 16, d6o >> 16) + struct.pack('>HHHH', d0 & 0xffff, d2 & 0xffff, d4o & 0xffff, d6o & 0xffff)
                    store[(combo, k, s)] = w
    return WA, WB

def colours(emu):
    a5 = int.from_bytes(emu.rd(0x135a, 4), 'big')
    t = emu.rd(a5, 0x30)
    return {'g': (t[0:8], t[8:16]), 'r': (t[0x10:0x18], t[0x18:0x20]), 'e': (t[0x20:0x28], t[0x28:0x30])}

def model_row(rec, WA, WB, col):
    w0, A, B, F = rec
    k = w0 >> 8
    Aal = A & ~15; Bal = B & ~15
    wA = Aal // 16; wB = Bal // 16     # python floor division == arithmetic shift for multiples of 16
    s_a = A & 15; s_b = B & 15
    combo = (F >> 13) & 7
    G = col['g'][1 if F & 0x8000 else 0]
    R = col['r'][1 if F & 0x4000 else 0]
    row = [None] * 20
    for s in range(20): row[s] = G
    for s in range(max(0, wB + 2), min(wA, 20)): row[s] = R
    for pos, w in ((wA, WA[(combo, k, s_a)]), (wB, WB[(combo, k, s_b)])):
        for j in (0, 1):
            if 0 <= pos + j < 20: row[pos + j] = w[8 * j:8 * j + 8]
    return b''.join(row)
