import sys, time
exec(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks/dl.py').read())
img, tag, mem = sys.argv[1], sys.argv[2], int(sys.argv[3])
machine = sys.argv[4]; tos = sys.argv[5]
extra = sys.argv[6].split() if len(sys.argv) > 6 else []
h = boot2(img, tag, mem=mem, machine=machine, tos=tos, extra=extra)
try:
    print('menu', h.boot_to_menu(240), flush=True)
    print('37a96', hex(h.peekl(0x37a96)), hex(h.peekw(0x37a9a)), 'flag 86fb0', hex(h.peekw(0x86fb0)), 'marker', h.marker(), 'vbl', hex(h.peekl(0x70)), flush=True)
    snap(h, 'dbg')
finally:
    h.close()
