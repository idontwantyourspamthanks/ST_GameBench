import sys, time
from pathlib import Path
from PIL import Image
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(G / 'work/vehicles_p3b')); sys.path.insert(0, str(G / 'tools')); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
import vt
from stharness import TOS
import mw2raids
out = G / 'work/mask'
h = vt.Hatari(snapshot=None, memsize_kb=4096, game_dir=G / 'build' / 'game', machine='tt', tos=TOS['3.06'], extra=['--mmu', 'true'])
def snap(name):
    im = Image.open(h.shot()).convert('RGB')
    im = im.crop((0, 0, 640, 400) if im.width == 640 else (96, 58, 736, 458))
    im.save(out / name)
try:
    t0 = time.time()
    time.sleep(70)
    ref = G / 'work' / 'ref' / 'mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): print('M/J/K', flush=True); break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): print('M accepted', flush=True); break
    time.sleep(45)
    mw2raids._enter_raids_from_hall(h)
    print('raid map %.0f s' % (time.time() - t0), flush=True)
    r = mw2raids.enter_raid(h, 275, 249)
    print('entered', r, 'marker', vt.memb(h, 0xb2ff8, 4), flush=True)
    time.sleep(6); snap('tt_00_boat.png'); h.savemem('/tmp/mask/tt_boat.sav')
    h.key('Escape', hold=0.6)
    k = 0; last = None; n21 = 0; bad = 0; t1 = time.time()
    while time.time() - t1 < 240 and n21 < 8:
        ty = h.peekw(0x6220); kb = vt.memb(h, 0xb4680, 8)
        if ty != last or ty == 0x15 or k % 10 == 0:
            snap(f'tt_{k:03d}_t{ty:02x}.png')
            print('tt', k, 'type', hex(ty), '6884', hex(h.peekw(0x6884)), '764c', hex(h.peekw(0x764c)), '6746', hex(h.peekw(0x6746)), '6886', hex(h.peekw(0x6886)), 'KB', [f'{b:02x}' for b in kb], flush=True)
        if ty == 0x15:
            n21 += 1
            if kb[0:2] != b'\0\0' or kb[2:4] != b'\0\0': bad += 1
        last = ty; k += 1; time.sleep(0.35)
    print('type21 samples', n21, 'with KB!=0', bad, flush=True)
    time.sleep(3)
    ty = h.peekw(0x6220); kb = vt.memb(h, 0xb4680, 8); snap('tt_99_final.png')
    print('final type', hex(ty), 'KB', [f'{b:02x}' for b in kb], flush=True)
    print('bus errors', sum('Bus Error' in l for l in h._logtext().splitlines()), flush=True)
finally:
    h.close()
