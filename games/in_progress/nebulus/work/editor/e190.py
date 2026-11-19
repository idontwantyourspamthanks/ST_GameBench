"""(NebLooksBuild: header of e180, the looks UI gate e190 follows below.)  Odd-aligned level records gate (NebOddFix, work/notes/editor.md 13.10).  Records are packed back to back, so a level with an odd number of
non-zero cells makes the next record start at an odd address; every reader must cope (68000: a word read at an odd address = address error).
For every file: loadbin it over the store $BC000 (rsOk = 0 forces the validation again), F10 opens the manager, the level list shows every level,
every level is started with Levels > n > Play (name at the tower intro via a breakpoint at $3d116 = the A0 the ed_name hook returns, grid vs the
decoded record, rows, mission/tower, initial time), Q back to the title, then every campaign: Play, first entry checked, entries forced one after the
other (door entry poked as in e33.py) with the same checks, until the game's own victory flow.  No Address/Bus Error/Illegal/Double fault in the log.
usage: e180.py GAMEDIR WORKDIR [ste|megaste|st] [file.ovl ...] [--snap FILE] [--nowalk] [--flow = the editor flow (c) instead of files] [--flags = the flags.b preservation gate] [--quick = start only the last and the first odd-start level of each file] [--disk = get each file into the store with Load from campaign disk (tools/nebcampaign.py new --ovl) instead of loadbin]   (default files: /tmp/looksgate/ne/odd/*.ovl from mk_odd.py)"""
from ui import *
import ovl, glob, re, subprocess
gd = __import__('pathlib').Path
args = [a for a in sys.argv[1:]]
SNAP = None; WALK = True
if '--snap' in args: i = args.index('--snap'); SNAP = args[i + 1]; del args[i:i + 2]
if '--nowalk' in args: args.remove('--nowalk'); WALK = False
if '--flow' in args: args.remove('--flow')
if '--flags' in args: args.remove('--flags')
QUICK = '--quick' in args
if QUICK: args.remove("--quick"); WALK = False
DISK = '--disk' in args
if DISK: args.remove('--disk')
GAMEDIR, WD = args[0], args[1]; MACH = args[2] if len(args) > 2 and args[2] in ('ste', 'megaste', 'st') else 'ste'
FILES = [a for a in args[2:] if a.endswith('.ovl')] or sorted(glob.glob('/tmp/looksgate/ne/odd/*.ovl'))
SNAP = SNAP or f'/tmp/looksgate/oddfix/title_{MACH}.sav'
fails = []; LOG = []
def chk(name, got, exp=True):
    ok = (got == exp); line = f"{'PASS' if ok else 'FAIL'} {name}: {got!r}" + ('' if ok else f"  (expected {exp!r})"); print(line, flush=True); LOG.append(line)
    if not ok: fails.append(name)
    return ok
def kw():
    import stharness
    if MACH == 'megaste': return dict(machine='megaste', tos=stharness.TOS['2.06'], memsize_kb=4096)
    if MACH == 'st': return dict(machine='st', tos=stharness.TOS['1.04'])
    return {}
if not os.path.exists(SNAP):
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    h = Nebulus(workdir=WD + '_snap', game=gd(GAMEDIR), **kw()); print('snapshot boot', h.boot_to_title(timeout=240), flush=True); time.sleep(3); h.savemem(SNAP); h.close(); time.sleep(1)
BP = '/tmp/looksgate/oddfix/bp_name.txt'; os.makedirs('/tmp/looksgate/oddfix', exist_ok=True); open(BP, 'w').write("m a0 16\n")

def goto(h, idx, tries=40):
    for _ in range(tries):
        items, sel = menu(h)
        if sel == idx: return items
        h.key('Down' if idx > sel else 'Up', hold=0.2); time.sleep(0.45)
    raise RuntimeError(f'goto {idx} failed')
