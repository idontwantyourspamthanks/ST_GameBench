"""Fix B gate with the real shipped code, cold-booted build dir.
Part 1: 20 real short key taps (xdotool, hold 0..60 ms): did stub1 latch (pc=$76d14), did stub2 consume it (pc=$76d2e), did fire reach the stand-fire handler.
Part 2: 1-frame pulse through the real ACIA path: the first real byte of the tap (RCtrl make $1d) is rewritten to $80 at pc=$38514 (debugger `r d0=$80`), the
next real byte ($80, the joystick packet one frame later) to $00 => the cell sees $80 for exactly one frame, delivered by the patched ACIA/stub code.
usage: realpulse.py <build dir> <tag> <n1> <n2>"""
import sys, json, time, re, random
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus
from tr import arm, marker, parse
def main(build, tag, n1, n2):
    h = Nebulus(game=Path(build), workdir=f'/tmp/strun-nin2g{tag}')
    rnd = random.Random(4); res = {'taps': [], 'pulses': []}; raw_dbg = []
    try:
        ok = h.boot_to_game(); print('in tower', ok)
        for c in ('w $3792c $4e $75', 'w $3398c 0 0 0 0 0 0 0 0', 'w $3b0aa $60'): h.debug(c, 0.2)
        R = h.R
        def wait_idle():
            for _ in range(20):
                try:
                    if h.peekw(0x33a20) == 0: return
                except IndexError:
                    pass
                time.sleep(0.4)
        extra = [('LATCH', 'pc = $76d14'), ('CONSUME', 'pc = $76d2e'), ('SHOOT', 'pc = $3a2f8')]
        for k in range(n1):
            wait_idle(); time.sleep(rnd.uniform(0.2, 0.5))
            hold = rnd.uniform(0, 0.06)
            order = arm(h, ['POLL', 'STORE'], extra); n0 = len(h._logtext()); marker(h)
            h._xdo('keydown', '--window', h.win, 'Control_R'); time.sleep(hold); h._xdo('keyup', '--window', h.win, 'Control_R')
            time.sleep(1.2); marker(h); time.sleep(0.3)
            txt = h._logtext()[n0:]; h.debug('b all', 0.3)
            ev = parse(txt, order, 1)
            names = [e['n'] for e in ev if e['n'] != 'M']
            sticky = h.peekw(0x76d00)
            r = {'hold_ms': round(hold * 1000), 'stores': [('%02x' % e['d0']) for e in ev if e['n'] == 'STORE'],
                 'latch_set': names.count('LATCH'), 'consumed': names.count('CONSUME'), 'shoot': names.count('SHOOT'), 'sticky_after': sticky}
            res['taps'].append(r); print('tap', k, r, flush=True)
        for k in range(n2):
            wait_idle(); time.sleep(rnd.uniform(0.2, 0.5))
            (R / 'subC.txt').write_text('r d0=$00\ne VBL\ne FrameCycles\n')
            (R / 'subBx.txt').write_text(f'b pc = $38514 :once :trace :file {R}/subC.txt\n')
            (R / 'subA.txt').write_text(f'r d0=$80\ne VBL\ne FrameCycles\nb pc = $38508 :once :trace :file {R}/subBx.txt\n')
            order = arm(h, ['POLL'], extra); n0 = len(h._logtext())
            h.cmd(f'hatari-debug b pc = $38514 :once :trace :file {R}/subA.txt'); time.sleep(0.2)
            marker(h)
            h._xdo('keydown', '--window', h.win, 'Control_R'); time.sleep(0.05); h._xdo('keyup', '--window', h.win, 'Control_R')
            time.sleep(1.2); marker(h); time.sleep(0.3)
            txt = h._logtext()[n0:]; h.debug('b all', 0.3)
            # raw: A = first "> r d0=$80" block time, B = "> r d0=$00" block time
            def stamp(cmd):
                i = txt.find('> ' + cmd)
                if i < 0: return None
                m = re.search(r'> e VBL\n= .*?#(\d+) \(dec\)\n> e FrameCycles\n= .*?#(\d+) \(dec\)', txt[i:], re.S)
                return (int(m.group(1)), int(m.group(2))) if m else None
            A, B = stamp('r d0=$80'), stamp('r d0=$00'); raw_dbg.append(txt) if A is None else None
            ev = parse(txt, order, 1)
            polls = [(e['vbl'], e['fc']) for e in ev if e['n'] == 'POLL']
            T = lambda x: x[0] * 160256 + x[1]
            inside = [p for p in polls if A and B and T(A) < T(p) < T(B)]
            names = [e['n'] for e in ev if e['n'] != 'M']
            r = {'A': A, 'B': B, 'gap_frames': round((T(B) - T(A)) / 160256, 2) if A and B else None, 'polls_inside': len(inside),
                 'latch_set': names.count('LATCH'), 'consumed': names.count('CONSUME'), 'shoot': names.count('SHOOT')}
            res['pulses'].append(r); print('pulse', k, r, flush=True)
    finally:
        h.close()
    json.dump(res, open(f'real_{tag}.json', 'w')); open(f'real_{tag}.dbg', 'w').write('\n=====\n'.join(raw_dbg))
if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]))
