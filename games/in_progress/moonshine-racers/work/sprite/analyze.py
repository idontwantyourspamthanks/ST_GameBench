import sys, struct, collections
sys.path.insert(0, 'work/sprite')
from parse import parse, CYC
DUMP = open('work/dumps/ram_race_start.bin', 'rb').read()
W = lambda a: struct.unpack('>H', DUMP[a:a + 2])[0]
L = lambda a: struct.unpack('>I', DUMP[a:a + 4])[0]
S = lambda x: x - 65536 if x >= 32768 else x
ISR_IN = {0xd11e, 0xd616, 0xcfb4}
ISR_OUT = {0xd136, 0xd672, 0xd68e, 0xd6ba, 0xd6f8, 0xd026}


def frames(path):
    ev, best = parse(path)
    out = []; cur = None; depth = 0; tin = 0; isr = 0
    for e in ev:
        pc = e['pc']
        if pc in ISR_IN:
            if depth == 0: tin = e['t']
            depth += 1; continue
        if pc in ISR_OUT:
            depth = max(0, depth - 1)
            if depth == 0 and tin: isr += e['t'] - tin; tin = 0
            continue
        if pc == 0xe406: depth = 0; tin = 0
        if depth > 0 and cur is None: continue
        e['isr'] = isr   # cumulative ISR time up to this event (only meaningful if depth == 0)
        e['depth'] = depth
        if pc == 0xe406:
            cur = {'ev': [e], 'frame': (e['mem'][0] << 8) | e['mem'][1]}
        elif cur is not None:
            cur['ev'].append(e)
            if pc == 0xe4fc:
                out.append(cur); cur = None
    return out


def slots(fr):
    """list of per-slot records for a frame: dict(a2, kind(e598/e568), flags, type, tbl, net cycles, calls[events])"""
    ev = fr['ev']; recs = []
    cur = None
    for e in ev:
        pc = e['pc']
        if pc in (0xe598, 0xe568, 0xe4fc):
            if cur is not None:
                cur['net'] = (e['t'] - cur['t0']) - (e['isr'] - cur['isr0'])
                recs.append(cur)
            cur = None
            if pc != 0xe4fc:
                m = e['mem']
                cur = {'a2': e['a2'], 'via': pc, 'flags': m[4], 'type': (m[12] << 8) | m[13], 'f6': (m[6] << 8) | m[7], 'f8': (m[8] << 8) | m[9],
                       'x': S((m[0] << 8) | m[1]), 'y': S((m[2] << 8) | m[3]), 'tbl': int.from_bytes(m[0x34:0x38], 'big'), 't0': e['t'], 'isr0': e['isr'], 'calls': [], 'mem': m}
        elif cur is not None and pc in CALLPCS:
            cur['calls'].append(e)
        elif cur is not None and pc in (0xed70, 0xe716):
            cur['rets'] = cur.get('rets', []) + [e]
    return recs

CALLPCS = {0xe710, 0xe8c8, 0xe920, 0xe9f2, 0xeaba, 0xeb0a, 0xec94, 0xed6e, 0xe7ae, 0x1551a, 0x1554a, 0x1556a, 0x155ac, 0x155cc, 0x15604}


# kernel address -> (nibble, cols, entry kind) from the pointer tables in the dump
def kernel_map():
    km = {}
    def grp(base, nib, kind):
        for c in range(1, 5):
            a = L(base + 4 * c)
            if a != 0x3a84: km.setdefault(a, (nib, c, kind))
    for base, nib in ((0x399c, 7), (0x39b0, 11), (0x39c4, 13), (0x3a14, 15)):
        grp(base, nib, 'full')
    for base, nib in ((0x38ac, 7), (0x38c0, 11), (0x38d4, 13), (0x38e8, 15)):   # post-setup entries (aligned+shifted dispatch inside)
        grp(base, nib, 'post')
    return km
KM = kernel_map()
def cls(a2):
    if a2 == 0x2c68: return 'player'
    if a2 == 0x3480: return 'player2'
    if a2 in (0x2ca0, 0x2cd8, 0x2d10): return 'opponent'
    return 'scenery'


def calls(sc):
    """Per-call records for a scene: type-0 single sprites (ed6e) and type-1/3 composite objects (e710)."""
    out = []
    for f in frames(f'work/sprite/raw/{sc}.log'):
        for r in slots(f):
            ev = r['calls']
            if not ev: continue
            c = cls(r['a2'])
            # rebuild times excluding isr
            def tn(e): return e['t'] - e['isr']
            if ev[0]['pc'] == 0xed6e:
                e = ev[0]; g = e['r']
                kern = g['a4']; d0 = S(g['d0'] & 0xffff); d1 = S(g['d1'] & 0xffff); d7 = g['d7'] & 0xffff
                nib, cols, kind = KM.get(kern, (0, 0, '?'))
                ent = g['a0']
                w = W(ent + 4) if ent < len(DUMP) - 16 else 0; h = W(ent + 6) if ent < len(DUMP) - 16 else 0
                # cycles: slot net (includes dispatch glue) and the kernel jsr -> return (needs ed70, not stored: use slot net minus glue)
                kc = (r['rets'][0]['t'] - r['rets'][0]['isr']) - tn(e) if r.get('rets') else None
                out.append(dict(sc=sc, cls=c, slot=r['a2'], kind='t0', kcyc=kc, kernel=kern, nib=nib, cols=cols, shift=d0 & 15, x=d0, y=d1, rows=d7, w=w, h=h, ent=ent,
                                net=r['net'], nparts=1))
            else:
                parts = [e for e in ev if e['pc'] in (0x1551a, 0x1554a, 0x1556a, 0x155ac, 0x155cc, 0x15604)]
                g0 = ev[0]['r']
                kc = (r['rets'][0]['t'] - r['rets'][0]['isr']) - tn(ev[0]) if r.get('rets') else None
                out.append(dict(sc=sc, cls=c, slot=r['a2'], kind='t13', kcyc=kc, type=r['type'], net=r['net'], nparts=len(parts), tbl=g0.get('a0'),
                                parts=[(p['pc'], p['r'].get('a0', 0), p['r'].get('d6', 0) & 15, p['r'].get('d7', 0) & 0xffff, p['r'].get('d0', 0) & 0xffff, p['r'].get('d1', 0) & 0xffff) for p in parts],
                                d0=S(g0['d0'] & 0xffff) if 'd0' in g0 else 0))
    return out
