#!/usr/bin/env python3
"""mk_testdisk.py: make the scratch test payload disk/MSTRACKS.TRK (NOT the product format: 'MSTK', version, 15 slots x 8 KB holding the 15 stock track blocks,
CRC32 of the body in the header; 122,892 B) and a 720 KB FAT12 floppy image disk/campaign.st holding it (mtools: mformat/mcopy)."""
import struct, sys, zlib, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "trackstudy"))
import msrtrack as M
(HERE / "disk").mkdir(exist_ok=True)
SLOT = 8192
body = b"".join(M.block(l)[2].ljust(SLOT, b"\0") for l in range(15))
data = b"MSTK" + struct.pack(">HHI", 1, 15, zlib.crc32(body) & 0xffffffff) + body
(HERE / "disk/MSTRACKS.TRK").write_bytes(data)
img = HERE / "disk/campaign.st"
img.unlink(missing_ok=True)
subprocess.run(["mformat", "-C", "-i", str(img), "-f", "720", "-v", "MSCAMP", "::"], check=True)
subprocess.run(["mcopy", "-i", str(img), str(HERE / "disk/MSTRACKS.TRK"), "::MSTRACKS.TRK"], check=True)
print(len(data), hex(zlib.crc32(data) & 0xffffffff))
