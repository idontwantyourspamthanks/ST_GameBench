#!/usr/bin/env python3
"""Masked pixel gate of the speech bar: S capture (set with sb_*) against F capture (the default set, speech drawn into the sky by ta_*), same snapshot, same input,
frames matched by the pass counter $100e (cap_sb.py directories).  Explicit rectangles, compared / excluded / differing counts, nothing is excluded silently:
  A  rows 65-199, whole width (horizon strip, road, objects, car): S == F                                  (excluded: nothing)
  B0 rows 0-15 (the top bar): S == F                                                                       (excluded: nothing)
  B  rows 42-64 (the sky that the strip does not cover): S must be sky (index 15) everywhere              (excluded: nothing)
  C  rows 42-64: S vs F: F shows speech pixels only inside the stock message box (112,42)-(303,64) and only while its ticker is active;
     outside that box and in frames without speech S == F                                                  (excluded: the box, in frames where F's ticker state is active or erasing)
  D  rows 16-41 (the strip), BOTH buffers of every pass: equal to the strip rendered by the Python model from that buffer's own shadow; the drawn buffer's shadow equals the ticker state
  E  (info) the visible differences: per frame the pixels of rows 16-64 that differ between S and F, and the rows/columns they cover
    python3 mask_sb.py F_DIR S_DIR [--tag TXT]"""
import sys, json, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sbart import *

RECTS = {'strip': (0, 16, 319, 41), 'sky_below': (0, 42, 319, 64), 'msgbox_below': (112, 42, 303, 64), 'bar': (0, 0, 319, 15), 'road': (0, 65, 319, 199)}
texts = {a: t for a, t in messages()}
DEBUG = True
PASSKEY = None


def text_at(c, BM):
    """message text of the record at BM: read from the capture of RAM $6000-$6fff when present, else the table of the race_start dump"""
    f = c['d'] / f"p{c['i']:03d}_txt.bin"
    if f.exists():
        t = f.read_bytes()[BM + 4 - 0x6000:BM + 4 - 0x6000 + 128]
        return t.split(b'\0')[0].decode('latin1')
    return texts.get(BM)


def load(d):
    meta = json.load(open(d / 'meta.json'))
    out = {}
    for i, m in enumerate(meta):
        ram = (d / f'p{i:03d}_ram.bin').read_bytes()
        out[m['pass_']] = dict(i=i, back=m['back'], ram=ram, d=d)
    return out


def buf(c, which):
    return planar_to_idx((c['d'] / f"p{c['i']:03d}_{which}.bin").read_bytes())


def drawn(c):
    return buf(c, '70000' if c['back'] == 0x70000 else '78000')


def model_ok(c, first=False):
    """check D for both buffers of one S frame; returns (compared, differing, ticker_ok)"""
    sb = (c['d'] / f"p{c['i']:03d}_sb.bin").read_bytes()
    comp = diff = 0
    for k, which in enumerate(('70000', '78000')):
        if first and c['back'] != (0x70000 if which == '70000' else 0x78000): continue          # the first frame of a capture: the other buffer has not been drawn yet
        BM, BN, FI = struct.unpack('>HHH', sb[16 * k:16 * k + 6])
        I = buf(c, which)
        e = np.zeros((200, 320), np.uint8)
        draw_strip(e, text_at(c, BM) if BM else None, BN, FI if FI else None)
        comp += 26 * 320
        dk = int((e[16:42] != I[16:42]).sum())
        diff += dk
        if dk and DEBUG: print(f'   D mismatch: pass {c["i"]} key {PASSKEY} buffer {which} shadow (msg {BM:#x} chars {BN} face {FI:#x}) differing px {dk}, strip colours in the buffer {sorted(set(I[16:42].ravel().tolist()))}, model colours {sorted(set(e[16:42].ravel().tolist()))}')
    kd = 0 if c['back'] == 0x70000 else 1
    BM, BN, FI = struct.unpack('>HHH', sb[16 * kd:16 * kd + 6])
    ram = c['ram']
    t11ab = ram[0x11ab - 0x1000]
    M = int.from_bytes(ram[0x11a8 - 0x1000:0x11a8 - 0x1000 + 2], 'big')
    tp = int.from_bytes(ram[0x11a4 - 0x1000:0x11a4 - 0x1000 + 2], 'big')
    n = (tp - M - 4) & 0xffff
    tick = (BM, BN) == ((M, n) if t11ab else (0, 0)) and ((FI != 0) == bool(t11ab))
    return comp, diff, tick


