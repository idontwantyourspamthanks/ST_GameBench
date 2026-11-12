"""Run probe.s (standalone copy of jag_poll's probe with FALCON=1, assembled to PROBE.PRG: vasmm68k_mot -Ftos -m68000 -o PROBE.PRG probe.s) on every machine.
usage: probe_prg.py machine tos mem   (pad A configured; for a pad machine host keys Up / x / o are held in turn and the raw group longs at $70220 are printed)"""
import sys, time, re, shutil
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from stharness import Hatari, TOS
machine, tosname = sys.argv[1], sys.argv[2]
mem = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
import pathlib
extra = ['--joy1', 'none', '--configfile', '/home/ryan/Code/AtariST/midwinter2/work/jagpad/pad.cfg'] + (['--mmu', 'true'] if machine == 'tt' else [])
h = Hatari(game_dir='/tmp/jagprobe/det', snapshot=None, machine=machine, tos=TOS[tosname], memsize_kb=mem, autorun='C:\\PROBE.PRG', extra=extra)
def mem_(a, n):
    out = h.debug(f'm ${a:x} {n}', 0.8); b = []
    for ln in out.splitlines():
        m = re.match(r'([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ){1,16})', ln)
        if m: b += [int(x, 16) for x in m.group(2).split()]
    return bytes(b)
try:
    for _ in range(40):
        time.sleep(3)
        b = mem_(0x70200, 96)
        if len(b) >= 0x54 and b[0x50:0x54] == b'DONE': break
    print(f'== {machine} TOS {tosname}: probe verdict J_ST = {b[0]:#04x} (1 pad ports present, 0xff none) done={b[0x50:0x54]}')
    if b[0] == 1:
        def raw(): d = mem_(0x70220, 16); return [d[i:i+4].hex() for i in range(0, 16, 4)]
        print('  idle   groups 4,3,2,1 raw $ff9200:$ff9202 =', raw())
        for key, what in (('Up', 'Up (group 4)'), ('x', 'B (group 3)'), ('o', 'Option (group 1)')):
            h._xdo('keydown', '--window', h.win, key); time.sleep(1.5)
            print(f'  {what:18s}', raw()); h._xdo('keyup', '--window', h.win, key); time.sleep(0.5)
    print('  bus-error log lines:', [x for x in h._logtext().splitlines() if 'us error' in x.lower() or 'Bus Error' in x][:4])
finally:
    h.close()
