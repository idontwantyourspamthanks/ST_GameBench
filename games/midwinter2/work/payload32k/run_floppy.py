"""Floppy-build acceptance cell (T1/T2/T3): cold boot from floppy images to the Lobos 3D view.

    python3 work/floppy_tests/run_cell.py NAME MACHINE TOS MEM_KB DISKDIR CLK [ref=PATH]

DISKDIR holds FFA_boot.st FFB_graphics.st (and optionally FFD_campaign.st; default: the
created campaign disk work/disk_overlay/FILES/FFD).  Drive A boots FFA and is then swapped to
the graphics disk at the game's "Insert Graphics Disk" prompt; drive B holds the campaign disk
from the start (the game finds it there without a prompt).  CLK = 0: stay at 8 MHz;
N: measure at 8 MHz first, then at N MHz; preN: set N MHz before the walk (T3).

TEST-ONLY: the game's own security check (identify a Secret Police member from the manual,
sub_02d65a) is skipped by writing PP's `$6002` bra.s to $2c574 from the debugger once the
M/J/K screen is up.  The floppy build itself does NOT contain this bypass.
"""
import json, os, shutil, sys, time, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from mw2harness import Hatari
from PIL import Image, ImageChops, ImageStat

B = Path.home() / "Emulators/BIOS/AtariST"
TOS = {'162': B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img",
       '104': B / "TOS v1.04 (1989)(Atari Corp)(Mega ST)(GB)[Rainbow TOS].img"}
name, machine, tos, mem, diskdir, clk, sset = sys.argv[1:8]
diskdir = Path(diskdir)
out = ROOT / "work" / "payload32k"
import struct
import mw2patch as M
res = {'cell': name, 'log': []}


allp = M.load_patches()
want = [p for p in allp if (p.default and (p.media in (None, 'floppy'))) or
        (sset in ('blob', 'fill') and p.name == 'test_blob16k') or (sset == 'fill' and p.name == 'zz_tmp_fill')]
img, sites = M.build_image(want, floppy=True)
datar = [(a, a + l) for p in want for a, l in p.data]
PAT = b'MW2-TEST-BLOB16K' + b''.join(struct.pack('>H', (0xB6010 + 2 * i) & 0xFFFF) for i in range(8184))


def check(tag):
    p = h.R / f'pl_{tag}.bin'
    if p.exists(): p.unlink()
    h.debug(f'savebin {p} 0xb2ff8 0x8008', 3.0)
    b = p.read_bytes(); marker, ram = b[:4], b[8:]
    diff = [i for i in range(0x8000) if ram[i] != img[i]]
    runs = []
    for i in diff:
        a = 0xB3000 + i
        if runs and a - runs[-1][1] <= 1: runs[-1][1] = a
        else: runs.append([a, a])
    un = [r for r in runs if not any(d0 <= r[0] and r[1] < d1 for d0, d1 in datar)]
    L(f'[{tag}] marker {marker!r}  payload $B3000-$BAFFF: {len(diff)} of 32768 bytes differ from the built image, '
      f'{len(runs)} runs, outside declared data: {[(hex(a), hex(b)) for a, b in un]}')
    L(f'[{tag}]   differing runs: {[(hex(a), hex(b)) for a, b in runs][:14]}')
    if sset in ('blob', 'fill'):
        L(f'[{tag}]   $B6000-$B9FFF == recognisable pattern: {ram[0x3000:0x7000] == PAT}  head {ram[0x3000:0x3020]!r}')
    L(f'[{tag}]   $B3000 head {ram[:8].hex()} image head {img[:8].hex()}; last 16 B $BAFF0: {ram[-16:].hex()}')


def L(*a):
    s = ' '.join(str(x) for x in a)
    res['log'].append(s)
    print(s, flush=True)


def sdiff(h, ref, box):
    cur = Image.open(h.shot()).convert("RGB").crop(box)
    d = ImageChops.difference(cur, Image.open(ref).convert("RGB").crop(box))
    return sum(ImageStat.Stat(d).mean) / 3


