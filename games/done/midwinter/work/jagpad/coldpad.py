#!/usr/bin/env python3
"""Cold boot of an HD build (default set + jag) into the J-mode ski view and a full pad test.

  coldpad.py MACHINE [BUILD]      MACHINE: ste (1 MB TOS 1.62) | st (1 MB TOS 1.04) | megast | megaste (4 MB TOS 2.06) | tt (4 MB TOS 3.06, --mmu true)
Machines without pad ports only get the boot + probe checks.  Hatari pad A = host keys of pad.cfg (a held key = a held pad button).
"""
import re, sys, time
from jlib import *

mach = sys.argv[1]
BUILD = sys.argv[2] if len(sys.argv) > 2 else str(GAME / 'build' / 'jag')
cfg = {'ste': dict(machine='ste', memsize_kb=1024), 'st': dict(machine='st', memsize_kb=1024),
       'megast': dict(machine='megast', memsize_kb=1024), 'megaste': dict(machine='megaste', memsize_kb=4096),
       'tt': dict(machine='tt', memsize_kb=4096, extra=['--mmu', 'true']),
       'falcon': dict(machine='falcon', memsize_kb=4096)}[mach]
extra = (cfg.pop('extra', None) or []) + PAD
t0 = time.time()
h = MW1(snapshot=None, game_dir=BUILD, extra=extra, **cfg)
P = lambda *a: print(*a, flush=True)
S = Sampler(h, [(0xb6bf0, 8), (0x24f98, 8), (0x24fba, 2), (0x12c98, 2), (0x15110, 2), (0x15112, 2), (0x12d5e, 4),
                (0x1efde, 2), (0x2c324, 4), (0x2c176, 6), (0x24faa, 8), (0x24fa2, 8), (0xb2ff8, 4)])


def show(tag):
    r = S()
    pj = r[0xb6bf0]
    P(f"{tag:12s} vbl={r['vbl']} PADST={pj[0]:02x} PADJ={pj[1]:02x} BTN={pj[2]:02x} OLD={pj[4:8].hex()} "
      f"vec=({s32(int.from_bytes(r[0x24f98][:4],'big'))/65536:+.1f},{s32(int.from_bytes(r[0x24f98][4:],'big'))/65536:+.1f}) "
      f"$24fba={r[0x24fba].hex()} head={s16(int.from_bytes(r[0x12c98],'big'))} rate={s16(int.from_bytes(r[0x15110],'big'))} "
      f"speed={int.from_bytes(r[0x15112],'big')} step={r[0x12d5e].hex()} menu={r[0x1efde].hex()} key24={r[0x2c324].hex()} "
      f"acc=({s16(int.from_bytes(r[0x24faa][:2],'big'))},{s16(int.from_bytes(r[0x24faa][4:6],'big'))})")
    return r


