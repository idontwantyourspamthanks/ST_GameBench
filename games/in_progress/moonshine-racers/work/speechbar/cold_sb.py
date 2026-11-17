"""Cold boot of a build to the race (new HUD), then: strip check from the buffers (breakpoint dump at a pass), Hatari screenshot, rate windows at 0/16/32 MHz.
python3 coldhd.py MACHINE MEM TOS GAMEDIR TAG [clocks=0,16,32] [vbls=300]"""
import sys, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar')
from mxlib import *
from sbart import messages, draw_strip, planar_to_idx as p2i
import numpy as np, struct
from msr import Moonshine, GAME
from stharness import TOS
from emuhud import to_png
machine, mem, tos, game, tag = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5]
clocks = [int(x) for x in (sys.argv[6] if len(sys.argv) > 6 else '0,16,32').split(',')]
vbls = int(sys.argv[7]) if len(sys.argv) > 7 else 300
OUT = GAME / 'work/speechbar/shots'; OUT.mkdir(parents=True, exist_ok=True)
h = Moonshine(machine=machine, memsize_kb=mem, game_dir=GAME / game, tos=TOS[tos], extra=['--cpuclock', '8'] if machine in ('st', 'megast', 'ste', 'megaste') else [])   # 68000 machines always power on at 8 MHz; clocks below are raised after the boot (as play.sh does)
def rd(addr, n):
    out = h.debug(f"m ${addr:x} {n}", 0.7); g = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    return bytes(g[addr + i] for i in range(n))
w = lambda d, o: (d[o] << 8) | d[o + 1]
def sample():
    v = h.vbl(); b = rd(0xb8f38, 12)
    return dict(vbl=v, frames=(w(b, 0) << 16) | w(b, 2), pass_=h.peekw(0x100e), pos=h.peekw(0x5ff8))
TEXTS = {a: t for a, t in messages()}
def dump_check(name, N):
    cf = h.R / f'cap_{name}.txt'
    cf.write_text(f"savebin {OUT}/{name}_70000.bin $70000 $7d00\nsavebin {OUT}/{name}_78000.bin $78000 $7d00\nsavebin {OUT}/{name}_sb.bin $ba900 $40\nsavebin {OUT}/{name}_ram.bin $1000 $400\n")
    for f in OUT.glob(f'{name}_*.bin'): f.unlink()
    h.cmd(f"hatari-debug b pc = $7b86 && ($100e).w = ${N:x} :trace :once :file {cf}")
    t0 = time.time()
    while not (OUT / f'{name}_ram.bin').exists() and time.time() - t0 < 120: time.sleep(0.3)
    time.sleep(0.8)
    ram = (OUT / f'{name}_ram.bin').read_bytes(); full = bytes(0x1000) + ram + bytes(0x400 - len(ram))
    sb = (OUT / f'{name}_sb.bin').read_bytes(); res = []
    for k, bn in enumerate(('70000', '78000')):
        idx = p2i((OUT / f'{name}_{bn}.bin').read_bytes())
        BM, BN, FI = struct.unpack('>HHH', sb[16 * k:16 * k + 6])
        e = np.zeros((200, 320), np.uint8); draw_strip(e, TEXTS.get(BM) if BM else None, BN, FI if FI else None)
        bad = int((idx[16:42] != e[16:42]).sum()); sky = int((idx[42:65] != 15).sum()); bar = int((idx[0:16] == 15).sum())
        to_png(idx, str(OUT / f'{name}_{bn}.png'))
        res.append(f"${bn}: shadow (msg {BM:#x} chars {BN} face {FI:#x}) strip rows16-41 != model {bad}, non-sky pixels rows 42-64 {sky}")
    print(f"STRIP CHECK {name} pass>={N}: $100e={w(full, 0x100e)} $11ab={full[0x11ab]} " + " | ".join(res), flush=True)
