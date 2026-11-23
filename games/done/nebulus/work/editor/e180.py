"""Odd-aligned level records gate (NebOddFix, work/notes/editor.md 13.10).  Records are packed back to back, so a level with an odd number of
non-zero cells makes the next record start at an odd address; every reader must cope (68000: a word read at an odd address = address error).
For every file: loadbin it over the store $BC000 (rsOk = 0 forces the validation again), F10 opens the manager, the level list shows every level,
every level is started with Levels > n > Play (name at the tower intro via a breakpoint at $3d116 = the A0 the ed_name hook returns, grid vs the
decoded record, rows, mission/tower, initial time), Q back to the title, then every campaign: Play, first entry checked, entries forced one after the
other (door entry poked as in e33.py) with the same checks, until the game's own victory flow.  No Address/Bus Error/Illegal/Double fault in the log.
usage: e180.py GAMEDIR WORKDIR [ste|megaste|st] [file.ovl ...] [--snap FILE] [--nowalk] [--flow = the editor flow (c) instead of files] [--flags = the flags.b preservation gate] [--quick = start only the last and the first odd-start level of each file] [--disk = get each file into the store with Load from campaign disk (tools/nebcampaign.py new --ovl) instead of loadbin]   (default files: /tmp/ne/odd/*.ovl from mk_odd.py)"""
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
FILES = [a for a in args[2:] if a.endswith('.ovl')] or sorted(glob.glob('/tmp/ne/odd/*.ovl'))
SNAP = SNAP or f'/tmp/oddfix/title_{MACH}.sav'
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
if os.environ.get('SNAP_EXPECT'):                                  # freshness guard: hex bytes the snapshot of the build under test must contain (v1.2: 303900077cbe)
    assert bytes.fromhex(os.environ['SNAP_EXPECT']) in __import__('gzip').open(SNAP).read(), f'stale snapshot {SNAP}: {os.environ["SNAP_EXPECT"]} not found'
