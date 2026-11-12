"""RAM diff at the capture point, J mode forced, base vs jag. usage: t_diff.py snapshot_name flips"""
import sys, json, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from jt import *
import abtest
snapn = sys.argv[1]; flips = int(sys.argv[2])
disp = [n for n in names() if n.startswith(('p4_', 'p7_'))]
def prefix(tag, only):
    p = build_live(only, tag)
    j = json.loads(Path(p + '.json').read_text())
    j['sites'].append({'addr': 0xeb76, 'orig': '', 'new': 'ffff00000000', 'name': 'J mode'})
    Path(p + '.json').write_text(json.dumps(j))
    return p
def run(tag, pre, snap, at):
    h = Hatari(snapshot=snap)
    try:
        od = G / 'build' / 'ab' / 'diff' / tag; od.mkdir(parents=True, exist_ok=True)
        cap = h.R / 'cap.txt'
        cap.write_text(f"savebin {od}/ram.bin 0 $80000\n")
        spec = json.loads(Path(pre + '.json').read_text())
        cmds = [f"loadbin {Path(pre + '.img').resolve()} ${spec['img_base']:x}"]
        for s in spec['sites']:
            cmds.append(f"w ${s['addr']:x} " + ' '.join(f"${b:02x}" for b in bytes.fromhex(s['new'])))
        cmds.append(f"b pc = ${h.FLIP:x} :{flips} :trace :once :file {cap}")
        app = h.R / 'apply.txt'; app.write_text('\n'.join(cmds) + '\n')
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${h.FLIP:x} :trace :once :file {app}")
        t = time.time()
        while not (od / 'ram.bin').exists() or len(h._logtext()[start:].split('Removed CPU breakpoint')) < 3:
            if time.time() - t > 300: raise TimeoutError
            time.sleep(0.5)
        time.sleep(1)
    finally:
        h.close()
    return (od / 'ram.bin').read_bytes()
base = prefix('abj_base', disp)
jag = prefix('abj_jag', disp + ['jag_poll', 'jag_dir', 'jag_btn'])
snap = str(G / 'work/snapshots' / snapn)
at = abtest.at_vbl_for(snap)
a = run('base', base, snap, at); b = run('jag', jag, snap, at)
diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i] and not (0xb3000 <= i < 0xbb000) and not (0x60000 <= i < 0x80000)]
print(len(diffs), 'differing bytes outside payload and screens')
# group into ranges
rg = []
for i in diffs:
    if rg and i - rg[-1][1] <= 8: rg[-1][1] = i
    else: rg.append([i, i])
for lo, hi in rg[:60]:
    print(f'${lo:05x}-${hi:05x}: base {a[lo:hi+1][:16].hex()}  jag {b[lo:hi+1][:16].hex()}')