def pick(h, what, gap=1.3):
    items, sel = menu(h)
    idx = what if isinstance(what, int) else [i for i, (a, p, t) in enumerate(items) if t.startswith(what)][0]
    goto(h, idx); h.key('Control_R', hold=0.35); time.sleep(gap)
def open_manager(h):
    for _ in range(4):
        h.key('F10', hold=0.4); time.sleep(2.0)
        if L(h, 0x70) != 0x382d8: return True
    return False
def timer(h):
    w = struct.unpack('>3H', grab(h, 0x3ad98, 6, 'tm')); return (w[0] // 8) * 100 + (w[1] // 8) * 10 + (w[2] // 8)
def bcd(x): return ((x >> 8) & 15) * 100 + ((x >> 4) & 15) * 10 + (x & 15)
def wait_running(h, tmo=60):
    t0 = time.time()
    while time.time() - t0 < tmo:
        time.sleep(0.7)
        if W(h, 0x33a20) == 0 and W(h, 0x33938) == 1: time.sleep(0.8); return True
    return False
def name_hits(h, n0):
    log = open(h.R / 'log.txt', errors='replace').read()[n0:]
    return [(int(a, 16), bytes(int(x, 16) for x in b.split())) for a, b in re.findall(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ){16})", log, re.M)]
def expect_grid(lv):
    e = bytearray(4096)
    for a in range(16):
        for r in range(lv['rows']): e[a * 256 + r] = lv['grid'][a][r]
    return bytes(e)
def check_start(h, tag, ent, lvs, n0):
    """ent = ('c', idx) or ('o', mission, tower); the tower must be running now"""
    ok = wait_running(h); chk(f'{tag}: tower started', ok)
    if not ok: return
    ttab = struct.unpack('>8H', grab(h, 0x3ad9e, 16, 'tt'))
    g = grab(h, 0x327f0, 4096, 'g'); rows = W(h, 0x33912); tw = W(h, 0x3390c); ms = W(h, 0x33910); rem = timer(h)
    hits = name_hits(h, n0)
    if ent[0] == 'c':
        lv = lvs[ent[1]]; exp = expect_grid(lv)
        d = [(i // 256, i % 256) for i in range(4096) if g[i] != exp[i]]
        chk(f'{tag}: grid == decoded record ({lv["name"]})', d[:6], [])
        chk(f'{tag}: rows/mission/tower', (rows, ms, tw), (lv['rows'], lv['mission'], lv['tower']))
        t = bcd(lv['time']) if lv['time'] else bcd(ttab[lv['tower']])
        chk(f'{tag}: initial time {t} s (remaining {rem})', t - 45 <= rem <= t, True)
        nm = lv['name'].encode() + b'\0'
        hit = hits[-1] if hits else None
        chk(f'{tag}: tower name hook A0=${hit[0]:x} text' if hit else f'{tag}: tower name hook fired', (hit[1][:len(nm)] if hit else None), nm)
        print(f'      record {ent[1]}: size {lv["size"]}, name A0 ${hit[0]:x} ({"odd" if hit[0] & 1 else "even"} address)' if hit else '', flush=True)
    else:
        og, orows = ovl.original(ent[1], ent[2])
        d = [(a, r) for a in range(16) for r in range(orows) if g[a * 256 + r] != og[a][r]]
        chk(f'{tag}: original M{ent[1]} T{ent[2] + 1} grid', d[:6], []); chk(f'{tag}: original rows/mission/tower', (rows, ms, tw), (orows, ent[1], ent[2]))
def wait_title(h, tmo=25):
    t0 = time.time()
    while time.time() - t0 < tmo:
        time.sleep(0.7)
        if W(h, 0x33938) == 9 and L(h, 0x70) == 0x382d8: time.sleep(1.5); return True
    return False
def force(h):
    poke(h, 0x33a46, bytes([0, 1])); poke(h, 0x33a20, bytes([0, 4])); poke(h, 0x33a1e, bytes([0, 0]))
def wait_pos(h, pos, tmo=90):
    t0 = time.time()
    while time.time() - t0 < tmo:
        time.sleep(1.0)
        if pos < 0:
            if W(h, 0x3390c) == 8: return True
        elif rs(h)[1] == pos and W(h, 0x33a20) == 0 and W(h, 0x33938) == 1: time.sleep(0.8); return True
    return False
def errors(h):
    log = open(h.R / 'log.txt', errors='replace').read()
    return [l for l in log.splitlines() if re.search(r'Address Error|Bus Error|Illegal|Double|exception', l)]

def run_file(path):
    data = open(path, 'rb').read(); name = os.path.basename(path)
    pr = ovl.validate(data); chk(f'{name}: ovl.py validate', pr, [])
    lvs, cs = ovl.parse(data)
    print(f'== {name}: {len(lvs)} levels, sizes {[l["size"] for l in lvs]}, {len(cs)} campaigns {cs}', flush=True)
    h = Nebulus(snapshot=SNAP, workdir=f'{WD}_{os.path.splitext(name)[0]}', game=gd(GAMEDIR), **kw())
    try:
        time.sleep(2)
        if DISK:
            zero = '/tmp/looksgate/oddfix/zero8k.ovl'; open(zero, 'wb').write(bytes(8192)); h.debug(f'loadbin {zero} $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
            img = f'/tmp/looksgate/oddfix/disk_{MACH}_{name[:-4]}.st'
            subprocess.run([sys.executable, G + 'tools/nebcampaign.py', 'new', img, '--ovl', path], check=True, capture_output=True)
            h.debug('b all', 0.3); h.cmd(f"hatari-debug b pc = $3d116 :trace :file {BP}"); time.sleep(0.3)
            chk(f'{name}: F10 opens the manager', open_manager(h))
            h.cmd(f'hatari-option --disk-a {img}'); time.sleep(2.0)
            pick(h, 'Load from campaign disk', 1.2); h.key('Control_R', hold=0.35); m = None
            for _ in range(80):
                time.sleep(0.5)
                if W(h, V + 174) == 0:
                    a = L(h, V + 20)
                    if a: m = grab(h, a, 48, 'ms').split(b'\0')[0].decode('latin1'); break
            chk(f'{name}: Load from campaign disk (nebcampaign.py new --ovl)', m, f'Loaded {len(lvs)} levels / {len(cs)} campaigns')
        else:
            h.debug(f'loadbin {path} $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
            h.debug('b all', 0.3); h.cmd(f"hatari-debug b pc = $3d116 :trace :file {BP}"); time.sleep(0.3)
        chk(f'{name}: store in RAM == file', grab(h, 0xBC000, 8192, 'st') == data)
        if not DISK: chk(f'{name}: F10 opens the manager', open_manager(h))
        pick(h, 'Levels'); items, sel = menu(h)
        chk(f'{name}: level list shows all levels', [t for a, p, t in items if a == 6], [l['name'] for l in lvs])
        h.key('Left', hold=0.2); time.sleep(1.0)
        odd = ovl.odd_starts(data)
        for i, lv in enumerate(lvs):
            if QUICK and i not in ([len(lvs) - 1] + odd[:1]): continue          # --quick: every level is validated/listed, only the last and the first odd-start level are started
            tag = f'{name} level {i} (record size {lv["size"]})'
            n0 = len(open(h.R / 'log.txt', errors='replace').read())
            pick(h, 'Levels'); pick(h, i); pick(h, 'Play', 1.0)
            check_start(h, tag + ' Play', ('c', i), lvs, n0)
            h.key('q', hold=0.3); wait_title(h, 12)
            if not chk(f'{tag}: F10 opens the manager again (= back at the title after Q)', open_manager(h)): break
        full = name in ('odd2.ovl', 'looks.ovl')
        pick(h, 'Campaigns'); items, sel = menu(h)
        chk(f'{name}: campaign list shows all campaigns', [t for a, p, t in items if a == 7], [n for n, e in cs]); h.key('Left', hold=0.2); time.sleep(1.0)
        order = [c for c in range(len(cs)) if c] + [0] if cs else []     # campaign 0 last: its walk ends in the game's victory flow
        for c in order:
            cn, ents = cs[c]; tag = f'{name} campaign {c} {cn}'
            dec = lambda e: ('o', ((e >> 3) & 1) + 1, e & 7) if e & 0x80 else ('c', e)
            if c and not full: continue                                     # stress files: campaigns other than the first are listed only
            pick(h, 'Campaigns'); pick(h, c); n0 = len(open(h.R / 'log.txt', errors='replace').read()); pick(h, 'Play', 1.0)
            check_start(h, tag + ' entry 0', dec(ents[0]), lvs, n0)
            if c == 0 and WALK and len(ents) > 1:
                h.key('e', hold=0.3); time.sleep(0.5)
                last = len(ents) if full else min(2, len(ents) - 1)         # stress files: the first campaign's first 2 transitions only (a transition takes ~25 s)
                for k in range(1, last + 1):
                    n0 = len(open(h.R / 'log.txt', errors='replace').read()); force(h)
                    if k < len(ents):
                        chk(f'{tag}: entry {k} reached', wait_pos(h, k))
                        check_start(h, f'{tag} entry {k}', dec(ents[k]), lvs, n0)
                    else:
                        chk(f'{tag}: victory flow after the last entry (game ends the campaign: $3390c = 8)', wait_pos(h, -1))
            else:
                h.key('q', hold=0.3)
                wait_title(h, 12)
                if not chk(f'{tag}: F10 opens the manager again (= back at the title after Q)', open_manager(h)): break
        v0 = h.vbl(); time.sleep(1.0); chk(f'{name}: game alive (VBL runs)', h.vbl() - v0 > 20)
        e = errors(h); chk(f'{name}: no Address/Bus Error/exception in the Hatari log', e, [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk(f'{name}: exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
def cells(h):
    g = grab(h, 0x327f0, 4096, 'gc'); rows = W(h, RS + 16)
    return sum(1 for a in range(16) for r in range(rows) if g[a * 256 + r])
def make_odd_level(h, tag, extra):
    """editor open on a new level: paint `extra` ledges on row 3, then fix the parity: the number of non-zero cells must be odd (the record is odd)"""
    h.key('Up', hold=0.2); time.sleep(0.4)
    for i in range(extra): h.key('l', hold=0.2); time.sleep(0.35); h.key('Right', hold=0.2); time.sleep(0.35)
    n = cells(h)
    if n % 2 == 0: h.key('l', hold=0.2); time.sleep(0.4); n2 = cells(h); n = n2 if n2 % 2 else (h.key('Right', hold=0.2), time.sleep(0.4), h.key('l', hold=0.2), time.sleep(0.4), cells(h))[-1]
    chk(f'{tag}: new level has an odd number of non-zero cells', n % 2, 1)
    return n
def run_flow():
    """(c) editor flow: two new levels with odd cell counts, Save to a campaign disk, Load it again, list, play both, validate the file"""
    import shutil, nebcampaign as nc
    D = '/tmp/looksgate/oddfix/flow/'; shutil.rmtree(D, ignore_errors=True); os.makedirs(D); disk = D + 'camp.st'; shutil.copy('/tmp/looksgate/ne/d/blank.st', disk)
    open(D + 'zero.ovl', 'wb').write(bytes(8192))
    h = Nebulus(snapshot=SNAP, workdir=f'{WD}_flow', game=gd(GAMEDIR), **kw())
    try:
        time.sleep(2); h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        h.debug('b all', 0.3); h.cmd(f"hatari-debug b pc = $3d116 :trace :file {BP}"); time.sleep(0.3)
        chk('flow: F10 opens the manager', open_manager(h))
        sizes = []
        for k in range(2):
            pick(h, 'Levels'); pick(h, '<new level>', 1.5)
            n = make_odd_level(h, f'flow level {k}', 3 + 2 * k); sizes.append(n)
            h.key('F10', hold=0.4); time.sleep(1.5)               # leave the editor: commit -> level list
            h.key('Left', hold=0.2); time.sleep(1.2)              # < back to the manager
        pick(h, 'Levels'); items, sel = menu(h); print('   list after editing:', [t for a, p, t in items], flush=True)
        chk('flow: two levels in the list', len([1 for a, p, t in items if a == 6]), 2)
        h.key('Left', hold=0.2); time.sleep(1.0)
        ram = grab(h, 0xBC000, 8192, 'fl'); lvs, cs = ovl.parse(ram)
        chk('flow: RAM store has 2 levels, both records odd, second starts at an odd offset', ([l['size'] % 2 for l in lvs], ovl.odd_starts(ram)), ([1, 1], [1]))
        chk('flow: RAM store validates (ovl.py rules)', ovl.validate(ram), [])
        h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        pick(h, 'Save to campaign disk', 1.2); h.key('Control_R', hold=0.35); t0 = time.time(); m = None
        for _ in range(60):
            time.sleep(0.5)
            if W(h, V + 174) == 0:
                a = L(h, V + 20)
                if a: m = grab(h, a, 48, 'ms').split(b'\0')[0].decode('latin1'); break
        chk('flow: Save to campaign disk', m, 'Saved'); print('   (save %.1f s)' % (time.time() - t0), flush=True)
        h.cmd('hatari-option --disk-a /tmp/looksgate/ne/d/blank.st'); time.sleep(3.0)           # inserting another image makes Hatari write the saved one back (e161.py); h.cmd(f'hatari-option --disk-a {D}x.st') if False else None
        ok, text, data = nc.status(open(disk, 'rb').read())
        chk('flow: saved image is a usable campaign disk', ok); print('   ', text, flush=True)
        chk('flow: saved NEBLEVEL.OVL == RAM store', data == ram)
        open(D + 'saved.ovl', 'wb').write(data); chk('flow: ovl.py validate of the saved file', ovl.validate(data), [])
        # Load it back over a zeroed store
        h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        pick(h, 'Load from campaign disk', 1.2); h.key('Control_R', hold=0.35); m = None
        for _ in range(60):
            time.sleep(0.5)
            if W(h, V + 174) == 0:
                a = L(h, V + 20)
                if a: m = grab(h, a, 48, 'ms').split(b'\0')[0].decode('latin1'); break
        chk('flow: Load from campaign disk', m, 'Loaded 2 levels / 0 campaigns'); chk('flow: store == saved file', grab(h, 0xBC000, 8192, 'fl') == data)
        pick(h, 'Levels'); items, sel = menu(h); chk('flow: list after reload shows both', len([1 for a, p, t in items if a == 6]), 2)
        h.key('Left', hold=0.2); time.sleep(1.0)
        for i, lv in enumerate(lvs):
            tag = f'flow level {i} (record size {lv["size"]})'; n0 = len(open(h.R / 'log.txt', errors='replace').read())
            pick(h, 'Levels'); pick(h, i); pick(h, 'Play', 1.0); check_start(h, tag + ' Play', ('c', i), lvs, n0)
            h.key('q', hold=0.3); wait_title(h, 12)
            if not chk(f'{tag}: F10 opens the manager again (= back at the title after Q)', open_manager(h)): break
        e = errors(h); chk('flow: no Address/Bus Error/exception in the Hatari log', e, [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('flow: exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
def flags_of(data):
    out = []; p = ovl.LV0
    for i in range(struct.unpack('>H', data[6:8])[0]): out.append(data[p + 3]); p += 20 + struct.unpack('>H', data[p + 4:p + 6])[0]
    return out
def save_load_disk(h, disk, what):
    m = None
    pick(h, what, 1.2); h.key('Control_R', hold=0.35)
    for _ in range(80):
        time.sleep(0.5)
        if W(h, V + 174) == 0:
            a = L(h, V + 20)
            if a: m = grab(h, a, 48, 'ms').split(b'\0')[0].decode('latin1'); break
    return m

REFDIR = os.environ.get('REFDIR', '/tmp/looksgate/r/base8_ste')      # run_look.py base8 dumps (T1..T8, flags 0) = the stock values of palette/raster/skyline/eyes
def rdref(t, a, n): return open(f'{REFDIR}/lvl{t}.bin', 'rb').read()[a:a + n]
def flag_byte(h): return grab(h, RS + 50, 1, 'fl')[0]
def tower_menu(h, label, gap=1.3):
    h.key('Control_R', hold=0.35); time.sleep(1.5)               # FIRE in the map: cell menu
    menu(h)
    pick(h, 'Tower >', 1.0); pick(h, label, gap)
def run_ui():
    """Looks UI gate: new level -> Tower > Colours / Enemies cycling (wrap), playtest shows the chosen palette + eyes, leave (commit), Save to disk,
    Load, Edit shows the flags again, Copy keeps them, Delete keeps the others, a new level starts with 0.  Then a playtest of the saved level."""
    import shutil, nebcampaign as nc
    D = '/tmp/looksgate/ui/'; shutil.rmtree(D, ignore_errors=True); os.makedirs(D); disk = D + 'camp.st'; shutil.copy('/tmp/looksgate/ne/d/blank.st', disk)
    open(D + 'zero.ovl', 'wb').write(bytes(8192))
    h = Nebulus(snapshot=SNAP, workdir=f'{WD}_ui', game=gd(GAMEDIR), **kw())
    try:
        time.sleep(2); h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        chk('ui: F10 opens the manager', open_manager(h))
        pick(h, 'Levels'); pick(h, '<new level>', 1.5)
        chk('ui: new level starts with flags 0', flag_byte(h), 0)
        seq = []
        for k in range(10):
            tower_menu(h, 'Colours: next'); seq.append(flag_byte(h) >> 4)
        chk('ui: Colours: next cycles 1..8 then wraps to 0 and 1 (10 presses)', seq, [1, 2, 3, 4, 5, 6, 7, 8, 0, 1])
        seq = []
        for k in range(6):
            tower_menu(h, 'Enemies: next'); seq.append(flag_byte(h) & 15)
        chk('ui: Enemies: next cycles 1..4 then wraps to 0 and 1 (6 presses), colours untouched', (seq, flag_byte(h) >> 4), ([1, 2, 3, 4, 0, 1], 1))
        for k in range(4): tower_menu(h, 'Colours: next')           # colours 1 -> 5
        for k in range(2): tower_menu(h, 'Enemies: next')           # enemies 1 -> 3
        chk('ui: flags = colours 5 / enemies 3 = $53', flag_byte(h), 0x53)
        h.shot(f'{D}02_panel_S5_E3.png')
        # a base tower of T3 (index 2) and a recognisable name: Look next x2
        for k in range(2):
            tower_menu(h, 'Look: next tower')
        chk('ui: base tower T3 (rsTow 2), flags unchanged', (W(h, RS + 14), flag_byte(h)), (2, 0x53))
        h.key('l', hold=0.2); time.sleep(0.4)
        # playtest
        h.key('Control_R', hold=0.35); time.sleep(1.0); pick(h, 'Playtest', 1.0)
        chk('ui: playtest running', wait_running(h, 90))
        time.sleep(2.0)
        pal = grab(h, 0x351ac, 32, 'p'); ras = grab(h, 0x40398, 8, 'r')
        chk('ui: playtest palette == stock tower 5 palette (colours 5)', pal, rdref(4, 0x351ac, 32))
        chk('ui: playtest raster == stock tower 5 raster', ras, rdref(4, 0x40398, 8))
        chk('ui: playtest skyline buffer == stock tower 5', grab(h, 0x100e0, 4096, 's'), rdref(4, 0x100e0, 4096))
        chk('ui: playtest eye frames == stock tower 3 eye design (enemies 3 -> design 2)', grab(h, 0x24be0, 0xaf00, 'e'), rdref(2, 0x24be0, 0xaf00))
        chk('ui: playtest base tower word $3390c = 2 (geometry/time/title follow the base tower)', W(h, 0x3390c), 2)
        h.shot(f'{D}03_playtest_colours5_enemies3_base3.png')
        h.key('F10', hold=0.4); time.sleep(2.0)                      # back to the editor
        chk('ui: back in the editor, flags still $53', (flag_byte(h), W(h, RS + 6)), (0x53, 1))
        h.key('F10', hold=0.4); time.sleep(1.5)                      # leave: commit
        ram = grab(h, 0xBC000, 8192, 'fl'); chk('ui: committed record flags', flags_of(ram), [0x53])
        chk('ui: store validates', ovl.validate(ram), [])
        h.key('Left', hold=0.2); time.sleep(1.2)
        h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        chk('ui: Save to campaign disk', save_load_disk(h, disk, 'Save to campaign disk'), 'Saved')
        h.cmd('hatari-option --disk-a /tmp/looksgate/ne/d/blank.st'); time.sleep(3.0)
        ok, text, data = nc.status(open(disk, 'rb').read()); chk('ui: saved disk usable', ok)
        chk('ui: saved file flags', flags_of(data), [0x53]); chk('ui: saved file == RAM store', data == ram)
        open(D + 'saved.ovl', 'wb').write(data)
        h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0])); h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        chk('ui: Load from campaign disk', save_load_disk(h, disk, 'Load from campaign disk'), 'Loaded 1 levels / 0 campaigns')
        chk('ui: reloaded flags', flags_of(grab(h, 0xBC000, 8192, 'fl')), [0x53])
        pick(h, 'Levels'); pick(h, 0); pick(h, 'Edit', 1.5)
        chk('ui: Edit shows the reloaded flags $53 (RS+50), base tower 2', (flag_byte(h), W(h, RS + 14)), (0x53, 2))
        h.shot(f'{D}04_edit_after_reload.png')
        h.key('F10', hold=0.4); time.sleep(1.5)
        pick(h, 0); pick(h, 'Copy', 1.5)
        chk('ui: Copy keeps the flags', flags_of(grab(h, 0xBC000, 8192, 'fl')), [0x53, 0x53])
        pick(h, '<new level>', 1.5); h.key('l', hold=0.2); time.sleep(0.4)
        chk('ui: new level starts with flags 0 again', flag_byte(h), 0)
        tower_menu(h, 'Enemies: next'); tower_menu(h, 'Enemies: next'); tower_menu(h, 'Enemies: next'); tower_menu(h, 'Enemies: next'); tower_menu(h, 'Enemies: next')
        tower_menu(h, 'Colours: next')
        chk('ui: third level: 5 Enemies presses wrap 0,1,2,3,4,0 and 1 Colours press = $10', flag_byte(h), 0x10)
        h.key('F10', hold=0.4); time.sleep(1.5)
        chk('ui: three records', flags_of(grab(h, 0xBC000, 8192, 'fl')), [0x53, 0x53, 0x10])
        pick(h, 0); pick(h, 'Delete', 1.5)
        chk('ui: Delete level 0 keeps the others', flags_of(grab(h, 0xBC000, 8192, 'fl')), [0x53, 0x10])
        h.key('Left', hold=0.2); time.sleep(1.2)
        pick(h, 'Levels'); pick(h, 1); pick(h, 'Play', 1.0)
        chk('ui: Play of the $11 level: tower running', wait_running(h, 90)); time.sleep(2.0)
        chk('ui: $10 (base T1, colours 1, enemies as base T1) = stock tower 1 palette + eyes', (grab(h, 0x351ac, 32, 'p'), grab(h, 0x24be0, 0xaf00, 'e')), (rdref(0, 0x351ac, 32), rdref(0, 0x24be0, 0xaf00)))
        chk('ui: no Address/Bus Error/exception in the Hatari log', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('ui: exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
run_ui()
print('FAILS', fails); open(f'/tmp/looksgate/logs/e190_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
