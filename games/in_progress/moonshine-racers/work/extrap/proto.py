import sys, struct
from emu import *

def region_runs(l):
    r = []
    for a in l:
        if r and a - r[-1][1] <= 1: r[-1][1] = a
        else: r.append([a, a])
    return r

def snap_ram(e): return e.read(0, 0x100000)
def load_ram(e, b): e.write(0, b)

def flip(e): e.call(0xd1ca)

def buf(e, base): return e.read(base, 0x7d00)

def stock_next(e):
    """from state at 7b74 (pass n rendered): flip, tail, head, pass n+1 body -> at 7b74 again"""
    flip(e)
    e.run(0x7b7a, 0x7a88)
    e.run(0x7a88, 0x7b74)

def set_a5(e):
    e.uc.reg_write(UC_M68K_REG_A5, e.l(0x1008))

STAGES_EXTRA = [0xfe50, 0xff76, 0x1003c, 0x17c24, 0x100b4, 0x17c42, 0x10a5e, 0x10a98, 0xe2e8, 'cars', 0xe316, 0xdd50, 0x18318, 0xe406, 0xef7a]

def car_step(e, k, v):
    if v == 0: return
    for i in range(4):
        a = 0x2ca0 + 0x38 * i
        if e.b(a + 4) & 0x40: continue
        d1 = v
        if e.w(0x1030): d1 = (d1 - e.sw(a + 0x22))
        step = int(round(d1 * k / v))
        d0 = e.sw(a + 0x20) - step
        if 0 <= d0 < 0x400 and (e.b(a+4) & 1):
            e.setw(a + 0x20, d0)

def extra_frame(e, k, stages=STAGES_EXTRA, lat=None):
    v = e.w(0x130c)
    e.setw(0x130c, k)
    if lat is not None: e.setw(0x1318, lat)
    for s in stages:
        set_a5(e)
        if s == 'cars': car_step(e, k, v)
        else: e.call(s)
    e.setw(0x130c, v)

def diffrows(a, b, rows=200):
    """report per-row differing byte counts for two 32000-byte screens"""
    out = []
    for r in range(rows):
        x = a[r*160:(r+1)*160]; y = b[r*160:(r+1)*160]
        n = sum(1 for i in range(160) if x[i] != y[i])
        if n: out.append((r, n))
    return out

if __name__ == "__main__":
    snapf = sys.argv[1] if len(sys.argv) > 1 else 'h_start_7a88.bin'
    e = Emu(snapf)
    e.run(0x7a88, 0x7b74)
    A = snap_ram(e)
    v = e.w(0x130c)
    print("v", v, "1008", hex(e.l(0x1008)))
    # stock next
    stock_next(e)
    S1 = buf(e, 0x78000); stock_state = snap_ram(e)
    print("stock n+1 100e", e.w(0x100e), "130c", e.w(0x130c))
    # extra with k = v (f=1)
    load_ram(e, A)
    flip(e)
    extra_frame(e, v)
    X1 = buf(e, 0x78000)
    d = diffrows(S1, X1)
    print("rows differing at f=1:", len(d), "bytes:", sum(n for r, n in d))
    print(d[:80])
