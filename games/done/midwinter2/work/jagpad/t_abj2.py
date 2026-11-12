"""determinism of the J-mode capture: base vs base (second run), jag vs jag"""
import sys, json
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from jt import *
import abtest
disp = [n for n in names() if n.startswith(('p4_', 'p7_'))]
def prefix(tag, only):
    p = build_live(only, tag)
    j = json.loads(Path(p + '.json').read_text())
    j['sites'].append({'addr': 0xeb76, 'orig': '', 'new': 'ffff00000000', 'name': 'J mode'})
    Path(p + '.json').write_text(json.dumps(j))
    return p
base = prefix('abj_base', disp)
jag = prefix('abj_jag', disp + ['jag_poll', 'jag_dir', 'jag_btn'])
snap = str(G / 'work/snapshots/1mb_ingame_walking.sav')
at = abtest.at_vbl_for(snap)
out = G / 'build' / 'ab' / 'abj2'
for tag, pre in (('base1', base), ('base2', base), ('jag1', jag), ('jag2', jag)):
    r = abtest.one(snap, at, pre, out / tag, 10)
    print(tag, r['md5']['buf60000.bin'][:8], r['md5']['buf70000.bin'][:8], flush=True)
