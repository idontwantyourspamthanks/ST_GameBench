"""Gate (b)/(c)/(d): the full floppy cell with the FDC trace, one drive or two.

    python3 cell16.py NAME MACHINE TOS MEM_KB DISKDIR CLK DRIVES [--soak SECS] [--ext st|msa]

MACHINE ste|megaste|st|tt; TOS 162|206|104|306; CLK 8|16 (16: runtime `--cpuclock 16` right after the start, held for the whole run);
DRIVES 1 = drive A only (`--drive-b false`), 2 = drive B holds the created campaign disk (work/disk_overlay/FILES/FFD) from the start.
Cold boot of DISKDIR/FFA_boot.st with `--fastfdc no --trace fdc`; at the orange "Insert Graphics Disk" prompt drive A is swapped to
FFB_graphics.st (the game has no change detection), key, M/J/K, HQ hall, personnel, map, Lobos, boss screen, 3D view; then the soak
(`--soak`: seconds of play with a fps / state check every 30 s).  The game's security check is skipped by the shipped trampoline itself (checked:
$2c574 = $6002); nothing is poked.  Results: work/floppy16/out/NAME.txt; the FDC trace is analysed for the game's first restore and for
any type I command cut by the game's own force interrupt.
"""
import os, sys, time, shutil, json, traceback
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GB = ROOT.parent.parent.parent
os.environ['HOME'] = '/tmp/mw2f/home'
os.environ['HATARI'] = os.environ.get('HATARI', '/home/ryan/Code/AtariST/hattari/build/src/hatari')
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
from mw2harness import Hatari
import fdctrace as F
from PIL import Image, ImageChops, ImageStat

a = sys.argv[1:]
name, machine, tosk, mem, diskdir, clk, drives = a[:7]
opts = a[7:]
soak = int(opts[opts.index('--soak') + 1]) if '--soak' in opts else 0
ext = opts[opts.index('--ext') + 1] if '--ext' in opts else 'st'      # st | msa: use the .msa copies of FFA and FFB
TOSF = {'162': 'TOS_1_62.img', '206': 'TOS_2_06.img', '104': 'TOS_1_04.img', '306': 'TOS_3_06_uk.img'}
diskdir = Path(diskdir).resolve()
scr = Path('/tmp/mw2f') / name
shutil.rmtree(scr, ignore_errors=True); scr.mkdir(parents=True)
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
log = []
def L(*x):
    s = ' '.join(str(v) for v in x); log.append(s); print(s, flush=True)

for src, dst in (('FFA_boot', 'disk_boot'), ('FFB_graphics', 'disk_gfx')):      # not A/B.st: Hatari auto-inserts <x>B.st into drive B
    shutil.copy(diskdir / f'{src}.{ext}', scr / f'{dst}.{ext}')
if drives == '2':
    shutil.copy(ROOT / 'work/disk_overlay/FILES/FFD', scr / 'disk_camp.st')
shutil.copy(diskdir / 'FFC_missions.st', scr / 'disk_miss.st')
if drives == '1':
    shutil.copy(ROOT / 'work/disk_overlay/FILES/FFD', scr / 'disk_camp.st')
(scr / 'empty').mkdir()
tracef = scr / 'fdc.trace'
extra = ['--disk-a', str(scr / f'disk_boot.{ext}'), '--fastfdc', 'no', '--trace', 'fdc', '--trace-file', str(tracef)]
extra += ['--disk-b', str(scr / 'disk_camp.st')] if drives == '2' else ['--drive-b', 'false']
if machine == 'tt':
    extra += ['--mmu', 'true']
