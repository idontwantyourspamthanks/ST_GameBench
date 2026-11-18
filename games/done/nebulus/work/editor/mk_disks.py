#!/usr/bin/env python3
"""Test disks for the campaign-disk gates -> /tmp/ne/d/: blank, t3 (valid, 1 level / 1 campaign), nofile (FAT12 without NEBLEVEL.OVL), short (4096 B file),
big (NEBLEVEL.OVL 8192 B of text = not a campaign), plus the 22 fuzz files of e90.py as fz_NN_<name>.st."""
import random, subprocess, sys, struct, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
import nebcampaign as nc, ovl
D = Path("/tmp/ne/d"); D.mkdir(parents=True, exist_ok=True)
subprocess.run([sys.executable, str(Path(__file__).parent / "ovl.py"), "test3", "/tmp/t3.ovl"], check=True)
base = bytearray(open("/tmp/t3.ovl", "rb").read())
(D / "blank.st").write_bytes(nc.build())
(D / "t3.st").write_bytes(nc.build(bytes(base)))
for n, ser in (("nofile", b"\x01\x02\x03"), ("short", b"\x04\x05\x06")):
    img = bytearray(nc.build()); 
    img[8:11] = ser
    d0 = nc.DIR0
    if n == "nofile":
        img[d0 + 32:d0 + 64] = bytes(32)                  # no file entry
    else:
        struct.pack_into("<L", img, d0 + 32 + 28, 4096)     # size 4096
    (D / f"{n}.st").write_bytes(bytes(img))
(D / "big.st").write_bytes(nc.build((b"Not a campaign disk. " * 400)[:8192]))
rng = random.Random(20261118)
files = []
for i in range(5): files.append(("random%d" % i, bytes(rng.randrange(256) for _ in range(8192))))
b = bytearray(8192); b[:4] = b"NCMP"
for i in range(4, 8192): b[i] = rng.randrange(256)
files.append(("magic+random", bytes(b)))
for k in (1, 2, 3, 5, 8, 12):
    b = bytearray(base)
    for _ in range(k): b[rng.randrange(8, 700)] = rng.randrange(256)
    files.append((f"flip{k}", bytes(b)))
b = bytearray(base); b[300:] = bytes(8192 - 300); files.append(("truncated300", bytes(b)))
b = bytearray(base); b[5] = 2; files.append(("version2", bytes(b)))
b = bytearray(base); b[6:8] = b"\x00\x7f"; files.append(("nlev127", bytes(b)))
b = bytearray(base); b[8:10] = b"\x00\xc8"; files.append(("ncamp200", bytes(b)))
b = bytearray(base); b[274] = 0; files.append(("rows0", bytes(b)))
b = bytearray(base); b[274] = 255; files.append(("rows255", bytes(b)))
b = bytearray(base); b[276:278] = b"\xff\xff"; files.append(("len65535", bytes(b)))
b = bytearray(base); b[16 + 12] = 255; b[16 + 14:16 + 30] = bytes([255] * 16); files.append(("camp255", bytes(b)))
b = bytearray(base); b[16 + 14:16 + 17] = bytes([0x7f, 0x90, 0x05]); files.append(("badentries", bytes(b)))
files.append(("valid", bytes(base)))
for n, (name, data) in enumerate(files):
    (D / f"fz_{n:02d}_{name.replace('+','_')}.st").write_bytes(nc.build(data))
    (D / f"fz_{n:02d}_{name.replace('+','_')}.ovl").write_bytes(data)
print(len(files), "fuzz files + 5 test disks in", D)
