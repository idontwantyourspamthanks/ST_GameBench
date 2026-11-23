"""np_shot site -> floppy address and equivalence check (read-only use of tools/nefloppy.py)."""
import sys, hashlib
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
import nefloppy as nf, nepatch
disk = nf.Disk(nf.SRC_IMG.read_bytes())
jmp0 = disk.read(disk.find(b"TOPPLER JMP"))
img = bytearray(nf.FILE_END - nf.BASE); img[0:28] = jmp0[0:28]
rel = nf.relocated(jmp0); img[28:28 + len(rel)] = rel
pp = nepatch.predicted_stage2(hook=False)
for a, n in ((0x3b87a, 4), (0x3b860, 40)):
    fa = nf.map_addr(a)
    print('PP $%x (%d B) -> floppy $%x' % (a, n, fa))
    print('  PP bytes     ', bytes(pp[a:a + n]).hex())
    print('  floppy bytes ', bytes(img[fa - nf.BASE:fa - nf.BASE + n]).hex())
    print('  site_equivalent', nf.site_equivalent(pp, img, a, n))
for a in (0x3b7c6, 0x3b7b6):
    fa = nf.map_addr(a)
    print('mask table PP $%x -> floppy $%x : equal %s' % (a, fa, bytes(pp[a:a + 16]) == bytes(img[fa - nf.BASE:fa - nf.BASE + 16])))
