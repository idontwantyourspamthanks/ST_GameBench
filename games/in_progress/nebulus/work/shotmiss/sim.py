"""Unicorn M68000 simulation of Nebulus' per-loop game logic (not rendering), from a 1 MB RAM dump taken at the loop-top poll.
Runs the game's own code; only the loop order is ours:  poll $3853a ; $37898 ; $3e188 ; $3b482 (creatures) ; $3b9a2 (shot) ; $3a572 (player) ;
then optionally [$3e1c2 .. $3792c spawn $3b3d8 ..] -- see LOOP.  Addresses are final RAM addresses."""
import struct, sys
from unicorn import *
from unicorn.m68k_const import *

SENT = 0xa0100       # return sentinel (never executed)
STK  = 0xa0f00

class Sim:
    def __init__(self, base='/tmp/shot_play_enemy.bin', patches=()):
        self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        try:
            self.uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        except Exception as e:
            print('cpu model', e)
        self.uc.mem_map(0, 0x100000)
        self.uc.mem_map(0x100000, 0x100000)          # scratch (a0100 etc.)
        self.uc.mem_map(0xf00000, 0x100000)          # hardware window as plain RAM
        self.uc.mem_write(0, open(base, 'rb').read())
        for a, b in patches:
            self.uc.mem_write(a, bytes(b))
        self.base_img = None

    # memory helpers
    def rb(self, a): return self.uc.mem_read(a, 1)[0]
    def rw(self, a): return struct.unpack('>H', self.uc.mem_read(a, 2))[0]
    def rsw(self, a): return struct.unpack('>h', self.uc.mem_read(a, 2))[0]
    def rl(self, a): return struct.unpack('>I', self.uc.mem_read(a, 4))[0]
    def ww(self, a, v): self.uc.mem_write(a, struct.pack('>H', v & 0xffff))
    def wb(self, a, v): self.uc.mem_write(a, bytes([v & 0xff]))
    def snap(self): return bytes(self.uc.mem_read(0, 0x100000))
    def restore(self, img): self.uc.mem_write(0, img)

    def call(self, addr, maxins=2000000):
        uc = self.uc
        for r in (UC_M68K_REG_D0, UC_M68K_REG_D1, UC_M68K_REG_D2, UC_M68K_REG_D3, UC_M68K_REG_D4, UC_M68K_REG_D5, UC_M68K_REG_D6, UC_M68K_REG_D7,
                  UC_M68K_REG_A0, UC_M68K_REG_A1, UC_M68K_REG_A2, UC_M68K_REG_A3, UC_M68K_REG_A4, UC_M68K_REG_A5, UC_M68K_REG_A6):
            uc.reg_write(r, 0)
        sp = STK - 4
        uc.mem_write(sp, struct.pack('>I', SENT))
        uc.reg_write(UC_M68K_REG_A7, sp)
        uc.emu_start(addr, SENT, count=maxins)
        assert uc.reg_read(UC_M68K_REG_PC) == SENT, hex(uc.reg_read(UC_M68K_REG_PC))
        return uc.reg_read(UC_M68K_REG_D0)

# ---- game variables
SL = 0x33944          # slot s word at SL+2*s; field F at +F
def fld(s, F): return SL + F + 2 * s
F_X, F_Y, F_FR, F_SORT, F_DX, F_CNT, F_ST, F_SPD, F_AUX, F_TGT = 0, 0x0c, 0x18, 0x24, 0x30, 0x3c, 0x48, 0x54, 0x60, 0x6c
PX, PY, PST, PSTEP, PDIR = 0x33a16, 0x33a18, 0x33a20, 0x33a1e, 0x33a1c

def slot(sim, s):
    return {k: sim.rsw(fld(s, F)) for k, F in (('x', F_X), ('y', F_Y), ('fr', F_FR), ('cnt', F_CNT), ('st', F_ST), ('spd', F_SPD), ('aux', F_AUX), ('tgt', F_TGT))}

LOOP = [0x3853a, 0x37898, 0x3e188, 0x3b482, 0x3b9a2, 0x3a572]
EXTRA = [0x3e1c2, 0x3792c, 0x3b3d8, 0x3ae6e, 0x3b0a4]

def loop(sim, extra=True, noenemy=False):
    for a in LOOP:
        sim.call(a)
    if extra:
        for a in EXTRA:
            if a == 0x3792c and noenemy: continue
            sim.call(a)

# ------------------------------------------------------------------ attempt harness
GR = 0x327f0
def cell(c, r): return GR + c * 256 + r
SHOT = 4
def sgn(v, m=0x400): v &= (m - 1); return v - m if v >= m // 2 else v

