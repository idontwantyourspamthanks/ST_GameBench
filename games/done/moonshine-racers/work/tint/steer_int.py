"""Pass-exact steering + measurement in Hatari.
python3 steer_int.py SNAP SET MHZ NPASS OUT.json [steer=zig|up|none] [mode=cyc|pass] [poke=ADDR=HEX ...] [car] [hz60]
 SET: A stock, F final tick OFF, N HUD default tick OFF (mode cyc); T/X final tick ON / extras, NT/NX baseline (mode pass)
 mode cyc : cycles per pass (loop top $796a -> flip $d1ca, interrupts included) + VBL per pass; speech flag $11ab; steering input chain at $796a
 mode pass: at each $7a88: VBL, $100e, NEXTRA $b8f32 (extras of the PREVIOUS pass), $b8f38.. counters, $11ab, $1226, $1021
 car: also count stub entries $bf500 / hit $bf5e6 (generated draw) per slot a2 ($2c68 car / $3480 layer)
Steering (pass domain, chain of one-shot breakpoints): zig = [up, up+left, up, up+right] each 15 passes; up = hold up; none = leave the snapshot input"""
import sys, json, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint')
from mxlib_int import *
import msrabtest as ab
from msr import Moonshine
snap, setn, mhz, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
opt = {a.split('=')[0]: a.split('=', 1)[1] for a in sys.argv[6:] if '=' in a and not a.startswith('poke')}
pokes = [a[5:] for a in sys.argv[6:] if a.startswith('poke=')]
steer = opt.get('steer', 'zig'); KS = int(opt['zigk']) if 'zigk' in opt else None; mode = opt.get('mode', 'cyc'); car = 'car' in sys.argv[6:]; hz60 = 'hz60' in sys.argv[6:]
SCH = {'zig': ([0x01, 0x05, 0x01, 0x09], 15), 'up': ([0x01], 1)}
vals, per = SCH.get(steer, (None, 0))
N = len(vals) * per if vals else 0
CYC = 160256
live = None
if setn != 'A':
    live = ab.live_build(SETS[setn])
    if pokes: live = ab.with_pokes(live, pokes, 'st_' + re.sub(r'\W', '', ','.join(pokes))[:30])
h = Moonshine(snapshot=ab.snap_path(snap))
R = h.R
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    if mhz: h.set_cpuclock(mhz)
    if hz60: h.debug("w $ff820a $fc")
    time.sleep(0.4); h.debug('b all', 0.3)
    if mode == 'cyc' and KS is not None:          # steering as a pure function of the pass key $100e from key KS (same inputs in every run: matched-pass comparison)
        top, nxt = 0x796a, 0xd1ca
        show = "m $100e 2\nm $11ab 1\n"
        for K in range(KS, KS + npass + 40):
            wr = f"w $6105 ${vals[((K - KS) // per) % len(vals)]:02x}\n"
            (R / f'c1_{K}.txt').write_text(f"e VBL\ne FrameCycles\n{wr}b pc = ${nxt:x} :trace :once :file {R}/c2_{K}.txt\n")
            (R / f'c2_{K}.txt').write_text(f"e VBL\ne FrameCycles\n{show}b pc = ${top:x} && ($100e).w = ${K + 1:x} :trace :once :file {R}/c1_{K + 1}.txt\n")
        first = f"{R}/c1_{KS}.txt"; unit = 2
    elif mode == 'cyc':
        top, nxt = 0x796a, 0xd1ca
        show = "m $100e 2\nm $11ab 1\n"
        for k in range(max(N, 1)):
            wr = f"w $6105 ${vals[(k // per) % len(vals)]:02x}\n" if vals else ""
            (R / f'c1_{k}.txt').write_text(f"e VBL\ne FrameCycles\n{wr}b pc = ${nxt:x} :trace :once :file {R}/c2_{k}.txt\n")
            (R / f'c2_{k}.txt').write_text(f"e VBL\ne FrameCycles\n{show}b pc = ${top:x} :trace :once :file {R}/c1_{(k + 1) % max(N, 1)}.txt\n")
        first = f"{R}/c1_0.txt"; unit = 2
    else:                                         # pass mode: persistent record breakpoint + key-based steering chain (a once-breakpoint re-armed at the same pc would fire again at once)
        top = 0x7a88
        show = "m $b8f32 2\nm $100e 2\nm $11ab 1\nm $1226 1\nm $1021 1\nm $b8f38 12\nm $b8f54 12\nm $bf008 2\n"
        import os
        if os.environ.get('TINT_SHOW'): show = os.environ['TINT_SHOW'].replace(';', '\n') + '\n'
        (R / 'rec.txt').write_text("e VBL\n" + show)
        K0 = h.peekw(0x100e) + 6
        if vals:
            for K in range(0, 4000):
                (R / f'z_{K}.txt').write_text(f"w $6105 ${vals[(K // per) % len(vals)]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {R}/z_{K + 1}.txt\n")
        first = None; unit = 1
    if car:
        for pc in (0xbf500, 0xbf5e6): (R / f'cc_{pc:x}.txt').write_text("e a2\n")
    n0 = len(h._logtext())
    if car:
        for pc in (0xbf500, 0xbf5e6): h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {R}/cc_{pc:x}.txt"); time.sleep(0.2)
    if mode == 'cyc':
        h.cmd(f"hatari-debug b pc = ${top:x}{(' && ($100e).w = $%x' % KS) if KS is not None else ''} :trace :once :file {first}")
    else:
        h.cmd(f"hatari-debug b pc = $7a88 :trace :file {R}/rec.txt"); time.sleep(0.2)
        if vals:
            h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${K0:x} :trace :once :file {R}/z_{K0}.txt"); time.sleep(0.2)
            h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = 1 :trace :file {R}/z_1.txt")
    t0 = time.time()
    while h._logtext()[n0:].count('> e VBL') < unit * npass + 2 and time.time() - t0 < 3000: time.sleep(2)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
    tail = {}
    for a, n in ((0xbf000, 16), (0xb8f20, 32), (0xb8f38, 16)):
        o = h.debug(f"m ${a:x} {n}", 0.8)
        tail[hex(a)] = ' '.join(re.findall(r'(?:^|\n)[0-9a-f]{8}:\s+((?:[0-9a-f]{2} ?)+)', o, re.I)).strip()
