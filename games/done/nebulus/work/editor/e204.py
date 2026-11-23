"""e204 (gate2): Copy tower for all 16 towers vs the original decode, Blank grid, Time +-50, Name...  (companion of e200; same snapshot)\n(e200 header:) NebLooksUI gate: colour / enemy / copy-tower list pickers with live preview, the editor view recolouring (EPAL), Crumble ledge placement, playtest of the pick, store round trip.
usage: e204.py BUILD_DIR WORKDIR [ste|megaste|st] [--snap FILE]"""
import sys, os, time, struct, re, shutil, gzip
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ulib_ui import *
import ovl, nebcampaign as nc
args = sys.argv[1:]
SNAP = None
if '--snap' in args: i = args.index('--snap'); SNAP = args[i + 1]; del args[i:i + 2]
BUILD, WD = args[0], args[1]; MACH = args[2] if len(args) > 2 else 'ste'
SNAP = SNAP or f'/tmp/nlg/x/title_{MACH}_new.sav'
OUT = f'{WD}_out/'; os.makedirs(OUT, exist_ok=True)
fails = []; LOG = []
def P(line): print(line, flush=True); LOG.append(line)
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
if not os.path.exists(SNAP): print('snapshot boot', mk_snap(BUILD, SNAP, MACH, WD + '_snap'), flush=True)
data = gzip.open(SNAP).read()
for sig in (b'Crumble ledge', b'Colours >', b'Level >', bytes.fromhex('303900077cbe')):
    assert sig in data, f'stale snapshot {SNAP}: {sig!r} missing'
SRC = open('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/patches/ed_editor.s').read()
TMAP = [int(x) for x in re.search(r"^tmap:\s+dc\.b\s+([\d,]+)", SRC, re.M).group(1).split(',')]
EPAL = 0xA8980
REFDIR = os.environ.get('REFDIR', '/tmp/nlg/x/lg/r/base8_ste')
def rdref(t, a, n): return open(f'{REFDIR}/lvl{t}.bin', 'rb').read()[a:a + n]
def theme(h, k):
    pal = grab(h, 0x35250 + k * 32, 32, 'tp'); return b''.join(pal[b:b + 2] for b in TMAP)
def epal(h): return grab(h, EPAL, 32, 'ep')
def flags_of(data):
    out = []; p = ovl.LV0
    for i in range(struct.unpack('>H', data[6:8])[0]): out.append(data[p + 3]); p += 20 + struct.unpack('>H', data[p + 4:p + 6])[0]
    return out
def recs(data):
    out = []; p = ovl.LV0
    for i in range(struct.unpack('>H', data[6:8])[0]):
        out.append(tuple(data[p:p + 4])); p += 20 + struct.unpack('>H', data[p + 4:p + 6])[0]
    return out
def lst(h): items, sel = menu(h); return [t for a, p, t in items], sel
def cell_at(h, x, y): return grab(h, 0x327f0 + x * 256 + y, 1, 'c')[0]
def open_list(h, label):
    level_menu(h, label, 1.2); return lst(h)
def bcd(x): return ((x >> 12) & 15) * 1000 + ((x >> 8) & 15) * 100 + ((x >> 4) & 15) * 10 + (x & 15)
def grid_of(h, rows):
    d = grab(h, 0x327f0, 0x1000, 'g'); return [d[a * 256 + r] for a in range(16) for r in range(rows)], d
def ring():
    g = [[0] * 48 for _ in range(16)]
    for a in range(16): g[a][1] = 0x81
    for a in (3, 4, 5): g[a][43] = 0x81
    for r in (44, 45, 46): g[4][r] = 0xc3
    return g
