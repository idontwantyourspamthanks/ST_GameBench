"""Cycles of each part of the HUD stage per pass, by class of the ticker state.
python3 stage_sb.py SNAP SET MHZ NPASS OUT.json
Persistent breakpoints (trace files: e VBL / e FrameCycles / m $11ab / m $100e): A = newhud entry $BB00C, B = ticker entry $11ef0, C = face routine entry $f90c (the sb hook for S),
D = after the face (`bsr.w hit` at $BB024), E = newhud rts $BB02C.  Stage parts: topbar = B-A, ticker = C-B, face(+sb) = D-C, hit = E-D.  Interrupts inside a part are included."""
import sys, json, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar')
from sblib import *
import msrabtest as ab
from msr import Moonshine
snap, setn, mhz, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
CYC = 160256
live = None if setn == 'A' else live_build_sb(SETS[setn], setn)
h = Moonshine(snapshot=ab.snap_path(snap))
R = h.R
PCS = {'A': 0xBB00C, 'B': 0x11ef0, 'C': 0xf90c, 'S1': 0xB6088, 'F1': 0xB6600, 'D': 0xBB024, 'E': 0xBB02C}
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    if mhz: h.set_cpuclock(mhz)
    time.sleep(0.4); h.debug('b all', 0.3)
    for j, (k, pc) in enumerate(PCS.items()):
        (R / f'st_{k}.txt').write_text(f"e VBL\ne FrameCycles\ne {1000 + j}\nm $11ab 1\nm $100e 2\nm $11a8 2\nm $11a4 2\nm $11b0 1\n")
    n0 = len(h._logtext())
    for k, pc in PCS.items():
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {R}/st_{k}.txt"); time.sleep(0.2)
    t0 = time.time()
    while h._logtext()[n0:].count('> e VBL') < 5 * npass + 5 and time.time() - t0 < 3000: time.sleep(2)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
def mem(sg):
    g = {}
    for ln in sg.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return g
ev = []
for sg in log.split('> e VBL')[1:]:
    nums = re.findall(r'#(\d+) \(dec\)', sg)
    if len(nums) < 3: continue
    g = mem(sg)
    ev.append((int(nums[0]) * CYC + int(nums[1]), int(nums[2]) - 1000, g.get(0x11ab, 0), (g.get(0x100e, 0) << 8) | g.get(0x100f, 0), g.get(0x11b0, 0)))
# group consecutive A,B,C,D,E: identify by ordering (A first); the breakpoints fire in program order A B C D E per pass (B/C only when the stage calls them)

names = list(PCS)
rows = []
cur = {}
for t, k, s11, p, b0 in ev:
    cur[names[k]] = (t, s11, p, b0)
    if names[k] == 'E':
        if all(x in cur for x in ('A', 'B', 'C', 'D', 'E')):
            a, b, c, d, e = (cur[x] for x in 'ABCDE')
            r = dict(p=a[2], speech=e[1], topbar=b[0] - a[0], ticker=c[0] - b[0], face=d[0] - c[0], hit=e[0] - d[0], stage=e[0] - a[0], s11ab_B=b[1], b0=a[3])
            if 'S1' in cur:
                r['sbent'] = cur['S1'][0] - c[0]
                if 'F1' in cur: r['stockface'] = cur['F1'][0] - cur['S1'][0]; r['sbface'] = d[0] - cur['F1'][0]
                else: r['stockface'] = d[0] - cur['S1'][0]; r['sbface'] = 0
            rows.append(r)
        cur = {}
json.dump(rows, open(out, 'w'))
import statistics as st
def cls(r):
    if r['b0'] != 0 or (r['s11ab_B'] != 0 and r['speech'] == 0): return 'erase'
    return 'none' if r['speech'] == 0 else ('typing' if r['speech'] == 1 else 'hold')
for c in ('none', 'typing', 'hold', 'erase'):
    sel = [r for r in rows if (cls(r) == c)]
    if sel:
        print(f"{setn} {snap} {c:7s} n {len(sel):3d}  stage {round(st.mean(r['stage'] for r in sel)):6d}  topbar {round(st.mean(r['topbar'] for r in sel)):6d}  ticker {round(st.mean(r['ticker'] for r in sel)):6d}  face {round(st.mean(r['face'] for r in sel)):6d}  hit {round(st.mean(r['hit'] for r in sel)):5d}   max stage {max(r['stage'] for r in sel)}" + (f"   | sbent {round(st.mean(r['sbent'] for r in sel))} stockface {round(st.mean(r['stockface'] for r in sel))} sbface {round(st.mean(r['sbface'] for r in sel))}" if 'sbent' in sel[0] else ''))
