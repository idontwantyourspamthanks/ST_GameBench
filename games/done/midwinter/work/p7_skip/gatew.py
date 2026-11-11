#!/usr/bin/env python3
"""gatew.py: mw1ab-style A/B gate (same captures) that reports the 3D window (rows 51..181) separately from the HUD rows.
    gatew.py --only <set> --base <set> --snapshot stand walk ... --flips 10 40 100 [--pre 'w $addr $xx..'] [--no-fps]
Window = rows 51..181 of each of the three buffers (what the render writes); HUD = everything else of the visible 32000 B.
Exit 0 when the window is identical in all three buffers at every point."""
import argparse, sys, hashlib, json, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/done/midwinter/tools')
import mw1ab
from mw1ab import WORK, BUFS, snap_path, at_vbl_for, make_live, tag_for, one as _one
import mw1ab
from mw1 import MW1
STATE = {'s12c': (0x12c60, 0x40), 's171': (0x171f0, 0x30), 'slot': (0x1cd7e, 0xb0), 's3b': (0xb3700, 0x40)}
ALL = {**BUFS, **STATE}

POKEAT = []        # [(K, [cmd...])] debugger commands executed at the K-th flip after the apply (K >= 2)

def one(snap, at, live, out, flips, fps, cache=False):
    """capture_frames (stharness) plus extra breakpoints POKEAT armed with the live set; also saves the state words STATE."""
    h = MW1(snapshot=str(snap))
    try:
        od = Path(out).resolve(); od.mkdir(parents=True, exist_ok=True)
        cap = h.R / 'cap.txt'
        cap.write_text("".join(f"savebin {od}/{n}.bin ${a_:x} ${ln:x}\n" for n, (a_, ln) in ALL.items()))
        spec = json.loads(Path(live + '.json').read_text())
        cmds = [f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}"]
        for st in spec['sites']:
            raw = bytes.fromhex(st['new'])
            for o in range(0, len(raw), 40):
                cmds.append(f"w ${st['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
        for k, cl in POKEAT:
            pf = h.R / f'poke{k}.txt'; pf.write_text("\n".join(cl) + "\n")
            cmds.append(f"b pc = $bd9a :{k} :trace :once :file {pf}")
        cmds.append(f"b pc = $bd9a :{flips} :trace :once :file {cap}")
        app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
        if h.vbl() >= at: raise ValueError('at_vbl passed')
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = $bd9a :trace :once :file {app}")
        last = od / f"{list(ALL)[-1]}.bin"
        t = time.time()
        while not last.exists():
            if time.time() - t > 600: raise TimeoutError('capture')
            time.sleep(0.5)
        time.sleep(1)
        f = mw1ab.flip_cycles(h, 1000) if fps else {'cyc': 0.0, 'flips': 0}
    finally:
        h.close()
    return {'flips': f['flips'], 'cyc': f['cyc']}

def diff(a, b):
    out = {}
    for n in BUFS:
        x = np.fromfile(a / f'{n}.bin', dtype=np.uint8)[:32000].reshape(200, 160)
        y = np.fromfile(b / f'{n}.bin', dtype=np.uint8)[:32000].reshape(200, 160)
        w = int((x[51:182] != y[51:182]).sum())
        hrows = sorted({int(r) for r in np.nonzero((x != y).any(axis=1))[0] if not 51 <= r < 182})
        out[n] = (w, int((x != y).sum()) - w, hrows)
    st = {}
    for n in STATE:
        x = (a / f'{n}.bin').read_bytes(); y = (b / f'{n}.bin').read_bytes()
        dd = [i for i in range(len(x)) if x[i] != y[i]]
        if dd: st[n] = [hex(i) for i in dd[:6]]
    out['state'] = st
    return out

def with_pokes(live, poke, tag):
    import json, shutil
    src = Path(live)
    dst = src.parent / ('live' + tag.replace('/', '_') + '_p')
    shutil.copy(str(src) + '.img', str(dst) + '.img')
    spec = json.loads(Path(str(src) + '.json').read_text())
    for cmd in [c.strip() for c in poke.split(';') if c.strip()]:
        t = cmd.split()
        assert t[0] == 'w'
        raw = bytes(int(x.lstrip('$'), 16) for x in t[2:])
        spec['sites'].append({'addr': int(t[1].lstrip('$'), 16), 'orig': raw.hex(), 'new': raw.hex(), 'name': 'poke'})
    Path(str(dst) + '.json').write_text(json.dumps(spec, indent=1))
    return str(dst)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='+', required=True); ap.add_argument('--base', nargs='*', default=[])
    ap.add_argument('--snapshot', nargs='*', default=['stand']); ap.add_argument('--flips', nargs='*', type=int, default=[10, 40])
    ap.add_argument('--no-fps', action='store_true')
    ap.add_argument('--poke', default='', help="debugger commands applied with the live set, e.g. 'w $2baec $ff $ff'")
    ap.add_argument('--soon', action='store_true', help='apply right after the restore (the moving phase of walk/turn) instead of +300 VBL')
    ap.add_argument('--tag', default='')
    ap.add_argument('--poke-at', action='append', default=[], help="K:cmd;cmd  run debugger commands at the K-th flip after the apply")
    a = ap.parse_args()
    for pa in a.poke_at:
        kk, cc = pa.split(':', 1); POKEAT.append((int(kk), [c.strip() for c in cc.split(';') if c.strip()]))
    WORK.mkdir(exist_ok=True)
    btag, ptag = tag_for(a.base) + a.tag, tag_for(a.only) + a.tag
    blive, plive = make_live(a.base), make_live(a.only)
    if a.poke or a.tag:
        blive, plive = [with_pokes(l, a.poke, a.tag) for l in (blive, plive)]
    ok = True
    for sn in a.snapshot:
        sp = snap_path(sn); at = at_vbl_for(sp) - (280 if a.soon else 0)
        for i, n in enumerate(a.flips):
            fps = not a.no_fps and i == 0
            bd = WORK / btag / f'{sn}_{at}_{n}'; pd = WORK / ptag / f'{sn}_{at}_{n}'
            with ThreadPoolExecutor(2) as ex:
                fb = ex.submit(one, sp, at, blive, bd, n, fps, True); fp = ex.submit(one, sp, at, plive, pd, n, fps)
                b, p = fb.result(), fp.result()
            d = diff(bd, pd)
            st = d.pop('state'); wsame = all(v[0] == 0 for v in d.values())
            ok &= wsame
            hud = {k: (v[1], v[2][:4] + ['..'] + v[2][-2:] if len(v[2]) > 6 else v[2]) for k, v in d.items()}
            sp_s = (f"; flips/1000VBL {b['flips']} -> {p['flips']}; cycles/frame {b['cyc']:.0f} -> {p['cyc']:.0f} "
                    f"({100 * (p['cyc'] - b['cyc']) / b['cyc']:+.1f} %)") if fps else ''
            print(f"{sn} --flips {n}: window {'IDENTICAL' if wsame else 'DIFFER ' + str({k: v[0] for k, v in d.items()})}; "
                  f"HUD bytes differing (buffer: n, rows) {hud}; state-word offsets that differ {st}{sp_s}", flush=True)
    print('WINDOW ALL IDENTICAL' if ok else 'WINDOW MISMATCH')
    sys.exit(0 if ok else 1)
main()
