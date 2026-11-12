"""Pixel identity in JOYSTICK mode, no pad pressed: display set (26 patches) vs display set + jag_*, both with $eb76 forced to J mode.
Sequential (one Hatari at a time). usage: t_abj.py [flips]"""
import sys, json, hashlib, subprocess
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from jt import *
import abtest
from pathlib import Path

def one(snap, at, live, out, flips):
    # same as abtest.one, but Hatari's default real-joystick port 1 reads as a stuck 'down' without a stick (the phantom joystick): --joy1 none
    h = Hatari(snapshot=snap, extra=['--joy1', 'none'])
    try:
        h.capture_frames(str(out), live=live, at_vbl=at, nth_flip=flips)
        f = h.fps(1000)
    finally:
        h.close()
    md = {n: hashlib.md5((Path(out) / n).read_bytes()[:abtest.VISIBLE]).hexdigest() for n in ('buf60000.bin', 'buf70000.bin')}
    return {'fps': f['fps'], 'flips': f['flips'], 'md5': md}
flips = int(sys.argv[1]) if len(sys.argv) > 1 else 10
disp = [n for n in names() if n.startswith(('p4_', 'p7_'))]
print(len(disp), 'display patches')
def prefix(tag, only):
    p = build_live(only, tag)
    j = json.loads(Path(p + '.json').read_text())
    j['sites'].append({'addr': 0xeb76, 'orig': '', 'new': 'ffff00000000', 'name': 'J mode'})
    Path(p + '.json').write_text(json.dumps(j))
    return p
base = prefix('abj_base', disp)
jag = prefix('abj_jag', disp + ['jag_poll', 'jag_dir', 'jag_btn'])
ok = True
for snap in ['work/snapshots/1mb_ingame_walking.sav', 'work/snapshots/1mb_ingame_foot.sav']:
    at = abtest.at_vbl_for(str(G / snap))
    name = Path(snap).stem
    out = G / 'build' / 'ab' / 'abj'
    b = one(str(G / snap), at, base, out / f'{name}_base_{flips}', flips)
    p = one(str(G / snap), at, jag, out / f'{name}_jag_{flips}', flips)
    same = b['md5'] == p['md5']
    ok &= same
    print(f"{name} (J mode, no pad, --joy1 none, flips {flips}): pixels {'IDENTICAL' if same else 'DIFFER'}  md5 base {b['md5']['buf60000.bin'][:8]}/{b['md5']['buf70000.bin'][:8]}  jag {p['md5']['buf60000.bin'][:8]}/{p['md5']['buf70000.bin'][:8]}  fps {b['fps']:.1f} -> {p['fps']:.1f}", flush=True)
sys.exit(0 if ok else 1)