ok = False
h = None
try:
    T0 = time.time()
    h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=GB / 'tos' / TOSF[tosk], game_dir=scr / 'empty',
               workdir=str(scr / 'run'), extra=extra)
    if clk != '8':
        h.set_cpuclock(int(clk))
    L(f'{name}: {machine} TOS {tosk} {mem} KB, {clk} MHz, {drives} drive(s), disks {diskdir}')
    ins = ROOT / 'work/floppy_tests/ref_insert_graphics.png'
    box = (280, 360, 560, 420)

    def sdiff(refp, bx):
        img = Image.open(h.shot()).convert('RGB')
        sb = (bx[0] - 96, bx[1] - 58, bx[2] - 96, bx[3] - 58) if img.width == 640 else bx      # TT screenshots have no border
        d = ImageChops.difference(img.crop(sb), Image.open(refp).convert('RGB').crop(bx))
        return sum(ImageStat.Stat(d).mean) / 3
    def mean_bright():
        im = Image.open(h.shot()).convert('RGB')
        bx = (0, 0, im.width, im.height - 40) if im.width == 640 else (96, 58, 736, 458)
        return sum(ImageStat.Stat(im.crop(bx)).mean) / 3
    served = []

    def service():
        """ONE drive: the game's black 'Insert X Disk / press any key' screen asks for the disk whose name string it compares ([$93ca] -> 'graf' / 'camp' / 'mission' / 'pers');
        put that disk into drive A (what a player does) and press a key."""
        if drives != '1' or mean_bright() > 8:
            return False
        time.sleep(2.5)                                 # a fade to black while loading is not a prompt: it must stay black (and no FDC traffic-free text shows)
        if mean_bright() > 8 or mean_bright() < 0.05:
            return False
        def peek(addr, n):
            ln = h.debug(f'm ${addr:x} {n}').strip().splitlines()[-1].split(':', 1)[1]
            return bytes(int(x, 16) for x in ln[:3 * n].split())
        ptr = int.from_bytes(peek(0x93ca, 4), 'big')
        s = peek(ptr, 8).split(b'\0')[0].decode('latin1')
        disk = {'graf': 'disk_gfx.' + ext, 'camp': 'disk_camp.st', 'miss': 'disk_miss.st'}.get(s[:4])
        if disk is None:
            return False
        h.cmd(f"hatari-option --disk-a {scr / disk}"); time.sleep(1.5)
        h.cmd('hatari-event keypress 57')
        served.append((round(time.time() - T0), s, disk))
        L('swap served: game asks for %r -> %s' % (s, disk))
        time.sleep(4)
        return True
        return True

    def pause(secs):
        t = time.time()
        while time.time() - t < secs:
            time.sleep(min(3, secs))
            service()
    t0 = time.time()
    while time.time() - t0 < 420:
        time.sleep(4)
        if sdiff(ins, box) < 0.3:
            break
    else:
        raise RuntimeError('never saw the Insert Graphics Disk prompt')
    L('insert-graphics prompt after %.0f s wall' % (time.time() - t0))
    h.cmd(f"hatari-option --disk-a {scr / f'disk_gfx.{ext}'}"); time.sleep(2)
    ref = ROOT / 'work/ref/mode_select.png'
    for i in range(40):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError('never reached the M/J/K screen')
    L('M/J/K screen after', i, 'presses; MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    L('security-check site $2c574:', h.debug('m $2c574 2').strip().splitlines()[-1])
    for _ in range(5):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(5)
        if not h.screen_matches(ref, (280, 350, 560, 420)):
            break
    FT = ROOT / 'work/floppy_tests'
    HALL = (FT / 'ref_hall.png', (96, 350, 736, 458))
    PERS = (FT / 'ref_personnel.png', (96, 100, 330, 350))
    MAP = (FT / 'ref_map.png', (96, 300, 560, 458))

    def wait_match(target, timeout):
        t = time.time()
        while time.time() - t < timeout:
            if sdiff(*target) < 4:
                return True
            if not service():
                time.sleep(3)
        return False

    def step(point, target, timeout=40):
        for attempt in range(4):
            h.goto(*point); h.click()
            if wait_match(target, timeout):
                return attempt
        raise RuntimeError(f'click at {point} never produced the expected screen')
    if not wait_match(HALL, 120):
        raise RuntimeError('never saw the HQ hall')
    L('hall; personnel click tries', step((554, 105), PERS))
    L('use-this-agent click tries', step((389, 140), HALL))
    L('control-door click tries', step((414, 185), MAP, timeout=100))
    pause(25)
    h.goto(150, 280); h.key('space'); pause(18)
    h.goto(230, 410); h.click(); pause(15)
    boss = ROOT / 'work/ref/boss_thumbs.png'
    for _ in range(6):
        h.goto(140, 415); h.click(); pause(8)
        if h.screen_matches(boss, (590, 60, 740, 125)):
            break
    else:
        raise RuntimeError('never reached the boss screen')
    h.goto(625, 92); h.click(); pause(40)
    for _ in range(12):
        if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2:
            break
        pause(5)
    else:
        raise RuntimeError('did not reach the 3D view')
    pause(30)
    h.center()
    L('3D view shot', h.shot(OUT / f'{name}_3d.png'))
    L('$6220=%x $700a=%x' % (h.peekw(0x6220), h.peekw(0x700A)), 'MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(10)
    r = h.world_rate(vbls=500); L('world_rate', r)
    hd = [h.peekw(0x6742)]
    h.rel(-150, 0)
    for i in range(8):
        time.sleep(1.5); hd.append(h.peekw(0x6742))
    L('heading series', [hex(x) for x in hd])
    if soak:
        t = time.time(); n = 0
        while time.time() - t < soak:
            h.rel(0, -120); time.sleep(2); h.center()
            time.sleep(28)
            f = h.fps(250)
            L('soak %3d s: fps %.1f flips %d  $6220=%x $700a=%x heading %x' % (time.time() - t, f['fps'], f['flips'], h.peekw(0x6220), h.peekw(0x700A), h.peekw(0x6742)))
            n += 1
        h.shot(OUT / f'{name}_soak.png')
    L('REACHED 3D VIEW and played %d s' % soak)
    ok = True
except Exception as e:
    L('EXC', repr(e)); L(traceback.format_exc())
    try:
        h.shot(OUT / f'{name}_exc.png')
    except Exception:
        pass
finally:
    if h:
        h.close()
ev, Lf, hz = F.parse(tracef)
L(f'trace: frame {Lf} lines = {hz:.1f} Hz')
c = F.first_game_restore(ev)
if c:
    e = c['start']
    L('first game restore: tr=%s head_track=%s -> %s after %.3f s' % (F.field(e['text'], 'tr'), F.field(e['text'], 'head_track'), c['how'], c['dur'] or -1))
cmds = F.game_type1(ev)
(OUT / f'{name}.cmds.txt').write_text('\n'.join(F.summary_line(x) for x in cmds) + '\n')
cuts = [x for x in cmds if x['how'] == 'FORCE-INT']
L('game type I commands: %d, cut by the game\'s force interrupt: %d' % (len(cmds), len(cuts)))
for x in cuts[:10]:
    L('  CUT:', F.summary_line(x))
durs = sorted((x['dur'], x['start']['text'].split()[3]) for x in cmds if x['dur'] is not None and x['how'] == 'complete')
if durs:
    L('longest completed game type I commands (s):', ', '.join('%.2f %s' % d for d in durs[-4:]))
L('CELL %s: %s' % (name, 'PASS' if ok and not cuts else ('PASS (no 3D failure) but %d cut commands' % len(cuts) if ok else 'FAIL')))
(OUT / f'{name}.txt').write_text('\n'.join(log) + '\n')
sys.exit(0 if ok else 1)
