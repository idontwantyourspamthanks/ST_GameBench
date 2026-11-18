"""Floppy gate cell.  usage: fgate.py IMAGE OUTDIR machine mem tos [patched|control|neg]
Cold boot from ONE disk image in drive A (--disk-a, --fastfdc no, no hard disk), real FDC timing.
patched: title -> credit band -> NEPO/hook bytes -> F10 manager -> editor (new level, cells, Playtest, F10 back, Save = 'Kept in RAM') -> Original game
         -> tower (timer, E, T, 20 s drive) -> FDC trace (all reads drive 0, no writes) -> crash lines.
control: the unpatched original floppy: title, credit band 0 px, original bytes at the hook sites, tower, F10 does nothing.
512 KB (mem 512): patched but the stub takes the editor hook out: NEPS, F10 does nothing, rest as patched."""
import sys, time, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nebfloppy import NebFloppy
from PIL import Image

img, out, mach, mem, tos = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), sys.argv[3], int(sys.argv[4]), sys.argv[5]
mode = sys.argv[6] if len(sys.argv) > 6 else "patched"
out.mkdir(parents=True, exist_ok=True)
h = NebFloppy(img, machine=mach, mem=mem, tos=tos, workdir=str(out / "wd"), trace="fdc")

def words(a, n):
    o = h.debug(f"m ${a:x} {n}", 0.6)
    b = bytes(int(x, 16) for l in o.splitlines() if re.match(r'^[0-9a-f]{8}:', l, re.I) for x in re.findall(r'(?<=\s)[0-9a-f]{2}(?=\s)', l.split(':', 1)[1][:48]))
    return b[:n]
def W(a): return int.from_bytes(words(a, 2), 'big')
def L(a): return int.from_bytes(words(a, 4), 'big')
PIC = (96, 58, 736, 458)
def shot(n):
    p = out / f'{n}.png'; h.shot(str(p)); return p
def crop_lit(n, box):
    p = shot(n); im = Image.open(p).convert('RGB').crop(PIC).crop(box); return sum(1 for q in im.getdata() if q != (0, 0, 0))
