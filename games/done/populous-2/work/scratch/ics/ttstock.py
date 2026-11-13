"""Stock ICS crack (unpatched) on a TT: sync forced to 50 Hz at the game entry so the PAL check passes; does it stop at INSERT POPULOUS-II DISK?  python3 ttstock.py <tag> <cpuclock|0>"""
import sys, time
exec(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks/dl.py').read())
tag, clk = sys.argv[1], int(sys.argv[2])
OUT = D/'run'; cmds = OUT/f'{tag}_cmds.txt'; cmds.write_text('w $ff820a $02\n')
extra = ['--mmu', 'true'] + (['--cpuclock', str(clk)] if clk else [])
h = boot2(D/'ICS91.st', tag, mem=4096, machine='tt', tos='3.06', extra=extra)
try:
    h.cmd(f'hatari-debug b pc = $140 :trace :once :file {cmds}')
    t0 = time.time(); ok = False
    time.sleep(10)
    while time.time() - t0 < 300:
        h.key('space', 0.6); time.sleep(6)
        if h.peekl(0x70) == 0x18fa: ok = True; break
    time.sleep(40)
    print(tag, 'cpuclock', clk or 'default', 'game vbl installed', ok, 'sync', hex(h.peekw(0xff820a) >> 8), 'turn', h.peekw(h.TURN), flush=True)
    snap(h, 'stock_tt')
    print('shot', D/'shots'/f'{tag}_stock_tt.png')
finally:
    h.close()