try:
    ok = h.boot_to_race(log=lambda *a: None)
    print(f"{machine} {mem} KB TOS {tos} build {game}: boot_to_race {ok} vbl {h.vbl()}", flush=True)
    print("marker $b2700:", rd(0xb2700, 4), "stage site $ef7a:", rd(0xef7a, 6).hex(), "$edea:", rd(0xedea, 6).hex(), "sb sites $f90c:", rd(0xf90c, 6).hex(), "$f994:", rd(0xf994, 6).hex(), "$120a4:", rd(0x120a4, 4).hex(), "$12086:", rd(0x12086, 2).hex(), "palette A col 14 $3cf0:", rd(0x3cf0, 2).hex(), flush=True)
    h.keypress(57); time.sleep(8)
    for k in range(6):
        if h.peekb(0x1021) == 2 and h.peekw(0x100e) > 20: break
        h.keypress(57); time.sleep(5)
    print("race loop: $1021", h.peekb(0x1021), "$100e", h.peekw(0x100e), flush=True)
    h.shot(str(OUT / f'cold_{tag}_start.png'))
    dump_check(f'cold_{tag}_a', h.peekw(0x100e) + 40)
    h.drive(True)
    time.sleep(25)
    dump_check(f'cold_{tag}_b', h.peekw(0x100e) + 40)
    h.shot(str(OUT / f'cold_{tag}_drive.png'))
    print("palette A col 14 $3cf0:", rd(0x3cf0, 2).hex(), flush=True)
    magic = rd(0xc0000, 8); wptr = rd(0xd7040, 4); k135a = rd(0x135a, 4)
    print(f"ROAD TABLES: RDG1 magic $c0000 = {magic[:4]!r} PM $c0004 = {magic[4:6].hex()} WPTR $d7040 = {wptr.hex()} vs $135a = {k135a.hex()} -> {'OK' if magic[:4] == b'RDG1' and wptr == k135a and wptr != bytes(4) else 'FAIL'}; old addresses $d0000 = {rd(0xd0000, 4).hex()} $e7040 = {rd(0xe7040, 4).hex()} (must be 0)", flush=True)
    ini = rd(0xbf000, 12); print(f"TB_CAR INIT $bf000 = {ini[0]} (1 generated path on, 2 off) NENT $bf008 = {int.from_bytes(ini[8:10],'big')} POOLP $bf004 = {ini[4:8].hex()}  TC_CLR flag $b6ff0 = {rd(0xb6ff0,2).hex()}  sites: $17c24 {rd(0x17c24,6).hex()} $e406 {rd(0xe406,8).hex()} $39ac {rd(0x39ac,4).hex()}", flush=True)
    for mhz in clocks:
        if mhz: h.set_cpuclock(mhz); time.sleep(2)
        a = sample(); time.sleep(vbls / 50 * 1.3); b = sample()
        hz = 50 if (rd(0xff820a, 2)[0] & 2) else 60
        dv = b['vbl'] - a['vbl']; dp = (b['pass_'] - a['pass_']) & 0xffff; de = b['frames'] - a['frames']
        print(f"RESULT {machine} {mem} TOS {tos} clock {mhz or 'native'}: window {dv} VBL, passes {dp} ({dp*hz/dv:.3f}/s @{hz}Hz), extra frames {de}, displayed fps {(dp+de)*hz/dv:.3f}, $ff820a={rd(0xff820a,2).hex()}, pos {a['pos']}->{b['pos']}", flush=True)
    h.shot(str(OUT / f'cold_{tag}_end.png'))
    t0 = time.time(); p0 = (h.peekw(0x100e), h.peekw(0x5ff8)); n = 0
    while time.time() - t0 < 120:
        time.sleep(9); n += 1; dump_check(f'cold_{tag}_p{n}', (h.peekw(0x100e) + 30) & 0xffff); p1 = (h.peekw(0x100e), h.peekw(0x5ff8), h.peekb(0x1021))
        print(f"PLAY {int(time.time() - t0)}s: $100e={p1[0]} pos={p1[1]} $1021={p1[2]} VBL {h.vbl()}", flush=True)
    log = h._logtext()
    print(f"PLAY DONE: {int(time.time() - t0)} s at {clocks[-1] or 'native'} MHz, $1021={h.peekb(0x1021)}, magic {rd(0xc0000, 4)!r}, Bus/Address Error lines in the log: {len(re.findall('Bus Error|Address Error', log))}, hatari alive: {h.proc.poll() is None}", flush=True)
    ini = rd(0xbf000, 12); print(f"TB_CAR at end: INIT {ini[0]} NENT {int.from_bytes(ini[8:10],'big')} POOLP {ini[4:8].hex()}", flush=True)
finally:
    h.close()
