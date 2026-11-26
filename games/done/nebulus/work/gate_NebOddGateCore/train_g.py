"""NebGateCore: trainers T/E on the shipped build, tower 1, STE 1 MB (TOS 1.62). usage: train_g.py [ste|megaste]"""
import sys, time, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus, TOS
machine = sys.argv[1] if len(sys.argv) > 1 else 'ste'
kw = {} if machine == 'ste' else dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096)
h = Nebulus(game='/tmp/oddcore/hd', workdir='/tmp/oddcore/train-' + machine, **kw)
def rd(a, n):
    o = h.debug(f'm ${a:x} {n}', 0.6); b = bytearray()
    for l in o.splitlines():
        m = re.match(r'^([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)', l, re.I)
        if m and int(m.group(1), 16) == a: b += bytes.fromhex(m.group(2).replace(' ', ''))
    return bytes(b[:n])
def W(a): return int.from_bytes(rd(a, 2), 'big')
def timer(): return tuple(rd(0x3ad98, 6)[1::2])
try:
    ok = h.boot_to_game(); print('boot_to_game', ok, 'timer', timer(), 'marker', rd(0xb0020,4), flush=True)
    time.sleep(1)
    print('before: frz', hex(W(0x76c02)), 'noen', hex(W(0x76c04)), 'states', [W(0x3398c+2*i) for i in range(4)], 'timer', timer())
    h.key('e', hold=0.5); time.sleep(2.0)
    print('after E: noen', hex(W(0x76c04)), 'frz', hex(W(0x76c02)), 'states', [W(0x3398c+2*i) for i in range(4)])
    t = [timer()]
    for i in range(3):
        time.sleep(2); t.append(timer())
    print('E on, timer over 6 s (alive, no input):', t, 'advancing', len(set(t)) == len(t))
    h.key('t', hold=0.5); time.sleep(1.5)
    print('after T: frz', hex(W(0x76c02)), 'noen', hex(W(0x76c04)))
    t = [timer()]
    for i in range(3):
        time.sleep(2); t.append(timer())
    print('T on, timer over 6 s:', t, 'FROZEN' if len(set(t)) == 1 else 'not frozen')
    h.key('t', hold=0.5); time.sleep(1.5)
    print('T again: frz', hex(W(0x76c02)))
    t = [timer()]; time.sleep(2.5); t.append(timer())
    print('T off, timer', t, 'running' if t[0] != t[1] else 'STILL FROZEN')
    h.key('e', hold=0.5); time.sleep(1.5)
    print('E again: noen', hex(W(0x76c04)))
finally:
    h.close()
