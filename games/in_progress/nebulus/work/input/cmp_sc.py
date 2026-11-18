"""Compare scripted runs per game loop: variable block diff (same loop index) + shifted player compare + framebuffer pixel compare."""
import sys, re
from pathlib import Path
from scripted2 import parse_flips, W
PL_LO, PL_HI = 0x33a16, 0x33a24          # player x,y,..,state,step,pose
def load(tag):
    txt = (W / 'sc' / tag / 'log.txt').read_text()
    fl = parse_flips(txt)
    i0 = next(i for i, f in enumerate(fl) if f['timer'] != (32, 0, 0))
    return fl[i0:], txt
def w(f, a): o = a - 0x33900; return int.from_bytes(f['blk'][o:o + 2], 'big')
def player(f): return tuple(w(f, a) for a in range(PL_LO, PL_HI, 2))
def nonplayer(f):
    b = bytearray(f['blk'])
    for a in list(range(PL_LO, PL_HI)) + list(range(0x338f0, 0x338fc)) + list(range(0x39f00, 0x39f00)):
        if 0 <= a - 0x33900 < len(b): b[a - 0x33900] = 0
    return bytes(b)
def frames(tag, txt):
    """{event_index: pixel bytes of the displayed buffer} from fb_k_a/b + m $38758 lines."""
    d = W / 'sc' / tag
    bases = re.findall(r'00038758:\s+([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2})', txt, re.I)
    caps = sorted(int(p.stem.split('_')[1]) for p in d.glob('fb_*_a.bin'))
    out = {}
    for k, b in zip(caps, bases):
        addr = int(''.join(b), 16)
        out[k] = (d / f'fb_{k}_{"b" if addr == 0x78000 else "a"}.bin').read_bytes()
    return out
def pix_diff(a, b):
    n = sum(1 for x, y in zip(a, b) if x != y)
    if not n: return 0, None
    rows = [i // 160 for i, (x, y) in enumerate(zip(a, b)) if x != y]
    return n, (min(rows), max(rows))
def main(stock, other, shift_ok=True):
    S, st = load(stock); P, pt = load(other)
    n = min(len(S), len(P)) - 2
    print(f'== {other} vs {stock}: {len(S)} / {len(P)} loops after timer start (compare first {n})')
    npd = [j for j in range(n) if nonplayer(S[j]) != nonplayer(P[j])]
    print('loops where the non-player block (creatures, timer, flags, energy, ...) differs at the SAME index:', npd[:40], f'({len(npd)})')
    for j in npd[:3]:
        a, b = nonplayer(S[j]), nonplayer(P[j])
        print('   loop', j, 'diff addrs', [hex(0x33900 + i) for i in range(len(a)) if a[i] != b[i]][:12])
    pd = [j for j in range(n) if player(S[j]) != player(P[j])]
    print('loops where the player vars differ at the same index:', pd[:60], f'({len(pd)})')
    sh = [j for j in pd if j + 1 < len(S) and player(P[j]) == player(S[j + 1])]
    print('  of those, patched[j] == stock[j+1] (exactly one loop earlier):', len(sh), 'of', len(pd), ' not explained:', [j for j in pd if j not in sh][:30])
    return S, P
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])

def creature_sim(f):
    """creature slots 0-3 (+ shot slot 4): X,Y,frame,counter,state,speed,aux,target; plus level/energy/timer/score-ish words not derived from the player."""
    out = []
    for fld in (0x00, 0x0c, 0x18, 0x3c, 0x48, 0x54, 0x60, 0x6c):
        for slot in range(4):
            out.append(w(f, 0x33944 + fld + 2 * slot))
    out += [w(f, 0x3390c), w(f, 0x3392c), w(f, 0x3393c), w(f, 0x33938)]    # tower, energy, spawn scan pointer, timer gate
    out += list(f['timer'])
    return tuple(out)
def main2(stock, other):
    S, _ = load(stock); P, _ = load(other)
    n = min(len(S), len(P)) - 2
    d = [j for j in range(n) if creature_sim(S[j]) != creature_sim(P[j])]
    print(f'creature/timer/energy simulation state differs at the same loop index in {len(d)} of {n} loops', d[:30])
if __name__ == '__main__' and len(sys.argv) > 3: main2(sys.argv[1], sys.argv[2])
