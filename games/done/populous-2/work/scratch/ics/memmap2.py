"""Pattern-fill test of a PATCHED ICS floppy: python3 memmap2.py <disk.st> <tag> <memKB>  (payload code intact + free tails untouched through a full game)"""
import sys, struct, time
exec(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks/dl.py').read())
img, tag, mem = sys.argv[1], sys.argv[2], int(sys.argv[3])
low = '--low' in sys.argv
top = mem*1024
OUT = Path('/tmp/icsmm')/tag; OUT.mkdir(parents=True, exist_ok=True)
def expect(a): return (a*2654435761+0x1234567) & 0xFFFFFFFF
def pat(lo, hi): return b''.join(struct.pack('>I', expect(a)) for a in range(lo, hi, 4))
import json
G2 = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2')
LJ = json.loads((G2/f"build/live/ics_{'low' if mem < 1024 else 'full'}.json").read_text()); LIMG = (G2/f"build/live/ics_{'low' if mem < 1024 else 'full'}.img").read_bytes()
LB = LJ['img_base']; LE = LB + len(LIMG)
if mem < 1024: RANGES = [(LE, 0x7fff8)]                        # the free tail of $7b380-$7ffff after our image
else: RANGES = [(0x7B380, 0x7fff8), (0x90000, 0xF8000)]      # below the payload, above the data-only blocks
h = boot2(img, tag, mem=mem)
bad = 0
def compare(d, step):
    global bad
    for lo, hi in RANGES:
        ch = [a for a in range(lo, hi, 4) if struct.unpack_from('>I', d, a)[0] != expect(a)]
        gr = []
        for a in ch:
            if gr and a-gr[-1][1] <= 16: gr[-1][1] = a+4
            else: gr.append([a, a+4])
        print(f'[{tag}] {step}: ${lo:x}-${hi:x} {len(ch)} longs changed', [(hex(a), hex(b)) for a, b in gr[:12]], flush=True)
        bad += len(ch)
    pd = [i for i in range(len(LIMG)) if LIMG[i] and d[LB+i] != LIMG[i]]
    print(f'[{tag}] {step}: payload ${LB:x}+{len(LIMG)}: {len(pd)} non-zero image bytes differ', flush=True); bad += len(pd)
def check(step):
    p = OUT/f'd_{step}.bin'
    h.dump(str(p), 0, top)
    for _ in range(60):
        if p.exists() and p.stat().st_size == top: break
        time.sleep(1)
    time.sleep(1)
    d = p.read_bytes(); compare(d, step); p.unlink()
try:
    cmds = ''
    for i, (lo, hi) in enumerate(RANGES):
        f = OUT/f'r{i}.bin'; f.write_bytes(pat(lo, hi)); cmds += f'loadbin {f} ${lo:x}\n'
    (OUT/'cmds.txt').write_text(cmds)
    h.cmd(f'hatari-debug b pc = $1770 :trace :once :file {OUT}/cmds.txt')
    print('menu', h.boot_to_menu(600) if hasattr(h,'boot_to_menu') else None, flush=True)
    check('menu')
    h._click(384, 257, 6); h._click(260, 98, 1.0)
    for ch in 'zeus': h.key(ch, 0.3); time.sleep(0.4)
    h.key('Return', 0.3); time.sleep(1.0)
    h._click(424, 418, 5); h._click(384, 258, 8); h._click(216, 448, 25)
    if not h.in_play(): h._click(400, 420, 14)
    print('in_play', h.in_play(), 'turn', h.peekw(h.TURN), flush=True)
    check('play')
    h.cmd('hatari-option --fast-forward on'); time.sleep(90)
    h.cmd('hatari-option --fast-forward off'); time.sleep(1)
    print('busy turn', h.peekl(0x3979a), flush=True)
    check('busy')
    for k in ('F1','1','2','3','4','5','F2','1','2','3','F3','1','2','F4','1','2','3','F5','1','2','3','F6','1','2','3'):
        h.key(k, 0.2); time.sleep(0.4); h._click(430, 300, 0.5)
    check('effects')
    r = save_load(h, 'T1'); print(r, flush=True)
    check('saveload')
    h._click(707, 374, 3); h._click(290, 194, 10); h._click(216, 448, 12); h._click(400, 420, 15)
    print('restart in play', h.in_play(), flush=True); check('restart')
    h._click(707, 374, 3); h._click(560, 194, 10); h._click(384, 258, 8); h._click(216, 448, 12); h._click(400, 420, 15)
    print('conquest2 in play', h.in_play(), flush=True); check('conquest2')
    h._click(707, 374, 3); h._click(560, 194, 10); h._click(384, 274, 10); time.sleep(3)
    print('custom in play', h.in_play(), flush=True)
    h.cmd('hatari-option --fast-forward on'); time.sleep(30); h.cmd('hatari-option --fast-forward off')
    check('custom')
finally:
    h.close()
print(f'[{tag}] RESULT', 'ALL INTACT' if not bad else f'{bad} changed')
