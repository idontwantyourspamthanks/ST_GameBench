#!/usr/bin/env python3
"""Cold boot of a built set to the 3D view, then check the p7_ck patches in that real (not snapshot) game.
    python3 work/p7_ck/boot.py NAME MACHINE(ste|megaste) TOS(162|206) MEM_KB GAME_DIR
Checks: 3D view ($6220 = d, $700a = 2), MWPO, p7_ck table block ($b5000, XTAB == decode of the live $68000 list),
visible window rows 58-199 of both buffers identical with the cull sites live vs reverted to their original bytes
(standing view is static), walking moves, fps with/without the cull sites."""
import sys, json, time, re, struct, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(ROOT / 'work/p7_ck'))
from mw2harness import Hatari
name, machine, tos, mem, game = sys.argv[1:6]
TOS = {'206': ROOT / 'tos/TOS_2_06.img', '162': Path.home() / 'Emulators/BIOS/AtariST/TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img'}
sys.path.insert(0, '/tmp/render_audit')
out = ROOT / 'work/p7_ck/boot'; out.mkdir(exist_ok=True)
log = []
def L(*a):
    s = ' '.join(str(x) for x in a); log.append(s); print(s, flush=True)
def runs(row):
    r = []; i = 0
    while i < 320:
        if row[i]:
            s = i
            while i < 320 and row[i]: i += 1
            r.append((s, i - 1))
        else: i += 1
    return r
def cockpit_runs(lst):
    W = lambda a: struct.unpack('>H', lst[a:a+2])[0]; Lg = lambda a: struct.unpack('>I', lst[a:a+4])[0]
    n = W(0) + 1; p = 2; pos = 0; rows = {}
    for _ in range(n):
        d = W(p); p += 2
        if d & 0x8000:
            pos += (~d) & 0xffff; cnt = W(p) + 1; p += 2
            for i in range(cnt):
                y = pos // 160; g = (pos % 160) // 8
                rows.setdefault(y, set()).update(range(g*16, g*16+16)); pos += 8
            p += cnt * 8
        else:
            pos += d; mk = Lg(p); p += 12
            y = pos // 160; g = (pos % 160) // 8; m = (mk >> 16) | (mk & 0xffff)
            for b in range(16):
                if not (m >> b) & 1: rows.setdefault(y, set()).add(g*16 + 15 - b)
            pos += 8
    return rows
h = None
try:
    h = Hatari(snapshot=None, memsize_kb=int(mem), game_dir=ROOT / game, machine=machine, tos=TOS[tos])
    L('cell', name, machine, tos, mem, game)
    h.boot_to_game('M')
    L('3D view: $6220=%x $700a=%x' % (h.peekw(0x6220), h.peekw(0x700A)))
    L('MWPO:', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    h.center(); time.sleep(3)
    h.debug(f'savebin {out}/{name}_blk.bin $b5000 $280 ', 1.5); h.debug(f'savebin {out}/{name}_list.bin $68000 $2000', 1.5)
    blk = (out / f'{name}_blk.bin').read_bytes(); lst = (out / f'{name}_list.bin').read_bytes()
    EN, BUILT, SYT = struct.unpack('>hhh', blk[:6])
    L('EN(between passes)', EN, 'BUILT', BUILT, 'SYT', SYT)
    rows = cockpit_runs(lst); bad = 0
    # the table holds the F table (suffix intersection); recompute it from the row runs
    U = {y: runs([x in rows.get(y, ()) for x in range(320)]) for y in range(176, 200)}
    F = {}; prev = None
    for y in range(199, 175, -1):
        cur = U[y] if prev is None else [(max(a, c), min(b, d)) for a, b in U[y] for c, d in prev if max(a, c) <= min(b, d)][:2]
        F[y] = cur; prev = cur
    for y in range(176, 200):
        a0, b0, a1, b1 = struct.unpack('>4h', blk[0x20 + 8*(y-176): 0x28 + 8*(y-176)])
        got = ([(a0, b0)] if a0 != 0x7fff else []) + ([(a1, b1)] if a1 != 0x7fff else [])
        if got != F[y]: bad += 1; L('F MISMATCH', y, got, F[y])
    L('F table rows mismatching the decoded list:', bad)
    res = {'table_bad': bad}
    # visible identity, patched vs reverted
    sites = [s for s in json.load(open('/tmp/ck/p4_all.json'))['sites'] if s['name'] in ('p7_ck_poly', 'p7_ck_obj', 'p7_ck_fill')]
    def grab(tag):
        h.debug(f'savebin {out}/{name}_{tag}60.bin $60000 $7d00', 1.0); h.debug(f'savebin {out}/{name}_{tag}70.bin $70000 $7d00', 1.0)
        return [(out / f'{name}_{tag}{b}.bin').read_bytes()[58*160:] for b in (60, 70)]
    A = grab('A')
    for s in sites:
        h.debug(f"w ${s['addr']:x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(s['orig'])), 0.3)
    time.sleep(8)
    B = grab('B')
    same = A == B
    L('window rows 58-199, cull sites live vs reverted: ', 'IDENTICAL' if same else 'DIFFER')
    res['identical'] = same
    # re-apply
    for s in sites:
        h.debug(f"w ${s['addr']:x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(s['new'])), 0.3)
    p0 = (h.peekw(0x66e6), h.peekw(0x66e8), h.peekw(0x66ea), h.peekw(0x66ec))
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(12)
    p1 = (h.peekw(0x66e6), h.peekw(0x66e8), h.peekw(0x66ea), h.peekw(0x66ec))
    L('walk', [hex(v) for v in p0], '->', [hex(v) for v in p1], 'moved' if p0 != p1 else 'NOT moved')
    res['moved'] = p0 != p1
    p = h.shot(); import shutil; shutil.copy(p, out / f'{name}_walk.png')
    f1 = h.fps(500); L('fps patched (cull live):', f1)
    for s in sites:
        h.debug(f"w ${s['addr']:x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(s['orig'])), 0.3)
    f0 = h.fps(500); L('fps with cull sites reverted:', f0)
    p = h.shot(); shutil.copy(p, out / f'{name}_walk_rev.png')
except Exception as e:
    L('EXC', repr(e)); L(traceback.format_exc())
    try: h.shot(out / f'{name}_exc.png')
    except Exception: pass
finally:
    if h: h.close()
    (out / f'{name}.json').write_text(json.dumps(log, indent=1))
