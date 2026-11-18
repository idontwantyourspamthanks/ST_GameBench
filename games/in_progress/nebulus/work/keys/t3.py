"""Tap-loss trials on the shipped image. usage: t3.py OUT.json machine(ste|megaste) method(xdo|fifo) holds(ms,csv) trials pages(csv) [joy]"""
import sys, time, re, json, random
from kh import KH
from stharness import TOS
import os
IMG=os.environ.get('IMG','/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-18.img')
WD=os.environ.get('WD','/tmp/nf/t3')
out, mach, method, holds, trials, pages = sys.argv[1:7]
joy = len(sys.argv)>7 and sys.argv[7]=='joy'
holds=[int(x) for x in holds.split(',')]; trials=int(trials); pages=[int(x) for x in pages.split(',')]
key = os.environ.get('KEY','F10'); sc = int(os.environ.get('SC','68'))
if mach=='megaste': h=KH(IMG, workdir=WD, machine='megaste', tos=TOS['2.06'], mem=4096, cpu=8, auto=r'C:\NEBULUS\START.TOS', joy=joy)
else: h=KH(IMG, workdir=WD, auto=r'C:\NEBULUS\START.TOS', joy=joy)
print(' '.join(h.args))
def mark():
    return '48 69 67 68' in h.debug('m $3d00f 4',0.25)
while not mark(): time.sleep(1.5)
print('title', round(time.time()-h.t0))
time.sleep(1)
def w(a): return h.peekw(a)
def page(): return w(0x3d5b6)
def v70(): return h.peekl(0x70)
base70 = v70(); print('vbl vector', hex(base70))
def press(hold, k=key, s=sc):
    if method=='xdo':
        h._xdo('keydown', k); time.sleep(hold); h._xdo('keyup', k)
    elif method=='fifo1':
        h.cmd(f'hatari-event keypress {s}')
    else:
        h.cmd(f'hatari-event keydown {s}'); time.sleep(hold); h.cmd(f'hatari-event keyup {s}')
res = {}
log = []
def close_mgr():
    # leave manager with long F10 (xdotool, 0.6s), wait for game VBL vector
    for i in range(6):
        h._xdo('keydown','F10'); time.sleep(0.6); h._xdo('keyup','F10'); time.sleep(0.8)
        if v70()==base70: return True
    return False
for hold in holds:
  for pg in pages:
    ok=0
    for t in range(trials):
        # wait for page pg
        t0=time.time()
        while page()!=pg:
            if time.time()-t0>40: print('page timeout', pg); break
        c = w(0x3d5b8)
        time.sleep(random.uniform(0,0.3))
        p0 = page()
        press(hold/1000.0)
        time.sleep(0.7)
        o = v70()!=base70
        log.append((hold,pg,p0,c,o))
        print(f'hold {hold}ms page {pg} (was {p0} ctr {c}) trial {t}: {"OPEN" if o else "no"}', flush=True)
        if o:
            ok+=1
            if not close_mgr(): print('could not close manager'); h.shot('/tmp/nf/t3_stuck.png'); break
    res[f'{hold}ms/page{pg}']=ok
    print('RESULT', hold, pg, ok, '/', trials, flush=True)
json.dump({'res':res,'log':log}, open(out,'w'))
h.close()