BP = '/tmp/oddfix/bp_name.txt'; os.makedirs('/tmp/oddfix', exist_ok=True); open(BP, 'w').write("m a0 16\n")

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
NOEN = 0x76c04                                                         # nt_trainers: 'E' toggles this word; a walk needs it SET before the tower starts (poked, not keyed: the key is racy and the first seconds with enemies on kill the player)
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
            zero = '/tmp/oddfix/zero8k.ovl'; open(zero, 'wb').write(bytes(8192)); h.debug(f'loadbin {zero} $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
            img = f'/tmp/oddfix/disk_{MACH}_{name[:-4]}.st'
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
            pick(h, 'Campaigns'); pick(h, c); n0 = len(open(h.R / 'log.txt', errors='replace').read())
            if c == 0 and WALK: poke(h, NOEN, bytes([0xff, 0xff]))        # walk: enemies off BEFORE the tower starts (nt_trainers noen cell)
            pick(h, 'Play', 1.0)
            check_start(h, tag + ' entry 0', dec(ents[0]), lvs, n0)
            if c == 0 and WALK and len(ents) > 1:
                chk(f'{tag}: enemies off (noen cell $76c04 = $ffff)', W(h, NOEN), 0xffff)
                last = len(ents) if full else min(2, len(ents) - 1)         # stress files: the first campaign's first 2 transitions only (a transition takes ~25 s)
                for k in range(1, last + 1):
                    n0 = len(open(h.R / 'log.txt', errors='replace').read()); wait_running(h, 30); force(h)
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
    D = '/tmp/oddfix/flow/'; shutil.rmtree(D, ignore_errors=True); os.makedirs(D); disk = D + 'camp.st'; shutil.copy('/tmp/ne/d/blank.st', disk)
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
        h.cmd('hatari-option --disk-a /tmp/ne/d/blank.st'); time.sleep(3.0)           # inserting another image makes Hatari write the saved one back (e161.py); h.cmd(f'hatari-option --disk-a {D}x.st') if False else None
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
def run_flags():
    """flags.b gate: three odd records with flags $ca/$35/$ff survive Edit + commit, Copy, Delete, a new level (flags 0), Save to disk and Load again"""
    import shutil, nebcampaign as nc
    D = '/tmp/oddfix/flags/'; shutil.rmtree(D, ignore_errors=True); os.makedirs(D); disk = D + 'camp.st'; shutil.copy('/tmp/ne/d/blank.st', disk)
    src = open('/tmp/ne/odd/flags35.ovl', 'rb').read(); open(D + 'zero.ovl', 'wb').write(bytes(8192))
    chk('flags: fixture flags', flags_of(src), [0xca, 0x35, 0xff])
    h = Nebulus(snapshot=SNAP, workdir=f'{WD}_flags', game=gd(GAMEDIR), **kw())
    try:
        time.sleep(2); h.debug(f'loadbin /tmp/ne/odd/flags35.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0]))
        chk('flags: F10 opens the manager', open_manager(h))
        pick(h, 'Levels'); pick(h, 1); pick(h, 'Edit', 1.5)
        chk('flags: Edit loads flags $35 into rsFlg (RS+50)', grab(h, RS + 50, 1, 'fl')[0], 0x35)
        h.key('p', hold=0.2); time.sleep(0.4); h.key('Right', hold=0.2); time.sleep(0.4); h.key('Up', hold=0.2); time.sleep(0.4); h.key('x', hold=0.2); time.sleep(0.4)
        h.key('F10', hold=0.4); time.sleep(1.5)                     # leave: commit
        ram = grab(h, 0xBC000, 8192, 'fl'); chk('flags: after Edit + commit', flags_of(ram), [0xca, 0x35, 0xff])
        a = ovl.parse(src)[0]; b = ovl.parse(ram)[0]
        chk('flags: edit changed the grid of level 1 only', [x['grid'] != y['grid'] for x, y in zip(a, b)], [False, True, False])
        chk('flags: level 1 mission/tower/time/name unchanged', [(l['mission'], l['tower'], l['time'], l['name']) for l in b], [(l['mission'], l['tower'], l['time'], l['name']) for l in a])
        chk('flags: store validates', ovl.validate(ram), [])
        pick(h, 'Levels', 1.0) if False else None
        pick(h, 1); pick(h, 'Copy', 1.5)                            # list: copy appended as level 3
        ram = grab(h, 0xBC000, 8192, 'fl'); chk('flags: after Copy of level 1', flags_of(ram), [0xca, 0x35, 0xff, 0x35])
        pick(h, 0); pick(h, 'Delete', 1.5)
        ram = grab(h, 0xBC000, 8192, 'fl'); chk('flags: after Delete of level 0', flags_of(ram), [0x35, 0xff, 0x35])
        pick(h, '<new level>', 1.5); h.key('l', hold=0.2); time.sleep(0.4)
        chk('flags: new level clears rsFlg', grab(h, RS + 50, 1, 'fl')[0], 0)
        h.key('F10', hold=0.4); time.sleep(1.5)
        ram = grab(h, 0xBC000, 8192, 'fl'); chk('flags: after a new level (flags 0)', flags_of(ram), [0x35, 0xff, 0x35, 0x00])
        chk('flags: store validates', ovl.validate(ram), [])
        h.key('Left', hold=0.2); time.sleep(1.2)
        h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        chk('flags: Save to campaign disk', save_load_disk(h, disk, 'Save to campaign disk'), 'Saved')
        h.cmd('hatari-option --disk-a /tmp/ne/d/blank.st'); time.sleep(3.0)           # inserting another image makes Hatari write the saved one back (e161.py)
        ok, text, data = nc.status(open(disk, 'rb').read()); chk('flags: saved disk usable', ok)
        chk('flags: saved file flags', flags_of(data), [0x35, 0xff, 0x35, 0x00]); chk('flags: saved file == RAM store', data == ram)
        h.debug(f'loadbin {D}zero.ovl $bc000', 0.8); poke(h, RS + 40, bytes([0, 0])); h.cmd(f'hatari-option --disk-a {disk}'); time.sleep(2.0)
        chk('flags: Load from campaign disk', save_load_disk(h, disk, 'Load from campaign disk'), 'Loaded 4 levels / 1 campaigns')
        chk('flags: reloaded store flags', flags_of(grab(h, 0xBC000, 8192, 'fl')), [0x35, 0xff, 0x35, 0x00])
        chk('flags: no Address/Bus Error/exception in the Hatari log', errors(h), [])
    except Exception as ex:
        import traceback; traceback.print_exc(); chk('flags: exception in the script', repr(ex)[:200], 'none')
    finally:
        h.close(); time.sleep(1)
if '--flags' in sys.argv: run_flags()
elif '--flow' in sys.argv: run_flow()
else:
    for f in FILES: run_file(f)
print('FAILS', fails); open(f'/tmp/e180_{MACH}.log', 'w').write('\n'.join(LOG) + f'\nFAILS {fails}\n')
