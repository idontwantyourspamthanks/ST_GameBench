import sys, pickle, vh
FIELDS = [('X',0x66e6,'sl'),('Y',0x66ea,'sl'),('H',0x6742,'w'),('H94',0x6294,'w'),('H4a',0x764a,'w'),('lean',0x674e,'sw'),('bank',0x6746,'sw'),
 ('pitch',0x674a,'w'),('thr',0x6750,'sw'),('r52',0x6752,'sw'),('r56',0x6756,'sw'),('r5a',0x675a,'sw'),('spd',0x6772,'sw'),('alt',0x764c,'sw'),('agl',0x66e2,'sw'),('gnd',0x66e4,'sw'),
 ('c52',0x7652,'sw'),('c54',0x7654,'sw'),('v46',0x7646,'sw'),('v48',0x7648,'sw'),('type',0x6220,'w'),('blk',0x676e,'w'),('cd',0x6290,'w'),('clk',0xeb8c,'l'),('d80',0x7680,'sw'),
 ('g36',0x34936,'sw'),('g38',0x34938,'sw'),('g3a',0x3493a,'sw'),('flg',0x6776,'w'),('f984',0xf984,'sw'),('hud',0x6888,'w'),('s767e',0x767e,'w'),('s6774',0x6774,'sw'),('y6768',0x6768,'sw'),('x6766',0x6766,'sw'),('r6fb6',0x6fb6,'sl'),('r6fba',0x6fba,'sl'),('btn',0x6fbe,'w'),('s688e',0x688e,'w'),('s6892',0x6892,'w')]
def get(m, a, k):
    s = vh.S(m)
    return {'sl': s.sl, 'w': s.w, 'sw': s.sw, 'l': s.l}[k](a)
def row(m): return {n: get(m, a, k) for n, a, k in FIELDS}
def load(tag):
    A, B = pickle.load(open(vh.OUT / (tag + '.pkl'), 'rb'))
    PH = lambda m: vh.S(m).w(0xb42e6)
    Ar = [row(m) for m in A]
    Br = [row(m) | {'PH': PH(m)} for m in B]
    return Ar, Br
def compare(tag, keys=None, show=True, skip=1):
    Ar, Br = load(tag)
    Bg = [r for r in Br[1:] if r['PH'] == 5]
    Ag = Ar[1:]
    keys = keys or ['X','Y','H','H94','H4a','lean','bank','thr','spd','alt','c52','c54','type','blk','cd','clk','d80','r5a','btn']
    bad = 0; n = min(len(Ag), len(Bg))
    for k in range(n):
        d = [x for x in keys if Ag[k][x] != Bg[k][x]]
        bad += bool(d)
        if show and (d or k < 2):
            print(k + 1, 'EQ' if not d else 'DIFF ' + ' '.join(f"{x}:{Ag[k][x]}/{Bg[k][x]}" for x in d))
    print(tag, 'groups', n, 'mismatching', bad)
    return Ar, Br, Ag, Bg
if __name__ == '__main__':
    Ar, Br, Ag, Bg = compare(sys.argv[1])
    if len(sys.argv) > 2:
        for r in Ar[:int(sys.argv[2])]: print({k: r[k] for k in ('X','Y','H','bank','thr','spd','alt','agl','btn')})
