"""1-frame pulse of the joystick fire cell $38498: press at VBL entry N, release at VBL entry N+1.
The game polls at line 263 of every even-numbered VBL frame.  'miss': pulse covers frames N=odd -> no poll sees it (poll at end of frame N+1
happens after the release). 'cover': N=even -> the poll (end of frame N) sees it.  latch: stubs installed + sticky set by the poke (stub1's effect)."""
import sys
from short import STUBS
from tr import *
def run(latch, phase, n=3):
    h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
    res=[]
    try:
        time.sleep(1.5)
        if latch:
            for c in STUBS: h.debug(c, 0.3)
        R = h.R
        for k in range(n):
            for _ in range(15):
                if h.peekw(0x33a20) == 0: break
                time.sleep(0.4)
            time.sleep(0.5)
            (R/'p.txt').write_text('e VBL\n')
            h.debug('b all', 0.3)
            n0 = len(h._logtext())
            h.cmd(f'hatari-debug b pc = $3853a :trace :once :file {R/"p.txt"}'); time.sleep(0.6)
            txt = h._logtext()[n0:]
            pv = int(re.findall(r'#(\d+) \(dec\)', txt)[-1])          # VBL number of a poll (even frame)
            N = pv + 150 + (0 if phase=='miss' else 1)
            (R/'press.txt').write_text('w $38498 $80\n' + ('w $8f0 $00 $01\n' if latch else '') + 'e VBL\ne FrameCycles\n')
            (R/'rel.txt').write_text('w $38498 $00\ne VBL\ne FrameCycles\n')
            h.debug('b all', 0.3)
            n1 = len(h._logtext())
            h.cmd(f'hatari-debug b pc = $3a2f8 :trace'); time.sleep(0.15)
            h.cmd(f'hatari-debug b VBL > {N} && pc = $382d8 :trace :once :file {R/"press.txt"}'); time.sleep(0.15)
            h.cmd(f'hatari-debug b VBL > {N+1} && pc = $382d8 :trace :once :file {R/"rel.txt"}'); time.sleep(0.15)
            time.sleep(4.5)
            txt = h._logtext()[n1:]
            h.debug('b all', 0.3)
            shoot = bool(re.search(r'\d+\. CPU breakpoint condition\(s\) matched \d+ times\.\n\tpc = \$3a2f8', txt))
            pr = re.findall(r'#(\d+) \(dec\)', txt)
            res.append(shoot); print(latch, phase, k, 'N=%d'%N, 'press/release stamps', pr[:4], 'registered' if shoot else 'LOST', flush=True)
            time.sleep(1.0)
    finally:
        h.close()
    return res
if __name__=='__main__':
    for latch, phase in ((False,'miss'),(True,'miss'),(True,'cover')):
        print('RESULT latch=%s phase=%s'%(latch,phase), run(latch, phase))
