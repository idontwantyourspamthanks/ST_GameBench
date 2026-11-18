"""End-to-end input latency v2: host key (xdotool) -> first *presented* change, counted in VBLs/flips.
tokens: VBL, TICK, WAIT, POLL, CONS, ACIA, S<xx> (byte stored to $38498), F<state hex> (flip with player state), <Mn> marker."""
import sys, json, random, statistics
from lib import *
EV.update({'TICK': 'pc = $382c0', 'WAIT': 'pc = $3868a', 'FLIP': 'pc = $3868e'})
NAMES = ['VBL','TICK','WAIT','POLL','CONS','ACIA','STORE','FLIP']

def trace(h, actions, tail=0.9, names=NAMES, extra=()):
    h.debug('b all', 0.3)
    order=[]
    (h.R/'r.txt').write_text('r\n'); (h.R/'s.txt').write_text('m $33a16 14\n')
    for n in names:
        f = ''
        if n=='STORE': f=f' :file {h.R/"r.txt"}'
        if n=='FLIP': f=f' :file {h.R/"s.txt"}'
        h.cmd(f'hatari-debug b {EV[n]} :trace{f}'); order.append(n); time.sleep(0.15)
    for n,c in extra:
        h.cmd(f'hatari-debug b {c} :trace'); order.append(n); time.sleep(0.15)
    time.sleep(0.2)
    n0 = len(h._logtext())
    h.cmd('hatari-debug e VBL')
    for dt, op, key in actions:
        time.sleep(dt)
        h._xdo('key'+op, '--window', h.win, key)
        h.cmd('hatari-debug e VBL')
    time.sleep(tail)
    h.cmd('hatari-debug e VBL'); time.sleep(0.3)
    txt = h._logtext()[n0:]
    h.debug('b all', 0.3)
    toks=[]
    for line in txt.splitlines():
        m=re.match(r'(\d+)\. CPU breakpoint', line)
        if m:
            i=int(m.group(1))-1; toks.append(order[i] if i<len(order) else '?'); continue
        if line.lstrip().startswith('D0 ') and toks and toks[-1]=='STORE':
            toks[-1]='S%02x'%(int(line.split()[1],16)&0xff); continue
        m=re.match(r'00033A16:\s+((?:[0-9a-f]{2} )+)', line, re.I)
        if m and toks and toks[-1]=='FLIP':
            toks[-1]='F'+m.group(1).replace(' ','')[:28]; continue
        if line.startswith('= '):
            toks.append('<M%s>'%line.split('#')[1].split(' ')[0])
    return toks

def fields(f):   # F + 14 bytes hex -> dict
    b = bytes.fromhex(f[1:])
    w = [int.from_bytes(b[i:i+2],'big') for i in range(0,14,2)]
    return dict(x=w[0], y=w[1], face=w[3], step=w[4], state=w[5], pose=w[6])

def analyze(toks, what):
    """what='fire' -> first flip whose state/pose differs from the pre-injection flip & state!=0 or pose change;
       what='right' -> first flip whose x ($33a16) differs."""
    i0 = next((i for i,t in enumerate(toks) if t.startswith('<M')), None)
    if i0 is None: return None
    try: j = next(i for i,t in enumerate(toks) if i>i0 and t.startswith('<M')); 
    except StopIteration: j=len(toks)
    pre = [t for t in toks[:i0] if t.startswith('F')]
    base = fields(pre[-1]) if pre else None
    vbl=0; res={}
    for t in toks[i0+1:j]:
        if t=='VBL': vbl+=1
        elif t.startswith('S') and len(t)==3:
            if t=='S80' or t=='S88' or t=='S08' or t=='S84' or t=='S01' or t=='S08': res.setdefault('joy', vbl)
        elif t=='POLL': res['lastpoll']=vbl
        elif t.startswith('F') and base is not None:
            f=fields(t)
            ch = (f['x']!=base['x']) if what=='right' else (f['state']!=base['state'] or f['pose']!=base['pose'])
            if ch and 'vis' not in res:
                res['vis']=vbl; res['poll']=res.get('lastpoll')
    res['t_end']=vbl
    return res
