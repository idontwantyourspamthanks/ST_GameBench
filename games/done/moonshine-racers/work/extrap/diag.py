import sys
from proto import *
dump = sys.argv[1]; target = int(sys.argv[2])
e = Emu(dump)
while True:
    e.run(0x7a88, 0x7b74)
    if e.w(0x100e) >= target: break
    flip(e); e.run(0x7b7a, 0x7a88)
A = snap_ram(e); v = e.w(0x130c)
print("pass", e.w(0x100e), "v", v)
stock_next(e); SP = snap_ram(e)
load_ram(e, A); flip(e); extra_frame(e, v); XP = snap_ram(e)
# slot compare
def slot_desc(m, a):
    return struct.unpack(">" + "H"*28, m[a:a+0x38])
for a in range(0x2c68, 0x34f0+0x38*6, 0x38):
    s, x = slot_desc(SP, a), slot_desc(XP, a)
    if s != x:
        diffs = [(hex(a+2*i), hex(s[i]), hex(x[i])) for i in range(28) if s[i] != x[i]]
        print(hex(a), "flags", hex(s[2]), diffs)
print("--- per-tick state changes (A=after render n, SP=after render n+1), words in $1000-$1400 and $23c0-$27ff")
def words(m, lo, hi): return {a: struct.unpack(">H", m[a:a+2])[0] for a in range(lo, hi, 2)}
for lo, hi in ((0x1000, 0x1400), (0x2300, 0x2440), (0x27c0, 0x2800)):
    wa, ws, wx = words(A, lo, hi), words(SP, lo, hi), words(XP, lo, hi)
    for a in wa:
        if wa[a] != ws[a] or ws[a] != wx[a]:
            print(f"{a:04x}: A={wa[a]:04x} stock_n+1={ws[a]:04x} extra={wx[a]:04x}", "" if ws[a]==wx[a] else "  <-- extra != stock")
