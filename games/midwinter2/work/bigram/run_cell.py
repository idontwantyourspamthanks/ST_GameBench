"""One cold-boot test cell for the >=4 MB fix.
usage: run_cell.py NAME MACHINE TOS(path|key) MEM_KB GAME_DIR [timing]
Checks: boot_to_game('M') 3D view ($6220==d, $700a==2), 'MWPO' at $B2FF8, $B3000.. payload bytes
vs. the built image (work/bigram/payload.img), a short walk ($66e6/$66ea, $6888).
timing: breakpoints on the HAGA service entry ($fc4) and exit ($1164) log the VBL at every call.
"""
import sys, json, time, re, traceback
from pathlib import Path
sys.path.insert(0, 'tools')
import mw2harness
from mw2harness import Hatari

name, machine, tos, mem, game = sys.argv[1:6]
timing = len(sys.argv) > 6 and sys.argv[6] == 'timing'
mem = int(mem)
TOS = {'206': Path('tos/TOS_2_06.img').resolve(), '104': Path('tos/TOS_1_04.img').resolve(),
       '162': Path.home() / 'Emulators/BIOS/AtariST/TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img'}
tosp = TOS.get(tos, Path(tos))
out = Path('work/bigram')
res = {'cell': name, 'log': []}


def L(*a):
    s = ' '.join(str(x) for x in a)
    res['log'].append(s)
    print(s, flush=True)


payload = (out / 'payload.img').read_bytes()
h = None


def peekl(addr):
    return (h.peekw(addr) << 16) | h.peekw(addr + 2)


try:
    h = Hatari(snapshot=None, memsize_kb=mem, game_dir=Path(game), machine=machine, tos=tosp)
    L('cell', name, machine, tosp.name, mem, 'KB', game)
    if timing:
        hb = 0xF8000 if mem < 2048 else (0x1F8000 if mem < 4096 else 0x3F8000)
        (h.R / 'ent.txt').write_text('e VBL\ne 1111\n')
        (h.R / 'ext.txt').write_text('e VBL\ne 2222\n')
        h.cmd('hatari-debug b all'); time.sleep(0.3)
        h.cmd(f'hatari-debug b pc = ${hb + 0xfc4:x} :trace :file {h.R / "ent.txt"}'); time.sleep(0.3)
        h.cmd(f'hatari-debug b pc = ${hb + 0x1164:x} :trace :file {h.R / "ext.txt"}'); time.sleep(0.3)
        L('timing breakpoints armed, HAGA base', hex(hb))
    # --- boot_to_game('M'), identical to the harness but recording VBLs ---
    time.sleep(25)
    ref = Path('work/ref/mode_select.png')
    v_start = h.vbl(); L('VBL at intro loop start', v_start)
    t0 = time.time()
    for _ in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError('never reached the M/J/K screen')
    v_mjk = h.vbl(); L('VBL at M/J/K screen', v_mjk, 'delta', v_mjk - v_start, 'wall', round(time.time() - t0))
    res['v_start'], res['v_mjk'] = v_start, v_mjk
    # rest of boot_to_game: from the key press on is the harness's own code path
    for _ in range(5):
        time.sleep(3)
        h.cmd('hatari-event keypress 50'); time.sleep(5)
        if not h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError('M/J/K key not accepted')
    time.sleep(4)
    h.goto(554, 105); h.click(); time.sleep(15)
    h.goto(389, 140); h.click(); time.sleep(12)
    h.goto(414, 185); h.click(); time.sleep(25)
    h.goto(150, 280); h.key('space'); time.sleep(18)
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
    p = h.shot()
    import shutil
    shutil.copy(p, out / f'{name}_3d.png')
    L('3D view: $6220=%x $700a=%x' % (h.peekw(0x6220), h.peekw(0x700A)))
    L('MWPO check:', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    # payload bytes at $B3000
    dump = h.R / 'b3000.bin'
    h.debug(f'savebin {dump} 0xb3000 0x1f00', 2.0)
    mem_b = dump.read_bytes()
    code_ok = mem_b[:0x400] == payload[:0x400]
    diff = [i for i in range(min(len(mem_b), len(payload))) if mem_b[i] != payload[i]]
    L('payload $B3000..$B33FF equals built image:', code_ok, '| whole $1F00: %d bytes differ' % len(diff),
      '(runtime data areas)' if diff else '')
    L('$B3000 first 16 bytes:', mem_b[:16].hex(), ' image:', payload[:16].hex())
    if diff:
        L('differing ranges (first 12):', [hex(0xb3000 + d) for d in diff[:12]], 'zeroed bytes in payload-nonzero area:',
          sum(1 for d in diff if mem_b[d] == 0 and payload[d] != 0))
    res['payload_ok'] = code_ok
    # short walk
    p0 = (peekl(0x66e6), peekl(0x66ea), h.peekw(0x6888))
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(12)
    p1 = (peekl(0x66e6), peekl(0x66ea), h.peekw(0x6888))
    L('walk start (x,y,dist):', [hex(v) for v in p0], ' after 12 s:', [hex(v) for v in p1],
      'moved' if p0 != p1 else 'NOT moved')
    h.shot(out / f'{name}_walk.png')
    res['moved'] = p0 != p1
    if timing:
        log = h._logtext()
        # sequences of VBL values at entry/exit, in order
        evs = re.findall(r'#(\d+) \(dec\).*?\n(?:.*?\n)*?.*?#(1111|2222) \(dec\)', log)
        L('timing: raw event count', len(evs))
        (out / f'{name}_events.txt').write_text(log)
except Exception as e:
    L('EXC', repr(e))
    L(traceback.format_exc())
    try:
        h.shot(out / f'{name}_exc.png')
    except Exception:
        pass
finally:
    if h:
        res['workdir'] = str(h.R)
        h.close()
    (out / f'{name}.json').write_text(json.dumps(res, indent=1, default=str))
