"""Regenerate dist/Midwinter2_patched_2026-11-08.zip (layout of the previous zip: MW2PATCH/ with the
build/game files, PATCHES.TXT, the shipped blank FILES/FFD)."""
import zipfile, time
from pathlib import Path
B = Path('build/game'); OUT = Path('dist/Midwinter2_patched_2026-11-08.zip')
patches = """Midwinter 2 (HAGA HD version by PP) - patched build, 2026-11-08

Changes vs the original HAGA release:
- Game speed is fixed to real time: the world no longer speeds up on
  faster machines (Mega STE 16 MHz, TT, Falcon, accelerators).
- On foot, movement is smooth at whatever frame rate the machine manages.
- About 15% faster 3D display on a stock 8 MHz ST/STE, pixel-identical.
- Direct controls: the mouse turns only while it moves; joystick/keyboard
  turn at a constant rate while held and stop on release.
- No grey fading while loading.
- fixed: >=4 MB hang. With 4 MB or more RAM on an ST/STE/Mega STE, earlier
  patched builds stopped at the orange "Flames of Freedom" title. PP's loader
  caches whole disk images in RAM from 4 MB up, which overwrote the patch code
  (the unpatched game was fine). The patched build now keeps the loader's
  200 KB chunked caching on those machines, as on 1-2 MB; loading takes a few
  seconds longer than the unpatched game does at 4 MB. TT/Falcon are unchanged.

Requirements and usage are as in README.TXT (1 MB RAM minimum).
Run RUNME.TOS from a hard disk / GEMDOS drive.
Create a campaign first: War Room -> Start New Campaign (copies the
missions disk into FILES\\FFD), then Control.
Tested on Hatari: ST (TOS 1.04) and STE (TOS 1.62) at 1 and 4 MB, Mega STE
(TOS 2.06) at 1, 2, 4, 8 and 14 MB, STE 16 MHz; TT/Falcon/Mega STE with EmuTOS.
"""
entries = ['RUNME.TOS', 'SOLUTION.TXT', 'FFF273.HST', 'LFF273.HST', 'FILES/', 'FILES/FFB', 'FILES/FFD',
           'FILES/FFE', 'FILES/FFC', 'FILES/FFA', 'README.TXT', 'PATCHES.TXT', 'HAGA', 'LOG.TXT', 'FF240R.BMP']
OUT.parent.mkdir(exist_ok=True)
now = time.localtime()[:6]
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    def add(name, data, method):
        zi = zipfile.ZipInfo('MW2PATCH/' + name, now); zi.compress_type = method
        zi.external_attr = (0o40755 << 16 | 0x10) if (name == '' or name.endswith('/')) else (0o100644 << 16)
        z.writestr(zi, data)
    add('', b'', zipfile.ZIP_STORED)
    for e in entries:
        if e.endswith('/'): add(e, b'', zipfile.ZIP_STORED)
        elif e == 'PATCHES.TXT': add(e, patches.encode(), zipfile.ZIP_DEFLATED)
        else: add(e, (B / e).read_bytes(), zipfile.ZIP_DEFLATED)
print('wrote', OUT)
