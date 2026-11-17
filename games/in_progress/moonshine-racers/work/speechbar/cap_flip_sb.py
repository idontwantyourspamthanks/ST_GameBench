"""Hatari: the strip (rows 16-41) of the buffer drawn for EVERY flip ($d1ca: main frames and extra frames), with the sb shadows and the ticker state, then the model check.
python3 cap_flip_sb.py SNAP SET MHZ NPASS OUT.json [steer=zig|up|none] [zigk=K] [hz60]
SET: S/F (tick OFF), TS/T (tick ON), XS/X (tick ON + extras).  Checks (printed): per flip the strip == model(shadow of the drawn buffer); shadow == ticker state;
the DISPLAYED sequence (drawn buffers in flip order) is monotone per message (characters never decrease, no old text after the erase); extra frames identified by a repeated $100e."""
import sys, json, re, time, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar')
from sblib import *
import msrabtest as ab
from msr import Moonshine
from sbart import messages, draw_strip, planar_to_idx
import numpy as np
snap, setn, mhz, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
opt = {a.split('=')[0]: a.split('=', 1)[1] for a in sys.argv[6:] if '=' in a}
steer = opt.get('steer', 'up'); KS = int(opt['zigk']) if 'zigk' in opt else None
vals, per = ({'zig': ([1, 5, 1, 9], 15), 'up': ([1], 1)}.get(steer) or (None, 0))
live = None if setn == 'A' else live_build_sb(SETS[setn], setn)
h = Moonshine(snapshot=ab.snap_path(snap)); R = h.R
body = "e VBL\nm $100e 2\nm $b8f38 4\nm $11ab 1\nm $11a8 2\nm $11a4 2\nm $ba900 32\n"
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    if mhz: h.set_cpuclock(mhz)
    time.sleep(0.4); h.debug('b all', 0.3)
    (R / 'fa.txt').write_text(body + "m $70a00 4160\n"); (R / 'fb.txt').write_text(body + "m $78a00 4160\n")
    if vals:
        K0 = h.peekw(0x100e) + 2
        for K in range(0, 4000):
            (R / f'z_{K}.txt').write_text(f"w $6105 ${vals[(K // per) % len(vals)]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {R}/z_{K + 1}.txt\n")
    n0 = len(h._logtext())
    h.cmd("hatari-debug b pc = $d1ca && ($1008).l = $70000 :trace :file " + str(R / 'fa.txt')); time.sleep(0.2)
    h.cmd("hatari-debug b pc = $d1ca && ($1008).l = $78000 :trace :file " + str(R / 'fb.txt')); time.sleep(0.2)
    if vals:
        h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${K0:x} :trace :once :file {R}/z_{K0}.txt"); time.sleep(0.2)
        h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = 1 :trace :file {R}/z_1.txt")
    t0 = time.time()
    while h._logtext()[n0:].count('> e VBL') < int(npass * (2.7 if setn.startswith('X') and mhz >= 16 else 1.4)) and time.time() - t0 < 3400: time.sleep(3)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
texts = {a: t for a, t in messages()}
def mem(sg):
    g = {}
    for ln in sg.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return g
frames = []
for sg in log.split('> e VBL')[1:]:
    g = mem(sg)
    nums = re.findall(r'#(\d+) \(dec\)', sg)
    if 0x70a00 not in g and 0x78a00 not in g: continue
    base = 0x70a00 if 0x70a00 in g else 0x78a00
    strip = bytes(g[base + i] for i in range(4160))
    w = lambda a: (g[a] << 8) | g[a + 1]
    frames.append(dict(vbl=int(nums[0]), p=w(0x100e), nf=int.from_bytes(bytes(g[0xb8f38 + i] for i in range(4)), 'big'), t11ab=g[0x11ab], M=w(0x11a8), tp=w(0x11a4),
                       buf=0 if base == 0x70a00 else 1, sb=bytes(g[0xba900 + i] for i in range(32)), strip=strip))
# main = first flip of a pass counter value, extra = repeated $100e
seen = set(); bad = collections = 0
res = dict(frames=len(frames), main=0, extra=0, strip_bad=0, strip_px_bad=0, tick_bad=0, nonmono=0, unknown=0, flip_gap=[])
lastM = None; lastn = -1; lastvbl = None
for f in frames:
    ex = f['p'] in seen; seen.add(f['p'])
    res['extra' if ex else 'main'] += 1
    BM, BN, FI = struct.unpack('>HHH', f['sb'][16 * f['buf']:16 * f['buf'] + 6])
    e = np.zeros((200, 320), np.uint8)
    if BM and BM not in texts: res['unknown'] += 1
    draw_strip(e, texts.get(BM) if BM else None, BN, FI if FI else None)
    a = np.frombuffer(f['strip'], '>u2').reshape(26, 20, 4)
    img = np.zeros((26, 320), np.uint8)
    for p in range(4):
        for bit in range(16): img[:, bit::16] |= (((a[:, :, p] >> (15 - bit)) & 1).astype(np.uint8) << p)
    nb = int((e[16:42] != img).sum())
    if nb: res['strip_bad'] += 1; res['strip_px_bad'] += nb
    n = (f['tp'] - f['M'] - 4) & 0xffff
    if not ((BM, BN) == ((f['M'], n) if f['t11ab'] else (0, 0)) and ((FI != 0) == bool(f['t11ab']))): res['tick_bad'] += 1
    if BM:
        if BM == lastM and BN < lastn: res['nonmono'] += 1
        lastM, lastn = BM, BN
    else: lastM, lastn = None, -1
    if lastvbl is not None: res['flip_gap'].append(f['vbl'] - lastvbl)
    lastvbl = f['vbl']
speech = sum(1 for f in frames if f['t11ab'])
print(f"{setn} {snap} {mhz}MHz {steer}: flips {res['frames']} (main {res['main']}, extra {res['extra']}), flips with a message {speech}; strip != model in {res['strip_bad']} flips ({res['strip_px_bad']} px); shadow != ticker state in {res['tick_bad']}; non-monotone {res['nonmono']}; unknown message {res['unknown']}")
res['flip_gap'] = None
json.dump(dict(res=res, frames=[dict(vbl=f['vbl'], p=f['p'], nf=f['nf'], t11ab=f['t11ab'], buf=f['buf'], M=f['M'], tp=f['tp']) for f in frames]), open(out, 'w'))