def K(k, hold=0.2, gap=0.5): h.key(k, hold=hold); time.sleep(gap)
def F(gap=0.8): K('Control_R', 0.35, gap)
TIMER = 0x3AD74
def timer(): return tuple(words(TIMER, 6)[1::2])
def states(): return tuple(W(0x3398c + 2 * i) for i in range(4))
slow = mem > 1024
try:
    t0 = time.time(); ok = h.boot_to_title(timeout=400, space_at=(25 if slow else 20)); print('title', bool(ok), '%.0fs' % (time.time() - t0), flush=True)
    if not ok:
        shot('notitle'); raise SystemExit('no title')
    # the frog page (page word $3d5ae == 0) carries the credit line
    best = 0
    for i in range(40):
        if W(0x3d5ae) == 0:
            best = max(best, crop_lit(f'frog{i}', (128, 288, 510, 318)))
            if best or mode == 'control' and i > 3:
                break
        time.sleep(1.0)
    print('credit band lit px (frog page)', best, '(patched: 3284 expected on a build that prints it; control: 0)', flush=True)
    print('marker $77ec0', words(0x77ec0, 4), '| sites: $39fd6', hex(W(0x39fd6)), '$38514', hex(W(0x38514)), hex(L(0x38516)), '$3dcec', hex(W(0x3dcec)), hex(L(0x3dcee)),
          '$3d690', hex(W(0x3d690)), hex(L(0x3d692)), '$3a30e', hex(W(0x3a30e)), '$377a2', hex(W(0x377a2)), hex(L(0x377a4)), '$3851a', hex(W(0x3851a)), hex(L(0x3851c)), flush=True)
    print('store $BC000', words(0xBC000, 8).hex(), flush=True)
    editor = mode == 'patched' and mem >= 1024
    time.sleep(1)
    K('F10', 0.6, 2.5)
    mgr = crop_lit('mgr', (130, 0, 330, 120)); title_rows = crop_lit('mgr_t', (100, 160, 600, 200))
    print('F10: menu text px', mgr, 'title rows px', title_rows, '| editor expected:', editor, flush=True)
    if editor and mgr:
        K('Down'); K('Down'); F(1.5); shot('levels_empty'); F(2.0); shot('editor')
        K('Right'); K('Right'); K('Up'); K('Up'); F(1.5); K('Down'); K('Down'); F(1.5); shot('cell_placed')
        # round 3: tile shortcut keys and a lift placed with A + FIRE (GRID cell = $327f0 + cx*256 + cy)
        def cell(cx, cy): return words(0x327F0 + cx * 256 + cy, 1)[0]
        K('p'); K('Right'); K('l'); K('Right'); K('d'); shot('shortcuts')
        print('shortcut keys: pillar p at (2,1)', hex(cell(2, 1)), 'ledge l at (3,1)', hex(cell(3, 1)), 'door d at (4,1..3)',
              [hex(cell(4, i)) for i in (1, 2, 3)], flush=True)
        K('Left'); K('Left'); K('Left'); K('Up')
        K('a'); time.sleep(1); shot('lift_from'); K('Down', 8); K('Down', 8); F(1.5); shot('lift_set')
        print('lift: column 2 rows', [hex(cell(2, i)) for i in range(0, 14)], flush=True)
        F(1.0); K('Down', 0.2, 0.4)
        # Playtest = menu item (fire, Down x9, fire), as work/editor/e40.py
        for i in range(8): K('Down', 0.2, 0.4)
        F(2.0)
        time.sleep(8); shot('playtest')
        print('playtest: timer', timer(), 'RS', words(0x77c80, 12).hex(), 'tower', W(0x3390c), flush=True)
        h.key('F10', hold=0.6); time.sleep(3); shot('back_in_editor')
        print('after F10 in playtest: RS', words(0x77c80, 12).hex(), flush=True)
        F(1.0)
        for i in range(10): K('Down', 0.2, 0.4)
        F(2.5); shot('save_prompt')
        F(1.0)
        for _ in range(40):                      # the game disk is in A: and has no NEBLEVEL.OVL -> read-only refusal, ~9 s
            time.sleep(0.5)
            if W(0x77cc0 + 174) == 0 and L(0x77cc0 + 20) != 0: break
        time.sleep(0.5); shot('saved')
        print('Save with the game disk in A: msg', repr(words(0x77cc0 + 20, 4)), 'store RAM', words(0xBC000, 8).hex(), flush=True)
        # real message text
        a = L(0x77cc0 + 20)
        import re as _re
        o = h.debug(f"m ${a:x} 32", 0.6)
        tb = bytes(int(x, 16) for l in o.splitlines() if _re.match(r'^[0-9a-f]{8}:', l, _re.I) for x in _re.findall(r'(?<= )([0-9a-f]{2})(?= )', l.split(':', 1)[1]))
        print('  message:', tb.split(b"\0")[0].decode('latin1'), flush=True)
        K('Down', 0.2, 0.5); F(1.5); shot('after_leave')
        K('Left', 0.2, 1.2); shot('after_back')
        for i in range(4): K('Up', 0.2, 0.4)
        F(5.0); shot('after_original')
    time.sleep(2)
    # a tower from the title
    for i in range(40):
        if W(0x3d5ae) == 0:
            break
        time.sleep(1.0)
    h.key('Right', hold=0.5); time.sleep(0.5); h.key('Control_R', hold=1.0); time.sleep(5.0)
    print('tower: timer', timer(), 'tower idx', W(0x3390c), flush=True)
    shot('tower')
    if mode != 'control':
        K('e', 0.5, 1.5); print('E: noen', hex(W(0x76c04)), 'states', states()); time.sleep(2); a0 = timer(); time.sleep(2); a1 = timer(); print('E on: timer', a0, a1, 'counting', a0 != a1)
        K('t', 0.5, 1.0); a = timer(); time.sleep(3); b = timer(); time.sleep(3); c = timer(); print('T: frz', hex(W(0x76c02)), a, b, c, 'frozen', a == b == c)
        K('t', 0.5, 1.0); a = timer(); time.sleep(3); b = timer(); print('T again: running', a, b, a != b)
    t1 = time.time(); v0 = h.vbl(); n = 0
    while time.time() - t1 < 20:
        h.key('Right', hold=1.0); h.key('Control_R', hold=0.15); time.sleep(0.2); n += 1
    shot('drive'); print('20 s drive: %d rounds, vbl +%d, tower %d, timer %s' % (n, h.vbl() - v0, W(0x3390c), timer()), flush=True)
    print('VBL vector', hex(L(0x70)), 'ACIA vector', hex(L(0x118)))
finally:
    h.close()
log = (out / 'wd' / 'log.txt').read_text(errors='replace')
reads = re.findall(r'fdc read sector addr=0x[0-9a-f]+ drive=(\d)', log)
writes = re.findall(r'fdc write sector', log)
print('FDC reads:', len(reads), 'drives', sorted(set(reads)), '| FDC sector writes:', len(writes))
print('crash lines in Hatari log:', len(re.findall(r'Address error|Illegal|double bus|CPU halted|bus error', log, re.I)))
