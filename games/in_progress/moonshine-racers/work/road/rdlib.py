import struct
from pathlib import Path
D = Path(__file__).resolve().parent / 'dump'
def u16(b, o): return struct.unpack('>H', b[o:o+2])[0]
def s16(b, o): return struct.unpack('>h', b[o:o+2])[0]
def u32(b, o): return struct.unpack('>I', b[o:o+4])[0]
def load(scene, p):
    d = D / scene
    r = lambda t, n: (d / f'p{p:03d}_{t}_{n}.bin').read_bytes()
    f = dict(a_lo=r('a','lo'), a_tb=r('a','tb'), a_g=r('a','g'), b_lo=r('b','lo'), b_g=r('b','g'), b_tab=r('b','tab'), b_cs=r('b','cs'), a_t68=r('a','t68'), a_sin=r('a','sin'), a_v=r('a','v'), s70=r('c','s70'), s78=r('c','s78'), d70=r('d','s70'), d78=r('d','s78'), pal=r('d','pal'))
    return f
def records(f):
    g = f['b_g']; ptr = u32(g, 0x684)
    o = ptr - 0x4500; recs = []
    while o < 0x4f78 - 0x4500:
        recs.append(struct.unpack('>HhhH', g[o:o+8])); o += 8   # w0, L, R, flags
    return recs
def backbuf(f):
    # back buffer = $1008 at stage a
    b = u32(f['a_lo'], 0x8)
    return f['s70'] if b == 0x70000 else f['s78']
def world(f):
    lo = f['a_lo']
    return dict(pos=u16(f['a_v'], 0x8), spd=u16(lo, 0x30c), p1308=u16(lo, 0x308), p130a=u16(lo, 0x30a), c1318=s16(lo,0x318), v1316=u16(lo,0x316), v13ae=u16(lo,0x3ae))

# ---- Musashi 68000 (work/road/musashi, cycle counting) harness: runs the game's own routines offline on a dumped frame ----------
import ctypes
GAME = Path(__file__).resolve().parents[2]
BASE_DUMP = GAME / 'work/dumps/ram_race_start.bin'
_lib = ctypes.CDLL(str(Path(__file__).resolve().parent / 'musashi/libm68k.so'))
_lib.ram_ptr.restype = ctypes.POINTER(ctypes.c_ubyte)
_lib.run_until.restype = ctypes.c_long
_lib.run_until.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_long]
_lib.set_reg.argtypes = [ctypes.c_int, ctypes.c_uint]
_lib.get_reg.restype = ctypes.c_uint
_lib.get_reg.argtypes = [ctypes.c_int]
_lib.prof_cyc.restype = ctypes.POINTER(ctypes.c_ulong); _lib.prof_cnt.restype = ctypes.POINTER(ctypes.c_ulong)
_lib.trace_pcs.restype = ctypes.POINTER(ctypes.c_uint); _lib.trace_cycs.restype = ctypes.POINTER(ctypes.c_int); _lib.trace_len.restype = ctypes.c_long
_lib.cpu_init()
def trace_on(on=1): _lib.trace_set(on)
def trace_get():
    n = _lib.trace_len(); p = _lib.trace_pcs(); c = _lib.trace_cycs()
    return [(p[i], c[i]) for i in range(n)]
def prof_clear(): _lib.prof_clear()
def prof_get():
    c = _lib.prof_cyc(); n = _lib.prof_cnt()
    return {i * 2: (c[i], n[i]) for i in range(0x80000) if n[i]}
RAMSZ = 0x200000
def ram_for(f, stage):
    ram = bytearray(BASE_DUMP.read_bytes()[:0x100000]) + bytearray(0x100000)
    def put(ad, b): ram[ad:ad+len(b)] = b
    put(0x1000, f['a_lo']); put(0x1400, f['a_sin']); put(0x2300, f['a_tb']); put(0x4500, f['a_g']); put(0x68000, f['a_t68']); put(0x1400, f['a_sin']); put(0x5ff0, f['a_v'])
    put(0x4ff8, f['b_tab']); put(0x10200, f['b_cs'])
    if stage == 'b':
        put(0x1000, f['b_lo']); put(0x4500, f['b_g'])
    return ram
class Emu:
    """D0..D7 = 0..7, A0..A7 = 8..15, PC 16, SR 17 (Musashi enum)."""
    def __init__(self, ram):
        self.mem = ctypes.cast(_lib.ram_ptr(), ctypes.POINTER(ctypes.c_ubyte * RAMSZ)).contents
        ctypes.memmove(self.mem, bytes(ram).ljust(RAMSZ, b'\0'), RAMSZ)
        self.cyc = 0
    def call(self, pc, regs=None, a7=0x1f0000, maxcyc=50_000_000):
        sent = 0x1ff000
        _lib.m68k_dummy = None
        for i in range(16): _lib.set_reg(i, 0)
        for k, v in (regs or {}).items(): _lib.set_reg(self._r(k), v)
        _lib.set_reg(15, a7 - 4)
        ctypes.memmove(ctypes.byref(self.mem, a7 - 4), sent.to_bytes(4, 'big'), 4)
        self.cyc = _lib.run_until(pc, sent, maxcyc)
        return self.cyc
    @staticmethod
    def _r(k):
        k = k.lower()
        return int(k[1]) + (8 if k[0] == 'a' else 0)
    def reg(self, k): return _lib.get_reg(self._r(k))
    def rd(self, ad, n): return bytes(self.mem[ad:ad+n])
    def wr(self, ad, b): ctypes.memmove(ctypes.byref(self.mem, ad), bytes(b), len(b))

def road_rows(f):
    """(first_row, bytes of the road rows 0..n-1 as drawn at stage c) rows listed bottom-up: row k = screen row 199-k."""
    recs = records(f); b = backbuf(f); n = len(recs)
    return [b[(199 - k) * 160:(200 - k) * 160] for k in range(n)]
def final_buf(f):
    b = u32(f['a_lo'], 0x8)
    return f['d70'] if b == 0x70000 else f['d78']

import json
def apply_live(emu, prefix):
    """Load a `msrpatch.py live` image + sites into the Musashi RAM."""
    spec = json.loads(Path(prefix + '.json').read_text())
    img = Path(prefix + '.img').read_bytes()
    emu.wr(spec['img_base'], img)
    for s in spec['sites']:
        emu.wr(s['addr'], bytes.fromhex(s['new']))
    return spec
