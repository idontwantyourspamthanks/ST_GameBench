"""Cold-boot gate for the default set incl. np_lift: NEPO marker, site count, np_lift site bytes, trainer T/E flags, F10 -> editor hook."""
from lp import *
import subprocess
outs = subprocess.run(['python3', str(NEB / 'tools/nepatch.py'), 'build', '--out', '/tmp/lp/patched2'], capture_output=True, text=True).stdout
print(outs.strip().splitlines()[-1])
h = mk('/tmp/lp/patched2', '/tmp/lp/w_cold')
try:
    print('boot to tower:', boot_tower(h, 'ste'))
    print('marker $b0020', rd(h, 0xb0020, 4), '(4e45504f = NEPO)')
    print('site count $b0024', int.from_bytes(rd(h, 0xb0024, 2), 'big'))
    for a, n in ((0x37c42, 14), (0x37c74, 14), (0x37c96, 14), (0x37d0c, 16), (0x37d5a, 16), (0x37d90, 16)):
        print(f'${a:x}', rd(h, a, n).hex())
    for key, flag in (('t', 0x76c02), ('e', 0x76c04)):
        before = int.from_bytes(rd(h, flag, 2), 'big')
        h.key(key, hold=1.0); time.sleep(0.6)
        print(f'trainer {key}: {before:#06x} -> {int.from_bytes(rd(h, flag, 2), "big"):#06x}')
    h.key('t', hold=1.0); time.sleep(0.4); h.key('e', hold=1.0); time.sleep(0.4)   # back off
    n0 = len(h._logtext())
    h.cmd('hatari-debug b pc = $7574c :trace'); time.sleep(0.3)
    h.key('F10', hold=0.5); time.sleep(1.5)
    print('editor title-poll hook hits after F10:', h._logtext()[n0:].count('matched'))
    h.shot('/tmp/lp/cold_editor.png')
    h.debug('b all', 0.3)
finally:
    h.close()