h = None
try:
    scratch = Path(f"/tmp/fl/run_{name}"); shutil.rmtree(scratch, ignore_errors=True)
    scratch.mkdir(parents=True)
    for src, dst in (("FFA_boot.st", "A.st"), ("FFB_graphics.st", "B.st")):
        shutil.copy(diskdir / src, scratch / dst)
    camp = diskdir / "FFD_campaign.st"
    shutil.copy(camp if camp.exists() else ROOT / "work/disk_overlay/FILES/FFD", scratch / "D.st")
    empty = scratch / "empty"; empty.mkdir()
    h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=TOS[tos], game_dir=empty,
               extra=['--disk-a', str(scratch / "A.st"), '--disk-b', str(scratch / "D.st")])
    ins = ROOT / "work/floppy_tests/ref_insert_graphics.png"
    box = (280, 360, 560, 420)
    t0 = time.time()
    while time.time() - t0 < 240:
        time.sleep(4)
        if sdiff(h, ins, box) < 0.3:
            break
    else:
        raise RuntimeError("never saw the Insert Graphics Disk prompt")
    L('insert-graphics prompt after %.0f s' % (time.time() - t0))
    h.cmd(f"hatari-option --disk-a {scratch / 'B.st'}"); time.sleep(2)
    ref = ROOT / "work/ref/mode_select.png"
    for i in range(40):
        h.cmd("hatari-event keypress 57"); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError("never reached the M/J/K screen")
    L('M/J/K screen after', i, 'presses')
    L('MWPO check', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    check('mjk')
    h.debug('w $2c574 $60 $02')
    for _ in range(5):
        time.sleep(3); h.cmd("hatari-event keypress 50"); time.sleep(5)
        if not h.screen_matches(ref, (280, 350, 560, 420)):
            break
    FT = ROOT / "work/floppy_tests"
    HALL = (FT / "ref_hall.png", (96, 350, 736, 458))
    PERS = (FT / "ref_personnel.png", (96, 100, 330, 350))
    MAP = (FT / "ref_map.png", (96, 300, 560, 458))

    def wait_match(target, timeout):
        t0 = time.time()
        while time.time() - t0 < timeout:
            if sdiff(h, target[0], target[1]) < 4:
                return True
            time.sleep(3)
        return False

    def step(point, target, timeout=40, key=None):
        """Click (or press `key` on) a point until the expected screen shows up.
        A click right after a palette fade can be lost, hence the retries."""
        for attempt in range(4):
            h.goto(*point)
            if key:
                h.key(key)
            else:
                h.click()
            if wait_match(target, timeout):
                return attempt
        raise RuntimeError(f"click at {point} never produced the expected screen")

    if not wait_match(HALL, 90):
        raise RuntimeError("never saw the HQ hall")
    check('hall0')
    L('hall; personnel click tries', step((554, 105), PERS))
    L('use-this-agent click tries', step((389, 140), HALL))
    L('control-door click tries', step((414, 185), MAP, timeout=100))
    time.sleep(25)                      # the map is still loading after it first shows
    check('map')
    h.goto(150, 280); h.key("space"); time.sleep(18)
    h.goto(230, 410); h.click(); time.sleep(15)
    boss = ROOT / "work/ref/boss_thumbs.png"
    for _ in range(6):
        h.goto(140, 415); h.click(); time.sleep(8)
        if h.screen_matches(boss, (590, 60, 740, 125)):
            break
    else:
        raise RuntimeError("never reached the boss screen")
    h.goto(625, 92); h.click(); time.sleep(40)
    for _ in range(12):
        if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2:
            break
        time.sleep(5)
    else:
        raise RuntimeError("did not reach the 3D view")
    time.sleep(30)                      # loads finish, palette fade done
    h.center()
    L('3D view shot', h.shot(out / f'{name}_3d.png'))
    L('6220=%x 700a=%x' % (h.peekw(0x6220), h.peekw(0x700A)))
    L('MWPO check', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    check('3d')
    h.dump(str(out / f'{name}_ram.bin'), 0, 0x100000); time.sleep(3)
    ramd = (out / f'{name}_ram.bin').read_bytes()
    L('floppy copy descriptor $E550-$E56F:', ramd[0xE550:0xE570].hex(' ', 2))
    nzb = [i for i in range(0xB0000, 0x100000) if ramd[i]]
    L('non-zero bytes in $B0000-$FFFFF:', len(nzb), 'of which inside $B3000-$BAFFF:', sum(1 for i in nzb if 0xB3000 <= i < 0xBB000),
      '| first/last non-zero outside the payload:', [hex(i) for i in nzb if not 0xB3000 <= i < 0xBB000][:3], [hex(i) for i in nzb if not 0xB3000 <= i < 0xBB000][-3:])
    L('ram dump', out / f'{name}_ram.bin')
    pre = clk.startswith('pre')          # 'preN': set N MHz before the walk (T3 on the same timeline as the 8 MHz cell)
    if pre:
        h.set_cpuclock(int(clk[3:])); time.sleep(3)
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(10)
    check('walk')
    L('walk shot', h.shot(out / f'{name}_walk.png'))
    r = h.world_rate(vbls=500); L('world_rate %s' % (clk[3:] + 'MHz (set before the walk)' if pre else '8MHz'), r)
    if clk != '0' and not pre:                       # T3: same straight walk at CLK MHz, no pointer warp
        h.set_cpuclock(int(clk)); time.sleep(5)
        r = h.world_rate(vbls=500); L(f'world_rate {clk}MHz', r)
        h.set_cpuclock(8); time.sleep(5)
    h.center(); time.sleep(1)
    hd = [h.peekw(0x6742)]; L('heading before', hex(hd[0]))
    h.rel(-150, 0)
    for i in range(8):
        time.sleep(1.5); hd.append(h.peekw(0x6742))
    L('heading series', [hex(x) for x in hd])
    h.shot(out / f'{name}_turned.png')
except Exception as e:
    L('EXC', repr(e)); L(traceback.format_exc())
    try:
        h.shot(out / f'{name}_exc.png')
    except Exception:
        pass
finally:
    if h:
        res['workdir'] = str(h.R); h.close()
    (out / f'{name}.json').write_text(json.dumps(res, indent=1, default=str))
