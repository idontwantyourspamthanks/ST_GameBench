"""Short-press registration: random hold 0..60 ms (xdotool), standing, fire. baseline vs sticky latch (live-patched stubs)."""
import sys, json
from tr import *
STUBS = [
 # stub1 @ $860: store byte; if (byte & $f0) == $80 -> sticky($8f0)=1; continue at $3851a
 'w $860 $13 $c0 $00 $03 $84 $98 $02 $00 $00 $f0 $0c $00 $00 $80 $66 $06 $31 $fc $00 $01 $08 $f0 $4e $f9 $00 $03 $85 $1a',
 # stub2 @ $880: d1 |= sticky; sticky=0; move.w d1,$338f0.l ; rts
 'w $880 $4a $78 $08 $f0 $67 $08 $32 $3c $00 $01 $42 $78 $08 $f0 $33 $c1 $00 $03 $38 $f0 $4e $75',
 # hooks
 'w $38514 $4e $f9 $00 $00 $08 $60',
 'w $3855a $4e $b9 $00 $00 $08 $80',
]
def go(tag, n, mhz, latch, seed=5):
    h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
    rnd = random.Random(seed); runs=[]
    try:
        time.sleep(1.5)
        if mhz != 8: h.set_cpuclock(mhz)
        time.sleep(1.0)
        if latch:
            print(h.debug('m $84c 180', 0.4)[:200])
            for c in STUBS: h.debug(c, 0.3)
            print(h.debug('m $860 16', 0.3), h.debug('m $38514 6',0.3), h.debug('m $3855a 6',0.3))
        for k in range(n):
            for _ in range(15):
                if h.peekw(0x33a20) == 0: break
                time.sleep(0.4)
            time.sleep(rnd.uniform(0.2, 0.5))
            hold = rnd.uniform(0.0, 0.06)
            order = arm(h, ['POLL','STORE','ACIA'], [('SHOOT','pc = $3a2f8')])
            n0 = len(h._logtext())
            marker(h)
            h._xdo('keydown','--window',h.win,'Control_R')
            time.sleep(hold)
            h._xdo('keyup','--window',h.win,'Control_R')
            marker(h)
            time.sleep(0.9)
            marker(h); time.sleep(0.4)
            txt = h._logtext()[n0:]
            h.debug('b all', 0.3)
            runs.append({'hold': hold, 'ev': parse(txt, order, 1)})
            print(tag, k, round(hold*1000), len(runs[-1]['ev']), flush=True)
    finally:
        h.close()
    json.dump(runs, open(f'raw_{tag}.json','w'))
if __name__=='__main__':
    go(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]=='latch')
