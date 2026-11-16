#!/usr/bin/env python3
"""Masked pixel gate for the new HUD (work/notes/hud_build.md).  tools/msrabtest.py compares whole screen buffers; this file compares colour-index images
with an explicit list of excluded rectangles and prints how many pixels were compared and excluded, so a gate cannot pass by over-excluding.

Library (used by work/hud/build/*.py and the Hatari mode below):
  planar_to_idx(bytes32000) -> (200, 320) palette indices
  RECTS: every excluded rectangle, named: x0, y0, x1, y1 inclusive (pixels)
  check_frame(new, ref, speech, strip_expect) -> dict of counts / differing pixel lists per check
Checks per frame (one screen buffer):
  A  rows 65-199 (whole width): new == ref, ref = the stock game with the HUD stage reduced to ticker + face and no cloud update (patch `test_hdref`);
     excluded: nothing (the horizon strip $18318 rewrites rows 65-119 every pass, the road rows 120-199); the new HUD must show exactly that.
  B  rows 16-64: every pixel must be the sky (index 15), except the message box (112,16)-(303,64) when a message is (or just was) on screen (`speech`).
  C  rows 0-15: must equal the strip image rendered from the HUD's own shadow values (`strip_expect`, see tools/msrhudgen.py + work/hud/build).
  D  (optional, against the real stock game) rows 85-199 outside the removed bottom elements: new == stock.
"""
import sys
import numpy as np

RECTS = {
    'strip': (0, 0, 319, 15),                       # new HUD strip (checked by C instead)
    'msgbox': (112, 16, 303, 64),                   # message ticker 112-271 + face 272-303, rows 16-64
    'speedo': (256, 148, 319, 176),                 # stock speedometer (hud.md footprint 256,151-319,174)
    'cup': (0, 170, 31, 199),                       # stock turbo cup (0,172)-(31,199)
    'gearlever': (270, 178, 305, 197),              # stock gear lever (272,180)-(303,195)
}
SKY = 15

def planar_to_idx(b):
    a = np.frombuffer(b[:32000], '>u2').reshape(200, 20, 4)
    out = np.zeros((200, 320), np.uint8)
    for p in range(4):
        for bit in range(16):
            out[:, bit::16] |= (((a[:, :, p] >> (15 - bit)) & 1).astype(np.uint8) << p)
    return out

def mask_of(*names):
    m = np.zeros((200, 320), bool)
    for n in names:
        x0, y0, x1, y1 = RECTS[n]
        m[y0:y1 + 1, x0:x1 + 1] = True
    return m

def check_frame(new, ref, speech, strip_expect, stock=None):
    """Returns {check: (compared, excluded, [(row, x, got, want) ...first 10])}."""
    res = {}
    # A: rows 65-199 vs the reduced-stock reference
    d = new[65:] != ref[65:]
    res['A rows65-199 vs ref'] = (int(d.size), 0, [(int(y) + 65, int(x), int(new[y + 65, x]), int(ref[y + 65, x])) for y, x in zip(*np.nonzero(d))][:10], int(d.sum()))
    # B: sky
    m = mask_of('msgbox') if speech else np.zeros((200, 320), bool)
    region = np.zeros((200, 320), bool); region[16:65] = True
    chk = region & ~m
    bad = chk & (new != SKY)
    res['B sky rows16-64'] = (int(chk.sum()), int((region & m).sum()), [(int(y), int(x), int(new[y, x]), SKY) for y, x in zip(*np.nonzero(bad))][:10], int(bad.sum()))
    # C: strip
    if strip_expect is not None:
        bad = new[:16] != strip_expect
        res['C strip rows0-15'] = (16 * 320, 0, [(int(y), int(x), int(new[y, x]), int(strip_expect[y, x])) for y, x in zip(*np.nonzero(bad))][:10], int(bad.sum()))
    if stock is not None:
        m = mask_of('speedo', 'cup', 'gearlever')
        region = np.zeros((200, 320), bool); region[85:] = True
        chk = region & ~m
        bad = chk & (new != stock)
        res['D rows85-199 vs stock'] = (int(chk.sum()), int((region & m).sum()), [(int(y), int(x), int(new[y, x]), int(stock[y, x])) for y, x in zip(*np.nonzero(bad))][:10], int(bad.sum()))
    return res

def summarize(allres):
    """allres: list of check_frame results -> table text and an ok flag."""
    tot = {}
    for r in allres:
        for k, (n, ex, ex_l, nbad) in r.items():
            t = tot.setdefault(k, [0, 0, 0, 0])
            t[0] += n; t[1] += ex; t[2] += nbad; t[3] += 1
    lines = []; ok = True
    for k, (n, ex, nbad, nf) in sorted(tot.items()):
        ok &= nbad == 0
        lines.append(f"  {k:26s} frames {nf:4d}  pixels compared {n:10d}  excluded {ex:9d}  differing {nbad:6d}  -> {'IDENTICAL' if nbad == 0 else 'DIFFER'}")
    return "\n".join(lines), ok


