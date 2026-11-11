"""chan.py trace... : per pass of sub_014e00 classify every memory access as render (the five calls: sky $1580e, markers $1d0a0,
geometry $18304, raster $19ce2, goggles $1bbe6) / non-render / ISR.  Reports
  * rbw: bytes the render reads before it writes them (the real inputs)
  * channels: rbw bytes that some non-render code or ISR writes (in the trace)
  * carried: rbw bytes that an earlier render of the trace wrote (render-to-render state)
  * window writes: non-render writes into the 3D window of the draw buffer
usage: chan.py [--json out.json] trace1 [trace2...]   (a trace's .vec file next to it gives the interrupt vectors)"""
import sys, json, struct, argparse
sys.path.insert(0, '.')
import rdset
rdset.NEXTPC = False
RS = {0x1580e, 0x1d0a0, 0x18304, 0x19ce2, 0x1bbe6}
RE = {0x14e26, 0x14e56, 0x14e5c, 0x14e62, 0x14e72}
SCREENS = [(0x58000,0x5fd00),(0x68000,0x6fd00),(0x78000,0x7fd00),(0x2d000,0x2dc00)]
def is_screen(b): return any(lo<=b<hi for lo,hi in SCREENS)

def entries(path):
    try:
        v = open(path + '.vec', 'rb').read()
    except OSError:
        return set()
    out = set()
    for off in list(range(0x64, 0x80, 4)) + list(range(0x100, 0x140, 4)):
        a = struct.unpack('>I', v[off - 0x60: off - 0x5c])[0]
        if a: out.add(a)
    return out

def run(paths, window_rows=(51, 182)):
    WR_pass = set()
    R = {}           # byte -> pc (first read before write, any pass)
    W = {}           # byte -> set((phase, pc))  non-render
    WR_all = set()   # bytes written by render in any pass
    carried = {}
    winw = {}
    npass = 0; nrender = 0
    for path in paths:
        ENTRY = entries(path)
        recs = rdset.parse(path)
        isr = []; phase = 'nr'; Wr = set(); had = False
        for (pc, mn, ops, nxt, line) in recs:
            if pc in ENTRY and (not isr or True):
                isr.append(pc)
            inisr = bool(isr)
            if inisr:
                if mn.startswith('rte'): isr.pop()
                ph = 'isr'
            else:
                if pc == 0x14e00:
                    npass += 1; Wr = set(); WR_all |= WR_pass; WR_pass = set()
                if pc in RS: phase = 'render'; 
                elif pc in RE: phase = 'nr'
                if pc == 0x1580e: nrender += 1
                ph = phase
            for kind, ea, size in rdset.accesses(mn, ops):
                for b in range(ea, ea + size):
                    if ph == 'render':
                        if kind == 'W': Wr.add(b); WR_pass.add(b)
                        elif b not in Wr:
                            if b not in R: R[b] = pc
                            if b in WR_all and b not in carried: carried[b] = pc
                    elif kind == 'W':
                        W.setdefault(b, set()).add((ph, pc))
    return R, W, carried, npass, nrender

def spans(bs):
    return rdset.intervals(sorted(bs))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('traces', nargs='+'); ap.add_argument('--json')
    ap.add_argument('--minrender', action='store_true')
    a = ap.parse_args()
    R, W, carried, npass, nrender = run(a.traces)
    print('passes', npass, 'renders', nrender, 'render rbw bytes', len(R), 'non-render written bytes', len(W))
    # exclude screen buffers and stack/scratch
    ch = sorted(b for b in R if b in W and not is_screen(b))
    print('channels', len(ch))
    iv = []
    for b in ch:
        if iv and b - iv[-1][1] <= 2: iv[-1][1] = b
        else: iv.append([b, b])
    for s, e in iv:
        ph = sorted({p for b in range(s, e + 1) if b in W for p, _ in W[b]})
        wp = sorted({hex(pc) for b in range(s, e + 1) if b in W for _, pc in W[b]})[:5]
        rp = sorted({hex(R[b]) for b in range(s, e + 1) if b in R})[:5]
        print(f'{s:06x}-{e:06x} {e-s+1:5d} {ph} w {wp} r {rp}')
    cc = sorted(b for b in carried if not is_screen(b))
    print('carried (render-written earlier, read by a later render before written):', len(cc))
    for s, e in spans(cc):
        print(f'  {s:06x}-{e:06x} {e-s+1} readers {sorted({hex(carried[b]) for b in range(s, e+1) if b in carried})[:4]}')
    if a.json:
        json.dump({'rbw': sorted(R), 'wnr': sorted(W), 'carried': cc}, open(a.json, 'w'))
