#!/usr/bin/env python3
"""vcmp.py A B [--off N] [--ign ADDR-ADDR ...] : per-tick diff of two vgate pickles (A tick k+off vs B sample k)."""
import pickle, sys, argparse, collections
VARS = {0x66e6:'X',0x66ea:'Y',0x6742:'hdg',0x6746:'bank',0x674a:'pitch',0x674e:'lean',0x6294:'hdg294',0x764a:'hdg764a',0x764c:'alt',0x6750:'thr',0x6772:'spd',
        0x6220:'type',0xeb8c:'clock',0x6290:'cd',0x66e2:'66e2',0x66e4:'66e4',0x6888:'6888',0x688e:'688e',0x7680:'7680',0x676e:'676e',0x6740:'6740',0x6752:'6752',0x6756:'6756',0x675a:'675a',
        0x6766:'6766',0x6768:'6768',0x6288:'6288',0x7646:'7646',0x7648:'7648',0x7652:'7652',0x7654:'7654',0x66ee:'sv66ee',0x66f2:'sv66f2',0x66fe:'sv66fe',0x670a:'cell',0x6fb6:'inX',0x6fba:'inY',
        0x6754:'6754',0x675c:'675c',0x676a:'676a',0x676c:'676c',0x6776:'6776',0x6774:'6774',0x6892:'6892',0xf984:'f984',0x34936:'h36',0x34938:'h38',0x3493a:'h3a',0x6746:'bank'}
def name(a):
    best = None
    for k, v in VARS.items():
        if k <= a < k + 2: return v
    return ''
def ranges(addrs):
    out = []; 
    for a in sorted(addrs):
        if out and a <= out[-1][1] + 2: out[-1][1] = a
        else: out.append([a, a])
    return out
def main():
    ap = argparse.ArgumentParser(); ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('--off', type=int, default=0)
    ap.add_argument('--ign', nargs='*', default=[]); ap.add_argument('--show', type=int, default=6); ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    A = pickle.load(open(f'/tmp/vg/{a.a}.pkl', 'rb')); B = pickle.load(open(f'/tmp/vg/{a.b}.pkl', 'rb'))
    ign = []
    for n in range(30): ign.append((0x3532 + n*0x42 + 0x36, 0x3532 + n*0x42 + 0x3b))   # NPC render-animation words (+$36 +$38 +$3a): advanced once per RENDER by $1ce38, not game state
    for s in a.ign:
        lo, hi = s.split('-'); ign.append((int(lo, 16), int(hi, 16)))
    n = min(len(A) - a.off, len(B))
    tot = collections.Counter(); first = {}
    badticks = 0
    for k in range(n):
        ra, rb = A[k + a.off], B[k]
        d = [x for x in ra if x != 'open' and x in rb and ra[x] != rb[x] and not any(lo <= x <= hi for lo, hi in ign)]
        if d: badticks += 1
        for r in ranges(d):
            key = (r[0], r[1])
            tot[key] += 1; first.setdefault(key, k)
        if d and not a.quiet and k < a.show:
            print(f'tick {k+1}: ' + ' '.join(f'{r[0]:x}-{r[1]:x}{"("+name(r[0])+")" if name(r[0]) else ""}' for r in ranges(d)[:14]))
    print(f'{a.a}[+{a.off}] vs {a.b}: ticks compared {n}, ticks with any diff {badticks}')
    for key, c in sorted(tot.items()):
        ra, rb = A[first[key] + a.off], B[first[key]]
        print(f'  {key[0]:x}-{key[1]:x} {name(key[0])}: {c} ticks, first at tick {first[key]+1}: A={bytes(ra[x] for x in range(key[0],key[1]+1)).hex()} B={bytes(rb[x] for x in range(key[0],key[1]+1)).hex()}')
main()
