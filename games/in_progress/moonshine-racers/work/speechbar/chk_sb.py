#!/usr/bin/env python3
"""Check a cap_sb.py capture directory: per pass, for BOTH buffers, the strip rows (16-41, all x) must equal the strip rendered by the Python model from that
buffer's shadow (message BM, characters BN, face frame FI of $B2A00/$B2A10); the buffer drawn in that pass must show the ticker's current state
(message $11a8 if $11ab != 0, characters = $11a4 - $11a8 - 4, face = non-zero when the message is on).
    python3 chk_sb.py DIR [--png N]"""
import sys, json, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbart import *

d = Path(sys.argv[1])
meta = json.load(open(d / 'meta.json'))
texts = {a: t for a, t in messages()}
pngn = int(sys.argv[sys.argv.index('--png') + 1]) if '--png' in sys.argv else -1
bad = 0
rows = []
for i, m in enumerate(meta):
    sb = (d / f'p{i:03d}_sb.bin').read_bytes()
    ram = (d / f'p{i:03d}_ram.bin').read_bytes()
    w = lambda a: int.from_bytes(ram[a - 0x1000:a - 0x1000 + 2], 'big')
    b = lambda a: ram[a - 0x1000]
    back = m['back']
    bufs = {0x70000: planar_to_idx((d / f'p{i:03d}_70000.bin').read_bytes()), 0x78000: planar_to_idx((d / f'p{i:03d}_78000.bin').read_bytes())}
    out = []
    for k, addr in enumerate((0x70000, 0x78000)):
        BM, BN, FI = struct.unpack('>HHH', sb[16 * k:16 * k + 6])
        I = bufs[addr]
        exp = np.full_like(I, 0)
        e = np.zeros((200, 320), np.uint8)
        text = texts.get(BM) if BM else None
        if BM and text is None:
            out.append(f'buf{k}: unknown message {BM:#x}')
            bad += 1
            continue
        draw_strip(e, text, BN, FI if FI else None)
        diff = int((e[16:42] != I[16:42]).sum())
        if diff:
            bad += 1
        out.append(f'buf{k}(BM {BM:#x} BN {BN} FI {FI:#x}) strip diff {diff}')
    # drawn buffer vs ticker state
    kd = 0 if back == 0x70000 else 1
    BM, BN, FI = struct.unpack('>HHH', sb[16 * kd:16 * kd + 6])
    t11ab, M, tp = b(0x11ab), w(0x11a8), w(0x11a4)
    n = (tp - M - 4) & 0xffff
    expM, expN = (M, n) if t11ab else (0, 0)
    ok = (BM, BN) == (expM, expN) and ((FI != 0) == bool(t11ab) or t11ab == 0 and FI == 0)
    if not ok:
        bad += 1
    out.append(f'drawn={back:#x} $11ab={t11ab} M={M:#x} n={n}: shadow ({BM:#x},{BN},{FI:#x}) {"ok" if ok else "MISMATCH"}')
    print(f'pass {m["pass_"]:5d}', ' | '.join(out))
print('bad', bad)
