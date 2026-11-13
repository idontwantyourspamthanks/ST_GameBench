"""Three saves fill the ICS floppy (3 x 56,690 B); a 4th must fail cleanly; every save loads back.  python3 saves3.py <disk> <tag> <memKB> [machine tos]"""
import sys, time, subprocess
exec(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks/dl.py').read())
img, tag, mem = sys.argv[1], sys.argv[2], int(sys.argv[3])
kw = dict(machine=sys.argv[4] if len(sys.argv) > 4 else 'ste')
if len(sys.argv) > 5: kw['tos'] = sys.argv[5]
h = boot2(img, tag, mem=mem, **kw)
def mdir():
    return subprocess.run(['mdir', '-i', str(h.cp), '::'], capture_output=True, text=True).stdout
def save(name):
    h._click(707, 374, 3); h._click(535, 178, 4)           # requester -> SAVE GAME
    h._click(470, 370, 1.0)
    for i in range(12): h.key('BackSpace', 0.15)
    for ch in name: h.key(ch.lower(), 0.3); time.sleep(0.3)
    h.key('Return', 0.3); time.sleep(1)
    h._click(288, 418, 12)                                  # SAVE
    snap(h, f's_{name}')
def load(name):
    h._click(707, 374, 3); h._click(318, 178, 4)           # requester -> LOAD GAME (the list shows the saves)
    snap(h, f'l_{name}_list')
try:
    r = to_play(h); print(r, flush=True)
    res = {}
    for n in ('A1', 'A2', 'A3'):
        t = h.peekw(h.TURN); save(n); res[n] = dict(turn=t, play=h.in_play()); time.sleep(8)
        print(n, res[n], [l for l in mdir().splitlines() if 'GAM' in l], flush=True)
    print('free after 3 saves:', mdir().strip().splitlines()[-1], flush=True)
    t = h.peekw(h.TURN); save('A4'); time.sleep(3); snap(h, 'a4_after')
    h._click(416, 178, 2); snap(h, 'a4_ok')                  # dismiss DISK FILE ERROR
    h._click(560, 418, 3); snap(h, 'a4_cancel')              # CANCEL the requester
    print('A4 (disk full, expected DISK FILE ERROR): in_play after OK+CANCEL', h.in_play(), flush=True)
    t3 = res['A3']['turn']
    h._click(707, 374, 3); h._click(318, 178, 4)             # LOAD GAME
    h._click(470, 370, 1.0)
    for i in range(12): h.key('BackSpace', 0.15)
    for ch in 'a3': h.key(ch, 0.3); time.sleep(0.3)
    h.key('Return', 0.3); time.sleep(1); h._click(288, 418, 12); snap(h, 'a3_loaded')
    print('LOAD A3 (saved at turn %d): turn now %d, in_play %s' % (t3, h.peekw(h.TURN), h.in_play()), flush=True)
    h.cmd('hatari-shortcut quit'); time.sleep(3)
    print('GAM files:', [l for l in mdir().splitlines() if 'GAM' in l], mdir().strip().splitlines()[-1], flush=True)
    print(subprocess.run(['fsck.fat', '-n', str(h.cp)], capture_output=True, text=True).stdout[-300:])
finally:
    h.close()
