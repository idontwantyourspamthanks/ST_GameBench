"""FLOPPY odd-record gate: work/editor/e180.py transformed to run on the floppy build (lone --disk-a, real FDC): addresses mapped with tools/nefloppy.map_addr,
the level file reaches the store with Load from campaign disk (nebcampaign.py new --ovl), no snapshot.
usage: fo180.py GAME.st WORKDIR [ste|st|megaste] file.ovl... [--quick]"""
import sys, re
N = '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
sys.path.insert(0, N + 'work/gate_NebOddGateCore'); sys.path.insert(0, N + 'tools'); sys.path.insert(0, N + 'work/editor'); sys.path.insert(0, N + 'work/floppy')
import lib                                  # patches ed.grab with the robust savebin reader
from nebfloppy import NebFloppy
import nefloppy
M = nefloppy.map_addr
src = open(N + 'work/editor/e180.py').read()
def rep(a, b, cnt=None):
    global src
    assert a in src, a
    src = src.replace(a, b)
rep("from ui import *", "from ui import *\nfrom nebfloppy import NebFloppy\nimport nefloppy")
rep("DISK = '--disk' in args", "DISK = True")
rep("if DISK: args.remove('--disk')", "pass")
rep("SNAP = SNAP or f'/tmp/oddfix/title_{MACH}.sav'", "SNAP = '/nonexistent'")
rep("if not os.path.exists(SNAP):", "if False:")
for a in ('0x3ad98', '0x3ad9e'):
    rep(a, hex(M(int(a, 16))))
rep("$3d116", "$%x" % M(0x3d116))
rep("/tmp/oddfix", "/tmp/oddcore/fo")
rep("h = Nebulus(snapshot=SNAP, workdir=f'{WD}_{os.path.splitext(name)[0]}', game=gd(GAMEDIR), **kw())",
    "h = NebFloppy(GAMEDIR, machine=MACH, mem=(4096 if MACH == 'megaste' else 1024), workdir=f'{WD}_{os.path.splitext(name)[0]}', trace='fdc')\n    print('title', h.boot_to_title(timeout=400, space_at=(25 if MACH == 'megaste' else 20)), flush=True)")
rep("        time.sleep(2)\n        if DISK:", "        time.sleep(3)\n        if DISK:")
sys.argv = [sys.argv[0]] + sys.argv[1:]
os_makedirs = __import__('os').makedirs('/tmp/oddcore/fo', exist_ok=True)
src = src.replace("/tmp/e180_{MACH}.log", "/tmp/oddcore/fo/e180_{MACH}.log")
exec(compile(src, 'e180_floppy', 'exec'))
