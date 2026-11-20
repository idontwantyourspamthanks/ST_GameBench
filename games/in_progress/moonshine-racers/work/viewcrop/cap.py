"""Unicorn (exact 68000 model) capture of every road draw of the DEFAULT set (live image X = FIN + mt_clock mt_pre mx_pre mx_sync) with X_TEST extras.
python3 cap.py DUMP NPASS NEXTRA KIND OUT.pkl
Per rd_draw call ($B5004): records, destination rows at entry, buffer after the draw, final image at the flip ($d1ca), Musashi cycles of the call (per record row) and of the
rd_geom call ($B4004) made just before.  Frame kinds: first rd_draw of a pass = main, others = extra (f = j/(n+1))."""
import sys, json, pickle, struct
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/work/extrap'); sys.path.insert(0, GAME + '/work/road')
from gate3 import *            # Emu, schedule, flip ...
import rdlib
from unicorn import *
from unicorn.m68k_const import *
dump, NP, NX, kind, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
LIVE = GAME + '/work/viewcrop/live/X'
RD_REC = 0xb503c
REGS = [UC_M68K_REG_D0 + i for i in range(8)] + [UC_M68K_REG_A0 + i for i in range(8)]
e = Emu(dump)
spec = json.load(open(LIVE + '.json')); e.write(spec['img_base'], open(LIVE + '.img', 'rb').read())
for s in spec['sites']: e.write(s['addr'], bytes.fromhex(s['new']))
e.setb(0xB8F21, NX)
uc = e.uc
frames = []; cur = {}
state = dict(p=0, nd=0, meas=False, geom=None)
def musashi(entry, regs):
    ram = bytearray(uc.mem_read(0, 0x100000)) + bytearray(0x100000)
    m = rdlib.Emu(ram)
    rdlib.trace_on(1)
    rr = {}
    for i in range(8): rr['d%d' % i] = regs[i]
    for i in range(7): rr['a%d' % i] = regs[8 + i]
    cyc = m.call(entry, rr)
    tr = rdlib.trace_get(); rdlib.trace_on(0)
    return cyc, tr
def on_geom(uc_, addr, size, ud):
    if not state['meas']: return
    regs = [uc.reg_read(r) for r in REGS]
    cyc, tr = musashi(0xB4004, regs)
    state['geom'] = cyc
def on_draw(uc_, addr, size, ud):
    regs = [uc.reg_read(r) for r in REGS]
    buf = e.l(0x1008)
    ptr = e.l(0x4b84)
    recs = [struct.unpack('>HHHH', e.read(a, 8)) for a in range(ptr, 0x4f78, 8)]
    d = dict(pass_=state['p'], idx=state['nd'], buf=buf, recs=recs, entry=e.read(buf, 0x7d00), cyc=None, rowcyc=None, geom=state['geom'],
             v=e.w(0x130c), lat=e.sw(0x1318), sp=e.w(0x130c))
    if state['meas']:
        cyc, tr = musashi(0xB5004, regs)
        d['cyc'] = cyc
        rows = []; c = 0; started = False
        for pc, cy in tr:
            if pc == RD_REC:
                if started: rows.append(c)
                c = 0; started = True
            c += cy
        rows.append(c)                      # last row incl. the terminator test / rts
        d['rowcyc'] = rows
    cur[state['nd']] = d
    state['nd'] += 1; state['geom'] = None
    ra = e.l(regs[15] if False else uc.reg_read(UC_M68K_REG_A7))
    d['ra'] = ra
    h = [None]
    def on_exit(uc2, a2, s2, ud2):
        d['exit'] = e.read(buf, 0x7d00)
        uc.hook_del(h[0])
    h[0] = uc.hook_add(UC_HOOK_CODE, on_exit, begin=ra, end=ra)
    frames.append(d)
def on_flip(uc_, addr, size, ud):
    if frames:
        frames[-1]['final'] = e.read(e.l(0x1008), 0x7d00)
        frames[-1]['final_buf'] = e.l(0x1008)
uc.hook_add(UC_HOOK_CODE, on_draw, begin=0xB5004, end=0xB5004)
uc.hook_add(UC_HOOK_CODE, on_geom, begin=0xB4004, end=0xB4004)
uc.hook_add(UC_HOOK_CODE, on_flip, begin=0xd1ca, end=0xd1ca)
WARM = 6
for p in range(NP):
    state['p'] = p; state['meas'] = p >= WARM
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
    e.run(0x7a88, 0x7b7a)
    e.run(0x7b7a, 0x7a88)
    if p % 10 == 0: print('pass', p, 'frames', len(frames), '130c', e.w(0x130c), file=sys.stderr)
pickle.dump(dict(frames=frames, nx=NX, warm=WARM), open(out, 'wb'))
print(len(frames), 'frames')
