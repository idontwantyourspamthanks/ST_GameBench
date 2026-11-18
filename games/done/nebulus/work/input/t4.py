from lib import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2a')
def run(label, cmds, wait=0.6):
    order = arm(h, ['VBL','ACIA','STORE','POLL'])
    time.sleep(0.2)
    n = len(h._logtext())
    for c in cmds:
        h.cmd(c); 
    h.cmd('hatari-debug e VBL')
    time.sleep(wait)
    h.cmd('hatari-debug e VBL')
    time.sleep(0.3)
    txt = h._logtext()[n:]
    h.debug('b all',0.3)
    toks=[]
    for line in txt.splitlines():
        m=re.match(r'(\d+)\. CPU breakpoint', line)
        if m: toks.append(order[int(m.group(1))-1])
        elif line.startswith('= '): toks.append('<'+line.split('#')[1].split(' ')[0]+'>')
    print(label, ' '.join(toks))
    print('  $38498=', h.debug('m $38498 1',0.4).splitlines()[1] if True else '')
try:
    time.sleep(1.5)
    run('idle', [])
    run('keypress 29', ['hatari-event keypress 29'])
    run('keypress Control_R', ['hatari-event keypress Control_R'])
    run('keypress 57', ['hatari-event keypress 57'])
    run('keydown ctrl_r', ['hatari-event keydown Control_R'], 0.6)
    run('keyup ctrl_r', ['hatari-event keyup Control_R'], 0.6)
finally:
    h.close()