def trace_keys(key, hold=1.5):
    """Per-VBL trace of the key table / last key while the pad button is held: counts makes and breaks."""
    cf = h.R / 'kt.txt'
    cf.write_text('e VBL\nm $2c29a 128\nm $2c324 4\n')
    h.debug('b all', 0.3)
    n = len(h._logtext())
    h.cmd(f'hatari-debug b pc = $b6900 :trace :file {cf}')
    time.sleep(0.4)
    kd(h, key); time.sleep(hold); ku(h, key); time.sleep(0.6)
    h.debug('b all', 0.3)
    out = h._logtext()[n:]
    prev = {}
    makes, breaks, nb, last = {}, {}, 0, None
    for blk in out.split('Reading debugger commands')[1:]:
        v = re.search(r'#(\d+) \(dec\)', blk)
        rows = re.findall(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', blk, re.M)
        if not v or len(rows) < 9:
            continue
        tab = {}
        for a, b in rows:
            a = int(a, 16)
            if a >= 0x2c29a and a < 0x2c29a + 128:
                for i, x in enumerate(b.split()):
                    tab[a + i - 0x2c29a] = int(x, 16)
        nb += 1
        if nb == 1:
            prev = tab          # the first block only sets the starting table (constant entries are not makes)
            continue
        for sc, val in tab.items():
            if val and not prev.get(sc):
                makes[sc] = makes.get(sc, 0) + 1
            if not val and prev.get(sc):
                breaks[sc] = breaks.get(sc, 0) + 1
        prev = tab
    P(f'  key {key:6s}: VBLs traced {nb}  makes { {hex(k): v for k, v in makes.items()} }  breaks { {hex(k): v for k, v in breaks.items()} }')
    return makes, breaks


try:
    P('config', mach, cfg, extra)
    h.boot_to_game('J', check=(mach not in ('tt', 'falcon')))
    P(f'boot_to_game J ok in {time.time() - t0:.0f} s, control mode {h.control_mode()}')
    time.sleep(2)
    r = show('after boot')
    P('MWPO marker:', r[0xb2ff8], ' sites:', h.peek(0x61e2, 8).hex(), h.peek(0x65e2, 6).hex(), h.peek(0x665e, 6).hex(), h.peek(0x6696, 6).hex())
    if mach in ('ste', 'falcon'):
        assert r[0xb6bf0][0] == 1, 'STE/Falcon: probe must say pad ports present'
        h.shot('/tmp/jag_cold_' + mach + '.png')
        DEV = {'pad': dict(left='left', right='right', up='up', down='down', fire='B', A='A'),
               'stick': dict(left='sleft', right='sright', up='sup', down='sdown', fire='sfire', A=None)}

        def ex(state, dev, fire=True):
            """the same input sequence from the pad or from the real stick (IKBD); one summary line"""
            k = DEV[dev]
            out = {}
            a = S(); kd(h, k['left']); time.sleep(2.0); b = S(); ku(h, k['left']); time.sleep(1.0); c = S()
            hd = lambda r: s16(int.from_bytes(r[0x12c98], 'big'))
            out['L'] = (hd(b) - hd(a), b['vbl'] - a['vbl'], s16(int.from_bytes(b[0x15110], 'big')), s32(int.from_bytes(b[0x24f98][:4], 'big')) / 65536,
                        s16(int.from_bytes(b[0x24faa][:2], 'big')))
            a = S(); kd(h, k['right']); time.sleep(2.0); b = S(); ku(h, k['right']); time.sleep(1.0)
            out['R'] = (hd(b) - hd(a), b['vbl'] - a['vbl'], s16(int.from_bytes(b[0x15110], 'big')), s32(int.from_bytes(b[0x24f98][:4], 'big')) / 65536,
                        s16(int.from_bytes(b[0x24faa][:2], 'big')))
            kd(h, k['up']); time.sleep(1.0); b = S(); ku(h, k['up']); time.sleep(0.8)
            out['U'] = (s32(int.from_bytes(b[0x24f98][4:], 'big')) / 65536, s16(int.from_bytes(b[0x24faa][4:6], 'big')))
            kd(h, k['down']); time.sleep(1.0); b = S(); ku(h, k['down']); time.sleep(0.8)
            out['D'] = (s32(int.from_bytes(b[0x24f98][4:], 'big')) / 65536, s16(int.from_bytes(b[0x24faa][4:6], 'big')))
            if not fire:
                P(f"  [{state:7s} {dev:5s}] L(dhead,dvbl,rate,vecx,accx)={out['L']} R={out['R']} U(vecy,accy)={out['U']} D={out['D']}")
                return out
            kd(h, k['fire']); time.sleep(0.8)
            fb = set(S()[0x24fba].hex() for _ in range(6))
            sp0 = int.from_bytes(S()[0x15112], 'big'); time.sleep(1.5); sp1 = int.from_bytes(S()[0x15112], 'big')
            ku(h, k['fire']); time.sleep(1.0)
            out['F'] = (sorted(fb), sp0, sp1, S()[0x24fba].hex())
            kd(h, 'A'); time.sleep(1.5); ku(h, 'A'); time.sleep(0.5)     # pad A = '>' = right button: stop walking, same start for the next run
            P(f"  [{state:7s} {dev:5s}] L(dhead,dvbl,rate,vecx,accx)={out['L']} R={out['R']} U(vecy,accy)={out['U']} D={out['D']} fire($24fba set,speed,speed+1.5s,after release)={out['F']}")
            return out

        # --- ski view: stick and pad in the same run
        show('ski idle')
        ex('ski', 'stick'); ex('ski', 'pad')
        kd(h, 'A'); time.sleep(1.5); show('hold A'); ku(h, 'A'); time.sleep(1.0); show('rel A')
        # --- the key buttons, one make per press
        trace_keys('C'); trace_keys('n3')
        trace_keys('pause', 2.0)
        P('  flips/50 VBL after the first pause press:', h.fps(50)['flips'])
        trace_keys('pause', 1.0)
        P('  flips/50 VBL after the second pause press:', h.fps(50)['flips'])
        # S: ski <-> snipe
        trace_keys('n2', 2.0); time.sleep(1); r = show('snipe?'); assert r[0x12d5e][2:] == bytes.fromhex('3f36'), r[0x12d5e].hex()
        ex('snipe', 'stick'); ex('snipe', 'pad')
        trace_keys('n2', 2.0); time.sleep(1); r = show('ski again?')
        # M: main map (a click-driven screen: CLOSE MAP with the mouse)
        trace_keys('n1', 2.0); time.sleep(1.5); show('map?'); h.shot('/tmp/jag_cold_map.png')
        h.click_at((612, 450), 3.0); show('map closed?')
        h.click(); time.sleep(3.0)          # the original needs a second click before the 3D view runs again (same without the patch)
        show('map closed'); P('  flips/50 VBL back in the ski view:', h.fps(50)['flips'])
        # buggy / glider step handlers forced (no save reaches them): turn path with the pad and with the stick
        for name, ptr in (('buggy', '$00 $01 $35 $9a'), ('glider', '$00 $01 $37 $3c')):
            h.debug('b all', 0.3)
            pokes = ['w $12d5e ' + ptr] + (['w $13598 $01 $04', 'w $14774 $00 $00'] if name == 'buggy' else [])
            app = h.R / 'poke.txt'; app.write_text('\n'.join(pokes) + '\n')
            n = len(h._logtext()); h.cmd(f'hatari-debug b pc = ${FLIP:x} :trace :once :file {app}')
            tt = time.time()
            while 'Removed CPU breakpoint' not in h._logtext()[n:] and time.time() - tt < 60:
                time.sleep(0.3)
            time.sleep(1.0)
            show(name + ' idle')
            ex(name, 'stick', fire=False); ex(name, 'pad', fire=False)
            ex(name, 'pad')          # fire last: the glider launches / the buggy drives and the action mode may end
            kd(h, 'C'); time.sleep(0.8); show(name + ' C'); ku(h, 'C'); time.sleep(0.5)
        # Option = X: leave the action mode
        trace_keys('opt', 1.5); time.sleep(1.5); show('after X')
    else:
        P('no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test')
        assert r[0xb6bf0][0] == 0xff, f'PADST = {r[0xb6bf0][0]:02x}'
        if mach not in ('tt', 'falcon'):
            cpv, pct, mine, totv = blob_cost(h, 100)
            P(f'cost without pad ports: {cpv:.1f} cycles/VBL in the blob (incl. the displaced calls\' jsr), {pct:.3f} % of the profiled cycles')
        # the game still runs: a pad key does nothing (no bus error, no input)
        kd(h, 'B'); time.sleep(1.0); r = show('B held'); ku(h, 'B')
        assert r[0xb6bf0][1:3] == b'\0\0', r[0xb6bf0].hex()
        h.shot('/tmp/jag_cold_' + mach + '.png')
finally:
    h.close()
P(f'total {time.time() - t0:.0f} s')
