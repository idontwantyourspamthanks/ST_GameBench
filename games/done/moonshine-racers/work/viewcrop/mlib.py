"""Instrumented Musashi (libm68k2.so): per-instruction (pc, cycles, screen row written by the instruction)."""
import ctypes, numpy as np
from pathlib import Path
L = ctypes.CDLL(str(Path(__file__).resolve().parent / 'musashi/libm68k2.so'))
L.ram_ptr.restype = ctypes.POINTER(ctypes.c_ubyte)
L.run_until.restype = ctypes.c_long; L.run_until.argtypes = [ctypes.c_uint, ctypes.c_uint, ctypes.c_long]
L.set_reg.argtypes = [ctypes.c_int, ctypes.c_uint]; L.get_reg.restype = ctypes.c_uint; L.get_reg.argtypes = [ctypes.c_int]
L.set_scr.argtypes = [ctypes.c_uint, ctypes.c_uint]
L.trace_pcs.restype = ctypes.POINTER(ctypes.c_uint); L.trace_cycs.restype = ctypes.POINTER(ctypes.c_int); L.trace_rows.restype = ctypes.POINTER(ctypes.c_short); L.trace_len.restype = ctypes.c_long
L.cpu_init()
RAMSZ = 0x200000
def run(ram1m, pc, stop, regs=None, scr=(0x70000, 0x78000), maxcyc=60_000_000, a7=0x1f0000):
    mem = ctypes.cast(L.ram_ptr(), ctypes.POINTER(ctypes.c_ubyte * RAMSZ)).contents
    ctypes.memmove(mem, bytes(ram1m).ljust(RAMSZ, b'\0'), RAMSZ)
    for i in range(16): L.set_reg(i, 0)
    for k, v in (regs or {}).items(): L.set_reg(int(k[1]) + (8 if k[0] == 'a' else 0), v)
    L.set_reg(15, a7 - 4)
    sent = 0x1ff000
    if stop is None:
        stop = sent; ctypes.memmove(ctypes.byref(mem, a7 - 4), sent.to_bytes(4, 'big'), 4)
    L.set_scr(*scr); L.trace_set(1)
    cyc = L.run_until(pc, stop, maxcyc)
    n = L.trace_len()
    pcs = np.ctypeslib.as_array(L.trace_pcs(), shape=(n,)).copy(); cy = np.ctypeslib.as_array(L.trace_cycs(), shape=(n,)).copy(); rows = np.ctypeslib.as_array(L.trace_rows(), shape=(n,)).copy()
    L.trace_set(0)
    return cyc, pcs, cy, rows
