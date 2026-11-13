"""Cold boot a built ICS floppy: python3 boot1.py <disk.st> <tag> <memKB> [machine tos]  -> menu, marker, play, screenshots"""
import sys, time
exec(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks/dl.py').read())
img, tag, mem = sys.argv[1], sys.argv[2], int(sys.argv[3])
machine = sys.argv[4] if len(sys.argv) > 4 else 'ste'
tos = sys.argv[5] if len(sys.argv) > 5 else None
kw = dict(machine=machine)
if tos: kw['tos'] = tos
h = boot2(img, tag, mem=mem, **kw)
try:
    r = to_play(h)
    print(tag, r, 'marker', h.marker(), hex(h.peekl(0x70)), 'turn', h.peekw(h.TURN), flush=True)
    snap(h, 'final')
    print('log errors:', [l for l in h._logtext().splitlines() if 'rror' in l][:6])
finally:
    h.close()