finally:
    h.close()
# ---- parse
def mem(sg):
    g = {}
    for ln in sg.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return g
cars = []
rows = []
if car:
    parts = re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n", log)
    for i in range(1, len(parts) - 1, 2):
        pc = int(parts[i].split('$')[1], 16); m = re.search(r"#(\d+)", parts[i + 1])
        if m: cars.append(('entry' if pc == 0xbf500 else 'hit', int(m.group(1))))
segs = log.split('> e VBL')[1:]
if mode == 'cyc':
    start = None
    for sg in segs:
        nums = re.findall(r'#(\d+) \(dec\)', sg)
        if len(nums) < 2: continue
        t = int(nums[0]) * CYC + int(nums[1]); g = mem(sg)
        if 0x100e in g and start is not None:
            rows.append(dict(p=(g[0x100e] << 8) | g[0x100f], work=t - start, speech=g.get(0x11ab, 0) != 0, vbl_end=int(nums[0]))); start = None
        elif 0x100e not in g: start = t
else:
    for sg in segs:
        nums = re.findall(r'#(\d+) \(dec\)', sg)
        if not nums: continue
        g = mem(sg)
        if 0x100e not in g: continue
        l = lambda a, n: int.from_bytes(bytes(g[a + i] for i in range(n)), 'big')
        rows.append(dict(vbl=int(nums[0]), p=l(0x100e, 2), nextra=l(0xb8f32, 2), speech=g[0x11ab], t1226=g[0x1226], mode=g[0x1021], frames=l(0xb8f38, 4), groups=l(0xb8f3c, 4), ticks=l(0xb8f40, 4), rsn=[l(0xb8f54 + 2 * i, 2) for i in range(6)], nent=l(0xbf008, 2)))
json.dump(dict(rows=rows, cars=cars, tail=tail, args=sys.argv[1:]), open(out, 'w'))
if mode == 'cyc':
    import statistics as st
    for nm, sp in (('no speech', False), ('speech', True)):
        w = [r['work'] for r in rows if r['speech'] == sp]
        if w: print(f"{setn} {snap} {steer} {mhz or 'native'}MHz {nm:10s} n {len(w)} mean {round(st.mean(w))} = {st.mean(w)/CYC:.3f} VBL min {min(w)} max {max(w)}")
    ws = [r['work'] for r in rows]
    if ws: print(f"   all passes n {len(ws)} mean {round(st.mean(ws))} = {st.mean(ws)/CYC:.3f} VBL; last 100 mean {round(st.mean(ws[-100:]))}")
    if rows: print("   VBL per pass (end-to-end, incl. wait): ", round((rows[-1]['vbl_end'] - rows[0]['vbl_end']) / max(len(rows) - 1, 1), 3))
else:
    print(f"{setn} {snap} {steer} {mhz}MHz pass-records {len(rows)}")
if car:
    e = sum(1 for k, _ in cars if k == 'entry'); hh = sum(1 for k, _ in cars if k == 'hit')
    print(f"car stub entries {e} compiled-draw hits {hh} = {100 * hh / max(e, 1):.1f} %   tail {tail}")