def main():
    F = load(Path(sys.argv[1])); S = load(Path(sys.argv[2]))
    keys = sorted(set(F) & set(S))
    tot = {k: [0, 0, 0, 0] for k in ('A rows65-199 S==F', 'B0 bar rows0-15 S==F', 'B sky rows42-64 == sky', 'C rows42-64 S==F outside msgbox', 'D strip rows16-41 == model (2 buffers)')}
    tickbad = 0; vis = []; nsp = 0
    for k in keys:
        fF, fS = drawn(F[k]), drawn(S[k])
        spF = F[k]['ram'][0x11ab - 0x1000] != 0
        spS = S[k]['ram'][0x11ab - 0x1000] != 0
        nsp += spF
        d = fF[65:] != fS[65:]
        t = tot['A rows65-199 S==F']; t[0] += d.size; t[2] += int(d.sum()); t[3] += 1
        d = fF[:16] != fS[:16]
        t = tot['B0 bar rows0-15 S==F']; t[0] += d.size; t[2] += int(d.sum()); t[3] += 1
        sky = fS[42:65]
        bad = sky != 15
        t = tot['B sky rows42-64 == sky']; t[0] += sky.size; t[2] += int(bad.sum()); t[3] += 1
        # C: F active (typing/hold/erase) = the stock message box is excluded; the pixels of F inside it that are not sky are the "visible differences"
        dd = fF[42:65] != fS[42:65]
        m = np.zeros((23, 320), bool)
        stock_active = bool((fF[42:65, 112:304] != 15).any())
        if stock_active:
            m[:, 112:304] = True
        t = tot['C rows42-64 S==F outside msgbox']; chk = ~m; t[0] += int(chk.sum()); t[1] += int(m.sum()); t[2] += int((dd & chk).sum()); t[3] += 1
        if stock_active:
            ys, xs = np.nonzero(dd)
            vis.append((k, int(dd.sum()), int(ys.min()) + 42, int(ys.max()) + 42, int(xs.min()), int(xs.max())))
        PASSKEY = k
        comp, diff, tick = model_ok(S[k], first=(S[k]["i"] == 0))
        t = tot['D strip rows16-41 == model (2 buffers)']; t[0] += comp; t[2] += diff; t[3] += 1
        tickbad += 0 if tick else 1
    print(f'frames matched by pass key: {len(keys)} (keys {keys[0]}..{keys[-1]}), frames where the default set has its ticker active: {nsp}')
    ok = True
    for name, (n, ex, bad, nf) in tot.items():
        ok &= bad == 0
        print(f'  {name:40s} frames {nf:4d} compared {n:9d} excluded {ex:8d} differing {bad:6d} -> {"IDENTICAL" if bad == 0 else "DIFFER"}')
    print(f'  drawn-buffer shadow == ticker state: {len(keys) - tickbad}/{len(keys)} frames')
    ok &= tickbad == 0
    if vis:
        r0 = min(v[2] for v in vis); r1 = max(v[3] for v in vis); x0 = min(v[4] for v in vis); x1 = max(v[5] for v in vis)
        print(f'  E visible differences below the strip (rows 42-64, only where the default set draws its message): {len(vis)} frames, rows {r0}-{r1}, columns {x0}-{x1}; mean differing pixels per such frame {sum(v[1] for v in vis) / len(vis):.0f}')
    print('RESULT:', 'IDENTICAL' if ok else 'DIFFER')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
