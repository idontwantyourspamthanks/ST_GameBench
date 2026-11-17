"""MSRMxFast model helpers: live images from the PRIVATE patch tool, the Unicorn exact model (work/extrap/emu.py)."""
import sys, os, json, subprocess
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
HERE = GAME + '/work/mxfast'
sys.path.insert(0, GAME + '/work/extrap'); sys.path.insert(0, HERE)
sys.path.insert(0, GAME + '/tools')
from emu import Emu
PRIV = HERE + '/msrpatch_priv.py'
def default_names():
    r = subprocess.run([sys.executable, PRIV, 'list'], capture_output=True, text=True, cwd=GAME)
    names = []
    for ln in r.stdout.splitlines():
        p = ln.split()
        if len(p) >= 3 and p[1] == 'yes' and not p[2].startswith('(') and p[2].startswith('$'):
            names.append(p[0])
    return names
PACER = ("mt_clock", "mt_pre", "mx_pre", "mx_sync", "mt_sync", "mf_sync", "mf_pre", "mg_sync", "mg_pace")
def sets():
    d = default_names()
    fin = [n for n in d if n not in PACER and n != 'pp_bigram_cache']
    return {'X': fin + ['mt_clock', 'mt_pre', 'mx_pre', 'mx_sync'],
            'M': fin + ['mt_clock', 'mt_pre', 'mf_pre', 'mf_sync'],
            'G': fin + ['mt_clock', 'mt_pre', 'mg_sync', 'mg_pace'],
            'T': fin + ['mt_clock', 'mt_pre', 'mt_sync'],
            'F': fin}
def live_build(v, tag=None, names=None):
    names = names or sets()[v]
    out = f"work/mxfast/live/{tag or v}"
    r = subprocess.run([sys.executable, PRIV, 'live', '--only', *names, '--out', out], capture_output=True, text=True, cwd=GAME)
    if r.returncode: raise SystemExit(r.stdout + r.stderr)
    return GAME + '/' + out
def apply_live(e, prefix):
    spec = json.load(open(prefix + '.json')); e.write(spec['img_base'], open(prefix + '.img', 'rb').read())
    for s in spec['sites']: e.write(s['addr'], bytes.fromhex(s['new']))
def schedule(p, kind):
    if kind == 'up': return 0x01
    if kind == 'zig': return [0x01, 0x05, 0x01, 0x09][(p // 15) % 4]
    if kind == 'left': return 0x05
    if kind == 'right': return 0x09
    if kind == 'rand':
        x = (p * 2654435761 + 12345) & 0xffffffff
        return [0x01, 0x05, 0x09, 0x01, 0x05, 0x09, 0x01, 0x02][(x >> 13) & 7]
    if kind == 'hard': return 0x05 if (p // 25) % 2 == 0 else 0x09
    return None
DUMPS = {'start': GAME + '/work/extrap/h_start_7a88.bin', 'drive': GAME + '/work/extrap/h_drive_7a88.bin', 'up': GAME + '/work/extrap/h_up_7a88.bin', 'grid': GAME + '/work/extrap/h_grid_7a88.bin'}
import re, tempfile
def symbols(patchfile):
    """label -> address (global labels and equates) of a patch source, all segments in one vasm run"""
    src = open(patchfile).read()
    with tempfile.TemporaryDirectory() as td:
        open(td + '/s.s', 'w').write("IB\tequ\t$b2700\nTABLE\tequ\t$b7000\n" + src)
        r = subprocess.run(['vasmm68k_mot', '-Fbin', '-m68000', '-quiet', '-L', td + '/l.txt', '-o', td + '/o.bin', td + '/s.s'], capture_output=True, text=True)
        if r.returncode: raise SystemExit(r.stderr)
        lst = open(td + '/l.txt').read()
    sec = lst.split('Symbols by name:')[-1]
    return {m.group(1): int(m.group(2), 16) for m in re.finditer(r'^(\S+)\s+[AE]:([0-9A-Fa-f]+)', sec, re.M)}
DUMPS.update({f'L{i}': GAME + f'/work/int/mx/dumps/L{i}.bin' for i in range(15)})
def labelmap(patchfile):
    """[(addr, 'global.local')] for every code label of a patch source (vasm listing), sorted by address."""
    src = open(patchfile).read()
    with tempfile.TemporaryDirectory() as td:
        open(td + '/s.s', 'w').write("IB\tequ\t$b2700\nTABLE\tequ\t$b7000\n" + src)
        r = subprocess.run(['vasmm68k_mot', '-Fbin', '-m68000', '-quiet', '-L', td + '/l.txt', '-o', td + '/o.bin', td + '/s.s'], capture_output=True, text=True)
        if r.returncode: raise SystemExit(r.stderr)
        lst = open(td + '/l.txt').read().split('Symbols by name:')[0]
    out = []; glob = ''; pend = []
    for ln in lst.splitlines():
        ma = re.match(r'^\S+:([0-9A-F]{8}) ', ln)
        ml = re.search(r'\t\s*\d+:\s*([A-Za-z_.][A-Za-z0-9_.]*):?(?:\s|$)', ln)
        lab = None
        if ml and (ml.group(0).strip().endswith(':') or re.match(r'\s*\d+:\s*[A-Za-z_.][A-Za-z0-9_.]*:', ln[ln.index('\t'):])):
            lab = ml.group(1)
        if lab:
            full = lab if not lab.startswith('.') else glob + lab
            if not lab.startswith('.'): glob = lab
            pend.append(full)
        if ma and pend and not re.match(r'^\S+:[0-9A-F]{8} [0-9A-F]+\t\s*\d*:?\s*$', ln) :
            a = int(ma.group(1), 16)
            for p in pend: out.append((a, p))
            pend = []
    return sorted(set(out))
