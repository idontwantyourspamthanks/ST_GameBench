"""prof.py snap live vbls [--pre ..]: apply live, settle, then `profile` over `vbls` VBL; print cycles in the p7_skip blob, the total and
the passes (NSKIP+NREND counter deltas) so cycles per skipped pass can be derived."""
import sys, time, json, argparse, struct
from pathlib import Path
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/midwinter/tools']
from mw1 import MW1
ap = argparse.ArgumentParser(); ap.add_argument('snap'); ap.add_argument('live'); ap.add_argument('vbls', type=int); ap.add_argument('--pre', default=''); ap.add_argument('--settle', type=int, default=330)
a = ap.parse_args()
snap = a.snap if '/' in a.snap else f'../snapshots/1mb_ski_{a.snap}.sav'
h = MW1(snapshot=snap)
def counters():
    b = h.peek(0xb6000, 64); l = lambda o: struct.unpack('>I', b[o:o+4])[0]
    return dict(NSKIP=l(16), NREND=l(20), NCHG=l(24))
try:
    spec = json.loads(Path(a.live + '.json').read_text())
    cmds = [f"loadbin {Path(a.live + '.img').resolve()} ${spec['img_base']:x}"]
    for s in spec['sites']:
        raw = bytes.fromhex(s['new'])
        for o in range(0, len(raw), 40):
            cmds.append(f"w ${s['addr']+o:x} " + " ".join(f"${b:02x}" for b in raw[o:o+40]))
    for p in a.pre.split(';'):
        if p.strip(): cmds.append(p.strip())
    app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
    v = h.vbl(); h.debug("b all", 0.3)
    h.cmd(f"hatari-debug b VBL > {v+20} && pc = $bd9a :trace :once :file {app}")
    time.sleep(3)
    while h.vbl() < v + a.settle: time.sleep(0.5)
    c0 = counters()
    prof = h.profile(a.vbls)
    c1 = counters()
    tot = sum(c for _, c in prof)
    blob = sum(c for ad, c in prof if 0xb5800 <= ad < 0xb6000)
    passes = (c1['NSKIP'] - c0['NSKIP']) + (c1['NREND'] - c0['NREND'])
    sk = c1['NSKIP'] - c0['NSKIP']
    print(f'profile over ~{a.vbls} VBL: total {tot} cycles, blob {blob}, passes {passes} (skip {sk}, render {c1["NREND"]-c0["NREND"]}), changes {c1["NCHG"]-c0["NCHG"]}')
    # top pages
    pages = {}
    for ad, c in prof: pages[ad >> 12] = pages.get(ad >> 12, 0) + c
    print('top 4K pages:', [(hex(p << 12), c) for p, c in sorted(pages.items(), key=lambda x: -x[1])[:10]])
    hook = {}
    for ad, c in prof:
        if 0xb5800 <= ad < 0xb6000: hook[ad] = c
    print('hook cycles', blob, 'per pass', blob / max(passes, 1))
finally:
    h.close()
