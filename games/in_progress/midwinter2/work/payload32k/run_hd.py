"""HD-build payload cell: cold boot to the 3D view, checking the $8000-byte payload ($B3000-$BAFFF) at
four points (end of staging, M/J/K screen, 3D view, after a walk).

    python3 work/payload32k/run_hd.py NAME MACHINE TOS MEM_KB GAME_DIR SET

SET = default | blob | fill : which patch set GAME_DIR was built from (selects the expected image):
  default = the shipped default set, blob = default + test_blob16k, fill = blob + zz_tmp_fill (throwaway).
At the staging end (breakpoint at the boot stub entry $4D9A6, reached by RUNME's `jmp` after the copy routine)
the debugger also logs the registers and dumps $B1000-$B2FFF (PP's stack-phase installer copy + stack).
"""
import sys, json, time, struct, traceback, shutil
from pathlib import Path
sys.path.insert(0, 'tools')
import mw2patch as M
from mw2harness import Hatari

name, machine, tos, mem, game, sset = sys.argv[1:7]
mem = int(mem)
TOS = {'206': Path('tos/TOS_2_06.img').resolve(), '104': Path('tos/TOS_1_04.img').resolve(),
       '162': Path.home() / 'Emulators/BIOS/AtariST/TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img'}
out = Path('work/payload32k'); res = {'cell': name, 'log': []}


def L(*a):
    s = ' '.join(str(x) for x in a)
    res['log'].append(s); print(s, flush=True)


allp = M.load_patches()
want = [p for p in allp if (p.default and p.media is None) or
        (sset in ('blob', 'fill') and p.name == 'test_blob16k') or (sset == 'fill' and p.name == 'zz_tmp_fill')]
img, sites = M.build_image(want)
datar = [(a, a + l) for p in want for a, l in p.data]
PAT = b'MW2-TEST-BLOB16K' + b''.join(struct.pack('>H', (0xB6010 + 2 * i) & 0xFFFF) for i in range(8184))
assert len(PAT) == 0x4000
L('cell', name, machine, tos, mem, 'KB', game, 'set', sset, 'image', len(img), 'B,', len(sites), 'sites')
h = None


def check(tag, wait_key=None):
    """Dump $B2FF8-$BB000 and compare with the built image."""
    p = h.R / f'pl_{tag}.bin'
    if p.exists(): p.unlink()
    h.debug(f'savebin {p} 0xb2ff8 0x8008', 3.0)
    b = p.read_bytes()
    assert len(b) == 0x8008, len(b)
    marker, ram = b[:4], b[8:]
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
    return marker == b'MWPO' or tag == 'stage', un


try:
    h = Hatari(snapshot=None, memsize_kb=mem, game_dir=Path(game), machine=machine, tos=TOS[tos])
    cf = h.R / 'stage.txt'
    cf.write_text(f'r\nm $b2ff8 16\nm $b1f40 96\nsavebin {h.R / "stage_b2ff8.bin"} 0xb2ff8 0x8008\n'
                  f'savebin {h.R / "stage_b1000.bin"} 0xb1000 0x2000\n')
    h.cmd('hatari-debug b all'); time.sleep(0.3)
    h.cmd(f'hatari-debug b pc = $4d9a6 :trace :once :file {cf}'); time.sleep(0.3)
    time.sleep(25)
    ref = Path('work/ref/mode_select.png')
    for _ in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError('never reached the M/J/K screen')
    log = h._logtext()
    # --- staging evidence
    s = log.find('Breakpoint')
    L('--- debugger log at the boot-stub breakpoint $4D9A6 (end of staging) ---')
    i = log.find('$004D9A6'); i = log.find('D0:') if i < 0 else i
    seg = log[max(0, log.find('D0:') - 200):log.find('D0:') + 1400]
    L(seg.rstrip())
    sb = (h.R / 'stage_b2ff8.bin').read_bytes()
    ram = sb[8:]
    sdiff = [i for i in range(0x8000) if ram[i] != img[i]]
    L(f'[stage] marker area {sb[:4].hex()}  $B3000-$BAFFF equals the built image at the stub entry: {not sdiff} ({len(sdiff)} bytes differ)')
    st = (h.R / 'stage_b1000.bin').read_bytes()
    nz = [i for i, v in enumerate(st) if v]
    L(f'[stage] non-zero bytes in $B1000-$B2FFF: first ${0xB1000 + nz[0]:x} last ${0xB1000 + nz[-1]:x}' if nz else '[stage] $B1000-$B2FFF all zero')
    ok1, un1 = check('mjk')
    for _ in range(5):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(5)
        if not h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError('M/J/K key not accepted')
    time.sleep(4)
    h.goto(554, 105); h.click(); time.sleep(15)
    h.goto(389, 140); h.click(); time.sleep(12)
    check('hall')
    h.goto(414, 185); h.click(); time.sleep(25)
    h.goto(150, 280); h.key('space'); time.sleep(18)
    check('map')
    h.goto(230, 410); h.click(); time.sleep(15)
    boss = Path('work/ref/boss_thumbs.png')
    for _ in range(6):
        h.goto(140, 415); h.click(); time.sleep(8)
        if h.screen_matches(boss, (590, 60, 740, 125)):
            break
    else:
        raise RuntimeError('never reached the boss screen')
    h.goto(625, 92); h.click(); time.sleep(40)
    for _ in range(12):
        if h.peekw(0x6220) == 0xD and h.peekw(0x700A) == 2:
            break
        time.sleep(5)
    else:
        raise RuntimeError(f'no 3D view ($6220={h.peekw(0x6220):#x}, $700a={h.peekw(0x700A):#x})')
    h.center()
    shutil.copy(h.shot(), out / f'{name}_3d.png')
    L('3D view: $6220=%x $700a=%x' % (h.peekw(0x6220), h.peekw(0x700A)))
    L('MWPO check:', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    check('3d')

    def pk(a):
        return (h.peekw(a) << 16) | h.peekw(a + 2)
    p0 = (pk(0x66e6), pk(0x66ea), h.peekw(0x6888))
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(12)
    p1 = (pk(0x66e6), pk(0x66ea), h.peekw(0x6888))
    L('walk (x,y,dist):', [hex(v) for v in p0], '->', [hex(v) for v in p1], 'moved' if p0 != p1 else 'NOT moved')
    check('walk')
    h.shot(out / f'{name}_walk.png')
except Exception as e:
    L('EXC', repr(e)); L(traceback.format_exc())
    try:
        h.shot(out / f'{name}_exc.png')
    except Exception:
        pass
finally:
    if h:
        res['workdir'] = str(h.R)
        try:
            shutil.copy(h.R / 'log.txt', out / f'{name}.hlog')
        except Exception:
            pass
        h.close()
    (out / f'{name}.json').write_text(json.dumps(res, indent=1, default=str))
