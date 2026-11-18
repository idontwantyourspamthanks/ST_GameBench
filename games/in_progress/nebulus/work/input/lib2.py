from lib import *
EXTRA = [('WALK','pc = $39d6a'), ('JUMP','pc = $39fc8'), ('JUMPB','pc = $39ffc'), ('SHOOT','pc = $3a2f8')]
BASE = ['VBL','POLL','FLIP','CONS','ACIA','STORE']
def tokens(txt, order):
    toks=[]
    for line in txt.splitlines():
        m=re.match(r'(\d+)\. CPU breakpoint', line)
        if m:
            i=int(m.group(1))-1
            toks.append(order[i] if i < len(order) else '?')
        elif line.lstrip().startswith('D0 ') and toks and toks[-1]=='STORE':
            toks[-1]='S%02x' % (int(line.split()[1],16)&0xff)
        elif line.startswith('= '):
            toks.append('<M%s>' % line.split('#')[1].split(' ')[0])
    return toks
def trial(h, actions, tail=0.8, names=BASE, extra=EXTRA):
    """actions: list of (host_sleep_before, ('down'|'up', keysym))  ; returns tokens"""
    order = arm(h, names, extra)
    time.sleep(0.2)
    n = len(h._logtext())
    h.cmd('hatari-debug e VBL')
    for dt, op, key in actions:
        time.sleep(dt)
        h._xdo('key'+op, '--window', h.win, key)
        h.cmd('hatari-debug e VBL')
    time.sleep(tail)
    h.cmd('hatari-debug e VBL')
    time.sleep(0.3)
    txt = h._logtext()[n:]
    h.debug('b all',0.3)
    return tokens(txt, order)