def run():
    h = Nebulus(snapshot=SNAP, workdir=WD, game=Path(BUILD), **({'machine': 'megaste', 'tos': stharness.TOS['2.06'], 'memsize_kb': 4096} if MACH == 'megaste' else {'machine': 'st', 'tos': stharness.TOS['1.04']} if MACH == 'st' else {}))
    D = OUT; open(D + 'zero.ovl', 'wb').write(bytes(8192))
    try:
        time.sleep(2); h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        chk('F10 opens the manager', open_manager(h))
        pick(h, 'Levels'); pick(h, '<new level>', 1.5)
        # --- Copy tower: all 16 shipped towers == the original decode (grid, rows, mission, tower, flags 0, time default)
        for k in (range(15, 16) if os.environ.get('TAIL') else range(16)):
            m, t = k // 8 + 1, k % 8
            items, sel = open_list(h, 'Copy tower >')
            goto(h, k); time.sleep(0.4); h.key('Control_R', hold=0.35); time.sleep(2.0)
            og, orows = ovl.original(m, t); rows = W(h, RS + 16)
            got, d = grid_of(h, orows)
            exp = [og[a][r] for a in range(16) for r in range(orows)]
            rest = any(d[a * 256 + r] for a in range(16) for r in range(orows, 256))
            chk(f'Copy tower #{k + 1} (M{m} T{t + 1}): mission/tower/flags, rows, grid == original decode, nothing beyond the rows', (W(h, RS + 12), W(h, RS + 14), flag_byte(h), rows, got == exp, rest), (m, t, 0, orows, True, False))
            if k in (0, 8, 15): h.shot(D + f'copy_{k + 1:02d}.png')
        # --- Blank grid
        level_menu(h, 'Blank grid', 1.5)
        g = ring(); got, d = grid_of(h, 48); exp = [g[a][r] for a in range(16) for r in range(48)]
        chk('Blank grid: rows 48, ring row 1 + ledge + exit door, rest empty (== the new-level grid), mission/flags untouched', (W(h, RS + 16), got == exp, W(h, RS + 12), flag_byte(h)), (48, True, 2, 0))      # Blank grid replaces the grid only: mission/tower stay those of the last Copy tower (M2)
        h.shot(D + 'blank.png')
        # --- Time +-50
        t0 = W(h, RS + 18); level_menu(h, 'Time +50', 1.0); t1 = W(h, RS + 18); level_menu(h, 'Time +50', 1.0); t2 = W(h, RS + 18)
        level_menu(h, 'Time -50', 1.0); level_menu(h, 'Time -50', 1.0); level_menu(h, 'Time -50', 1.0); t3 = W(h, RS + 18)
        chk('Time +50 twice (+50 each), then -50 three times (net -50 vs start; BCD seconds)', (bcd(t1) - bcd(t0), bcd(t2) - bcd(t1), bcd(t3) - bcd(t0)), (50, 50, -50))
        P(f'time words {t0:04x} {t1:04x} {t2:04x} {t3:04x}')
        # --- Name...
        n0 = grab(h, RS + 28, 12, 'n0'); level_menu(h, 'Name...', 1.0)
        h.key('Up', hold=0.2); time.sleep(0.5); h.key('Up', hold=0.2); time.sleep(0.5); h.key('Right', hold=0.2); time.sleep(0.5); h.key('Down', hold=0.2); time.sleep(0.5); h.key('Control_R', hold=0.35); time.sleep(1.2)
        n1 = grab(h, RS + 28, 12, 'n1'); P(f'name before {n0!r} after {n1!r}')
        chk('Name...: the name bytes changed by the entry keys (first letter and second letter), menu closed', (n1 != n0, n1[:1] != n0[:1], n1[1:2] != n0[1:2]), (True, True, True))
        h.shot(D + 'name.png')
        h.key('F10', hold=0.4); time.sleep(1.5)
        ram = grab(h, 0xBC000, 8192, 'fl'); lv = ovl.parse(ram)[0]; P(f'committed level name {lv[0]["name"]!r} time {lv[0]["time"]:04x}')
        chk('committed record carries the new name and time', (lv[0]['name'].strip() == n1.split(b"\0")[0].decode('latin1').strip(), lv[0]['time'] == t3), (True, True))
        chk('no Address/Bus Error/exception in the Hatari log', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run()
print('FAILS', fails); open(f'{WD}_e204_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