class Probe:
    """code hooks: log every execution of the shot-vs-creature overlap test and its result"""
    def __init__(self, sim):
        self.sim = sim; self.rows = []; self.cur = None
        sim.uc.hook_add(UC_HOOK_CODE, self.h_enter, begin=0x3b7d6, end=0x3b7d6)
        sim.uc.hook_add(UC_HOOK_CODE, self.h_after, begin=0x3ba14, end=0x3ba14)
        sim.uc.hook_add(UC_HOOK_CODE, self.h_terr, begin=0x3ba0c, end=0x3ba0c)
        sim.uc.hook_add(UC_HOOK_CODE, self.h_terr2, begin=0x3ba10, end=0x3ba10)
        self.terr_hit = None
    def h_terr(self, uc, a, sz, ud):   # at bcs after sub_03a834 : carry = shot inside terrain
        sr = uc.reg_read(UC_M68K_REG_SR); self.terr_hit = bool(sr & 1)
    def h_terr2(self, uc, a, sz, ud):
        self.terr_hit = False
    def h_enter(self, uc, a, sz, ud):
        a1 = uc.reg_read(UC_M68K_REG_A1)
        self.cur = a1 if a1 == 0x3394c else None
        if self.cur:
            sm = self.sim
            self.entry = dict(sx=sm.rsw(fld(SHOT, F_X)), sy=sm.rsw(fld(SHOT, F_Y)), cr=[(sm.rsw(fld(k, F_X)), sm.rsw(fld(k, F_Y)), sm.rsw(fld(k, F_ST))) for k in range(4)])
    def h_after(self, uc, a, sz, ud):
        if self.cur is None: return
        sr = uc.reg_read(UC_M68K_REG_SR); hit = bool(sr & 1)
        a0 = uc.reg_read(UC_M68K_REG_A0)
        self.rows.append((hit, (a0 - SL) // 2 if hit else None, self.entry))
        self.cur = None

def mk_attempt(base_img, patches=()):
    """returns a function run(attempt) -> log dict. One Sim, restored from base_img each time."""
    sim = Sim()
    return sim

def prep(sim, img, ball, frog, stack=False, noenemy=True, patches=(), extra_slots=()):
    sim.restore(img)
    for a, b in patches:
        sim.uc.mem_write(a, bytes(b))
    if noenemy:
        sim.wb(0x3792c, 0x4e); sim.wb(0x3792d, 0x75)
    for k in range(4): sim.ww(fld(k, F_ST), 0)
    for r in (15, 16): sim.wb(cell(12, r), 0x82 if stack else 0)
    if ball:
        sl = dict(x=76, y=60, st=1, spd=0, cnt=0, tgt=1, aux=0); sl.update(ball)
        for k, F in (('x', F_X), ('y', F_Y), ('st', F_ST), ('spd', F_SPD), ('cnt', F_CNT), ('tgt', F_TGT), ('aux', F_AUX)):
            sim.ww(fld(0, F), sl[k] & 0xffff)
        sim.ww(fld(0, F_FR), 0)
    for k, e in enumerate(extra_slots, 1):
        for kk, F in (('x', F_X), ('y', F_Y), ('st', F_ST), ('spd', F_SPD), ('cnt', F_CNT), ('tgt', F_TGT), ('aux', F_AUX)):
            sim.ww(fld(k, F), e[kk] & 0xffff)
    sim.ww(PX, frog['x']); sim.ww(PY, frog.get('y', 60)); sim.ww(PST, 0); sim.ww(PSTEP, 0)
    sim.ww(PDIR, frog.get('dir', 0))

def shoot(sim, fire_at=0, nloops=40, pulse=2, probe=None, log=True):
    """loop with a fire pulse starting at loop `fire_at`; returns list of per-loop dict"""
    out = []
    for i in range(nloops):
        sim.wb(0x38498, 0x80 if fire_at <= i < fire_at + pulse else 0)
        if probe: probe.rows.clear(); probe.terr_hit = None
        loop(sim, extra=False)
        b = slot(sim, 0); sh = slot(sim, SHOT)
        out.append(dict(i=i, bx=b['x'], by=b['y'], bst=b['st'], bcnt=b['cnt'], bspd=b['spd'],
                        sx=sh['x'], sy=sh['y'], sst=sh['st'], scnt=sh['cnt'], pst=sim.rw(PST), pstep=sim.rw(PSTEP), px=sim.rw(PX),
                        ov=[(h, k) for h, k, e in probe.rows] if probe else None, ent=[e for h, k, e in probe.rows] if probe else None, terr=probe.terr_hit if probe else None,
                        others=[slot(sim, k)['st'] for k in (1, 2, 3)]))
    return out
