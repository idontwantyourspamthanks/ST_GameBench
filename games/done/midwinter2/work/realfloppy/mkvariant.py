"""mkvariant.py SRC_DIR DST_DIR TIMEOUT_HEX  -- copy a floppy set, set the game's FDC wait long at $27cb0 (default $50000), fix the dir xor."""
import sys, shutil, struct
from pathlib import Path
from ffa import FFA
src, dst, to = Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3], 16)
dst.mkdir(parents=True, exist_ok=True)
for f in src.glob('FF*'): shutil.copy(f, dst/f.name)
a = FFA(str(dst/'FFA_boot.st')); d = bytearray(a.read(9))
i = 0x27cb0 - 0x3104
assert d[i-2:i] == bytes.fromhex('203c') and d[i:i+4] == bytes.fromhex('00050000'), d[i-2:i+6].hex()
d[i:i+4] = struct.pack('>I', to)
a.write(9, bytes(d)); e = a.entry(9); ck = FFA.xor(bytes(d))
a.b[e['o']:e['o']+2] = struct.pack('>H', ck)
open(dst/'FFA_boot.st', 'wb').write(a.b)
print('ok', hex(to), 'cksum', hex(ck))