# ----------------------------------------------------------------------------------------------------------------------------------- Hatari mode
def _hatari_main():
    import argparse, hashlib, json, time
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import msrabtest as ab
    import msrhudgen
    from msr import Moonshine
    ap = argparse.ArgumentParser(description="masked pixel gate on snapshots (Hatari): candidate vs reference vs stock")
    ap.add_argument('--cand', nargs='+', required=True, help='candidate patch set (live), e.g. hd_stage hd_init hd_clouds mr_edge rd_geom rd_draw rd_init')
    ap.add_argument('--ref', nargs='+', required=True, help='reference patch set, e.g. test_hdref hd_clouds mr_edge rd_geom rd_draw rd_init')
    ap.add_argument('--stock', nargs='*', default=None, help='stock-side patch set for check D (same pixel-identical render patches only; empty = pure stock)')
    ap.add_argument('--snapshots', nargs='*', default=['race_start', 'race_grid', 'race_up', 'race_drive'])
    ap.add_argument('--flips', nargs='*', type=int, default=[10, 40])
    ap.add_argument('--neg', choices=['none', 'nopaint', 'nowipe'], default='none', help='negative control: leave stale pixels (the gate must DIFFER)')
    ap.add_argument('--out', default='work/hud/build/mask')
    a = ap.parse_args()
    ex = {'st': (0x1000, 0x400), 'sh': (0xBCF00, 0x80)}
    bufs = dict(ab.BUFFERS); bufs.update(ex)
    out = ab.GAME / a.out; out.mkdir(parents=True, exist_ok=True)
    def cap(snap, at, names, tag, fl, pokes=()):
        d = out / f"{tag}_{Path(snap).stem}_{at}_{fl}"
        live = ab.live_build(names) if names else None
        if live is not None and pokes:
            live = ab.with_pokes(live, list(pokes), tag + hashlib.md5(' '.join(pokes).encode()).hexdigest()[:6])
        if not (d / 'sh.bin').exists():
            h = Moonshine(snapshot=snap)
            try:
                h.capture_frames(str(d), flip_addr=0xD1CA, at_vbl=at, nth_flip=fl, live=str(live) if live else None, buffers=bufs)
            finally:
                h.close()
        return d
    pokes = []
    if a.neg != 'none':
        names = a.cand
        live = ab.live_build(names); img = live.with_suffix('.img').read_bytes(); spec = json.loads(live.with_suffix('.json').read_text())
        if a.neg == 'nopaint': pokes = ['bcf00=ff', 'bcf40=ff']
        else:
            i = img.index(bytes.fromhex('47e81ea0')); pokes = ['%x=0640' % (spec['img_base'] + i + 2)]
    allres = []; xres = []
    for name in a.snapshots:
        snap = ab.snap_path(name); at = ab.at_vbl_for(snap)
        for fl in a.flips:
            dc = cap(snap, at, a.cand, 'cand' + a.neg, fl, pokes)
            dr = cap(snap, at, a.ref, 'ref', fl)
            ds = cap(snap, at, a.stock, 'stock', fl) if a.stock is not None else None
            st = (dc / 'st.bin').read_bytes(); sh = (dc / 'sh.bin').read_bytes()
            speech = st[0x1ab] != 0
            drawn = int.from_bytes(st[0x8:0xc], 'big')              # $1008 at the flip: the buffer just drawn
            for bn, base in (('b70000', 0x70000), ('b78000', 0x78000)):
                new = planar_to_idx((dc / f'{bn}.bin').read_bytes())
                ref = planar_to_idx((dr / f'{bn}.bin').read_bytes())
                shb = sh[0x40:0x80] if base == 0x78000 else sh[0:0x40]
                exp = msrhudgen.expected_strip(shb) if shb[0] else None
                r = check_frame(new, ref, speech, exp, stock=planar_to_idx((ds / f'{bn}.bin').read_bytes()) if ds else None)
                allres.append(r)
                line = ', '.join(f"{k.split()[0]}:{v[3]}" for k, v in r.items())
                print(f"{name:11s} flip {fl:3d} {bn} (drawn={'yes' if base == drawn else 'no '}) speech={'Y' if speech else 'n'} differing pixels {line}", flush=True)
                for k, v in r.items():
                    if v[3]: print('      first', k, v[2][:4])
    txt, ok = summarize(allres)
    print(f"candidate: {' '.join(a.cand)}   reference: {' '.join(a.ref)}   negative control: {a.neg}")
    print(txt)
    print('RESULT:', 'IDENTICAL' if ok else 'DIFFER')
    sys.exit(0 if ok else 1)

if __name__ == '__main__':
    _hatari_main()
