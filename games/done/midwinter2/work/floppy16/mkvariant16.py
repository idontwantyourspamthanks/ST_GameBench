"""Negative-control variants of a v1.6 set: mkvariant16.py SRC_DIR DST_DIR (nowait|nonflops|nopark)
nowait   : fdctab68 value $000a0000 -> $00050000 (stock game FDC wait on a 68000; the head is still parked)
nonflops : the nodrb entry ($28b46 <- $0000) is dropped: the table terminator moved to its start (stock single-drive behaviour)
nopark   : stage 1's `bsr.w $4dcb8` (head park) -> nop nop (the stub file is rewritten in the boot track, the dir has no checksum for it)
Fixes the directory XOR of file 10.  The files are test-only."""
import sys, shutil, struct
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'realfloppy'))
from ffa import FFA
src, dst, kind = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
dst.mkdir(parents=True, exist_ok=True)
for f in src.glob('FF*'): shutil.copy(f, dst / f.name)
a = FFA(str(dst / 'FFA_boot.st'))
if kind in ('nowait', 'nonflops'):
    d = bytearray(a.read(10))
    if kind == 'nowait':
        pat = bytes.fromhex('00027cb00004000a0000')       # dc.l $27cb0 / dc.w 4 / dc.l $a0000
        new = bytes.fromhex('00027cb0000400050000')
    else:
        pat = bytes.fromhex('00028b46000200000000' '00028b24000200007000' '00000000')  # nodrb: two entries and the terminator
        new = bytes(len(pat))
    assert d.count(pat) == 1, (kind, d.count(pat))
    i = d.index(pat)
    d[i:i + len(pat)] = new                          # nonflops: the nodrb table becomes all zero (address 0 = terminator)
    a.write(10, bytes(d)); e = a.entry(10)
    a.b[e['o']:e['o'] + 2] = struct.pack('>H', FFA.xor(bytes(d)))
else:
    assert kind == 'nopark'
    o = 0x200 + 0x4ddaa - 0x4d9a6
    st1 = bytes(a.b[o:o + 36])
    pat = bytes.fromhex('6100fef2')
    assert st1.count(pat) == 1, st1.hex()
    j = o + st1.index(pat)
    a.b[j:j + 4] = bytes.fromhex('4e714e71')
open(dst / 'FFA_boot.st', 'wb').write(a.b)
print('ok', kind)
